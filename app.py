"""
app.py
─────────────────────────────────────────────────────────────────────────────
Sacred Lunar Calendar — Flask API server (Railway deployment).

Endpoints:
  POST /generate        — generate 1 or 12 months (JSON body)
  POST /shopify/order   — Shopify orders/paid webhook
  GET  /health          — health check

New in this version:
  • utc_offset / timezone support (correct Rising sign for all customers)
  • 12-month plan: generates all 12 months, emails as ZIP of PDFs
  • Optional intention field woven into Claude content
─────────────────────────────────────────────────────────────────────────────
"""

import base64
import datetime
import hashlib
import hmac
import json
import os
import tempfile
import threading
import zipfile
from pathlib import Path

from flask import Flask, request, jsonify, send_file, abort

from generate_calendar import generate, generate_annual

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY      = os.environ.get('ANTHROPIC_API_KEY', '')
SHOPIFY_WEBHOOK_SECRET = os.environ.get('SHOPIFY_WEBHOOK_SECRET', '')
EMAIL_FROM             = os.environ.get('EMAIL_FROM', 'hello@bathhaus.com')
SENDGRID_API_KEY       = os.environ.get('SENDGRID_API_KEY', '')
OUTPUT_DIR             = os.environ.get('OUTPUT_DIR', '/tmp/calendars')

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


# ── Health ────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'sacred-lunar-calendar'})


# ── /generate ─────────────────────────────────────────────────────────────────

@app.route('/generate', methods=['POST'])
def generate_calendar():
    """
    Generate a personalized calendar — 1 month or 12.

    Required fields:
      name          string
      birth_date    YYYY-MM-DD
      birth_time    HH:MM  (local time at birthplace)
      birth_lat     float  OR  birth_city string
      birth_lon     float  OR  birth_city string

    UTC offset (at least one required for accurate Rising sign):
      utc_offset    float   e.g. -7.0 for PDT  (preferred — from browser)
      timezone      string  e.g. "America/Los_Angeles"  (fallback)
      birth_city    string  used for geocoding + timezone lookup if no utc_offset

    For single month:
      year          int
      month         int  1-12

    For 12-month plan:
      plan          "12"
      start_year    int
      start_month   int  1-12
      (year/month also accepted as aliases)

    Optional:
      intention     string  woven into Claude's content
      format        "html" | "pdf"  (default: pdf for 12-month, html for single)
    """
    data = request.get_json(force=True)

    # ── Parse birth data ──
    required = ['name', 'birth_date', 'birth_time']
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing fields: {missing}'}), 400

    try:
        birth_date = datetime.date.fromisoformat(data['birth_date'])
        h, m       = map(int, data['birth_time'].split(':')[:2])
        birth_time = datetime.time(h, m)
    except (ValueError, KeyError) as e:
        return jsonify({'error': f'Invalid date/time: {e}'}), 400

    # ── Resolve coordinates ──
    birth_lat, birth_lon = _resolve_coords(data)
    if birth_lat is None:
        return jsonify({'error': 'Provide birth_lat + birth_lon, or birth_city'}), 400

    # ── Resolve UTC offset ──
    utc_offset = _resolve_utc_offset(data, birth_lat, birth_lon)

    # ── Plan ──
    plan = str(data.get('plan', data.get('calendar_plan', '1'))).strip()

    # ── Intention (optional) ──
    intention = data.get('intention', '').strip()

    fmt = data.get('format', 'pdf' if plan == '12' else 'html').lower()

    try:
        if plan == '12':
            start_year  = int(data.get('start_year',  data.get('year',  datetime.date.today().year)))
            start_month = int(data.get('start_month', data.get('month', datetime.date.today().month)))

            result = generate_annual(
                name=data['name'],
                birth_date=birth_date,
                birth_time=birth_time,
                birth_lat=birth_lat,
                birth_lon=birth_lon,
                utc_offset=utc_offset,
                start_year=start_year,
                start_month=start_month,
                intention=intention,
                api_key=ANTHROPIC_API_KEY,
                output_dir=OUTPUT_DIR,
                mock_claude=not bool(ANTHROPIC_API_KEY),
            )
            # Return ZIP of all 12 PDFs
            zip_path = result['zip']
            safe_name = data['name'].lower().replace(' ', '_')
            filename  = f"{safe_name}_sacred_calendar_{start_year}_{start_month:02d}_annual.zip"
            return send_file(zip_path, mimetype='application/zip',
                             as_attachment=True, download_name=filename)

        else:
            year  = int(data.get('year',  datetime.date.today().year))
            month = int(data.get('month', datetime.date.today().month))

            result = generate(
                name=data['name'],
                birth_date=birth_date,
                birth_time=birth_time,
                birth_lat=birth_lat,
                birth_lon=birth_lon,
                utc_offset=utc_offset,
                year=year,
                month=month,
                intention=intention,
                api_key=ANTHROPIC_API_KEY,
                output_dir=OUTPUT_DIR,
                to_pdf=(fmt == 'pdf'),
                mock_claude=not bool(ANTHROPIC_API_KEY),
            )
            file_path = result.get('pdf') if fmt == 'pdf' else result.get('html')
            if not file_path or not os.path.exists(file_path):
                return jsonify({'error': 'File generation failed'}), 500

            ext      = 'pdf' if fmt == 'pdf' else 'html'
            mimetype = 'application/pdf' if fmt == 'pdf' else 'text/html'
            safe     = data['name'].lower().replace(' ', '_')
            fname    = f"{safe}_lunar_calendar_{year}_{month:02d}.{ext}"
            return send_file(file_path, mimetype=mimetype,
                             as_attachment=True, download_name=fname)

    except Exception as e:
        app.logger.error(f'Generation error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ── /shopify/order ────────────────────────────────────────────────────────────

@app.route('/shopify/order', methods=['POST'])
def shopify_order_webhook():
    """
    Receives Shopify orders/paid webhook.
    Extracts birth data + plan from line_item.properties or note_attributes.
    Runs generation async (returns 200 immediately to Shopify).
    """
    # Verify HMAC
    if SHOPIFY_WEBHOOK_SECRET:
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256', '')
        body        = request.get_data()
        computed    = hmac.new(
            SHOPIFY_WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(base64.b64encode(computed).decode(), hmac_header):
            app.logger.warning('Invalid Shopify HMAC')
            abort(401)

    order          = request.get_json(force=True)
    order_id       = order.get('id', 'unknown')
    customer_email = order.get('email', '')
    app.logger.info(f'Order #{order_id} — {customer_email}')

    birth_data = _extract_birth_data(order)
    if not birth_data:
        app.logger.warning(f'Order #{order_id}: no birth data — skipping')
        return jsonify({'status': 'skipped', 'reason': 'no birth data'}), 200

    # Resolve coords
    birth_lat, birth_lon = _resolve_coords(birth_data)
    if birth_lat is None and 'birth_city' in birth_data:
        coords = _geocode_city(birth_data['birth_city'])
        if coords:
            birth_lat, birth_lon = coords
        else:
            app.logger.warning(f'Order #{order_id}: geocode failed for {birth_data.get("birth_city")}')
            return jsonify({'status': 'error', 'reason': 'geocode failed'}), 200

    if birth_lat is None:
        return jsonify({'status': 'error', 'reason': 'no location data'}), 200

    utc_offset = _resolve_utc_offset(birth_data, birth_lat, birth_lon)
    plan       = str(birth_data.get('calendar_plan', '1')).strip()
    intention  = birth_data.get('intention', '').strip()

    today       = datetime.date.today()
    start_year  = int(birth_data.get('calendar_year',  today.year))
    start_month = int(birth_data.get('calendar_month',
                      today.month + 1 if today.month < 12 else 1))

    def _run():
        try:
            birth_date_obj = datetime.date.fromisoformat(birth_data['birth_date'])
            h, m = map(int, birth_data['birth_time'].split(':')[:2])
            birth_time_obj = datetime.time(h, m)

            if plan == '12':
                result = generate_annual(
                    name=birth_data['birth_name'],
                    birth_date=birth_date_obj,
                    birth_time=birth_time_obj,
                    birth_lat=birth_lat,
                    birth_lon=birth_lon,
                    utc_offset=utc_offset,
                    start_year=start_year,
                    start_month=start_month,
                    intention=intention,
                    api_key=ANTHROPIC_API_KEY,
                    output_dir=OUTPUT_DIR,
                )
                if result.get('zip') and customer_email:
                    _send_annual_email(
                        customer_email, birth_data['birth_name'],
                        result['zip'], result['months'], order_id
                    )
            else:
                result = generate(
                    name=birth_data['birth_name'],
                    birth_date=birth_date_obj,
                    birth_time=birth_time_obj,
                    birth_lat=birth_lat,
                    birth_lon=birth_lon,
                    utc_offset=utc_offset,
                    year=start_year,
                    month=start_month,
                    intention=intention,
                    api_key=ANTHROPIC_API_KEY,
                    output_dir=OUTPUT_DIR,
                    to_pdf=True,
                )
                if result.get('pdf') and customer_email:
                    _send_calendar_email(
                        customer_email, birth_data['birth_name'],
                        result['pdf'], start_year, start_month, order_id
                    )
            app.logger.info(f'Order #{order_id}: complete → {customer_email}')
        except Exception as e:
            app.logger.error(f'Order #{order_id}: failed — {e}', exc_info=True)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'accepted', 'order_id': order_id}), 200


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_coords(data: dict) -> tuple[float | None, float | None]:
    """Return (lat, lon) from data dict. Geocodes birth_city if needed."""
    if 'birth_lat' in data and 'birth_lon' in data:
        try:
            return float(data['birth_lat']), float(data['birth_lon'])
        except (ValueError, TypeError):
            pass
    if 'birth_city' in data:
        coords = _geocode_city(data['birth_city'])
        if coords:
            return coords
    return None, None


def _resolve_utc_offset(data: dict, lat: float, lon: float) -> float:
    """
    Resolve UTC offset at time of birth.

    Priority:
    1. utc_offset in data (float, from browser Intl API — most reliable)
    2. timezone in data (IANA string, e.g. "America/Los_Angeles")
    3. timezonefinder from lat/lon + birth_date (most accurate for historical dates)
    4. Fall back to 0.0 (UTC) with a warning logged

    Note: for historical accuracy (DST, timezone boundary changes) the
    timezonefinder + pytz approach is the best we can do without a full
    historical timezone database.
    """
    # 1. Browser-provided offset (already correct for the date of purchase,
    #    may differ from birth date DST — timezonefinder handles that better)
    if 'utc_offset' in data:
        try:
            return float(data['utc_offset'])
        except (ValueError, TypeError):
            pass

    # 2. IANA timezone string → historical offset at birth date
    tz_name = data.get('timezone', '')
    birth_date_str = data.get('birth_date', '')

    if tz_name and birth_date_str:
        offset = _tz_to_offset(tz_name, birth_date_str)
        if offset is not None:
            return offset

    # 3. timezonefinder: lat/lon → IANA timezone → historical offset
    if lat is not None and lon is not None and birth_date_str:
        try:
            from timezonefinder import TimezoneFinder
            tf      = TimezoneFinder()
            tz_name = tf.timezone_at(lat=lat, lng=lon)
            if tz_name:
                offset = _tz_to_offset(tz_name, birth_date_str)
                if offset is not None:
                    return offset
        except Exception as e:
            app.logger.warning(f'timezonefinder error: {e}')

    app.logger.warning('Could not resolve UTC offset — defaulting to 0.0 (UTC)')
    return 0.0


def _tz_to_offset(tz_name: str, birth_date_str: str) -> float | None:
    """Convert IANA timezone + birth date to UTC offset (hours)."""
    try:
        import pytz
        tz          = pytz.timezone(tz_name)
        birth_date  = datetime.date.fromisoformat(birth_date_str)
        # Use noon on birth date to determine DST status
        local_noon  = datetime.datetime(birth_date.year, birth_date.month,
                                        birth_date.day, 12, 0)
        localized   = tz.localize(local_noon, is_dst=None)
        offset_secs = localized.utcoffset().total_seconds()
        return offset_secs / 3600
    except Exception:
        return None


def _geocode_city(city: str) -> tuple[float, float] | None:
    try:
        from geopy.geocoders import Nominatim
        geo      = Nominatim(user_agent='bath-haus-lunar-calendar')
        location = geo.geocode(city, timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        app.logger.warning(f'Geocode error for {city}: {e}')
    return None


def _extract_birth_data(order: dict) -> dict | None:
    """Extract birth data from Shopify order note_attributes + line item properties."""
    data = {}

    for attr in order.get('note_attributes', []):
        k = attr.get('name', '').lower().replace(' ', '_')
        v = attr.get('value', '').strip()
        if k and v:
            data[k] = v

    for item in order.get('line_items', []):
        for prop in item.get('properties', []):
            k = prop.get('name', '').lower().replace(' ', '_')
            v = prop.get('value', '').strip()
            if k and v:
                data.setdefault(k, v)  # note_attributes win

    has_location = (('birth_lat' in data and 'birth_lon' in data)
                    or 'birth_city' in data)
    if not all(k in data for k in ['birth_name', 'birth_date', 'birth_time']):
        return None
    if not has_location:
        return None
    return data


def _send_calendar_email(to_email, name, pdf_path, year, month, order_id):
    month_name = datetime.date(year, month, 1).strftime('%B %Y')
    if not SENDGRID_API_KEY:
        app.logger.info(f'[EMAIL SKIPPED] Would send {month_name} to {to_email}')
        return
    try:
        import sendgrid
        from sendgrid.helpers.mail import (Mail, Attachment, FileContent,
                                           FileName, FileType, Disposition)
        with open(pdf_path, 'rb') as f:
            pdf_b64 = base64.b64encode(f.read()).decode()

        msg = Mail(from_email=EMAIL_FROM, to_emails=to_email,
                   subject=f'Your Sacred Lunar Calendar — {month_name}',
                   html_content=_email_body_single(name, month_name))
        msg.attachment = Attachment(
            FileContent(pdf_b64),
            FileName(f'sacred_lunar_calendar_{year}_{month:02d}.pdf'),
            FileType('application/pdf'),
            Disposition('attachment'),
        )
        sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
        resp = sg.send(msg)
        app.logger.info(f'SendGrid: {resp.status_code}')
    except Exception as e:
        app.logger.error(f'Email failed: {e}')


def _send_annual_email(to_email, name, zip_path, months, order_id):
    """Send a 12-month ZIP to the customer."""
    if not SENDGRID_API_KEY:
        app.logger.info(f'[EMAIL SKIPPED] Would send annual ZIP to {to_email}')
        return
    try:
        import sendgrid
        from sendgrid.helpers.mail import (Mail, Attachment, FileContent,
                                           FileName, FileType, Disposition)
        with open(zip_path, 'rb') as f:
            zip_b64 = base64.b64encode(f.read()).decode()

        first_month = months[0] if months else 'your year'
        subj        = f'Your Sacred Lunar Calendar — Annual Collection'
        msg = Mail(from_email=EMAIL_FROM, to_emails=to_email,
                   subject=subj,
                   html_content=_email_body_annual(name, months))
        msg.attachment = Attachment(
            FileContent(zip_b64),
            FileName(f'sacred_lunar_calendar_annual.zip'),
            FileType('application/zip'),
            Disposition('attachment'),
        )
        sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
        resp = sg.send(msg)
        app.logger.info(f'SendGrid annual: {resp.status_code}')
    except Exception as e:
        app.logger.error(f'Annual email failed: {e}')


def _email_body_single(name: str, month_name: str) -> str:
    first = name.split()[0]
    return f"""
    <div style="font-family:'Georgia',serif;max-width:600px;margin:0 auto;
                color:#3a3a2e;background:#faf9f6;padding:48px 32px;">
      <div style="text-align:center;margin-bottom:40px;">
        <p style="font-size:13px;letter-spacing:0.18em;text-transform:uppercase;
                  color:#7a8c6e;margin:0;">Bath Haus</p>
        <h1 style="font-size:26px;font-weight:400;margin:12px 0 0;
                   letter-spacing:0.04em;">Your Sacred Lunar Calendar</h1>
        <p style="color:#7a8c6e;margin:8px 0 0;">{month_name}</p>
      </div>
      <p style="line-height:1.8;font-size:16px;">Dear {first},</p>
      <p style="line-height:1.8;font-size:16px;">
        Your personalized Sacred Lunar Calendar for {month_name} is attached —
        woven from the specific positions of the sky at the moment of your birth.
      </p>
      <p style="line-height:1.8;font-size:16px;">
        Inside you'll find your monthly transmission, key dates, planetary alignments,
        Gene Keys activations, and bath rituals timed to the lunar phases.
      </p>
      <p style="line-height:1.8;font-size:16px;">
        May this month's waters carry you home.
      </p>
      <p style="line-height:1.8;font-size:16px;color:#7a8c6e;margin-top:40px;">
        With love,<br/><em>Bath Haus</em>
      </p>
    </div>"""


def _email_body_annual(name: str, months: list) -> str:
    first       = name.split()[0]
    months_list = ', '.join(months) if months else 'all 12 months'
    return f"""
    <div style="font-family:'Georgia',serif;max-width:600px;margin:0 auto;
                color:#3a3a2e;background:#faf9f6;padding:48px 32px;">
      <div style="text-align:center;margin-bottom:40px;">
        <p style="font-size:13px;letter-spacing:0.18em;text-transform:uppercase;
                  color:#7a8c6e;margin:0;">Bath Haus</p>
        <h1 style="font-size:26px;font-weight:400;margin:12px 0 0;
                   letter-spacing:0.04em;">Your Sacred Lunar Calendar</h1>
        <p style="color:#7a8c6e;margin:8px 0 0;">Annual Collection</p>
      </div>
      <p style="line-height:1.8;font-size:16px;">Dear {first},</p>
      <p style="line-height:1.8;font-size:16px;">
        Your complete Sacred Lunar Calendar collection is attached — 12 personalized
        months, each woven from the specific coordinates of your birth.
      </p>
      <p style="line-height:1.8;font-size:16px;">
        Your collection covers: {months_list}.
      </p>
      <p style="line-height:1.8;font-size:16px;">
        Each month arrives as a separate PDF inside the ZIP file.
        Open them in order, or jump to whatever the waters are calling you toward.
      </p>
      <p style="line-height:1.8;font-size:16px;">
        May this year's waters carry you home.
      </p>
      <p style="line-height:1.8;font-size:16px;color:#7a8c6e;margin-top:40px;">
        With love,<br/><em>Bath Haus</em>
      </p>
    </div>"""


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
