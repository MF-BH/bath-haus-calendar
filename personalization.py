"""
personalization.py
─────────────────────────────────────────────────────────────────────────────
Builds the data packet and Claude API prompt for one calendar month.
All sky event dates passed to Claude are REAL calculated dates, not invented.
Claude is instructed to write about those exact dates only.
─────────────────────────────────────────────────────────────────────────────
"""

import json
import datetime
from astro_calc import (
    NatalChart, get_month_sky_events, personal_month, SIGNS,
    get_hd_type_meaning, get_hd_authority_meaning,
    get_hd_profile_meaning, get_hd_cross_meaning,
)

# ── Numerology names ──────────────────────────────────────────────────────────

YEAR_NAMES = {
    1: 'Initiation', 2: 'Gestation', 3: 'Expression', 4: 'Foundation',
    5: 'Freedom',    6: 'Harmony',   7: 'Inner Work',  8: 'Abundance',
    9: 'Completion', 11: 'Illumination', 22: 'Master Builder'
}

MONTH_NAMES = {
    1: 'Seeding',  2: 'Receiving',  3: 'Creating',   4: 'Building',
    5: 'Shifting', 6: 'Nurturing',  7: 'Reflecting',  8: 'Manifesting',
    9: 'Releasing', 11: 'Awakening', 22: 'Visioning'
}

# ── Gene Keys ─────────────────────────────────────────────────────────────────

GENE_KEY_GIFTS = {
     1: 'Freshness',      2: 'Orientation',    3: 'Innovation',     4: 'Understanding',
     5: 'Patience',       6: 'Diplomacy',       7: 'Guidance',       8: 'Style',
     9: 'Determination', 10: 'Naturalness',    11: 'Idealism',      12: 'Discrimination',
    13: 'Discernment',   14: 'Competence',     15: 'Magnetism',     16: 'Versatility',
    17: 'Far-Sightedness',18: 'Integrity',     19: 'Sensitivity',   20: 'Self-Assurance',
    21: 'Authority',      22: 'Graciousness',  23: 'Simplicity',    24: 'Invention',
    25: 'Acceptance',     26: 'Artfulness',    27: 'Altruism',      28: 'Totality',
    29: 'Commitment',     30: 'Lightness',     31: 'Leadership',    32: 'Preservation',
    33: 'Mindfulness',    34: 'Strength',      35: 'Adventure',     36: 'Compassion',
    37: 'Equality',       38: 'Perseverance',  39: 'Dynamism',      40: 'Resolve',
    41: 'Anticipation',   42: 'Celebration',   43: 'Insight',       44: 'Teamwork',
    45: 'Synergy',        46: 'Delight',       47: 'Transmutation', 48: 'Wisdom',
    49: 'Revolution',     50: 'Equilibrium',   51: 'Initiative',    52: 'Restraint',
    53: 'Expansion',      54: 'Aspiration',    55: 'Freedom',       56: 'Enrichment',
    57: 'Intuition',      58: 'Vitality',      59: 'Intimacy',      60: 'Realism',
    61: 'Inspiration',    62: 'Precision',     63: 'Inquiry',       64: 'Imagination',
}

GENE_KEY_SHADOWS = {
     1: 'Entropy',        2: 'Dislocation',    3: 'Chaos',          4: 'Intolerance',
     5: 'Impatience',     6: 'Conflict',        7: 'Division',       8: 'Mediocrity',
     9: 'Inertia',       10: 'Self-Obsession', 11: 'Obscurity',     12: 'Vanity',
    13: 'Discord',       14: 'Compromise',     15: 'Dullness',      16: 'Indifference',
    17: 'Opinion',       18: 'Judgment',       19: 'Co-dependence', 20: 'Superficiality',
    21: 'Control',       22: 'Dishonour',      23: 'Complexity',    24: 'Addiction',
    25: 'Constriction',  26: 'Pride',          27: 'Selfishness',   28: 'Purposelessness',
    29: 'Half-heartedness',30:'Desire',        31: 'Arrogance',     32: 'Failure',
    33: 'Forgetting',    34: 'Force',          35: 'Hunger',        36: 'Turbulence',
    37: 'Weakness',      38: 'Struggle',       39: 'Provocation',   40: 'Exhaustion',
    41: 'Fantasy',       42: 'Expectation',    43: 'Deafness',      44: 'Interference',
    45: 'Dominance',     46: 'Seriousness',    47: 'Oppression',    48: 'Inadequacy',
    49: 'Reaction',      50: 'Corruption',     51: 'Agitation',     52: 'Stress',
    53: 'Immaturity',    54: 'Greed',          55: 'Victimisation', 56: 'Distraction',
    57: 'Unease',        58: 'Dissatisfaction',59:'Dishonesty',     60: 'Limitation',
    61: 'Psychosis',     62: 'Intellectualism',63:'Doubt',          64: 'Confusion',
}

GENE_KEY_SIDDHIS = {
     1: 'Beauty',         2: 'Unity',           3: 'Innocence',      4: 'Forgiveness',
     5: 'Timelessness',   6: 'Peace',           7: 'Virtue',         8: 'Exquisiteness',
     9: 'Invincibility', 10: 'Being',          11: 'Light',         12: 'Purity',
    13: 'Empathy',       14: 'Bounteousness',  15: 'Florescence',   16: 'Mastery',
    17: 'Omniscience',   18: 'Perfection',     19: 'Sacrifice',     20: 'Presence',
    21: 'Valour',        22: 'Grace',          23: 'Quintessence',  24: 'Silence',
    25: 'Universal Love',26: 'Invisibility',   27: 'Selflessness',  28: 'Immortality',
    29: 'Devotion',      30: 'Rapture',        31: 'Humility',      32: 'Veneration',
    33: 'Revelation',    34: 'Majesty',        35: 'Boundlessness', 36: 'Humanity',
    37: 'Tenderness',    38: 'Honour',         39: 'Liberation',    40: 'Divine Will',
    41: 'Emanation',     42: 'Detachment',     43: 'Epiphany',      44: 'Synarchy',
    45: 'Communion',     46: 'Ecstasy',        47: 'Transfiguration',48:'Wisdom',
    49: 'Rebirth',       50: 'Harmony',        51: 'Awakening',     52: 'Stillness',
    53: 'Superabundance',54: 'Ascension',      55: 'Freedom',       56: 'Intoxication',
    57: 'Clarity',       58: 'Bliss',          59: 'Transparency',  60: 'Justice',
    61: 'Sanctity',      62: 'Impeccability',  63: 'Truth',         64: 'Illumination',
}

def gene_key_label(gate: int) -> str:
    shadow = GENE_KEY_SHADOWS.get(gate, '')
    gift   = GENE_KEY_GIFTS.get(gate, '')
    siddhi = GENE_KEY_SIDDHIS.get(gate, '')
    return f"GK {gate} — {shadow} → {gift} → {siddhi}"


# ── build_month_packet ────────────────────────────────────────────────────────

def build_month_packet(
    name:       str,
    birth_date: datetime.date,
    chart:      NatalChart,
    year:       int,
    month:      int,
) -> dict:
    sky          = get_month_sky_events(year, month)
    pm           = personal_month(birth_date, year, month)
    month_str    = datetime.date(year, month, 1).strftime('%B')
    significant  = _find_personal_resonances(chart, sky['events'])

    # Build alignments
    try:
        from astro_alignments import get_month_alignments
        alignments = get_month_alignments(year, month)
    except Exception:
        alignments = []

    packet = {
        'person':    {'name': name, 'birth_date': birth_date.isoformat()},
        'chart': {
            'sun':                  f"{chart.sun_degree}° {chart.sun_sign}",
            'moon':                 chart.moon_sign,
            'rising':               chart.rising_sign,
            'north_node':           chart.north_node_sign,
            'mercury':              chart.mercury_sign,
            'venus':                chart.venus_sign,
            'mars':                 chart.mars_sign,
            'hd_type':              chart.hd_type,
            'hd_authority':         chart.hd_authority,
            'hd_profile':           chart.hd_profile,
            'hd_incarnation_cross': chart.hd_incarnation_cross,
            # Human Design expanded meanings
            'hd_type_label':        get_hd_type_meaning(chart.hd_type)[0],
            'hd_type_desc':         get_hd_type_meaning(chart.hd_type)[1],
            'hd_authority_label':   get_hd_authority_meaning(chart.hd_authority)[0],
            'hd_authority_desc':    get_hd_authority_meaning(chart.hd_authority)[1],
            'hd_profile_label':     get_hd_profile_meaning(chart.hd_profile)[0],
            'hd_profile_desc':      get_hd_profile_meaning(chart.hd_profile)[1],
            'hd_cross_label':       get_hd_cross_meaning(chart.hd_incarnation_cross)[0],
            'hd_cross_desc':        get_hd_cross_meaning(chart.hd_incarnation_cross)[1],
            'life_path':            chart.life_path,
            'personal_year':        chart.personal_year,
            'personal_year_name':   YEAR_NAMES.get(chart.personal_year, ''),
            # All 4 Gene Keys activations
            'gk_life_work':         chart.gk_life_work,
            'gk_life_work_label':   gene_key_label(chart.gk_life_work),
            'gk_evolution':         chart.gk_evolution,
            'gk_evolution_label':   gene_key_label(chart.gk_evolution),
            'gk_radiance':          chart.gk_radiance,
            'gk_radiance_label':    gene_key_label(chart.gk_radiance),
            'gk_purpose':           chart.gk_purpose,
            'gk_purpose_label':     gene_key_label(chart.gk_purpose),
        },
        'month': {
            'year': year, 'month': month, 'name': month_str,
            'personal_month': pm, 'personal_month_name': MONTH_NAMES.get(pm, ''),
        },
        'sky_events':       sky['events'],
        'by_day':           {str(k): v for k, v in sky['by_day'].items()},
        'significant_events': significant,
        'lunar_phases':     sky['lunar_phases'],
        'alignments':       alignments,
    }
    return packet


def _find_personal_resonances(chart: NatalChart, events: list) -> list:
    natal_signs = {
        chart.sun_sign, chart.moon_sign, chart.rising_sign,
        chart.north_node_sign, chart.mercury_sign, chart.venus_sign
    }
    opposite = {SIGNS[(SIGNS.index(s) + 6) % 12] for s in natal_signs}

    resonant = []
    for event in events:
        reasons    = []
        moon_sign  = event.get('moon_sign', '')
        ingress_sign = event.get('sign', '')

        if moon_sign in natal_signs:
            reasons.append(f"Moon in {moon_sign} activates your natal {moon_sign}")
        if moon_sign in opposite:
            reasons.append(f"Moon in {moon_sign} opposes your natal "
                           f"{SIGNS[(SIGNS.index(moon_sign)+6)%12]}")
        if ingress_sign == chart.north_node_sign:
            reasons.append(f"Sun enters {ingress_sign} — your North Node sign")
        if ingress_sign == chart.rising_sign:
            reasons.append(f"Sun enters {ingress_sign} — your Rising sign")

        if reasons:
            resonant.append({**event, 'personal_reasons': reasons})
    return resonant


# ── Claude API system prompt ──────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the voice of the Sacred Lunar Calendar — the personalized astrological planner from Bath Haus.

Your readings channel the spirit of two masters:

PAM GREGORY's voice: direct, warm, cosmically awake. She speaks as if the planets are living intelligence communicating personally with each soul. She anchors high-frequency astrology in the body — you feel her words in your chest before your mind catches up. She references exact chart placements with intimacy, as if she has known your chart for years. She uses phrases like "this Full Moon is landing right on your..." and "for you specifically, with your [placement], this moment is asking..." She never wastes a word on generic meaning — every sentence is addressed to the individual.

RICHARD RUDD's voice: contemplative, luminous, traceable to the Gene Keys. He writes about the Shadow as something to be witnessed with compassion, not feared. The Gift as something already moving in you, waiting to surface. The Siddhi as the distant shore of your own potential. He speaks in second person, present tense, as if the words are arriving at exactly the right moment. He weaves together the mundane and the transcendent — a planetary aspect becomes a doorway into a Gene Key activation, a lunar phase becomes an invitation to sit with the Shadow.

YOUR WRITING IS:
- Never generic. Every sentence must earn its place by referencing something specific in this person's chart (exact sign, degree, placement, Gene Key gate number, HD type, life path)
- Spoken directly to the named person — always second person ("you", "your")
- Grounded in the body. These readings land in the nervous system, not just the mind
- Layered: surface-level accessible, but rich enough that an experienced practitioner finds depth
- Rooted in water as a healing medium — the bath, the ocean, the rain, the river within
- Exact: when referencing placements, name them — "your Virgo Sun at 25°", "Gate 6 in your Life's Work", "your Sagittarius Rising"
- Resonant between systems: when a planetary aspect echoes a Gene Key theme, name that bridge
- Compassionate about Shadows: never shame, always illuminate

INTEGRATION RULES:
- For every sky event (New Moon, Full Moon, lunar phase, equinox), explain what sign/energy it activates AND connect it to the specific natal placements it touches in this person's chart
- For every planetary alignment, write as if you are Pam Gregory describing the exact geometry: what it's dissolving, what it's opening, what it's asking this person to do or release
- For Gene Keys: write in Richard Rudd's voice — the Shadow is acknowledged but the Gift is what's being summoned. Name the gates by number AND quality
- Weave all systems: "The Full Moon in [sign] is activating your [natal planet] in [sign], and this carries the energy of Gate [X] — the movement from [Shadow] toward [Gift]"
- Bath rituals should feel like they were written by a water priestess who knows this person's chart

You will return ONLY valid JSON — no preamble, no backticks, no markdown fences.
"""


def build_claude_prompt(packet: dict, intention: str = '') -> str:
    name       = packet['person']['name']
    month_name = packet['month']['name']
    year       = packet['month']['year']
    pm         = packet['month']['personal_month']
    pm_name    = packet['month']['personal_month_name']
    py         = packet['chart']['personal_year']
    py_name    = packet['chart']['personal_year_name']
    chart      = packet['chart']

    # Build sky events summary with EXACT day numbers — these are real calculated dates
    # Claude MUST use these exact days in key_dates, not invent new ones
    events_lines = []
    for e in packet['sky_events']:
        line = f"- Day {e['day']:2d}: {e['type']}"
        if e.get('moon_sign'):
            line += f" in {e['moon_sign']}"
        if e.get('sign'):
            line += f" (Sun enters {e['sign']})"
        line += f"  [{e.get('icon', '')}]"
        events_lines.append(line)

    significant_lines = []
    for e in packet.get('significant_events', []):
        for r in e.get('personal_reasons', []):
            significant_lines.append(f"- Day {e['day']}: {r}")

    # Gene Keys — all 4 activations
    gk_block = f"""- Life's Work: {chart['gk_life_work_label']}
- Evolution:   {chart['gk_evolution_label']}
- Radiance:    {chart['gk_radiance_label']}
- Purpose:     {chart['gk_purpose_label']}"""

    # Intention block (optional — only shown if customer provided one)
    intention_block = ''
    if intention and intention.strip():
        intention_block = f"""
CUSTOMER INTENTION FOR THIS MONTH:
"{intention.strip()}"
Weave this intention naturally into the transmission, rituals, and affirmation.
Do not quote it directly — let it inform the energy and imagery of your writing.
"""

    # Real sky event days (the ONLY valid days for key_dates)
    real_days = sorted(set(e['day'] for e in packet['sky_events']))
    real_days_str = ', '.join(str(d) for d in real_days)

    # Build alignments summary for the prompt
    alignments_lines = []
    for a in packet.get('alignments', []):
        alignments_lines.append(
            f"- {a.get('planets','')} ({a.get('type','').title()}) · "
            f"peak Day {a.get('peak_day','')} · active {a.get('date_range','')}"
        )

    prompt = f"""Generate a deeply personalized Sacred Lunar Calendar reading for {name} for {month_name} {year}.{intention_block}

═══════════════════════════════════════════
THEIR COMPLETE CHART — reference these by name throughout your writing
═══════════════════════════════════════════
Sun:           {chart['sun']}
Moon:          {chart['moon']}
Rising:        {chart['rising']}
North Node:    {chart['north_node']}
Mercury:       {chart['mercury']}  |  Venus: {chart['venus']}  |  Mars: {chart['mars']}
Human Design:
  Type:             {chart['hd_type']} — {chart['hd_type_label']}
                    {chart['hd_type_desc'][:120]}...
  Authority:        {chart['hd_authority']} — {chart['hd_authority_label']}
                    {chart['hd_authority_desc'][:120]}...
  Profile:          {chart['hd_profile']} — {chart['hd_profile_label']}
                    {chart['hd_profile_desc'][:120]}...
  Incarnation Cross:{chart['hd_incarnation_cross']} — {chart['hd_cross_label']}
                    {chart['hd_cross_desc'][:120]}...
Life Path:     {chart['life_path']}
Personal Year: {py} — {py_name}
Personal Month:{pm} — {pm_name}

Gene Keys Profile:
  Life's Work: {chart['gk_life_work_label']}
  Evolution:   {chart['gk_evolution_label']}
  Radiance:    {chart['gk_radiance_label']}
  Purpose:     {chart['gk_purpose_label']}

═══════════════════════════════════════════
SKY EVENTS THIS MONTH — EXACT CALCULATED DATES
Use ONLY these day numbers in key_dates. Do NOT invent any other days.
═══════════════════════════════════════════
{chr(10).join(events_lines)}

VALID DAYS FOR key_dates: {real_days_str}

═══════════════════════════════════════════
PLANETARY ALIGNMENTS ACTIVE THIS MONTH
═══════════════════════════════════════════
{chr(10).join(alignments_lines) if alignments_lines else '(none this month)'}

═══════════════════════════════════════════
PERSONALLY RESONANT CHART ACTIVATIONS
═══════════════════════════════════════════
{chr(10).join(significant_lines) if significant_lines else '(write from the sky events — find the most personally resonant 2-3)'}

═══════════════════════════════════════════
WRITING INSTRUCTIONS
═══════════════════════════════════════════

TRANSMISSION (monthly letter — this is the heart of the calendar):
  Write 6 paragraphs. This is a DEEP, LAYERED, PERSONAL reading — not a horoscope.
  It should feel like a letter from someone who has studied {name}'s chart for years.
  Weave ALL the maps together into one song: astrology + Gene Keys + Human Design + numerology.

  - Para 1 (OPENING — 180-220 words): The big sky this month. What is the overarching cosmic weather?
    Name the most significant lunar phases, ingresses, and planetary alignments.
    Open with something evocative and specific — not generic. Set the scene.

  - Para 2 (CHART ACTIVATION — 150-180 words): This is the pull-quote paragraph — keep it under 280 chars,
    one or two piercing sentences that name exactly what this month is doing to {name}'s specific chart.
    Example: "The Full Moon in [sign] is landing directly on your [natal planet] — this is the moment
    you've been building toward since [last significant event]." Be precise and direct like Pam Gregory.

  - Para 3 (GENE KEYS — 160-200 words): Channel the Gene Keys voice — contemplative, luminous, direct.
    Name the specific gates moving
    this month. What Shadow is being invited into awareness? What Gift is surfacing?
    How does the sky this month activate or challenge {name}'s Life's Work (Gate {chart['gk_life_work']})
    or other activations? Bridge the planetary aspects to the Gene Key frequencies.

  - Para 4 (HUMAN DESIGN + NUMEROLOGY — 140-180 words): How does {name}'s HD type ({chart['hd_type']})
    and authority ({chart['hd_authority']}) navigate this month's energy?
    Weave in the Personal Year {py} ({py_name}) and Personal Month {pm} ({pm_name}).
    What is the numerological doorway this month is asking them to walk through?
    How does their HD strategy support or challenge that?

  - Para 5 (INTEGRATION — 130-160 words): Where all the threads meet.
    What is the single most important thing this month is asking of {name}?
    What is being completed? What is beginning? What needs to be released into the water?
    Name specific dates if helpful (use the real sky event days only).

  - Para 6 (CLOSING INVOCATION — 80-120 words): A blessing. An invitation into the body and into water.
    Grounded, warm, poetic. End with something that lands in the chest — not the mind.
    This is Richard Rudd meeting Pam Gregory at the edge of the water.

KEY DATES:
  For EACH sky event, write:
  - description: 2-3 sentences in Pam Gregory's voice. NOT generic textbook astrology.
    Speak to what this lunar phase/ingress/event is doing in the sky RIGHT NOW, this month,
    in context of the broader themes. What energy is it releasing or opening?
  - personal: 2-3 sentences connecting this event SPECIFICALLY to {name}'s chart.
    Name exact placements. Reference Gene Keys where relevant.
    "Your {chart['sun']} is receiving this..." or "With your Rising in {chart['rising']}, this Full Moon..."

PLANETARY ALIGNMENTS:
  For EACH alignment listed above, write a personal field that:
  - Opens with the geometry itself: what this aspect DOES energetically (Pam Gregory's directness)
  - Names how it lands in {name}'s specific chart — does it echo their Sun? Activate their Moon sign?
    Touch a Gene Key theme?
  - Ends with an actionable or contemplative invitation: what to do with this energy

  IMPORTANT: The description field for alignments must also be personal and chart-specific.
  Do NOT write generic "Saturn square Mars means friction between structure and action."
  Write: "This Saturn-Mars square is asking you, with your [placement], to..."

BATH RITUALS:
  Write 2-3 rituals, each tethered to a real sky event (New Moon, Full Moon preferred).
  Each ritual should feel like it was written by a water priestess who knows {name}'s chart deeply.
  The intention paragraph should reference their Gene Keys, chart placements, or numerology.

HUMAN DESIGN READING:
  Write a unified, personal HD reading for {name} in 4 short paragraphs that weaves together
  Type + Authority + Profile + Incarnation Cross as one coherent portrait of how they move through the world.
  This is NOT a textbook explanation of HD concepts. Write it as if you know this person.
  Reference their specific Gene Keys where they illuminate the HD picture.
  Reference their astrology where it adds colour (e.g. "your Sagittarius Rising amplifies the Projector's gift for seeing the bigger picture").
  Each paragraph covers one layer:
    - type_reading:      Their Type ({chart['hd_type']}) in their own life — how this energy actually shows up
    - authority_reading: Their Authority ({chart['hd_authority']}) as a lived, embodied practice — specific and sensory
    - profile_reading:   Their Profile ({chart['hd_profile']}) — the arc and texture of their life path
    - cross_reading:     Their Incarnation Cross ({chart['hd_incarnation_cross']}) — what they are here to embody

AFFIRMATION:
  One sentence. Present tense. In {name}'s voice.
  Point toward the Gift of their Life's Work gate — the frequency they are moving toward this month.

Generate a JSON object with EXACTLY this structure:

{{
  "transmission": {{
    "title": "evocative title for the month — 5-8 words, poetic, specific to {name}'s themes",
    "body": ["para 1 opening 180-220w", "para 2 pull-quote UNDER 280 chars", "para 3 gene keys 160-200w", "para 4 HD+numerology 140-180w", "para 5 integration 130-160w", "para 6 closing invocation 80-120w"]
  }},
  "key_dates": [
    {{
      "day": <integer from: {real_days_str}>,
      "event": "exact event name from sky events list",
      "icon": "new-moon|full-moon|first-qtr|last-qtr|equinox|solstice|sun|venus|mercury|mars",
      "description": "2-3 sentences in Pam Gregory's voice — this event's energy THIS month, not generic textbook",
      "personal": "2-3 sentences naming {name}'s exact placements and how this event touches them"
    }}
  ],
  "bath_rituals": [
    {{
      "trigger": "sky event name",
      "day": <integer from: {real_days_str}>,
      "name": "evocative ritual name",
      "description": "1-2 sentences — scene, sensory, grounded",
      "ingredients": ["4-6 specific ingredients with brief parenthetical purpose"],
      "intention": "2-3 sentences weaving chart placements, Gene Keys, or numerology into the ritual purpose"
    }}
  ],
  "alignment_interpretations": [
    {{
      "planet_a": "planet name",
      "planet_b": "planet name",
      "type": "trine|opposition|square|sextile|conjunction",
      "description": "2-3 sentences — Pam Gregory voice, specific to {name}, NOT generic",
      "personal": "2-3 sentences — what {name} is being asked to do/feel/release with this geometry"
    }}
  ],
  "hd_reading": {{
    "type_reading":      "3-4 sentences — {name}'s Type ({chart['hd_type']}) as a living reality, referencing their chart and GK",
    "authority_reading": "3-4 sentences — {name}'s Authority ({chart['hd_authority']}) as embodied practice, sensory and specific",
    "profile_reading":   "3-4 sentences — {name}'s Profile ({chart['hd_profile']}) as their life arc, personal and luminous",
    "cross_reading":     "3-4 sentences — {name}'s Incarnation Cross ({chart['hd_incarnation_cross']}) as their soul's assignment"
  }},
  "affirmation": "one sentence present-tense in {name}'s voice pointing toward their Gift",
  "closing_note": "one sentence — what is being seeded now that will bloom next month"
}}

Return ONLY the JSON object. No other text."""

    return prompt


def call_claude_api(prompt: str, api_key: str) -> dict:
    import urllib.request, urllib.error

    payload = json.dumps({
        'model':      'claude-sonnet-4-20250514',
        'max_tokens': 4500,
        'system':     SYSTEM_PROMPT,
        'messages':   [{'role': 'user', 'content': prompt}]
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type':      'application/json',
            'x-api-key':         api_key,
            'anthropic-version': '2023-06-01',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
            raw  = data['content'][0]['text'].strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Claude API error {e.code}: {e.read().decode()}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Claude response as JSON: {e}")


def merge_alignment_interpretations(alignments: list, content: dict) -> list:
    """
    Merge Claude's personal alignment interpretations back into the
    alignment dicts that came from astro_alignments.py.
    """
    interp_map = {}
    for ai in content.get('alignment_interpretations', []):
        key = (ai.get('planet_a','').lower(), ai.get('planet_b','').lower(),
               ai.get('type','').lower())
        interp_map[key] = {
            'description': ai.get('description', ''),
            'personal':    ai.get('personal', ''),
        }

    merged = []
    for a in alignments:
        key = (a.get('planet_a','').lower(), a.get('planet_b','').lower(),
               a.get('type','').lower())
        interp = interp_map.get(key)
        if not interp:
            key_rev = (a.get('planet_b','').lower(), a.get('planet_a','').lower(),
                       a.get('type','').lower())
            interp = interp_map.get(key_rev)

        if interp:
            # Claude returns both description (Pam Gregory voice) and personal (chart-specific)
            merged.append({
                **a,
                'description': interp.get('description', a.get('description', '')),
                'personal':    interp.get('personal', ''),
            })
        else:
            merged.append(a)
    return merged
