"""
astro_alignments.py
─────────────────────────────────────────────────────────────────────────────
Computes planetary alignments (aspects) active during a given month.
Consistent with astro_calc.py — same Meeus approximations, no extra deps.

Aspects detected:
  Conjunction  ☌   0°   ± 8°
  Sextile      ⚹  60°   ± 6°
  Square       □  90°   ± 7°
  Trine        △  120°  ± 8°
  Opposition   ☍  180°  ± 8°

Planets tracked: Sun, Mercury, Venus, Mars, Jupiter, Saturn
(Moon moves too fast to produce multi-day aspects — excluded)

Public API:
  get_month_alignments(year, month) → list[dict]

  Each dict matches what render_alignments_section() in calendar_generator.py
  expects, plus extra fields for the Claude prompt:
  {
    type:        'trine' | 'opposition' | 'square' | 'sextile' | 'conjunction',
    planets:     '♀ Venus △ ♂ Mars',
    planet_a:    'Venus',
    planet_b:    'Mars',
    date_range:  'Mar 8–16',
    peak_date:   datetime.date,
    peak_day:    8,
    orb:         1.4,
    description: str,   ← generic astronomical meaning (pre-filled)
    personal:    '',    ← filled by call_claude_api_alignments()
  }
─────────────────────────────────────────────────────────────────────────────
"""

import math
import calendar as cal_mod
import datetime


# ── Aspect table ──────────────────────────────────────────────────────────────

ASPECTS = [
    ('conjunction',  0,   8),
    ('sextile',     60,   6),
    ('square',      90,   7),
    ('trine',      120,   8),
    ('opposition', 180,   8),
]

ASPECT_SYMBOLS = {
    'trine':       '△',
    'opposition':  '☍',
    'square':      '□',
    'sextile':     '⚹',
    'conjunction': '☌',
}

PLANET_GLYPHS = {
    'Sun':     '☉',
    'Mercury': '☿',
    'Venus':   '♀',
    'Mars':    '♂',
    'Jupiter': '♃',
    'Saturn':  '♄',
}

# Ordered from fastest to slowest — pairs checked in this order
PLANETS = ['Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']


# ── Julian Day & centuries ─────────────────────────────────────────────────────
# Mirrors astro_calc.py — using the same approach for consistency.

def _jd(year: int, month: int, day: int) -> float:
    """Julian Day for noon UTC on the given date."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return (day + (153 * m + 2) // 5 + 365 * y
            + y // 4 - y // 100 + y // 400 - 32045) - 0.5


def _T(jd: float) -> float:
    """Julian centuries from J2000.0."""
    return (jd - 2451545.0) / 36525.0


def _norm(x: float) -> float:
    return x % 360


# ── Planetary longitudes ──────────────────────────────────────────────────────
# Same coefficients as astro_calc._approx_planet_longitude() for consistency.

def _sun_lon(T: float) -> float:
    L0 = 280.46646 + 36000.76983 * T
    M  = math.radians(_norm(357.52911 + 35999.05029 * T))
    C  = ((1.914602 - 0.004817 * T) * math.sin(M)
          + (0.019993 - 0.000101 * T) * math.sin(2 * M)
          + 0.000289 * math.sin(3 * M))
    return _norm(L0 + C)


def _mercury_lon(T: float) -> float:
    L = _norm(252.2509 + 149472.6746 * T)
    M = math.radians(_norm(168.6562 + 149472.5153 * T))
    return _norm(L + 23.4400 * math.sin(M) + 2.9818 * math.sin(2 * M))


def _venus_lon(T: float) -> float:
    L = _norm(181.9798 + 58517.8156 * T)
    M = math.radians(_norm(212.2529 + 58517.8039 * T))
    return _norm(L + 0.7758 * math.sin(M) + 0.0033 * math.sin(2 * M))


def _mars_lon(T: float) -> float:
    L = _norm(355.4330 + 19140.2993 * T)
    M = math.radians(_norm(19.3870 + 19140.2993 * T))
    return _norm(L + 10.6912 * math.sin(M) + 0.6228 * math.sin(2 * M))


def _jupiter_lon(T: float) -> float:
    L = _norm(34.3515 + 3034.9057 * T)
    M = math.radians(_norm(20.9202 + 3034.9061 * T))
    return _norm(L + 5.5549 * math.sin(M) + 0.1683 * math.sin(2 * M))


def _saturn_lon(T: float) -> float:
    L = _norm(50.0774 + 1222.1138 * T)
    M = math.radians(_norm(317.0207 + 1221.5515 * T))
    return _norm(L + 6.3585 * math.sin(M) - 0.2204 * math.sin(2 * M))


LON_FN = {
    'Sun':     _sun_lon,
    'Mercury': _mercury_lon,
    'Venus':   _venus_lon,
    'Mars':    _mars_lon,
    'Jupiter': _jupiter_lon,
    'Saturn':  _saturn_lon,
}


def _planet_lons(jd: float) -> dict[str, float]:
    T = _T(jd)
    return {p: fn(T) for p, fn in LON_FN.items()}


# ── Aspect geometry ───────────────────────────────────────────────────────────

def _angular_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def _check_aspect(lon_a: float, lon_b: float) -> tuple[str, float] | None:
    """Return (aspect_name, orb_in_degrees) if within orb, else None."""
    sep = _angular_distance(lon_a, lon_b)
    for name, angle, max_orb in ASPECTS:
        orb = abs(sep - angle)
        if orb <= max_orb:
            return name, round(orb, 2)
    return None


# ── Generic descriptions ──────────────────────────────────────────────────────

_PLANET_NATURE = {
    'Sun':     'vitality, identity, and creative will',
    'Mercury': 'mind, communication, and perception',
    'Venus':   'love, beauty, and magnetic attraction',
    'Mars':    'desire, courage, and initiating force',
    'Jupiter': 'expansion, wisdom, and abundance',
    'Saturn':  'structure, discipline, and earned mastery',
}

_ASPECT_QUALITY = {
    'conjunction':  ('merge and amplify',                'Intensifying'),
    'sextile':      ('open supportive pathways between', 'Harmonious'),
    'square':       ('create productive friction between','Activating'),
    'trine':        ('flow freely between',               'Easeful'),
    'opposition':   ('illuminate the polarity between',   'Clarifying'),
}

def _generic_description(pa: str, pb: str, aspect: str) -> str:
    verb, quality = _ASPECT_QUALITY.get(aspect, ('connect', 'Notable'))
    na = _PLANET_NATURE.get(pa, pa.lower())
    nb = _PLANET_NATURE.get(pb, pb.lower())
    return (
        f"{quality} geometry between {pa} and {pb}. "
        f"The energies of {na} {verb} the forces of {nb}. "
        f"When planets form a precise {aspect}, their qualities become "
        f"directly available to channel."
    )


# ── Main public function ──────────────────────────────────────────────────────

def get_month_alignments(year: int, month: int) -> list[dict]:
    """
    Scan the month day by day.

    Returns the most significant planetary aspects — one entry per
    planet-pair/aspect combination, at the day of tightest orb.
    Capped at 6 alignments (fills the Planetary Alignments page cleanly).
    Sorted tightest orb first (most exact = most potent).

    The 'personal' field in each dict is empty string — it gets filled
    by call_claude_api_alignments() in personalization.py.
    """
    num_days = cal_mod.monthrange(year, month)[1]
    month_abbr = datetime.date(year, month, 1).strftime('%b')

    # Pass 1 — find the peak-orb day for each (pa, pb, aspect_type)
    best: dict[tuple, dict] = {}
    for day in range(1, num_days + 1):
        jd = _jd(year, month, day)
        lons = _planet_lons(jd)
        for i, pa in enumerate(PLANETS):
            for pb in PLANETS[i + 1:]:
                result = _check_aspect(lons[pa], lons[pb])
                if result is None:
                    continue
                aspect_name, orb = result
                key = (pa, pb, aspect_name)
                if key not in best or orb < best[key]['orb']:
                    best[key] = {'day': day, 'orb': orb}

    if not best:
        return []

    # Pass 2 — collect every active day per confirmed key (for date ranges)
    active_days: dict[tuple, list[int]] = {k: [] for k in best}
    for day in range(1, num_days + 1):
        jd = _jd(year, month, day)
        lons = _planet_lons(jd)
        for i, pa in enumerate(PLANETS):
            for pb in PLANETS[i + 1:]:
                result = _check_aspect(lons[pa], lons[pb])
                if result is None:
                    continue
                aspect_name, _ = result
                key = (pa, pb, aspect_name)
                if key in active_days:
                    active_days[key].append(day)

    # Build output
    events = []
    for key, info in best.items():
        pa, pb, aspect_name = key

        sym = ASPECT_SYMBOLS.get(aspect_name, '')
        ga  = PLANET_GLYPHS.get(pa, '')
        gb  = PLANET_GLYPHS.get(pb, '')
        planets_str = f"{ga} {pa} {sym} {gb} {pb}"

        days = sorted(active_days.get(key, [info['day']]))
        if len(days) <= 1:
            date_range = f"{month_abbr} {days[0]}"
        elif days[-1] - days[0] == len(days) - 1:
            date_range = f"{month_abbr} {days[0]}–{days[-1]}"    # contiguous
        else:
            date_range = f"{month_abbr} {days[0]}–{days[-1]}"    # sparse, show span

        events.append({
            'type':        aspect_name,
            'planet_a':    pa,
            'planet_b':    pb,
            'planets':     planets_str,
            'date_range':  date_range,
            'peak_date':   datetime.date(year, month, info['day']),
            'peak_day':    info['day'],
            'orb':         info['orb'],
            'description': _generic_description(pa, pb, aspect_name),
            'personal':    '',
        })

    events.sort(key=lambda e: e['orb'])
    return events[:6]
