"""
generate_calendar.py
─────────────────────────────────────────────────────────────────────────────
Main pipeline: birth data in → personalized Sacred Lunar Calendar PDF out.

Usage (direct):
  python generate_calendar.py

Imported by app.py as:
  from generate_calendar import generate
─────────────────────────────────────────────────────────────────────────────
"""

import datetime
import json
import os
from pathlib import Path

from astro_calc import calculate_natal_chart, get_month_sky_events
from personalization import (
    build_month_packet, build_claude_prompt, call_claude_api,
    YEAR_NAMES, MONTH_NAMES, personal_month
)
from calendar_generator import render_calendar_html, save_html, convert_to_pdf


# ── Mock Claude response for testing without API key ─────────────────────────

def _mock_claude_response(name: str, month_name: str, year: int, aspects: list) -> dict:
    """Return a plausible mock Claude response for dry-run testing."""
    mock_alignments = []
    for a in aspects[:3]:
        mock_alignments.append({
            "type": a['type'],
            "planets": a['planets'],
            "date_range": a['date_range'],
            "description": (
                f"The {a['type']} between {a['planets']} brings a period of "
                f"heightened awareness and energetic dialogue between these two principles. "
                f"This geometry invites integration rather than conflict."
            ),
            "personal": (
                f"For you, {name}, this activation touches your natal placements in a way "
                f"that calls for attentiveness to how these themes move through your body. "
                f"Trust what arises in stillness during this window."
            ),
        })

    return {
        "transmission": {
            "title": f"The Water Knows the Way",
            "body": [
                f"Something in you has been preparing for {month_name}, {name}. Not the calendar version — the version your body already knew was coming.",
                "The sky this month asks you to release what you've been holding in your jaw, your shoulders, the space between your shoulder blades. The tension that isn't yours.",
                "Water is the great reminder: it doesn't force its way. It finds. It moves around what resists and through what opens.",
                "You are entering a month of finding. Not seeking. Finding what was always present, waiting for you to slow down enough to recognize it."
            ]
        },
        "key_dates": [
            {
                "day": 7,
                "event": "New Moon",
                "icon": "new-moon",
                "description": "The New Moon marks the beginning of a new lunar cycle — a threshold moment for intention-setting and seeding what you wish to grow.",
                "personal": f"With your natal Moon in Virgo, {name}, this New Moon activates your capacity for discernment. What you plant now will be filtered through your gift of precise knowing."
            },
            {
                "day": 22,
                "event": "Full Moon",
                "icon": "full-moon",
                "description": "The Full Moon illuminates what has been quietly growing since the New Moon two weeks prior. Emotions surface. Clarity arrives. Things reach their natural peak.",
                "personal": f"Your Virgo Moon meets the Full Moon's light with particular intensity this month, {name}. Something you've been analyzing from a distance is ready to be felt instead."
            }
        ],
        "bath_rituals": [
            {
                "trigger": "New Moon",
                "day": 7,
                "name": "The Seeding Bath",
                "description": "On the eve of the New Moon, the water receives what you are ready to call forward. The darkness is not empty — it is potential.",
                "ingredients": ["Epsom salt", "Rose petals", "Frankincense oil", "A single white candle"],
                "intention": f"As you lower into the water, {name}, speak one thing aloud that you are ready to begin. Not a wish — a declaration. Let the water carry it."
            },
            {
                "trigger": "Full Moon",
                "day": 22,
                "name": "The Release Bath",
                "description": "The Full Moon asks what has served its purpose. The bath becomes a vessel for completion.",
                "ingredients": ["Sea salt", "Lavender", "Eucalyptus oil", "Moon water if available"],
                "intention": "Let the water receive what you are done carrying. You don't need to name it perfectly. The body knows. Let it go on your exhale."
            }
        ],
        "planetary_alignments": mock_alignments,
        "affirmation": f"I move through {month_name} rooted in what I know, open to what I cannot yet see, and trusting the water to show me the way.",
        "closing_note": f"Next month carries a different quality — a gathering after this month's release."
    }


# ── Main generate function ────────────────────────────────────────────────────

def generate(
    name: str,
    birth_date: datetime.date,
    birth_time: datetime.time,
    birth_lat: float,
    birth_lon: float,
    year: int,
    month: int,
    api_key: str = '',
    output_dir: str = '/tmp/calendars',
    to_pdf: bool = False,
    mock_claude: bool = False,
) -> dict:
    """
    Full pipeline: birth data → HTML (and optionally PDF).

    Returns:
        {'html': '/path/to/file.html', 'pdf': '/path/to/file.pdf' or None}
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_name = name.lower().replace(' ', '_')
    base = f"{safe_name}_{year}_{month:02d}"

    # 1. Calculate natal chart
    chart = calculate_natal_chart(birth_date, birth_time, birth_lat, birth_lon)

    # 2. Build month data packet (includes sky events + aspects)
    packet = build_month_packet(name, birth_date, chart, year, month)

    # 3. Get or mock Claude content
    if mock_claude or not api_key:
        print(f"[generate] Mock mode — skipping Claude API call")
        content = _mock_claude_response(
            name,
            datetime.date(year, month, 1).strftime('%B'),
            year,
            packet.get('aspects', [])
        )
    else:
        prompt = build_claude_prompt(packet)
        print(f"[generate] Calling Claude API...")
        content = call_claude_api(prompt, api_key)
        print(f"[generate] Claude response received")

    # 4. Extract alignments from Claude response (may supplement with calc data)
    alignments = _merge_alignments(content.get('planetary_alignments', []),
                                   packet.get('aspects', []))

    # 5. Resolve numerology display names
    pm = personal_month(birth_date, year, month)
    py = chart.personal_year
    personal_year_name  = YEAR_NAMES.get(py, str(py))
    personal_month_name = MONTH_NAMES.get(pm, str(pm))

    # 6. Render HTML
    html = render_calendar_html(
        person_name=name,
        birth_date=birth_date,
        chart=chart,
        year=year,
        month=month,
        packet=packet,
        content=content,
        personal_year_name=personal_year_name,
        personal_month_num=pm,
        personal_month_name=personal_month_name,
        alignments=alignments,
    )

    html_path = os.path.join(output_dir, f"{base}.html")
    save_html(html, html_path)
    print(f"[generate] HTML saved: {html_path}")

    pdf_path = None
    if to_pdf:
        pdf_path = os.path.join(output_dir, f"{base}.pdf")
        convert_to_pdf(html_path, pdf_path)
        print(f"[generate] PDF saved: {pdf_path}")

    return {'html': html_path, 'pdf': pdf_path}


def _merge_alignments(claude_alignments: list, calc_aspects: list) -> list:
    """
    Merge Claude-generated alignment interpretations with calculated aspect data.
    Claude's text is authoritative; calc data fills in missing date_range / planets.
    """
    if not claude_alignments:
        return []

    # Build a lookup of calc aspects by (planet1, planet2, type)
    calc_lookup = {}
    for a in calc_aspects:
        key = (a['planet1'], a['planet2'], a['type'])
        calc_lookup[key] = a

    merged = []
    for ca in claude_alignments:
        # Ensure date_range is present (Claude might omit it)
        if not ca.get('date_range'):
            # Try to find matching calc aspect
            for a in calc_aspects:
                if (a['type'] == ca.get('type') and
                        a['planets'] == ca.get('planets')):
                    ca['date_range'] = a['date_range']
                    break
        merged.append(ca)

    return merged


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    # End-to-end test with Mandana's real birth data
    result = generate(
        name='Mandana',
        birth_date=datetime.date(1986, 9, 18),
        birth_time=datetime.time(12, 1),
        birth_lat=34.0522,
        birth_lon=-118.2437,
        year=2026,
        month=5,
        api_key=os.environ.get('ANTHROPIC_API_KEY', ''),
        output_dir='/tmp/calendars',
        to_pdf=False,
        mock_claude=not bool(os.environ.get('ANTHROPIC_API_KEY')),
    )
    print(f"\n✓ Calendar generated:")
    print(f"  HTML: {result['html']}")
    if result['pdf']:
        print(f"  PDF:  {result['pdf']}")
