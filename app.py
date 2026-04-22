"""
app.py
─────────────────────────────────────────────────────────────────────────────
Sacred Lunar Calendar — Flask API server for Railway deployment.

Endpoints:
  POST /generate      — generate a calendar (JSON body, returns HTML/PDF)
  POST /shopify/order — Shopify order webhook (triggers generation + email)
  GET  /health        — health check
─────────────────────────────────────────────────────────────────────────────
"""

import datetime
import hashlib
import hmac
import json
import os
import tempfile
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_file, abort

from generate_calendar import generate

app = Flask(__name__)

# ── Config from environment ───────────────────────────────────────────────────

ANTHROPIC_API_KEY     = os.environ.get('ANTHROPIC_API_KEY', '')
SHOPIFY_WEBHOOK_SECRET = os.environ.get('SHOPIFY_WEBHOOK_SECRET', '')
EMAIL_FROM            = os.environ.get('EMAIL_FROM', 'hello@bathhaus.com')
SENDGRID_API_KEY      = os.environ.get('SENDGRID_API_KEY', '')
OUTPUT_DIR            = os.environ.get('OUTPUT_DIR', '/tmp/calendars')

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


# ── Health check ──────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'sacred-lunar-calendar'})


# ── /generate — direct API call ───────────────────────────────────────────────

@app.route('/generate', methods=['POST'])
def generate_calendar():
    """
    Generate a personalized calendar.

    Request JSON:
    {
      "name":        "Mandana",
      "birth_date":  "1986-09-18",
      "birth_time":  "12:01",
      "birth_lat":   34.0522,
      "birth_lon":   -118.2437,
      "year":        2026,
      "month":       3,
      "format":      "html"   // or "pdf"
    }

    Returns: the HTML or PDF file directly (Content-Disposition: attachment)
    """
    data = request.get_json(force=True)

    # Validate required fields
    required = ['name', 'birth_date', 'birth_time', 'birth_lat', 'birth_lon', 'year', 'month']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing fields: {missing}'}), 400

    try:
        birth_date = datetime.date.fromisoformat(data['birth_date'])
        h, m = map(int, data['birth_time'].split(':'))
        birth_time = datetime.time(h, m)
    except (ValueError, KeyError) as e:
        return jsonify({'error': f'Invalid date/time format: {e}'}), 400

    fmt = data.get('format', 'html').lower()
    to_pdf = (fmt == 'pdf')

    try:
        result = generate(
            name=data['name'],
            birth_date=birth_date,
            birth_time=birth_time,
            birth_lat=float(data['birth_lat']),
            birth_lon=float(data['birth_lon']),
            year=int(data['year']),
            month=int(data['month']),
            api_key=ANTHROPIC_API_KEY,
            output_dir=OUTPUT_DIR,
            to_pdf=to_pdf,
            mock_claude=not bool(ANTHROPIC_API_KEY),
        )
    except Exception as e:
        app.logger.error(f'Generation error: {e}')
        return jsonify({'error': str(e)}), 500

    file_path = result.get('pdf') if to_pdf else result.get('html')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File generation failed'}), 500

    mimetype = 'application/pdf' if to_pdf else 'text/html'
    ext = 'pdf' if to_pdf else 'html'
    filename = f"{data['name'].lower().replace(' ','_')}_lunar_calendar_{data['year']}_{data['month']:02d}.{ext}"

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


# ── /shopify/order — Shopify webhook ─────────────────────────────────────────

@app.route('/shopify/order', methods=['POST'])
def shopify_order_webhook():
    """
    Receives Shopify 'orders/paid' webhook.

    Shopify sends order data as JSON. Bath Haus collects birth data via
    line item properties or order note attributes at checkout.

    Expected birth data fields (from order.note_attributes or line_item.properties):
      - birth_name     (string)
      - birth_date     (YYYY-MM-DD)
      - birth_time     (HH:MM, 24h)
      - birth_city     (string, optional — used to resolve lat/lon)
      - birth_lat      (float, optional if birth_city provided)
      - birth_lon      (float, optional if birth_city provided)
      - calendar_month (integer, optional — defaults to next month)
      - calendar_year  (integer, optional — defaults to current year)
    """

    # ── Verify Shopify HMAC signature ────────────────────────────────────────
    if SHOPIFY_WEBHOOK_SECRET:
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256', '')
        body = request.get_data()
        computed = hmac.new(
            SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).digest()
        import base64
        computed_b64 = base64.b64encode(computed).decode('utf-8')
        if not hmac.compare_digest(computed_b64, hmac_header):
            app.logger.warning('Invalid Shopify HMAC signature')
            abort(401)

    order = request.get_json(force=True)
    order_id = order.get('id', 'unknown')
    customer_email = order.get('email', '')

    app.logger.info(f'Order received: #{order_id} — {customer_email}')

    # ── Extract birth data from order ────────────────────────────────────────
    birth_data = _extract_birth_data(order)
    if not birth_data:
        app.logger.warning(f'Order #{order_id}: no birth data found — skipping calendar generation')
        return jsonify({'status': 'skipped', 'reason': 'no birth data'}), 200

    # ── Resolve coordinates if only city provided ────────────────────────────
    if 'birth_lat' not in birth_data and 'birth_city' in birth_data:
        coords = _geocode_city(birth_data['birth_city'])
        if coords:
            birth_data['birth_lat'], birth_data['birth_lon'] = coords
        else:
            app.logger.warning(f'Could not geocode city: {birth_data["birth_city"]}')
            return jsonify({'status': 'error', 'reason': 'could not geocode birth city'}), 200

    # ── Determine calendar month ──────────────────────────────────────────────
    today = datetime.date.today()
    cal_year  = int(birth_data.get('calendar_year',  today.year))
    cal_month = int(birth_data.get('calendar_month', today.month + 1 if today.month < 12 else 1))

    # ── Run generation async (don't block Shopify's 5s timeout) ──────────────
    def _generate_and_email():
        try:
            result = generate(
                name=birth_data['birth_name'],
                birth_date=datetime.date.fromisoformat(birth_data['birth_date']),
                birth_time=datetime.time(*map(int, birth_data['birth_time'].split(':'))),
                birth_lat=float(birth_data['birth_lat']),
                birth_lon=float(birth_data['birth_lon']),
                year=cal_year,
                month=cal_month,
                api_key=ANTHROPIC_API_KEY,
                output_dir=OUTPUT_DIR,
                to_pdf=True,
            )
            if result.get('pdf') and customer_email:
                _send_calendar_email(
                    to_email=customer_email,
                    customer_name=birth_data['birth_name'],
                    pdf_path=result['pdf'],
                    year=cal_year,
                    month=cal_month,
                    order_id=order_id,
                )
                app.logger.info(f'Order #{order_id}: calendar sent to {customer_email}')
        except Exception as e:
            app.logger.error(f'Order #{order_id}: generation failed — {e}')

    thread = threading.Thread(target=_generate_and_email, daemon=True)
    thread.start()

    return jsonify({'status': 'accepted', 'order_id': order_id}), 200


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_birth_data(order: dict) -> dict | None:
    """
    Extract birth data from Shopify order.
    Checks: note_attributes → line item properties → order note (fallback).

    Shopify note_attributes format:
      [{"name": "birth_date", "value": "1986-09-18"}, ...]
    """
    data = {}

    # 1. Check order note_attributes (set via checkout customization)
    for attr in order.get('note_attributes', []):
        key = attr.get('name', '').lower().replace(' ', '_')
        val = attr.get('value', '').strip()
        if key and val:
            data[key] = val

    # 2. Check line item properties (set via product page JS)
    for line_item in order.get('line_items', []):
        for prop in line_item.get('properties', []):
            key = prop.get('name', '').lower().replace(' ', '_')
            val = prop.get('value', '').strip()
            if key and val:
                data.setdefault(key, val)  # note_attributes take priority

    # Require minimum fields to proceed
    required = ['birth_name', 'birth_date', 'birth_time']
    has_location = ('birth_lat' in data and 'birth_lon' in data) or 'birth_city' in data

    if not all(k in data for k in required) or not has_location:
        return None

    return data


def _geocode_city(city: str) -> tuple[float, float] | None:
    """Resolve city name to (lat, lon) using geopy."""
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent='bath-haus-lunar-calendar')
        location = geolocator.geocode(city, timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        app.logger.warning(f'Geocoding error for {city}: {e}')
    return None


def _send_calendar_email(
    to_email: str,
    customer_name: str,
    pdf_path: str,
    year: int,
    month: int,
    order_id: str,
) -> None:
    """
    Send the generated PDF calendar via SendGrid.
    Falls back to logging if SendGrid is not configured.
    """
    month_name = datetime.date(year, month, 1).strftime('%B %Y')

    if not SENDGRID_API_KEY:
        app.logger.info(
            f'[EMAIL SKIPPED — no SENDGRID_API_KEY] '
            f'Would send {month_name} calendar to {to_email}'
        )
        return

    try:
        import sendgrid
        from sendgrid.helpers.mail import (
            Mail, Attachment, FileContent, FileName,
            FileType, Disposition
        )
        import base64

        with open(pdf_path, 'rb') as f:
            pdf_data = base64.b64encode(f.read()).decode('utf-8')

        message = Mail(
            from_email=EMAIL_FROM,
            to_emails=to_email,
            subject=f'Your Sacred Lunar Calendar — {month_name}',
            html_content=_email_body(customer_name, month_name),
        )
        attachment = Attachment(
            FileContent(pdf_data),
            FileName(f'sacred_lunar_calendar_{year}_{month:02d}.pdf'),
            FileType('application/pdf'),
            Disposition('attachment'),
        )
        message.attachment = attachment

        sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        app.logger.info(f'SendGrid response: {response.status_code}')

    except Exception as e:
        app.logger.error(f'Email send failed: {e}')


def _email_body(name: str, month_name: str) -> str:
    first_name = name.split()[0]
    return f"""
    <div style="font-family: 'Georgia', serif; max-width: 600px; margin: 0 auto;
                color: #3a3a2e; background: #faf9f6; padding: 48px 32px;">
      <div style="text-align: center; margin-bottom: 40px;">
        <p style="font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase;
                  color: #7a8c6e; margin: 0;">Bath Haus</p>
        <h1 style="font-size: 26px; font-weight: 400; margin: 12px 0 0;
                   letter-spacing: 0.04em;">Your Sacred Lunar Calendar</h1>
        <p style="color: #7a8c6e; margin: 8px 0 0;">{month_name}</p>
      </div>

      <p style="line-height: 1.8; font-size: 16px;">Dear {first_name},</p>
      <p style="line-height: 1.8; font-size: 16px;">
        Your personalized Sacred Lunar Calendar for {month_name} is attached —
        woven from the specific positions of the sky at the moment of your birth.
      </p>
      <p style="line-height: 1.8; font-size: 16px;">
        Inside you'll find your monthly transmission, key dates and their personal
        significance for your chart, and bath rituals timed to the lunar phases.
      </p>
      <p style="line-height: 1.8; font-size: 16px;">
        May this month's waters carry you home.
      </p>
      <p style="line-height: 1.8; font-size: 16px; color: #7a8c6e; margin-top: 40px;">
        With love,<br/>
        <em>Bath Haus</em>
      </p>
    </div>
    """


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
