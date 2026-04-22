"""
personalization.py
─────────────────────────────────────────────────────────────────────────────
Takes a NatalChart and monthly sky events, produces a structured data packet
that the Claude API will use to write personalized transmissions, key date
interpretations, and bath rituals.

All prompts are crafted to produce JSON — clean, parseable, templatable.
─────────────────────────────────────────────────────────────────────────────
"""

import json
import datetime
from astro_calc import (
    NatalChart, get_month_sky_events, personal_month,
    SIGNS
)

# ── Personal year/month names ─────────────────────────────────────────────────

YEAR_NAMES = {
    1: 'Initiation', 2: 'Gestation', 3: 'Expression', 4: 'Foundation',
    5: 'Freedom', 6: 'Harmony', 7: 'Inner Work', 8: 'Abundance',
    9: 'Completion', 11: 'Illumination', 22: 'Master Builder'
}

MONTH_NAMES = {
    1: 'Seeding', 2: 'Receiving', 3: 'Creating', 4: 'Building',
    5: 'Shifting', 6: 'Nurturing', 7: 'Reflecting', 8: 'Manifesting',
    9: 'Releasing', 11: 'Awakening', 22: 'Visioning'
}

GENE_KEY_GIFTS = {
    1: 'Freshness', 2: 'Orientation', 3: 'Innovation', 4: 'Understanding',
    5: 'Patience', 6: 'Diplomacy', 7: 'Guidance', 8: 'Style',
    9: 'Determination', 10: 'Naturalness', 11: 'Idealism', 12: 'Discrimination',
    13: 'Discernment', 14: 'Competence', 15: 'Magnetism', 16: 'Versatility',
    17: 'Far-Sightedness', 18: 'Integrity', 19: 'Sensitivity', 20: 'Self-Assurance',
    21: 'Authority', 22: 'Graciousness', 23: 'Simplicity', 24: 'Invention',
    25: 'Acceptance', 26: 'Artfulness', 27: 'Altruism', 28: 'Totality',
    29: 'Commitment', 30: 'Lightness', 31: 'Leadership', 32: 'Preservation',
    33: 'Mindfulness', 34: 'Strength', 35: 'Adventure', 36: 'Compassion',
    37: 'Equality', 38: 'Perseverance', 39: 'Dynamism', 40: 'Resolve',
    41: 'Anticipation', 42: 'Celebration', 43: 'Insight', 44: 'Teamwork',
    45: 'Synergy', 46: 'Delight', 47: 'Transmutation', 48: 'Wisdom',
    49: 'Revolution', 50: 'Equilibrium', 51: 'Initiative', 52: 'Restraint',
    53: 'Expansion', 54: 'Aspiration', 55: 'Freedom', 56: 'Enrichment',
    57: 'Intuition', 58: 'Vitality', 59: 'Intimacy', 60: 'Realism',
    61: 'Inspiration', 62: 'Precision', 63: 'Inquiry', 64: 'Imagination',
}

GENE_KEY_SIDDHIS = {
    15: 'Florescence', 49: 'Rebirth', 4: 'Forgiveness', 10: 'Being',
}


def build_month_packet(
    name: str,
    birth_date: datetime.date,
    chart: NatalChart,
    year: int,
    month: int
) -> dict:
    """
    Assemble the complete data packet for one calendar month.
    This is passed to the Claude API prompt builder.
    """
    sky = get_month_sky_events(year, month)
    pm = personal_month(birth_date, year, month)
    month_name_str = datetime.date(year, month, 1).strftime('%B')

    # Identify which sky events are personally significant
    significant = _find_personal_resonances(chart, sky['events'])

    packet = {
        'person': {
            'name': name,
            'birth_date': birth_date.isoformat(),
        },
        'chart': {
            'sun':           f"{chart.sun_degree}° {chart.sun_sign}",
            'moon':          f"{chart.moon_degree}° {chart.moon_sign}",
            'rising':        f"{chart.rising_degree}° {chart.rising_sign}",
            'mercury':       chart.mercury_sign,
            'venus':         chart.venus_sign,
            'mars':          chart.mars_sign,
            'jupiter':       chart.jupiter_sign,
            'saturn':        chart.saturn_sign,
            'north_node':    chart.north_node_sign,
            'hd_type':       chart.hd_type,
            'hd_authority':  chart.hd_authority,
            'hd_profile':    chart.hd_profile,
            'hd_definition': chart.hd_definition,
            'hd_defined_centers': sorted(chart.hd_defined_centers),
            'hd_conscious_sun_gate':   chart.hd_conscious_sun_gate,
            'hd_unconscious_sun_gate': chart.hd_unconscious_sun_gate,
            'life_path':     chart.life_path,
            'personal_year': chart.personal_year,
            'personal_year_name': YEAR_NAMES.get(chart.personal_year, ''),
        },
        'month': {
            'year':  year,
            'month': month,
            'name':  month_name_str,
            'personal_month':      pm,
            'personal_month_name': MONTH_NAMES.get(pm, ''),
        },
        'sky_events':       sky['events'],
        'by_day':           {str(k): v for k, v in sky['by_day'].items()},
        'significant_events': significant,
        'lunar_phases':     sky['lunar_phases'],
        'aspects':          sky.get('aspects', []),
        'wheel_events':     sky.get('wheel_events', []),
    }
    return packet


def _find_personal_resonances(chart: NatalChart, events: list) -> list:
    """
    Flag sky events that have personal chart significance.
    A New/Full Moon in someone's natal Moon sign, or a solar ingress
    that triggers a natal placement, is marked as personally resonant.
    """
    resonant = []
    natal_signs = {
        chart.sun_sign, chart.moon_sign, chart.rising_sign,
        chart.north_node_sign, chart.mercury_sign, chart.venus_sign
    }
    # Opposite signs also matter (especially for Full Moons)
    opposite = {SIGNS[(SIGNS.index(s) + 6) % 12] for s in natal_signs}

    for event in events:
        reasons = []
        moon_sign = event.get('moon_sign', '')
        ingress_sign = event.get('sign', '')

        if moon_sign in natal_signs:
            reasons.append(f"Moon in {moon_sign} activates your natal {moon_sign}")
        if moon_sign in opposite:
            reasons.append(f"Moon in {moon_sign} opposes your natal {SIGNS[(SIGNS.index(moon_sign)+6)%12]}")
        if ingress_sign == chart.north_node_sign:
            reasons.append(f"Sun enters {ingress_sign} — your North Node sign")
        if ingress_sign == chart.rising_sign:
            reasons.append(f"Sun enters {ingress_sign} — your Rising sign")

        if reasons:
            resonant.append({**event, 'personal_reasons': reasons})

    return resonant


# ── Prompt builder for Claude API ─────────────────────────────────────────────

def _load_framework() -> str:
    """
    Load the interpretive framework document.
    Looks for bath_haus_interpretive_framework.md alongside this file,
    then falls back to the compact inline version.
    """
    import os
    candidates = [
        os.path.join(os.path.dirname(__file__), 'bath_haus_interpretive_framework.md'),
        os.path.join(os.getcwd(), 'bath_haus_interpretive_framework.md'),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    # Fallback compact version
    return _FALLBACK_SYSTEM_PROMPT

_FALLBACK_SYSTEM_PROMPT = """You are the voice of the Sacred Lunar Calendar — a personalized astrological planner from Bath Haus.

VOICE: Write like an experienced astrologer speaking directly and warmly to this specific person.
Think: Pam Gregory's precision and specificity, filtered through intimate personal knowledge of their chart.

RULES (non-negotiable):
- Always name the exact degree and sign of every transit mentioned
- Always connect sky events to at least one specific natal placement
- Always include both the felt quality AND practical guidance for each event
- Speak directly: "you" and "your" always — never "they"
- Never use generic phrases: "powerful energy," "big shifts," "transformation is possible"
- Weave Human Design type and authority in naturally — one reference per reading minimum
- Include Personal Year and Personal Month context
- Never use language derived from Ra Uru Hu or Richard Rudd texts

Bath Haus makes water filtration products for the sacred bath — all rituals are grounded in the body and in water.

You will return ONLY valid JSON — no preamble, no backticks, no markdown.
"""

SYSTEM_PROMPT = _load_framework() + """

---

## FINAL INSTRUCTION

You are generating content for the Bath Haus Sacred Lunar Calendar.
Apply every principle in this framework to the chart data you receive.
You will return ONLY valid JSON — no preamble, no backticks, no markdown.
The quality standard: every paragraph must be specific enough that it could only have been written for this person's chart.
"""

def build_claude_prompt(packet: dict) -> str:
    """
    Build the user-turn prompt for the Claude API call.
    Returns a prompt that asks Claude to generate all personalized
    content for one calendar month as structured JSON.
    """
    name = packet['person']['name']
    month_name = packet['month']['name']
    year = packet['month']['year']
    pm = packet['month']['personal_month']
    pm_name = packet['month']['personal_month_name']
    py = packet['chart']['personal_year']
    py_name = packet['chart']['personal_year_name']

    events_summary = []
    for e in packet['sky_events']:
        line = f"- {e['type']}: Day {e['day']}"
        if 'moon_sign' in e:
            line += f" in {e['moon_sign']}"
        if 'sign' in e:
            line += f" → {e['sign']}"
        events_summary.append(line)

    significant_summary = []
    for e in packet['significant_events']:
        for r in e.get('personal_reasons', []):
            significant_summary.append(f"- Day {e['day']}: {r}")

    wheel_summary = []
    for e in packet.get('wheel_events', []):
        wheel_summary.append(f"- {e['type']}: Day {e['day']} — {e.get('description', '')}")

    wheel_block = (
        '\n'.join(wheel_summary)
        if wheel_summary
        else "- No Wheel of the Year events this month"
    )

    aspects_summary = []
    for a in packet.get('aspects', []):
        aspects_summary.append(
            f"- {a['type'].title()}: {a['planets']} "
            f"({a.get('p1_sign','')} · {a.get('p2_sign','')}), "
            f"active {a['date_range']}"
        )

    chart = packet['chart']

    aspects_block = (
        '\n'.join(aspects_summary)
        if aspects_summary
        else "- No major outer-planet aspects this month"
    )

    prompt = f"""Generate personalized Sacred Lunar Calendar content for {name} for {month_name} {year}.

THEIR NATAL CHART:
- Sun:     {chart['sun']}
- Moon:    {chart['moon']}
- Rising:  {chart['rising']}
- Mercury: {chart['mercury']}
- Venus:   {chart['venus']}
- Mars:    {chart['mars']}
- Jupiter: {chart['jupiter']}
- Saturn:  {chart['saturn']}
- North Node: {chart['north_node']}

HUMAN DESIGN:
- Type:       {chart['hd_type']}
- Authority:  {chart['hd_authority']}
- Profile:    {chart['hd_profile']}
- Definition: {chart['hd_definition']}
- Defined Centers: {', '.join(chart['hd_defined_centers'])}
- Conscious Sun Gate: {chart['hd_conscious_sun_gate']}
- Unconscious Sun Gate: {chart['hd_unconscious_sun_gate']}

NUMEROLOGY:
- Life Path: {chart['life_path']}
- Personal Year: {py} ({py_name})
- Personal Month: {pm} ({pm_name})

SKY EVENTS THIS MONTH:
{chr(10).join(events_summary)}

WHEEL OF THE YEAR EVENTS THIS MONTH:
{wheel_block}

PLANETARY ALIGNMENTS THIS MONTH (aspects):
{aspects_block}

PERSONALLY SIGNIFICANT EVENTS (chart activations):
{chr(10).join(significant_summary) if significant_summary else "- See all events, find the most resonant 2-3"}

Generate a JSON object with EXACTLY this structure:

{{
  "transmission": {{
    "title": "short evocative title for the month (5-8 words)",
    "body": ["paragraph 1", "paragraph 2", "paragraph 3", "paragraph 4"]
  }},
  "key_dates": [
    {{
      "day": <integer>,
      "event": "name of event",
      "icon": "new-moon|full-moon|first-qtr|last-qtr|venus|mercury|sun|mars|saturn|jupiter",
      "description": "2-3 sentence interpretation of this event in general",
      "personal": "2-3 sentences specific to {name}'s chart — reference exact placements"
    }}
  ],
  "bath_rituals": [
    {{
      "trigger": "name of the sky event that calls this ritual",
      "day": <integer>,
      "name": "evocative ritual name",
      "description": "1-2 sentences setting the scene",
      "ingredients": ["ingredient 1", "ingredient 2", "ingredient 3", "ingredient 4"],
      "intention": "2-3 sentences — what to do, what to feel, what to release or receive"
    }}
  ],
  "planetary_alignments": [
    {{
      "type": "trine|opposition|square|sextile|conjunction",
      "planets": "Planet · Planet",
      "date_range": "use the date_range from the aspects data above",
      "description": "2-3 sentences on what this aspect means in general — its quality and energy",
      "personal": "2-3 sentences specific to {name}'s chart — how these planets interact with her natal placements, what this activates for her specifically"
    }}
  ],
  "affirmation": "one sentence in {name}'s voice — present tense, personal, grounded in her month",
  "closing_note": "one sentence preview of next month's energy"
}}

For planetary_alignments: generate one entry per aspect listed above. If no aspects were listed, return an empty array.
Return ONLY the JSON object. No other text."""

    return prompt


def call_claude_api(prompt: str, api_key: str) -> dict:
    """
    Call the Claude API with the personalization prompt.
    Returns parsed JSON content dict.
    """
    import urllib.request
    import urllib.error

    payload = json.dumps({
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 4000,
        'system': SYSTEM_PROMPT,
        'messages': [{'role': 'user', 'content': prompt}]
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            raw = data['content'][0]['text']
            # Strip any accidental markdown fences
            raw = raw.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Claude API error {e.code}: {e.read().decode()}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Claude response as JSON: {e}")
