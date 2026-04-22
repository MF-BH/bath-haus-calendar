"""
astro_calc.py
─────────────────────────────────────────────────────────────────────────────
Astronomical calculation layer for the Sacred Lunar Calendar engine.

BACKEND SELECTION (set at top of file):
  'swisseph' — production-grade, arc-second precision (requires pyswisseph)
  'meeus'    — pure Python Meeus algorithms, ~1-2° accuracy, no dependencies

Switch to 'swisseph' in production:
  pip install pyswisseph
  Download ephemeris files from https://www.astro.com/ftp/swisseph/ephe/
  Set EPHE_PATH below to the directory containing those files.

All times returned as UTC datetime objects.
All angles in decimal degrees (0–360).
─────────────────────────────────────────────────────────────────────────────
"""

import math
import datetime
from dataclasses import dataclass
from typing import Optional

# ── Backend selection ─────────────────────────────────────────────────────────

BACKEND = 'meeus'   # switch to 'swisseph' in production
EPHE_PATH = '/usr/share/ephe'  # path to Swiss Ephemeris data files

# Try to import swisseph; fall back gracefully
_swe = None
if BACKEND == 'swisseph':
    try:
        import swisseph as swe
        swe.set_ephe_path(EPHE_PATH)
        _swe = swe
    except ImportError:
        import warnings
        warnings.warn(
            "pyswisseph not installed — falling back to Meeus approximations.\n"
            "Install with: pip install pyswisseph\n"
            "Download ephemeris files from: https://www.astro.com/ftp/swisseph/ephe/"
        )

# ── Zodiac helpers ────────────────────────────────────────────────────────────

SIGNS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]
SIGN_SYMBOLS = ['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓']

def longitude_to_sign(lon: float) -> tuple:
    """Return (sign_name, degree_within_sign, symbol)."""
    lon = lon % 360
    idx = int(lon // 30)
    deg = lon % 30
    return SIGNS[idx], deg, SIGN_SYMBOLS[idx]

def sign_symbol(sign_name: str) -> str:
    idx = SIGNS.index(sign_name)
    return SIGN_SYMBOLS[idx]

# ── Julian Day helpers ────────────────────────────────────────────────────────

def datetime_to_jd(dt: datetime.datetime) -> float:
    """Convert UTC datetime to Julian Day Number."""
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = (dt.day + (153 * m + 2) // 5 + 365 * y
           + y // 4 - y // 100 + y // 400 - 32045)
    frac = (dt.hour + dt.minute / 60 + dt.second / 3600) / 24 - 0.5
    return jdn + frac

def jd_to_datetime(jd: float) -> datetime.datetime:
    """Convert Julian Day Number to UTC datetime."""
    jd = jd + 0.5
    z = int(jd)
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    frac_day = f
    hour = int(frac_day * 24)
    minute = int((frac_day * 24 - hour) * 60)
    second = int(((frac_day * 24 - hour) * 60 - minute) * 60)
    return datetime.datetime(year, month, day, hour, minute, second,
                             tzinfo=datetime.timezone.utc)

# ── Planet longitude — unified interface ──────────────────────────────────────

# Swiss Ephemeris planet IDs
_SWE_PLANETS = {
    'sun':     0,
    'moon':    1,
    'mercury': 2,
    'venus':   3,
    'mars':    4,
    'jupiter': 5,
    'saturn':  6,
    'uranus':  7,
    'neptune': 8,
    'pluto':   9,
    'node':   11,  # mean north node
}

def get_planet_longitude(jd: float, planet: str) -> float:
    """
    Return ecliptic longitude for a planet at JD.
    Uses Swiss Ephemeris if available, else Meeus approximation.
    """
    if _swe is not None:
        planet_id = _SWE_PLANETS.get(planet)
        if planet_id is not None:
            result = _swe.calc_ut(jd, planet_id, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
            return result[0][0] % 360
    # Fallback to Meeus
    return _meeus_planet_longitude(jd, planet)


def _meeus_planet_longitude(jd: float, planet: str) -> float:
    """Meeus approximation for planet longitudes."""
    T = (jd - 2451545.0) / 36525
    if planet == 'sun':
        return _sun_longitude(jd)
    elif planet == 'moon':
        return _approx_moon_longitude(jd)
    elif planet == 'mercury':
        L = 252.2509 + 149472.6746 * T
        M = math.radians((168.6562 + 149472.5153 * T) % 360)
        return (L + 23.4400 * math.sin(M)) % 360
    elif planet == 'venus':
        L = 181.9798 + 58517.8156 * T
        M = math.radians((212.2529 + 58517.8039 * T) % 360)
        return (L + 0.7758 * math.sin(M)) % 360
    elif planet == 'mars':
        L = 355.4330 + 19140.2993 * T
        M = math.radians((19.3870 + 19140.2993 * T) % 360)
        return (L + 10.6912 * math.sin(M)) % 360
    elif planet == 'jupiter':
        L = (34.351519 + 3034.905675 * T) % 360
        M = math.radians((20.9 + 3034.9 * T) % 360)
        return (L + 5.5549 * math.sin(M) + 0.1683 * math.sin(2*M)) % 360
    elif planet == 'saturn':
        L = (50.077444 + 1222.113777 * T) % 360
        M = math.radians((317.02 + 1222.11 * T) % 360)
        return (L + 6.3585 * math.sin(M) + 0.2204 * math.sin(2*M)) % 360
    elif planet == 'node':
        return (125.0445479 - 1934.1362608 * T) % 360
    return 0.0


def _sun_longitude(jd: float) -> float:
    """Meeus Sun longitude, ch. 25."""
    T = (jd - 2451545.0) / 36525
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T**2
    M  = 357.52911 + 35999.05029 * T - 0.0001537 * T**2
    M_r = math.radians(M % 360)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T**2) * math.sin(M_r)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M_r)
         + 0.000289 * math.sin(3 * M_r))
    sun_lon = (L0 + C) % 360
    omega = math.radians(125.04 - 1934.136 * T)
    return (sun_lon - 0.00569 - 0.00478 * math.sin(omega)) % 360


def _approx_moon_longitude(jd: float) -> float:
    """Meeus Moon longitude, simplified."""
    T = (jd - 2451545.0) / 36525
    L0 = 218.3164477 + 481267.88123421 * T
    Mprime = 134.9633964 + 477198.8675055 * T
    F  = 93.2720950 + 483202.0175233 * T
    lon = L0 + 6.289 * math.sin(math.radians(Mprime))
    lon -= 1.274 * math.sin(math.radians(2 * F - Mprime))
    lon += 0.658 * math.sin(math.radians(2 * F))
    lon -= 0.214 * math.sin(math.radians(2 * Mprime))
    return lon % 360


# ── Meeus lunar phase calculator ──────────────────────────────────────────────

def _lunar_phase_jd(year: float, phase: int) -> float:
    """
    Return JD of a lunar phase near the given fractional year.
    phase: 0=New, 1=First Quarter, 2=Full, 3=Last Quarter
    Meeus, Astronomical Algorithms ch. 49
    """
    k = round((year - 2000) * 12.3685) + phase * 0.25
    T = k / 1236.85
    JDE = (2451550.09766
           + 29.530588861 * k
           + 0.00015437 * T**2
           - 0.000000150 * T**3
           + 0.00000000073 * T**4)
    M = math.radians(2.5534 + 29.10535670 * k
                     - 0.0000014 * T**2 - 0.00000011 * T**3)
    Mprime = math.radians(201.5643 + 385.81693528 * k
                          + 0.0107582 * T**2 + 0.00001238 * T**3
                          - 0.000000058 * T**4)
    F = math.radians(160.7108 + 390.67050284 * k
                     - 0.0016118 * T**2 - 0.00000227 * T**3
                     + 0.000000011 * T**4)
    Omega = math.radians(124.7746 - 1.56375588 * k
                         + 0.0020672 * T**2 + 0.00000215 * T**3)
    if phase == 0:
        corr = (-0.40720 * math.sin(Mprime) + 0.17241 * math.sin(M)
                + 0.01608 * math.sin(2*Mprime) + 0.01039 * math.sin(2*F)
                + 0.00739 * math.sin(Mprime-M) - 0.00514 * math.sin(Mprime+M)
                + 0.00208 * math.sin(2*M) - 0.00111 * math.sin(Mprime-2*F)
                - 0.00057 * math.sin(Mprime+2*F) + 0.00056 * math.sin(2*Mprime+M)
                - 0.00042 * math.sin(3*Mprime) + 0.00042 * math.sin(M+2*F)
                + 0.00038 * math.sin(M-2*F) - 0.00024 * math.sin(2*Mprime-M)
                - 0.00017 * math.sin(Omega) - 0.00007 * math.sin(Mprime+2*M))
    elif phase == 2:
        corr = (-0.40614 * math.sin(Mprime) + 0.17302 * math.sin(M)
                + 0.01614 * math.sin(2*Mprime) + 0.01043 * math.sin(2*F)
                + 0.00734 * math.sin(Mprime-M) - 0.00515 * math.sin(Mprime+M)
                + 0.00209 * math.sin(2*M) - 0.00111 * math.sin(Mprime-2*F)
                - 0.00057 * math.sin(Mprime+2*F) + 0.00056 * math.sin(2*Mprime+M)
                - 0.00042 * math.sin(3*Mprime) + 0.00042 * math.sin(M+2*F)
                + 0.00038 * math.sin(M-2*F) - 0.00024 * math.sin(2*Mprime-M)
                - 0.00017 * math.sin(Omega) - 0.00007 * math.sin(Mprime+2*M))
    else:
        corr = (-0.62801 * math.sin(Mprime) + 0.17172 * math.sin(M)
                - 0.01183 * math.sin(Mprime+M) + 0.00862 * math.sin(2*Mprime)
                + 0.00804 * math.sin(2*F) + 0.00454 * math.sin(Mprime-M)
                + 0.00204 * math.sin(2*M) - 0.00180 * math.sin(Mprime-2*F)
                - 0.00070 * math.sin(Mprime+2*F) - 0.00040 * math.sin(3*Mprime)
                - 0.00034 * math.sin(2*Mprime-M) + 0.00032 * math.sin(M+2*F)
                + 0.00032 * math.sin(M-2*F) - 0.00028 * math.sin(Mprime+2*M)
                + 0.00027 * math.sin(2*Mprime+M) - 0.00017 * math.sin(Omega)
                - 0.00005 * math.sin(Mprime-M-2*F))
    return JDE + corr


def get_lunar_phases_in_month(year: int, month: int) -> list:
    frac_year = year + (month - 1) / 12.0
    phase_names = {0: 'New Moon', 1: 'First Quarter', 2: 'Full Moon', 3: 'Last Quarter'}
    phase_icons = {0: 'new-moon', 1: 'first-qtr', 2: 'full-moon', 3: 'last-qtr'}
    results = []
    for offset in range(-2, 5):
        for phase_idx in [0, 1, 2, 3]:
            jd = _lunar_phase_jd(frac_year, phase_idx)
            jd += offset * 29.530588861
            dt = jd_to_datetime(jd)
            if dt.year == year and dt.month == month:
                moon_lon = get_planet_longitude(jd, 'moon')
                sign, deg, sym = longitude_to_sign(moon_lon)
                results.append({
                    'type': phase_names[phase_idx],
                    'icon': phase_icons[phase_idx],
                    'datetime_utc': dt,
                    'day': dt.day,
                    'moon_sign': sign,
                    'moon_degree': round(deg, 1),
                    'moon_symbol': sym,
                    'time_str': dt.strftime('%-I:%M %p UTC'),
                })
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x['datetime_utc']):
        key = (r['type'], r['day'])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# ── Solar ingresses ───────────────────────────────────────────────────────────

def get_solar_ingresses_in_month(year: int, month: int) -> list:
    """Return Sun sign ingresses occurring in this month."""
    start = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
    end = (datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
           if month == 12
           else datetime.datetime(year, month + 1, 1, tzinfo=datetime.timezone.utc))
    results = []
    step = datetime.timedelta(hours=6)
    dt = start
    prev_sign_idx = int(get_planet_longitude(datetime_to_jd(dt), 'sun') // 30)
    while dt < end:
        dt_next = dt + step
        lon = get_planet_longitude(datetime_to_jd(dt_next), 'sun')
        sign_idx = int(lon // 30)
        if sign_idx != prev_sign_idx:
            lo, hi = datetime_to_jd(dt), datetime_to_jd(dt_next)
            for _ in range(20):
                mid = (lo + hi) / 2
                lon_mid = get_planet_longitude(mid, 'sun')
                if int(lon_mid // 30) == prev_sign_idx:
                    lo = mid
                else:
                    hi = mid
            ingress_dt = jd_to_datetime((lo + hi) / 2)
            if ingress_dt.year == year and ingress_dt.month == month:
                sign = SIGNS[sign_idx % 12]
                results.append({
                    'type': f'Sun enters {sign}',
                    'icon': 'sun',
                    'datetime_utc': ingress_dt,
                    'day': ingress_dt.day,
                    'sign': sign,
                    'sign_symbol': SIGN_SYMBOLS[sign_idx % 12],
                    'time_str': ingress_dt.strftime('%-I:%M %p UTC'),
                })
            prev_sign_idx = sign_idx
        else:
            prev_sign_idx = sign_idx
        dt = dt_next
    return results


# ── Wheel of the Year ─────────────────────────────────────────────────────────

WHEEL_EVENTS = [
    {'name': 'Spring Equinox',  'icon': 'equinox',    'target_lon': 0.0,   'subtype': 'solar'},
    {'name': 'Summer Solstice', 'icon': 'solstice',   'target_lon': 90.0,  'subtype': 'solar'},
    {'name': 'Autumn Equinox',  'icon': 'equinox',    'target_lon': 180.0, 'subtype': 'solar'},
    {'name': 'Winter Solstice', 'icon': 'solstice',   'target_lon': 270.0, 'subtype': 'solar'},
    {'name': 'Imbolc',          'icon': 'imbolc',     'target_lon': 315.0, 'subtype': 'crossquarter'},
    {'name': 'Beltane',         'icon': 'beltane',    'target_lon': 45.0,  'subtype': 'crossquarter'},
    {'name': 'Lughnasadh',      'icon': 'lughnasadh', 'target_lon': 135.0, 'subtype': 'crossquarter'},
    {'name': 'Samhain',         'icon': 'samhain',    'target_lon': 225.0, 'subtype': 'crossquarter'},
]

WHEEL_DESCRIPTIONS = {
    'Spring Equinox':  'Equal day and night. The astrological new year. Emergence and initiation.',
    'Summer Solstice': 'The longest day. Peak light. Fullness and outward expression.',
    'Autumn Equinox':  'Equal day and night. Harvest and balance. Turning inward.',
    'Winter Solstice': 'The longest night. Stillness and the return of light.',
    'Imbolc':          'First stirrings of spring. Seeds beneath snow. Creative quickening.',
    'Beltane':         'Peak of spring. Vitality and the fire of life. Full creative power.',
    'Lughnasadh':      'First harvest. What has ripened. Gratitude for what was built.',
    'Samhain':         'The thinning of the veil. Ancestors and completion. The dark half begins.',
}


def get_wheel_events_in_month(year: int, month: int) -> list:
    start = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
    end = (datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
           if month == 12
           else datetime.datetime(year, month + 1, 1, tzinfo=datetime.timezone.utc))
    results = []
    for event in WHEEL_EVENTS:
        target = event['target_lon']
        step = datetime.timedelta(hours=6)
        cursor = start
        prev_lon = get_planet_longitude(datetime_to_jd(cursor), 'sun')
        while cursor < end:
            cursor_next = cursor + step
            lon = get_planet_longitude(datetime_to_jd(cursor_next), 'sun')
            prev_dist = (prev_lon - target) % 360
            curr_dist = (lon - target) % 360
            if prev_dist > 180 and curr_dist <= 180:
                lo_jd = datetime_to_jd(cursor)
                hi_jd = datetime_to_jd(cursor_next)
                for _ in range(24):
                    mid_jd = (lo_jd + hi_jd) / 2
                    mid_lon = get_planet_longitude(mid_jd, 'sun')
                    if (mid_lon - target) % 360 > 180:
                        lo_jd = mid_jd
                    else:
                        hi_jd = mid_jd
                exact_dt = jd_to_datetime((lo_jd + hi_jd) / 2)
                if exact_dt.year == year and exact_dt.month == month:
                    results.append({
                        'type':         event['name'],
                        'icon':         event['icon'],
                        'subtype':      event['subtype'],
                        'datetime_utc': exact_dt,
                        'day':          exact_dt.day,
                        'description':  WHEEL_DESCRIPTIONS[event['name']],
                        'time_str':     exact_dt.strftime('%-I:%M %p UTC'),
                    })
                break
            prev_lon = lon
            cursor = cursor_next
    results.sort(key=lambda x: x['datetime_utc'])
    return results


# ── Ascendant (Rising sign) ───────────────────────────────────────────────────

def get_ascendant(jd: float, lat: float, lon: float) -> float:
    """
    Calculate Ascendant longitude.
    Uses Swiss Ephemeris houses (Placidus) if available, else Meeus approximation.
    """
    if _swe is not None:
        try:
            cusps, ascmc = _swe.houses(jd, lat, lon, b'P')  # Placidus
            return ascmc[0] % 360  # ascmc[0] is the Ascendant
        except Exception:
            pass
    return _meeus_ascendant(jd, lat, lon)


def _meeus_ascendant(jd: float, lat: float, lon: float) -> float:
    """Meeus approximation for Ascendant."""
    T = (jd - 2451545.0) / 36525
    theta0 = 280.46061837 + 360.98564736629 * (jd - 2451545) + 0.000387933 * T**2
    lst = (theta0 + lon) % 360
    eps = math.radians(23.4393 - 0.013 * T)
    lst_r = math.radians(lst)
    lat_r = math.radians(lat)
    asc = math.atan2(math.cos(lst_r),
                     -(math.sin(lst_r) * math.cos(eps)
                       + math.tan(lat_r) * math.sin(eps)))
    return math.degrees(asc) % 360


# ── Human Design calculation ──────────────────────────────────────────────────
#
# Human Design is derived from two chart moments:
#   Conscious (birth):    planetary positions at exact birth datetime
#   Unconscious (design): planetary positions exactly 88.736° of Sun travel
#                         before birth (~88 days prior)
#
# Each position maps to one of 64 gates (I Ching hexagrams) and one of
# 6 lines within that gate. Gates are assigned to the 9 energy centers
# via fixed channels. Defined centers determine Type and Authority.
#
# The gate/channel/center structure below is the public, factual architecture
# of the Human Design system — not Ra Uru Hu's interpretive language.
# ─────────────────────────────────────────────────────────────────────────────

# Gate mapping: ecliptic longitude → gate number (1–64)
# Gates are assigned in I Ching order around the wheel, starting at ~Capricorn 0°.
# This is the standard, publicly documented HD mandala structure.
# Reference: the HD mandala assigns gates to 5.625° segments of the ecliptic.
# Starting point: Gate 41 at 0° Capricorn (Winter Solstice point).

# Gate sequence around the zodiac wheel starting from 0° Capricorn:
GATE_SEQUENCE = [
    41, 19, 13, 49, 30, 55, 37, 63, 22, 36, 25, 17,
    21, 51, 42, 3,  27, 24, 2,  23, 8,  20, 16, 35,
    45, 12, 15, 52, 39, 53, 62, 56, 31, 33, 7,  4,
    29, 59, 40, 64, 47, 6,  46, 18, 48, 57, 32, 50,
    28, 44, 1,  43, 14, 34, 9,  5,  26, 11, 10, 58,
    38, 54, 61, 60
]

def longitude_to_gate_line(lon: float) -> tuple:
    """
    Convert ecliptic longitude to (gate, line).
    Each gate spans 360/64 = 5.625 degrees.
    Each line spans 5.625/6 = 0.9375 degrees.
    Starting point: Gate 41 at 270° (0° Capricorn).
    Returns (gate_number, line_number) where line is 1–6.
    """
    # Offset so 270° (Capricorn 0°) = 0 in our gate wheel
    adjusted = (lon - 270.0) % 360
    gate_idx = int(adjusted / 5.625)
    gate_idx = min(gate_idx, 63)  # safety clamp
    gate = GATE_SEQUENCE[gate_idx]
    # Line within gate (1–6)
    pos_within_gate = adjusted - (gate_idx * 5.625)
    line = int(pos_within_gate / 0.9375) + 1
    line = min(max(line, 1), 6)
    return gate, line


# Channels: each connects two gates between two centers.
# A channel is defined when BOTH gates are active (conscious or unconscious).
# Structure: {(gate_a, gate_b): (center_a, center_b)}
CHANNELS = {
    (1, 8):   ('G', 'Throat'),
    (2, 14):  ('G', 'Sacral'),
    (3, 60):  ('Sacral', 'Root'),
    (4, 63):  ('Ajna', 'Head'),
    (5, 15):  ('Sacral', 'G'),
    (6, 59):  ('Sacral', 'Emotional'),
    (7, 31):  ('G', 'Throat'),
    (9, 52):  ('Sacral', 'Root'),
    (10, 20): ('G', 'Throat'),
    (10, 34): ('G', 'Sacral'),
    (10, 57): ('G', 'Spleen'),
    (11, 56): ('Ajna', 'Throat'),
    (12, 22): ('Throat', 'Emotional'),
    (13, 33): ('G', 'Throat'),
    (16, 48): ('Throat', 'Spleen'),
    (17, 62): ('Ajna', 'Throat'),
    (18, 58): ('Spleen', 'Root'),
    (19, 49): ('Root', 'Emotional'),
    (20, 34): ('Throat', 'Sacral'),
    (20, 57): ('Throat', 'Spleen'),
    (21, 45): ('Ego', 'Throat'),
    (23, 43): ('Throat', 'Ajna'),
    (24, 61): ('Ajna', 'Head'),
    (25, 51): ('G', 'Ego'),
    (26, 44): ('Ego', 'Spleen'),
    (27, 50): ('Sacral', 'Spleen'),
    (28, 38): ('Spleen', 'Root'),
    (29, 46): ('Sacral', 'G'),
    (30, 41): ('Emotional', 'Root'),
    (32, 54): ('Spleen', 'Root'),
    (35, 36): ('Throat', 'Emotional'),
    (37, 40): ('Emotional', 'Ego'),
    (39, 55): ('Root', 'Emotional'),
    (42, 53): ('Sacral', 'Root'),
    (47, 64): ('Ajna', 'Head'),
}

# Which gates belong to which center
CENTER_GATES = {
    'Head':      {61, 63, 64},
    'Ajna':      {4, 11, 17, 23, 24, 43, 47},
    'Throat':    {8, 12, 16, 20, 23, 31, 33, 35, 45, 56, 62},
    'G':         {1, 2, 7, 10, 13, 15, 25, 29, 46},
    'Ego':       {21, 26, 40, 51},
    'Sacral':    {3, 5, 9, 14, 27, 29, 34, 42, 59},
    'Spleen':    {10, 16, 18, 26, 27, 28, 32, 33, 44, 48, 50, 57},
    'Emotional': {6, 12, 19, 22, 30, 36, 37, 39, 41, 49, 55},
    'Root':      {19, 28, 32, 38, 39, 41, 52, 53, 54, 58, 60},
}

MOTOR_CENTERS = {'Sacral', 'Emotional', 'Ego', 'Root'}
THROAT_CONNECTED_MOTORS = {'Sacral', 'Emotional', 'Ego', 'Root'}

def _get_design_jd(birth_jd: float) -> float:
    """
    Calculate the Design (unconscious) JD — the moment 88.736° of solar
    travel before birth. We step backward until Sun has moved exactly that far.
    """
    target_lon = (get_planet_longitude(birth_jd, 'sun') - 88.736) % 360
    # Approximate: 88.736° / 360° * 365.25 days ≈ 90 days
    approx_jd = birth_jd - 90.0
    # Binary search to find exact moment
    lo_jd = birth_jd - 95.0
    hi_jd = birth_jd - 85.0
    for _ in range(40):
        mid_jd = (lo_jd + hi_jd) / 2
        mid_lon = get_planet_longitude(mid_jd, 'sun')
        # Angular distance from target
        dist = (mid_lon - target_lon) % 360
        if dist < 180:
            hi_jd = mid_jd
        else:
            lo_jd = mid_jd
    return (lo_jd + hi_jd) / 2


def _collect_active_gates(jd: float) -> set:
    """Return set of active gate numbers for a given JD (all 10 planets)."""
    planets = ['sun', 'moon', 'mercury', 'venus', 'mars',
               'jupiter', 'saturn', 'uranus', 'neptune', 'node']
    gates = set()
    for planet in planets:
        try:
            lon = get_planet_longitude(jd, planet)
            gate, _ = longitude_to_gate_line(lon)
            gates.add(gate)
        except Exception:
            pass
    return gates


def _get_defined_centers(active_gates: set) -> set:
    """
    Determine which centers are defined given a set of active gates.
    A center is defined when a complete channel (both gates) is active.
    """
    defined = set()
    for (g1, g2), (c1, c2) in CHANNELS.items():
        if g1 in active_gates and g2 in active_gates:
            defined.add(c1)
            defined.add(c2)
    return defined


def _determine_type(defined_centers: set) -> str:
    """
    Determine HD Type from defined centers.
    Rules (publicly documented):
      Manifestor:          Throat defined + connected to a motor, Sacral NOT defined
      Generator:           Sacral defined, Throat NOT connected to Sacral directly
      Manifesting Generator: Sacral defined, Throat connected to Sacral (via channel)
      Projector:           Sacral NOT defined, Throat NOT connected to motor
      Reflector:           No centers defined
    """
    if not defined_centers:
        return 'Reflector'

    sacral_defined = 'Sacral' in defined_centers
    throat_defined = 'Throat' in defined_centers

    # Check if Throat is directly connected to Sacral via a channel
    throat_sacral_connected = False
    for (g1, g2), (c1, c2) in CHANNELS.items():
        if set([c1, c2]) == {'Throat', 'Sacral'}:
            throat_sacral_connected = True
            break

    # Check if Throat is connected to any motor
    throat_motor_connected = any(
        m in defined_centers and throat_defined
        for m in MOTOR_CENTERS
    )

    if sacral_defined:
        if throat_defined and throat_sacral_connected:
            return 'Manifesting Generator'
        return 'Generator'
    elif throat_defined and throat_motor_connected:
        return 'Manifestor'
    else:
        return 'Projector'


def _determine_authority(defined_centers: set, hd_type: str) -> str:
    """
    Determine inner Authority from defined centers.
    Priority order (publicly documented):
    """
    if hd_type == 'Reflector':
        return 'Lunar'
    if 'Emotional' in defined_centers:
        return 'Emotional'
    if 'Sacral' in defined_centers:
        return 'Sacral'
    if 'Spleen' in defined_centers:
        return 'Splenic'
    if 'Ego' in defined_centers:
        return 'Ego'
    if 'G' in defined_centers:
        return 'Self'
    return 'Mental'


def _determine_profile(conscious_line: int, unconscious_line: int) -> str:
    """Profile is the conscious/unconscious line combination of the Sun gate."""
    return f"{conscious_line}/{unconscious_line}"


def _determine_definition(defined_centers: set) -> str:
    """
    Single, Split, Triple Split, or Quadruple Split definition.
    Simplified: count connected groups of defined centers.
    """
    if not defined_centers:
        return 'No Definition'
    # Build adjacency from channels
    adj = {c: set() for c in defined_centers}
    for (g1, g2), (c1, c2) in CHANNELS.items():
        if c1 in defined_centers and c2 in defined_centers:
            adj[c1].add(c2)
            adj[c2].add(c1)
    # Count connected components via BFS
    visited = set()
    components = 0
    for start in defined_centers:
        if start not in visited:
            components += 1
            queue = [start]
            while queue:
                node = queue.pop()
                if node not in visited:
                    visited.add(node)
                    queue.extend(adj[node] - visited)
    labels = {1: 'Single Definition', 2: 'Split Definition',
              3: 'Triple Split', 4: 'Quadruple Split'}
    return labels.get(components, f'{components}-way Split')


def calculate_human_design(birth_jd: float) -> dict:
    """
    Calculate Human Design chart from birth Julian Day.

    Returns dict with:
      type, authority, profile, definition,
      conscious_gates (list of (gate, line) tuples),
      unconscious_gates (list of (gate, line) tuples),
      defined_centers (set of center names),
      active_gates (set of all gate numbers)
    """
    design_jd = _get_design_jd(birth_jd)

    planets = ['sun', 'moon', 'mercury', 'venus', 'mars',
               'jupiter', 'saturn', 'uranus', 'neptune', 'node']

    conscious_gates = []
    unconscious_gates = []
    all_active_gates = set()

    for planet in planets:
        try:
            c_lon = get_planet_longitude(birth_jd, planet)
            u_lon = get_planet_longitude(design_jd, planet)
            c_gate, c_line = longitude_to_gate_line(c_lon)
            u_gate, u_line = longitude_to_gate_line(u_lon)
            conscious_gates.append((planet, c_gate, c_line))
            unconscious_gates.append((planet, u_gate, u_line))
            all_active_gates.add(c_gate)
            all_active_gates.add(u_gate)
        except Exception:
            pass

    defined_centers = _get_defined_centers(all_active_gates)
    hd_type = _determine_type(defined_centers)
    authority = _determine_authority(defined_centers, hd_type)
    definition = _determine_definition(defined_centers)

    # Profile from conscious Sun gate line / unconscious Sun gate line
    c_sun_line = next((line for planet, gate, line in conscious_gates
                       if planet == 'sun'), 1)
    u_sun_line = next((line for planet, gate, line in unconscious_gates
                       if planet == 'sun'), 1)
    profile = _determine_profile(c_sun_line, u_sun_line)

    # Incarnation Cross: conscious Sun/Earth gates + unconscious Sun/Earth gates
    c_sun_gate  = next((gate for p, gate, l in conscious_gates   if p == 'sun'),  0)
    c_earth_gate = (GATE_SEQUENCE[(GATE_SEQUENCE.index(c_sun_gate) + 32) % 64]
                    if c_sun_gate in GATE_SEQUENCE else 0)
    u_sun_gate  = next((gate for p, gate, l in unconscious_gates  if p == 'sun'),  0)
    u_earth_gate = (GATE_SEQUENCE[(GATE_SEQUENCE.index(u_sun_gate) + 32) % 64]
                    if u_sun_gate in GATE_SEQUENCE else 0)
    incarnation_cross = f"Gate {c_sun_gate}/{c_earth_gate} · {u_sun_gate}/{u_earth_gate}"

    return {
        'type':              hd_type,
        'authority':         authority,
        'profile':           profile,
        'definition':        definition,
        'incarnation_cross': incarnation_cross,
        'defined_centers':   defined_centers,
        'active_gates':      all_active_gates,
        'conscious_gates':   conscious_gates,
        'unconscious_gates': unconscious_gates,
        'conscious_sun_gate':   c_sun_gate,
        'unconscious_sun_gate': u_sun_gate,
    }


# ── Natal chart dataclass ─────────────────────────────────────────────────────

@dataclass
class NatalChart:
    # Astrology
    sun_sign: str
    sun_degree: float
    sun_longitude: float
    moon_sign: str
    moon_degree: float
    rising_sign: str
    rising_degree: float
    mercury_sign: str
    venus_sign: str
    mars_sign: str
    jupiter_sign: str
    saturn_sign: str
    north_node_sign: str
    # Human Design
    hd_type: str
    hd_authority: str
    hd_profile: str
    hd_definition: str
    hd_incarnation_cross: str
    hd_defined_centers: set
    hd_active_gates: set
    hd_conscious_sun_gate: int
    hd_unconscious_sun_gate: int
    # Numerology
    life_path: int
    personal_year: int


def calculate_natal_chart(birth_date: datetime.date,
                           birth_time: datetime.time,
                           birth_lat: float,
                           birth_lon: float) -> NatalChart:
    """
    Calculate full natal chart from birth data.
    Uses Swiss Ephemeris if installed, else Meeus approximations.
    """
    birth_dt = datetime.datetime(
        birth_date.year, birth_date.month, birth_date.day,
        birth_time.hour, birth_time.minute,
        tzinfo=datetime.timezone.utc
    )
    jd = datetime_to_jd(birth_dt)

    # Planetary positions
    sun_lon     = get_planet_longitude(jd, 'sun')
    moon_lon    = get_planet_longitude(jd, 'moon')
    mercury_lon = get_planet_longitude(jd, 'mercury')
    venus_lon   = get_planet_longitude(jd, 'venus')
    mars_lon    = get_planet_longitude(jd, 'mars')
    jupiter_lon = get_planet_longitude(jd, 'jupiter')
    saturn_lon  = get_planet_longitude(jd, 'saturn')
    node_lon    = get_planet_longitude(jd, 'node')

    sun_sign,     sun_deg,     _ = longitude_to_sign(sun_lon)
    moon_sign,    moon_deg,    _ = longitude_to_sign(moon_lon)
    mercury_sign, _,           _ = longitude_to_sign(mercury_lon)
    venus_sign,   _,           _ = longitude_to_sign(venus_lon)
    mars_sign,    _,           _ = longitude_to_sign(mars_lon)
    jupiter_sign, _,           _ = longitude_to_sign(jupiter_lon)
    saturn_sign,  _,           _ = longitude_to_sign(saturn_lon)
    node_sign,    _,           _ = longitude_to_sign(node_lon)

    # Ascendant
    rising_lon = get_ascendant(jd, birth_lat, birth_lon)
    rising_sign, rising_deg, _ = longitude_to_sign(rising_lon)

    # Human Design
    hd = calculate_human_design(jd)

    # Numerology
    lp = _life_path(birth_date)
    py = _personal_year(birth_date, datetime.date.today().year)

    return NatalChart(
        sun_sign=sun_sign,         sun_degree=round(sun_deg, 1),
        sun_longitude=round(sun_lon, 4),
        moon_sign=moon_sign,       moon_degree=round(moon_deg, 1),
        rising_sign=rising_sign,   rising_degree=round(rising_deg, 1),
        mercury_sign=mercury_sign,
        venus_sign=venus_sign,
        mars_sign=mars_sign,
        jupiter_sign=jupiter_sign,
        saturn_sign=saturn_sign,
        north_node_sign=node_sign,
        hd_type=hd['type'],
        hd_authority=hd['authority'],
        hd_profile=hd['profile'],
        hd_definition=hd['definition'],
        hd_incarnation_cross=hd['incarnation_cross'],
        hd_defined_centers=hd['defined_centers'],
        hd_active_gates=hd['active_gates'],
        hd_conscious_sun_gate=hd['conscious_sun_gate'],
        hd_unconscious_sun_gate=hd['unconscious_sun_gate'],
        life_path=lp,
        personal_year=py,
    )


# ── Planetary aspects ─────────────────────────────────────────────────────────

PLANETS_FOR_ASPECTS = ['sun', 'mercury', 'venus', 'mars', 'jupiter', 'saturn']
PLANET_NAMES = {
    'sun': 'Sun', 'moon': 'Moon', 'mercury': 'Mercury',
    'venus': 'Venus', 'mars': 'Mars', 'jupiter': 'Jupiter', 'saturn': 'Saturn'
}
ASPECTS = {
    'conjunction': (0,   8),
    'sextile':     (60,  6),
    'square':      (90,  7),
    'trine':       (120, 8),
    'opposition':  (180, 8),
}

def _angular_distance(lon1: float, lon2: float) -> float:
    diff = abs(lon1 - lon2) % 360
    return diff if diff <= 180 else 360 - diff

def get_month_aspects(year: int, month: int) -> list:
    start_dt = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
    end_dt = (datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
              if month == 12
              else datetime.datetime(year, month + 1, 1, tzinfo=datetime.timezone.utc))
    start_jd = datetime_to_jd(start_dt)
    days_in_month = (end_dt - start_dt).days
    planets = PLANETS_FOR_ASPECTS
    pairs = [(p1, p2) for i, p1 in enumerate(planets) for p2 in planets[i+1:]]
    found = []
    seen = set()
    for p1, p2 in pairs:
        for day in range(days_in_month):
            jd = start_jd + day
            jd_next = jd + 1
            lon1 = get_planet_longitude(jd, p1)
            lon2 = get_planet_longitude(jd, p2)
            lon1_next = get_planet_longitude(jd_next, p1)
            lon2_next = get_planet_longitude(jd_next, p2)
            dist      = _angular_distance(lon1, lon2)
            dist_next = _angular_distance(lon1_next, lon2_next)
            for aspect_name, (target, orb) in ASPECTS.items():
                if aspect_name == 'conjunction' and set([p1, p2]) == {'sun', 'moon'}:
                    continue
                in_orb = abs(dist - target) <= orb
                in_orb_next = abs(dist_next - target) <= orb
                is_exact = ((dist - target) * (dist_next - target) < 0
                            or (in_orb and day == 0))
                if is_exact or (in_orb and not in_orb_next):
                    key = (p1, p2, aspect_name)
                    if key in seen:
                        continue
                    seen.add(key)
                    orb_end = day
                    for d2 in range(day, days_in_month):
                        l1 = get_planet_longitude(start_jd + d2, p1)
                        l2 = get_planet_longitude(start_jd + d2, p2)
                        if abs(_angular_distance(l1, l2) - target) <= orb:
                            orb_end = d2
                        else:
                            break
                    exact_day = day + 1
                    orb_start_date = datetime.date(year, month, day + 1)
                    orb_end_date   = datetime.date(year, month, min(orb_end + 1, days_in_month))
                    date_range = (orb_start_date.strftime('%b %-d')
                                  if orb_start_date == orb_end_date
                                  else f"{orb_start_date.strftime('%b %-d')}–{orb_end_date.strftime('%-d')}")
                    p1_sign, p1_deg, _ = longitude_to_sign(get_planet_longitude(jd, p1))
                    p2_sign, p2_deg, _ = longitude_to_sign(get_planet_longitude(jd, p2))
                    found.append({
                        'type':       aspect_name,
                        'planet1':    p1,
                        'planet2':    p2,
                        'planets':    f"{PLANET_NAMES[p1]} · {PLANET_NAMES[p2]}",
                        'exact_day':  exact_day,
                        'date_range': date_range,
                        'p1_sign':    p1_sign,
                        'p2_sign':    p2_sign,
                        'p1_degree':  round(p1_deg, 1),
                        'p2_degree':  round(p2_deg, 1),
                    })
    found.sort(key=lambda x: x['exact_day'])
    def significance(a):
        outer = {'jupiter', 'saturn', 'mars'}
        return -(int(a['planet1'] in outer) + int(a['planet2'] in outer))
    found.sort(key=significance)
    return found[:6]


# ── Monthly sky events ────────────────────────────────────────────────────────

def get_month_sky_events(year: int, month: int) -> dict:
    """Master function: all sky events for a given month."""
    lunar_phases    = get_lunar_phases_in_month(year, month)
    solar_ingresses = get_solar_ingresses_in_month(year, month)
    wheel_events    = get_wheel_events_in_month(year, month)
    aspects         = get_month_aspects(year, month)

    all_events = lunar_phases + solar_ingresses + wheel_events
    all_events.sort(key=lambda x: x['datetime_utc'])

    # Deduplicate by (day, type)
    seen_keys = set()
    deduped = []
    for e in all_events:
        key = (e['day'], e['type'])
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(e)
    all_events = deduped

    days = {}
    for e in all_events:
        d = e['day']
        if d not in days:
            days[d] = []
        days[d].append(e)

    return {
        'year':            year,
        'month':           month,
        'events':          all_events,
        'by_day':          days,
        'lunar_phases':    lunar_phases,
        'solar_ingresses': solar_ingresses,
        'wheel_events':    wheel_events,
        'aspects':         aspects,
    }


# ── Numerology ────────────────────────────────────────────────────────────────

def _reduce(n: int, keep_master: bool = True) -> int:
    while n > 9 and not (keep_master and n in (11, 22, 33)):
        n = sum(int(d) for d in str(n))
    return n

def _life_path(birth_date: datetime.date) -> int:
    total = (sum(int(d) for d in str(birth_date.year))
             + _reduce(birth_date.month, False)
             + _reduce(birth_date.day, False))
    return _reduce(total)

def _personal_year(birth_date: datetime.date, for_year: int) -> int:
    total = (_reduce(birth_date.month, False)
             + _reduce(birth_date.day, False)
             + sum(int(d) for d in str(for_year)))
    return _reduce(total)

def personal_month(birth_date: datetime.date, for_year: int, for_month: int) -> int:
    py = _personal_year(birth_date, for_year)
    return _reduce(py + for_month)


# ── Eclipse detection ─────────────────────────────────────────────────────────

def check_eclipse(lunar_phase: dict) -> Optional[dict]:
    """Placeholder — production: use Swiss Ephemeris eclipse functions."""
    return None
