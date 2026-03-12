"""
generate_calendar.py
─────────────────────────────────────────────────────────────────────────────
Main pipeline orchestrator.

Public API:
  generate(...)       → {'html': path, 'pdf': path|None}
  generate_annual(...)→ {'zip': path, 'months': [str,...], 'files': [path,...]}
─────────────────────────────────────────────────────────────────────────────
"""

import datetime
import os
import zipfile
from pathlib import Path

from astro_calc import calculate_natal_chart
from personalization import (
    build_month_packet, build_claude_prompt,
    call_claude_api, merge_alignment_interpretations,
    YEAR_NAMES, MONTH_NAMES, personal_month,
)
from calendar_generator import render_calendar_html, save_html, convert_to_pdf


# ── Mock content (offline / no API key) ──────────────────────────────────────

def _mock_content(name: str, month_name: str, sky_events: list,
                  chart=None) -> dict:
    """
    Preview-quality mock — renders the full 6-paragraph transmission structure
    with real chart data woven in, so the HTML preview matches live output.
    chart is the NatalChart object; falls back to generic if not provided.
    """
    icon_map = {
        'New Moon': 'new-moon', 'Full Moon': 'full-moon',
        'First Quarter': 'first-qtr', 'Last Quarter': 'last-qtr',
        'Spring Equinox': 'equinox', 'Autumn Equinox': 'equinox',
        'Summer Solstice': 'solstice', 'Winter Solstice': 'solstice',
    }

    # Pull real chart values if available, else use graceful fallbacks
    sun_sign     = getattr(chart, 'sun_sign',     'your Sun sign')      if chart else 'your Sun sign'
    sun_deg      = getattr(chart, 'sun_degree',   '')                   if chart else ''
    moon_sign    = getattr(chart, 'moon_sign',    'your Moon sign')     if chart else 'your Moon sign'
    rising       = getattr(chart, 'rising_sign',  'your Rising sign')   if chart else 'your Rising sign'
    north_node   = getattr(chart, 'north_node_sign', 'your North Node') if chart else 'your North Node'
    hd_type      = getattr(chart, 'hd_type',      'your Human Design type') if chart else 'your type'
    hd_auth      = getattr(chart, 'hd_authority', 'your authority')     if chart else 'your authority'
    hd_profile   = getattr(chart, 'hd_profile',   '')                   if chart else ''
    life_path    = getattr(chart, 'life_path',    '')                   if chart else ''
    pers_year    = getattr(chart, 'personal_year', '')                  if chart else ''
    gk_lw        = getattr(chart, 'gk_life_work',  6)                  if chart else 6
    gk_ev        = getattr(chart, 'gk_evolution',  36)                 if chart else 36

    from personalization import (YEAR_NAMES, MONTH_NAMES,
                                  GENE_KEY_GIFTS, GENE_KEY_SHADOWS, GENE_KEY_SIDDHIS)
    py_name  = YEAR_NAMES.get(pers_year, 'your personal year')
    lw_gift  = GENE_KEY_GIFTS.get(gk_lw, 'Diplomacy')
    lw_shadow= GENE_KEY_SHADOWS.get(gk_lw, 'Conflict')
    lw_sid   = GENE_KEY_SIDDHIS.get(gk_lw, 'Peace')
    ev_gift  = GENE_KEY_GIFTS.get(gk_ev, 'Compassion')
    ev_shadow= GENE_KEY_SHADOWS.get(gk_ev, 'Turbulence')

    # Find the two most significant events for naming in the transmission
    lunar_events = [e for e in sky_events if e.get('icon') in
                    ('new-moon', 'full-moon', 'first-qtr', 'last-qtr')]
    new_moon  = next((e for e in lunar_events if 'New'  in e.get('type','')), None)
    full_moon = next((e for e in lunar_events if 'Full' in e.get('type','')), None)
    nm_day    = new_moon['day']  if new_moon  else '—'
    fm_day    = full_moon['day'] if full_moon else '—'
    nm_sign   = new_moon.get('moon_sign','')  if new_moon  else ''
    fm_sign   = full_moon.get('moon_sign','') if full_moon else ''

    body = [
        # Para 1 — Opening: cosmic weather
        (f"{month_name} arrives as a month of precision and power. The New Moon on Day {nm_day}"
         f"{' in ' + nm_sign if nm_sign else ''} opens a portal of focused intention — "
         f"this is not a month for broad strokes, {name}. The sky is asking you to narrow your gaze "
         f"and commit. A Sun-Saturn conjunction later in the month forms the spine of everything: "
         f"where are you building something that will last? What structures in your life are ready "
         f"to be tested against the real? The Full Moon on Day {fm_day}"
         f"{' in ' + fm_sign if fm_sign else ''} illuminates the answer — something that has been "
         f"quietly maturing for six months finally becomes visible. The light this month is not soft. "
         f"It is clear, direct, and asking you to be honest with yourself about where you are truly "
         f"planting your energy and where you are still hedging."),

        # Para 2 — Pull-quote: the one piercing sentence (kept under 280 chars)
        (f"The Full Moon on Day {fm_day} is landing directly on your {moon_sign} Moon — "
         f"what you have been carrying in the body is finally ready to be named."),

        # Para 3 — Gene Keys
        (f"Richard Rudd would say that Gate {gk_lw} — your Life's Work — holds the movement from "
         f"{lw_shadow} toward {lw_gift}, and ultimately toward the Siddhi of {lw_sid}. This month, "
         f"the planetary geometry is activating exactly that arc. The {lw_shadow} you may have been "
         f"living inside — the familiar friction that has felt like a wall — is actually the threshold. "
         f"Gate {gk_ev}, your Evolution gate, carries the frequency of {ev_shadow} moving toward "
         f"{ev_gift}. When these two gates are both in play, as they are this month under the "
         f"Sun-Saturn pressure, the question is not 'how do I get through this' but 'what is this "
         f"trying to make me into?' The water is the answer. The bath is not a luxury this month — "
         f"it is the laboratory where the alchemy actually happens."),

        # Para 4 — Human Design + Numerology
        (f"As a {hd_type}, you are not designed to initiate from willpower — you are designed to "
         f"respond, to wait, to let life come to you and then move from the clarity of your "
         f"{hd_auth}. This is a month when that design will be tested. The Personal Year {pers_year} "
         f"({py_name}) is asking you to build, and building can feel like forcing when you are "
         f"wired the way you are. The invitation is subtler than that: {hd_type}s in a {py_name} "
         f"year build by deepening, not by expanding. Profile {hd_profile}, you carry the gift of "
         f"both the hermit and the network — this month honours the hermit first. Go in before you "
         f"go wide. Let your {hd_auth} be the compass, not your ambitions."),

        # Para 5 — Integration
        (f"If there is one thread to pull this month, {name}, it is this: something that has been "
         f"underground is ready to surface. Your {sun_sign} Sun has spent years in the realm of "
         f"refinement and discernment — and now, with your North Node in {north_node} pointing "
         f"toward the direction of your growth, the sky is creating a corridor. Walk through it. "
         f"The Full Moon on Day {fm_day} is your marker. What you release at that lunation, "
         f"you will not need to carry into the next cycle. What you receive — in the stillness "
         f"after, in the bath, in the quiet — is the actual transmission."),

        # Para 6 — Closing invocation
        (f"Lower yourself into the water this month, {name}, and let it hold what you cannot yet "
         f"name. The lunations will do their work. The planets are in conversation with your chart "
         f"in ways that have been years in the making. You do not need to understand it all — "
         f"you only need to be present to it. The water knows. Let it speak."),
    ]

    key_dates = [
        {
            'day':         e['day'],
            'event':       e['type'],
            'icon':        icon_map.get(e['type'], e.get('icon', 'sun')),
            'description': (f"The {e['type']} arrives on Day {e['day']}, "
                            f"carrying the energy of completion and new beginnings. "
                            f"This is one of the most potent windows of the month."),
            'personal':    (f"For you, {name}, with your {sun_sign} Sun and {moon_sign} Moon, "
                            f"this {e['type']} activates the themes you have been working with "
                            f"most intimately. Pay close attention to what arises in the body."),
        }
        for e in sky_events
    ]

    first_day = sky_events[0]['day'] if sky_events else 14
    return {
        'transmission': {
            'title': f'What the Water Knows, {name}',
            'body':  body,
        },
        'key_dates': key_dates,
        'bath_rituals': [{
            'trigger':     sky_events[0]['type'] if sky_events else 'Lunar Phase',
            'day':         first_day,
            'name':        'The Mirror Bath',
            'description': 'A ritual of full presence — letting the water reflect everything.',
            'ingredients': ['Rose petals', 'Sea salt', 'Lavender oil', 'White candle'],
            'intention':   'Let the water hold the answer.',
        }],
        'alignment_interpretations': [],
        'affirmation':  f'I, {name}, am exactly where I need to be.',
        'closing_note': 'Next month brings new energy to build upon.',
    }


# ── Single-month pipeline ─────────────────────────────────────────────────────

def generate(
    name:        str,
    birth_date:  datetime.date,
    birth_time:  datetime.time,
    birth_lat:   float,
    birth_lon:   float,
    year:        int,
    month:       int,
    utc_offset:  float = 0.0,
    intention:   str   = '',
    api_key:     str   = '',
    output_dir:  str   = '/tmp/calendars',
    to_pdf:      bool  = False,
    mock_claude: bool  = False,
) -> dict:
    """
    Full pipeline: birth data → personalized calendar HTML (+ optional PDF).

    utc_offset  UTC hours offset at birth (e.g. -7.0 for PDT).
                Resolved by app.py via browser → timezonefinder fallback.
                Critical for correct Rising sign calculation.

    intention   Optional customer intention, woven into Claude's content.
                Pass empty string '' if not provided.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    month_name = datetime.date(year, month, 1).strftime('%B')
    safe_name  = name.lower().replace(' ', '_')
    base_name  = f'{safe_name}_{year}_{month:02d}'

    # 1. Natal chart
    chart = calculate_natal_chart(
        birth_date, birth_time, birth_lat, birth_lon,
        utc_offset=utc_offset,
    )

    # 2. Monthly data packet
    packet     = build_month_packet(name, birth_date, chart, year, month)
    alignments = packet['alignments']

    # 3. Claude (or mock)
    if mock_claude or not api_key:
        content = _mock_content(name, month_name, packet['sky_events'], chart=chart)
    else:
        prompt  = build_claude_prompt(packet, intention=intention)
        content = call_claude_api(prompt, api_key)

    # 4. Merge alignment interpretations
    alignments = merge_alignment_interpretations(alignments, content)

    # 5. Labels
    personal_year_name  = YEAR_NAMES.get(chart.personal_year, '')
    personal_month_num  = personal_month(birth_date, year, month)
    personal_month_name = MONTH_NAMES.get(personal_month_num, '')

    # 6. Render
    html = render_calendar_html(
        person_name=name, birth_date=birth_date, chart=chart,
        year=year, month=month, packet=packet, content=content,
        personal_year_name=personal_year_name,
        personal_month_num=personal_month_num,
        personal_month_name=personal_month_name,
        alignments=alignments,
    )

    html_path = os.path.join(output_dir, f'{base_name}.html')
    save_html(html, html_path)
    result = {'html': html_path, 'pdf': None}

    if to_pdf:
        pdf_path      = os.path.join(output_dir, f'{base_name}.pdf')
        convert_to_pdf(html_path, pdf_path)
        result['pdf'] = pdf_path

    return result


# ── 12-month annual pipeline ──────────────────────────────────────────────────

def generate_annual(
    name:         str,
    birth_date:   datetime.date,
    birth_time:   datetime.time,
    birth_lat:    float,
    birth_lon:    float,
    start_year:   int,
    start_month:  int,
    utc_offset:   float = 0.0,
    intention:    str   = '',
    api_key:      str   = '',
    output_dir:   str   = '/tmp/calendars',
    mock_claude:  bool  = False,
) -> dict:
    """
    Generate 12 consecutive monthly calendars and bundle them as a ZIP.

    The natal chart is calculated once (same birth data for all months).
    Claude is called once per month with that month's specific sky events.

    Returns
    -------
    {
      'zip':    '/path/to/name_annual_YYYY_MM.zip',
      'months': ['March 2026', 'April 2026', ...],
      'files':  ['/path/to/name_2026_03.pdf', ...]
    }
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Chart calculated once
    chart = calculate_natal_chart(
        birth_date, birth_time, birth_lat, birth_lon,
        utc_offset=utc_offset,
    )

    pdf_paths    = []
    month_labels = []

    for i in range(12):
        total  = (start_month - 1) + i
        year   = start_year + total // 12
        month  = total % 12 + 1
        mn     = datetime.date(year, month, 1).strftime('%B %Y')
        safe   = name.lower().replace(' ', '_')
        base   = f'{safe}_{year}_{month:02d}'

        packet     = build_month_packet(name, birth_date, chart, year, month)
        alignments = packet['alignments']

        if mock_claude or not api_key:
            month_str = datetime.date(year, month, 1).strftime('%B')
            content   = _mock_content(name, month_str, packet['sky_events'], chart=chart)
        else:
            prompt  = build_claude_prompt(packet, intention=intention)
            content = call_claude_api(prompt, api_key)

        alignments = merge_alignment_interpretations(alignments, content)

        personal_year_name  = YEAR_NAMES.get(chart.personal_year, '')
        personal_month_num  = personal_month(birth_date, year, month)
        personal_month_name = MONTH_NAMES.get(personal_month_num, '')

        html = render_calendar_html(
            person_name=name, birth_date=birth_date, chart=chart,
            year=year, month=month, packet=packet, content=content,
            personal_year_name=personal_year_name,
            personal_month_num=personal_month_num,
            personal_month_name=personal_month_name,
            alignments=alignments,
        )

        html_path = os.path.join(output_dir, f'{base}.html')
        pdf_path  = os.path.join(output_dir, f'{base}.pdf')
        save_html(html, html_path)
        convert_to_pdf(html_path, pdf_path)

        pdf_paths.append(pdf_path)
        month_labels.append(mn)

    # ZIP all PDFs
    safe     = name.lower().replace(' ', '_')
    zip_name = f'{safe}_annual_{start_year}_{start_month:02d}.zip'
    zip_path = os.path.join(output_dir, zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in pdf_paths:
            zf.write(p, os.path.basename(p))

    return {'zip': zip_path, 'months': month_labels, 'files': pdf_paths}
