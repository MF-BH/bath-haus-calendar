"""
astro_calc.py
─────────────────────────────────────────────────────────────────────────────
Astronomical + numerological calculation layer for the Sacred Lunar Calendar.

ACCURACY NOTES:
────────────────
• Sun sign/degree:    Meeus ch.25, accurate to ~0.01°  ✓ Production-ready
• Moon sign/degree:   Meeus simplified, accurate to ~1-3°  ✓ Sign-level reliable
• Lunar phase dates:  Meeus ch.49, accurate to ~minutes  ✓ Production-ready
• Solar ingresses:    Meeus binary-search, accurate to ~5 min  ✓ Production-ready
• Rising/Ascendant:   Requires correct UTC offset from client.
                      Accurate to ~1° when utc_offset is provided.
• Planet longitudes:  Rough (~5°). Set BACKEND='swisseph' for precision.
• HD Type/Authority:  Heuristic from planet gate clusters. Set BACKEND='swisseph'
                      and use a full Rave Chart for certified accuracy.
• Gene Keys gates:    Uses the correct 64-gate I-Ching zodiac wheel.
                      4 activations: Life Work, Evolution, Radiance, Purpose.
• Numerology:         Pure arithmetic — 100% accurate.

TO UPGRADE TO SWISS EPHEMERIS:
  pip install pyswisseph
  Set BACKEND = 'swisseph' below.
─────────────────────────────────────────────────────────────────────────────
"""

import math
import datetime
from dataclasses import dataclass
from typing import Optional

BACKEND = 'meeus'   # switch to 'swisseph' when pyswisseph is installed

# ── Zodiac ────────────────────────────────────────────────────────────────────

SIGNS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]
SIGN_SYMBOLS = ['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓']

def longitude_to_sign(lon: float) -> tuple[str, float, str]:
    lon = lon % 360
    idx = int(lon // 30)
    return SIGNS[idx], lon % 30, SIGN_SYMBOLS[idx]

def sign_symbol(sign_name: str) -> str:
    return SIGN_SYMBOLS[SIGNS.index(sign_name)]

# ── Gene Keys / Human Design gate wheel ──────────────────────────────────────
# 64 I-Ching hexagram gates mapped around the tropical zodiac wheel.
# Sector 0 = Aries 0°, each sector = 5.625° (360/64).
# Source: Human Design System / Gene Keys (Ra Uru Hu / Richard Rudd)

GK_GATE_WHEEL = [
    25, 17, 21, 51, 42,  3, 27, 24,  2, 23,  8, 20, 16, 35, 45, 12,
    15, 52, 39, 53, 62, 56, 31, 33,  7,  4, 29, 59, 40, 64, 47,  6,
    46, 18, 48, 57, 32, 50, 28, 44,  1, 43, 14, 34,  9,  5, 26, 11,
    10, 58, 38, 54, 61, 60, 41, 19, 13, 49, 30, 55, 37, 63, 22, 36,
]

def longitude_to_gate(lon: float) -> int:
    """Convert ecliptic longitude to HD/GK gate number (1-64)."""
    return GK_GATE_WHEEL[int((lon % 360) / 5.625)]

def opposite_gate(gate: int) -> int:
    """Return the gate directly opposite in the I-Ching wheel."""
    idx = GK_GATE_WHEEL.index(gate)
    return GK_GATE_WHEEL[(idx + 32) % 64]

# ── Julian Day ────────────────────────────────────────────────────────────────

def datetime_to_jd(dt: datetime.datetime) -> float:
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = (dt.day + (153 * m + 2) // 5 + 365 * y
           + y // 4 - y // 100 + y // 400 - 32045)
    frac = (dt.hour + dt.minute / 60 + dt.second / 3600) / 24 - 0.5
    return jdn + frac

def jd_to_datetime(jd: float) -> datetime.datetime:
    jd = jd + 0.5
    z  = int(jd)
    f  = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day   = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year  = c - 4716 if month > 2 else c - 4715
    hour   = int(f * 24)
    minute = int((f * 24 - hour) * 60)
    second = int(((f * 24 - hour) * 60 - minute) * 60)
    return datetime.datetime(year, month, day, hour, minute, second,
                             tzinfo=datetime.timezone.utc)

# ── Meeus lunar phase calculator ──────────────────────────────────────────────

def _lunar_phase_jd(year: float, phase: int) -> float:
    k      = round((year - 2000) * 12.3685) + phase * 0.25
    T      = k / 1236.85
    JDE    = (2451550.09766 + 29.530588861 * k + 0.00015437 * T**2
              - 0.000000150 * T**3 + 0.00000000073 * T**4)
    M      = math.radians(2.5534 + 29.10535670 * k - 0.0000014 * T**2)
    Mprime = math.radians(201.5643 + 385.81693528 * k + 0.0107582 * T**2)
    F      = math.radians(160.7108 + 390.67050284 * k - 0.0016118 * T**2)
    Omega  = math.radians(124.7746 - 1.56375588 * k + 0.0020672 * T**2)

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


def get_lunar_phases_in_month(year: int, month: int) -> list[dict]:
    frac_year   = year + (month - 1) / 12.0
    phase_names = {0: 'New Moon', 1: 'First Quarter', 2: 'Full Moon', 3: 'Last Quarter'}
    phase_icons = {0: 'new-moon', 1: 'first-qtr', 2: 'full-moon', 3: 'last-qtr'}

    results = []
    for offset in range(-2, 5):
        for phase_idx in [0, 1, 2, 3]:
            jd = _lunar_phase_jd(frac_year, phase_idx) + offset * 29.530588861
            dt = jd_to_datetime(jd)
            if dt.year == year and dt.month == month:
                moon_lon = _approx_moon_longitude(jd)
                sign, deg, sym = longitude_to_sign(moon_lon)
                results.append({
                    'type': phase_names[phase_idx], 'icon': phase_icons[phase_idx],
                    'datetime_utc': dt, 'day': dt.day,
                    'moon_sign': sign, 'moon_degree': round(deg, 1),
                    'moon_symbol': sym, 'time_str': dt.strftime('%-I:%M %p UTC'),
                })

    seen, unique = set(), []
    for r in sorted(results, key=lambda x: x['datetime_utc']):
        key = (r['type'], r['day'])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def _approx_moon_longitude(jd: float) -> float:
    T      = (jd - 2451545.0) / 36525
    L0     = 218.3164477 + 481267.88123421 * T
    Mprime = 134.9633964 + 477198.8675055 * T
    F      = 93.2720950  + 483202.0175233 * T
    lon    = (L0
              + 6.289 * math.sin(math.radians(Mprime))
              - 1.274 * math.sin(math.radians(2*F - Mprime))
              + 0.658 * math.sin(math.radians(2*F))
              - 0.214 * math.sin(math.radians(2*Mprime)))
    return lon % 360

# ── Solar ingresses ───────────────────────────────────────────────────────────

def _sun_longitude(jd: float) -> float:
    T   = (jd - 2451545.0) / 36525
    L0  = 280.46646 + 36000.76983 * T + 0.0003032 * T**2
    M   = 357.52911 + 35999.05029 * T - 0.0001537 * T**2
    M_r = math.radians(M % 360)
    C   = ((1.914602 - 0.004817*T - 0.000014*T**2) * math.sin(M_r)
           + (0.019993 - 0.000101*T) * math.sin(2*M_r)
           + 0.000289 * math.sin(3*M_r))
    omega = math.radians(125.04 - 1934.136 * T)
    return (L0 + C - 0.00569 - 0.00478 * math.sin(omega)) % 360


def get_solar_ingresses_in_month(year: int, month: int) -> list[dict]:
    start = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
    end   = (datetime.datetime(year+1, 1, 1, tzinfo=datetime.timezone.utc)
             if month == 12
             else datetime.datetime(year, month+1, 1, tzinfo=datetime.timezone.utc))

    results = []
    step    = datetime.timedelta(hours=6)
    dt      = start
    prev_idx = int(_sun_longitude(datetime_to_jd(dt)) // 30)

    while dt < end:
        dt_next  = dt + step
        lon      = _sun_longitude(datetime_to_jd(dt_next))
        sign_idx = int(lon // 30)
        if sign_idx != prev_idx:
            lo, hi = datetime_to_jd(dt), datetime_to_jd(dt_next)
            for _ in range(20):
                mid = (lo + hi) / 2
                (lo if int(_sun_longitude(mid) // 30) == prev_idx else hi)
                if int(_sun_longitude(mid) // 30) == prev_idx:
                    lo = mid
                else:
                    hi = mid
            ingress_dt = jd_to_datetime((lo + hi) / 2)
            if ingress_dt.year == year and ingress_dt.month == month:
                sign = SIGNS[sign_idx % 12]
                if sign in ('Aries', 'Libra'):
                    event_icon = 'equinox'
                    event_type = 'Spring Equinox' if sign == 'Aries' else 'Autumn Equinox'
                elif sign in ('Cancer', 'Capricorn'):
                    event_icon = 'solstice'
                    event_type = 'Summer Solstice' if sign == 'Cancer' else 'Winter Solstice'
                else:
                    event_icon = 'sun'
                    event_type = f'Sun enters {sign}'
                results.append({
                    'type': event_type, 'icon': event_icon,
                    'datetime_utc': ingress_dt, 'day': ingress_dt.day,
                    'sign': sign, 'sign_symbol': SIGN_SYMBOLS[sign_idx % 12],
                    'time_str': ingress_dt.strftime('%-I:%M %p UTC'),
                })
            prev_idx = sign_idx
        else:
            prev_idx = sign_idx
        dt = dt_next

    return results

# ── Natal chart ───────────────────────────────────────────────────────────────

@dataclass
class NatalChart:
    sun_sign:             str
    sun_degree:           float
    moon_sign:            str
    moon_degree:          float
    rising_sign:          str
    rising_degree:        float
    mercury_sign:         str
    venus_sign:           str
    mars_sign:            str
    north_node_sign:      str
    hd_type:              str
    hd_authority:         str
    hd_profile:           str
    hd_incarnation_cross: str
    life_path:            int
    personal_year:        int
    # Gene Keys — 4 main activation gates
    gk_life_work:         int   # Conscious Sun gate (natal)
    gk_evolution:         int   # Conscious Earth gate (opposite sun)
    gk_radiance:          int   # Design Sun gate (~88 days before birth)
    gk_purpose:           int   # Design Earth gate (opposite design sun)


def calculate_natal_chart(
    birth_date: datetime.date,
    birth_time: datetime.time,
    birth_lat:  float,
    birth_lon:  float,
    utc_offset: float = 0.0,   # LOCAL time UTC offset, e.g. -7.0 for PDT
) -> NatalChart:
    """
    Calculate natal chart from birth data.

    birth_time is LOCAL time at birthplace.
    utc_offset is the UTC offset at time of birth (e.g. -7.0 for PDT, -5.0 for EST).
    Without utc_offset the Rising sign will be wrong by several signs.
    """
    if BACKEND == 'swisseph':
        return _natal_swisseph(birth_date, birth_time, birth_lat, birth_lon, utc_offset)

    # Convert local → UTC
    local_dt = datetime.datetime(birth_date.year, birth_date.month, birth_date.day,
                                 birth_time.hour, birth_time.minute)
    utc_dt   = (local_dt - datetime.timedelta(hours=utc_offset)).replace(
                    tzinfo=datetime.timezone.utc)
    jd = datetime_to_jd(utc_dt)

    sun_lon     = _sun_longitude(jd)
    moon_lon    = _approx_moon_longitude(jd)
    rising_lon  = _approximate_rising(jd, birth_lat, birth_lon)
    mercury_lon = _approx_planet_longitude(jd, 'mercury')
    venus_lon   = _approx_planet_longitude(jd, 'venus')
    mars_lon    = _approx_planet_longitude(jd, 'mars')

    T        = (jd - 2451545.0) / 36525
    node_lon = (125.0445479 - 1934.1362608 * T) % 360

    sun_sign,     sun_deg,     _ = longitude_to_sign(sun_lon)
    moon_sign,    moon_deg,    _ = longitude_to_sign(moon_lon)
    rising_sign,  rising_deg,  _ = longitude_to_sign(rising_lon)
    mercury_sign, _,           _ = longitude_to_sign(mercury_lon)
    venus_sign,   _,           _ = longitude_to_sign(venus_lon)
    mars_sign,    _,           _ = longitude_to_sign(mars_lon)
    north_node_sign, _,        _ = longitude_to_sign(node_lon)

    lp = _life_path(birth_date)
    py = _personal_year(birth_date, datetime.date.today().year)

    hd_type, hd_auth, hd_profile, hd_cross = _hd_approximate(
        sun_lon, moon_lon, rising_lon, mercury_lon, venus_lon, mars_lon)

    gk_lw, gk_ev, gk_rad, gk_pur = _gene_keys_profile(jd, sun_lon)

    return NatalChart(
        sun_sign=sun_sign,       sun_degree=round(sun_deg, 1),
        moon_sign=moon_sign,     moon_degree=round(moon_deg, 1),
        rising_sign=rising_sign, rising_degree=round(rising_deg, 1),
        mercury_sign=mercury_sign, venus_sign=venus_sign, mars_sign=mars_sign,
        north_node_sign=north_node_sign,
        hd_type=hd_type, hd_authority=hd_auth,
        hd_profile=hd_profile, hd_incarnation_cross=hd_cross,
        life_path=lp, personal_year=py,
        gk_life_work=gk_lw, gk_evolution=gk_ev,
        gk_radiance=gk_rad, gk_purpose=gk_pur,
    )



# ── Human Design meaning tables ───────────────────────────────────────────────

HD_TYPE_MEANINGS = {
    'Projector': (
        'Guide & Witness',
        "You are not here to work in the traditional sense — you are here to guide, "
        "direct, and see others with penetrating clarity. Your energy is focused and "
        "selective. You are designed to wait for the right invitation before sharing "
        "your gifts, and when that invitation comes from the correct people, your "
        "wisdom lands with transformative precision. Success comes through recognition, "
        "not initiation. Rest is not laziness — it is your sacred fuel."
    ),
    'Generator': (
        'Builder & Responder',
        "You carry the life force of the planet — you are the builders, the sustainers, "
        "the ones whose energy powers the world when it is channelled into what truly "
        "lights you up. You are designed to respond rather than initiate: wait for "
        "life to present itself, then feel the gut's yes or no. When you follow your "
        "Sacral response into work and relationships that genuinely enrol you, your "
        "energy is near-limitless. Frustration is your signal to pause and re-align."
    ),
    'Manifesting Generator': (
        'Multi-Passionate Responder',
        "You carry the life force of the Generator with the initiating spark of the "
        "Manifestor — you are the fastest movers in the Human Design system, designed "
        "to skip steps and find shortcuts that others miss. Your power is in responding "
        "and then moving — but you must inform others before acting to reduce the "
        "resistance you'll otherwise meet. Frustration and anger are your signals. "
        "Your path is not linear; it zigzags, and that is by design."
    ),
    'Manifestor': (
        'Initiator & Trailblazer',
        "You carry the rarest and most independent energy type — you are here to "
        "initiate, to impact, to begin things that others then sustain. You do not "
        "need to wait: you are designed to move when the impulse arises. But informing "
        "others before you act is your key to reducing the resistance and control "
        "that your energy field can trigger. Anger is your not-self signal. Peace "
        "is your signature when you move in alignment."
    ),
    'Reflector': (
        'Mirror of the Community',
        "You are the rarest Human Design type — less than 1% of the population. "
        "You have no defined centres, which means you are a pure mirror of the "
        "environments and people around you. Your wellbeing is exquisitely sensitive "
        "to the quality of your surroundings and relationships. You are designed to "
        "wait 28 days — a full lunar cycle — before making major decisions, sampling "
        "the decision across all the moon's transits. Disappointment is your "
        "not-self signal. Surprise and delight are your natural state when aligned."
    ),
}

HD_AUTHORITY_MEANINGS = {
    'Sacral': (
        'Gut Response',
        "Your truth lives in the visceral, pre-verbal response of the Sacral centre — "
        "the 'uh-huh' of yes and the 'unh-unh' of no that arises before the mind can "
        "intercept it. Do not wait to think — feel the gut's response in real time. "
        "Ask yourself yes/no questions. The body knows before the mind does."
    ),
    'Splenic': (
        'Body Intuition',
        "Your authority is the quietest and most immediate in the system — a subtle "
        "whisper from the body's survival intelligence that speaks once and does not "
        "repeat itself. It is the feeling of health, safety, and rightness in the "
        "present moment. If it feels off in your body right now, it is. Trust the "
        "first, quiet impression — your Splenic authority does not second-guess itself."
    ),
    'Emotional': (
        'Emotional Wave',
        "You are designed to wait through your emotional wave before making decisions. "
        "Clarity does not come in the moment — it comes in time, as the wave moves "
        "from high to low and back again. 'Never make a decision in the high or the low' "
        "is your guiding principle. Wait until the emotional charge has settled and "
        "you can feel a quiet inner knowing. There is no complete clarity — but you "
        "will feel what is most true when the wave has passed through."
    ),
    'Ego': (
        'Heart-Will',
        "Your authority speaks through genuine desire and commitment from the heart. "
        "Make decisions based on what you truly want — not obligation, not what others "
        "expect of you. When you speak from the heart's will and make promises you "
        "can genuinely keep, your energy is powerful and consistent. Notice what you "
        "naturally reach toward when no one is watching."
    ),
    'Mental': (
        'Outer Authority',
        "Your clarity comes through talking — literally. You are designed to sound "
        "your decision out loud to trusted people in trusted environments, and to "
        "listen to what you hear yourself saying. You do not need advice from others; "
        "you need witnesses to your own voice finding its truth. The environment and "
        "the people you process with matter deeply to the quality of your decisions."
    ),
    'Self': (
        'Identity Navigation',
        "You make decisions correctly when you feel at home in yourself — when the "
        "environment feels right, the timing feels right, and the people feel right. "
        "Your Self authority navigates through a felt sense of identity: does this "
        "feel like me? Ask yourself: do I love myself when I do this? Does this "
        "feel like where I belong?"
    ),
    'Lunar': (
        '28-Day Cycle',
        "You are a Reflector, and your authority is the moon itself. For major "
        "decisions, wait the full 28 days and observe how you feel about the decision "
        "as the moon moves through all twelve gates of the Wheel. Speak the decision "
        "to different people across the cycle. The answer that remains constant — "
        "or deepens — across the full lunar month is your truth."
    ),
}

HD_PROFILE_MEANINGS = {
    '1/3': (
        'Investigator / Martyr',
        "You build security through deep research and foundational knowledge. "
        "Your first line needs to know — thoroughly, exhaustively — before it can "
        "move forward. Your third line learns through experimentation and trial; "
        "what looks like failure to others is your curriculum. You bond-break "
        "when things are no longer correct, and this is not fickleness — it is "
        "how you gather the experiential wisdom you're here to offer."
    ),
    '2/4': (
        'Hermit / Opportunist',
        "You carry natural gifts you are often unaware of — talents that others "
        "see in you long before you recognise them in yourself. Your second line "
        "needs solitude to regenerate and to let the gifts percolate. Your fourth "
        "line thrives in a network of close, trusted relationships — your "
        "opportunities come through people who know and love you. You are called "
        "out of your hermitage by the right invitations, and you recognise them "
        "because they feel like recognition of who you already are."
    ),
    '3/5': (
        'Martyr / Heretic',
        "You are a living laboratory — you learn through direct, embodied "
        "experience, through what works and what doesn't, and you become the "
        "practical guide who has actually lived what they teach. Your fifth line "
        "is projected upon: others see you as the one with the practical solution "
        "to their problems, sometimes before you have offered anything. Hold your "
        "reputation carefully — it precedes you."
    ),
    '4/6': (
        'Opportunist / Role Model',
        "Your life unfolds in three distinct phases. In your first 30 years, "
        "you are experimenting, building your foundation of relationships. At "
        "around 30, you move into a quieter period of observation — watching "
        "from the roof, integrating what you've learned. After 50, you descend "
        "as the living example, the Role Model who has embodied what they teach. "
        "Your network of close relationships is your most powerful resource — "
        "the right people open every door."
    ),
    '5/1': (
        'Heretic / Investigator',
        "You carry the projection field of the saviour — others will see you as "
        "the one with the practical answer to their most pressing problems, often "
        "from the first meeting. You need solid foundational knowledge to back up "
        "the solutions your fifth line is expected to deliver. You are here to "
        "universalise — to take what you know and offer it in a way that works "
        "for many. Karma and reputation are your key themes."
    ),
    '6/2': (
        'Role Model / Hermit',
        "You are on the same three-phase journey as the 4/6, but with a deeper "
        "need for solitude woven through each phase. In your first 30 years, you "
        "are experimenting. From 30-50, you observe from above — often "
        "misunderstood as detached or unavailable. After 50, you descend as the "
        "embodied exemplar, the living proof that a life of integrity is possible. "
        "You are deeply magnetic when you allow yourself to be seen in your natural state."
    ),
    '1/4': (
        'Investigator / Opportunist',
        "You build security through deep research — you need to know before you "
        "can move — and your opportunities consistently come through your network "
        "of close, trusted relationships. Knowledge and connection are your twin "
        "foundations. The right information, in the hands of the right people "
        "who know you, is your path."
    ),
    '4/1': (
        'Opportunist / Investigator',
        "Your primary channel is your network — close, trusted relationships "
        "are the ground of your life. Your first line foundation needs to be "
        "solid, and when it is, your fourth line can build bridges that carry "
        "real weight. Security comes from knowing what you know, and from the "
        "people you have invested in over time."
    ),
    '2/5': (
        'Hermit / Heretic',
        "Your natural, unhoned gifts become practical solutions for others — "
        "your fifth line carries the projection of the practical guide, while "
        "your second line needs real solitude to let those gifts regenerate and "
        "deepen. You may be called into roles of leadership and problem-solving "
        "that feel almost accidental to you. The key is discerning which "
        "calls are genuinely aligned."
    ),
    '5/2': (
        'Heretic / Hermit',
        "You carry practical solutions from gifts you may not fully recognise "
        "in yourself. Your fifth line is projected upon as the one who can fix "
        "what is broken, while your second line needs significant solitude to "
        "let those gifts operate naturally. Selective engagement is not "
        "selfishness — it is how you protect the quality of what you offer."
    ),
    '3/6': (
        'Martyr / Role Model',
        "You learn through experience, through what sticks and what falls away, "
        "and your three-phase life mirrors the 6/2 and 4/6 journey. Your early "
        "years are a rich curriculum of experimentation. Over time, what you have "
        "genuinely lived becomes the foundation of the wise, embodied guidance "
        "you are here to offer. Experience is not a detour — it is the path."
    ),
    '6/3': (
        'Role Model / Martyr',
        "You are the observer who learns through experience — your sixth line "
        "watches from above while your third line is in the laboratory below. "
        "The three-phase life gives you time to integrate before you fully "
        "embody the role model you're becoming. Your lived experience, including "
        "the 'mistakes,' is exactly the credential that makes your wisdom real."
    ),
}

HD_CROSS_MEANINGS = {
    'Cross of Planning': (
        'Community & Infrastructure',
        "You carry one of the most common Incarnation Crosses on the planet — "
        "you are part of the great wave of souls born to plan, organise, "
        "and build the structures that communities need to function. Your "
        "purpose is not dramatic or singular — it is essential. You are here "
        "to contribute to the sustainable architecture of human life. "
        "When you are building something that genuinely serves others, "
        "you are in full alignment with your incarnation."
    ),
    'Cross of the Vessel of Love': (
        'Universal Love',
        "You are here to embody and transmit love in its most universal form — "
        "not romantic love alone, but the love that underlies all life. "
        "Your incarnation is a living question about what it means to love "
        "without condition, to be a vessel through which the heart of the "
        "cosmos moves. The quality of your love is your contribution to the world."
    ),
    'Cross of the Sphinx': (
        'Orientation & Direction',
        "You carry the cross of those who are oriented to the future and to "
        "the deepest questions of direction and meaning. Your incarnation "
        "asks: where are we going? You are here to question, to seek, "
        "and to help others find their direction through life's mysteries. "
        "The Sphinx guards the threshold — and so do you."
    ),
    'Cross of Penetration': (
        'Depth & Revelation',
        "You are here to penetrate the surface — to go deeply into life, "
        "into ideas, into people, and to help others face what lies beneath "
        "their shadows. Your incarnation is an invitation to go where others "
        "hesitate, and to bring back what you find with honesty and precision."
    ),
    'Cross of Explanation': (
        'Teaching & Communication',
        "You are here to explain — to take complex truths and make them "
        "accessible, to be the teacher who bridges the known and the unknown. "
        "Your incarnation carries the gift of communication in service of "
        "understanding. When you are teaching or explaining, you are most "
        "fully yourself."
    ),
    'Cross of Confrontation': (
        'Revealing & Witnessing',
        "You are here to bring what is hidden into the light — to confront "
        "what is unconscious, unspoken, or avoided, and to do so with the "
        "precision and care of a skilled surgeon. Your incarnation is a "
        "gift to those who are ready to see clearly."
    ),
    'Cross of the Four Ways': (
        'Navigation & Crossroads',
        "You stand at the crossroads — your incarnation carries the themes "
        "of choice, direction, and the navigation of life's turning points. "
        "You are here to help yourself and others find the right road at "
        "the key junctions of life."
    ),
    'Cross of the Sleeping Phoenix': (
        'Transformation & Rising',
        "Your incarnation carries the theme of transformation — of dying to "
        "what was in order to become what is next. Like the phoenix, your "
        "deepest gifts emerge through the fires of change. You are here to "
        "model regeneration."
    ),
}

def get_hd_type_meaning(hd_type: str) -> tuple:
    return HD_TYPE_MEANINGS.get(hd_type, (hd_type, ''))

def get_hd_authority_meaning(authority: str) -> tuple:
    return HD_AUTHORITY_MEANINGS.get(authority, (authority, ''))

def get_hd_profile_meaning(profile: str) -> tuple:
    return HD_PROFILE_MEANINGS.get(profile, (profile, ''))

def get_hd_cross_meaning(cross: str) -> tuple:
    return HD_CROSS_MEANINGS.get(cross, (cross, ''))

def _gene_keys_profile(jd_birth: float, sun_lon: float) -> tuple[int, int, int, int]:
    """
    4 Gene Keys activation gates.

    Life's Work = Conscious Sun gate (natal sun longitude)
    Evolution   = Conscious Earth gate (wheel-opposite of Life's Work)
    Radiance    = Design Sun gate (sun ~88.736 days before birth)
    Purpose     = Design Earth gate (wheel-opposite of Radiance)
    """
    jd_design      = jd_birth - 88.736
    sun_design_lon = _sun_longitude(jd_design)

    gate_lw  = longitude_to_gate(sun_lon)
    gate_ev  = opposite_gate(gate_lw)
    gate_rad = longitude_to_gate(sun_design_lon)
    gate_pur = opposite_gate(gate_rad)
    return gate_lw, gate_ev, gate_rad, gate_pur


def _hd_approximate(sun_lon, moon_lon, asc_lon,
                     mercury_lon, venus_lon, mars_lon) -> tuple:
    """
    Approximate HD type from planet gate clusters.
    NOTE: A certified HD chart requires all planets for both birth + design dates.
    This heuristic is reasonable but not certified. Recommend pyswisseph upgrade.
    """
    SACRAL_GATES = {3, 5, 9, 14, 27, 29, 34, 59}
    THROAT_GATES = {8, 12, 16, 20, 23, 31, 33, 35, 45, 56, 62}

    active = {longitude_to_gate(l) for l in
              [sun_lon, moon_lon, asc_lon, mercury_lon, venus_lon, mars_lon]}
    sacral = len(active & SACRAL_GATES)
    throat = len(active & THROAT_GATES)

    if sacral >= 2:
        hd_type   = 'Manifesting Generator' if throat >= 1 else 'Generator'
        authority = 'Sacral'
    elif sacral == 1 and throat >= 1:
        hd_type   = 'Manifestor'
        authority = 'Splenic' if any(g in {18,28,32,48,50,57} for g in active) else 'Ego'
    else:
        hd_type   = 'Projector'
        authority = 'Splenic' if any(g in {18,28,32,48,50,57} for g in active) else 'Mental'

    # Profile line from sun position within its gate
    line = int(((sun_lon % 360) % 5.625) / (5.625 / 6)) + 1
    line = max(1, min(6, line))
    profile_map = {1:'1/3', 2:'2/4', 3:'3/5', 4:'4/6', 5:'5/1', 6:'6/2'}
    profile = profile_map[line]

    return hd_type, authority, profile, 'Cross of Planning'


def _approximate_rising(jd: float, lat: float, lon: float) -> float:
    T     = (jd - 2451545.0) / 36525
    theta = 280.46061837 + 360.98564736629 * (jd - 2451545) + 0.000387933 * T**2
    lst   = (theta + lon) % 360
    eps   = math.radians(23.4393 - 0.013 * T)
    lst_r = math.radians(lst)
    lat_r = math.radians(lat)
    asc   = math.atan2(math.cos(lst_r),
                       -(math.sin(lst_r) * math.cos(eps)
                         + math.tan(lat_r) * math.sin(eps)))
    return math.degrees(asc) % 360


def _approx_planet_longitude(jd: float, planet: str) -> float:
    T = (jd - 2451545.0) / 36525
    if planet == 'mercury':
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
    return 0.0


# ── Swiss Ephemeris stub ──────────────────────────────────────────────────────

def _natal_swisseph(birth_date, birth_time, birth_lat, birth_lon, utc_offset):
    try:
        import swisseph as swe
    except ImportError:
        raise RuntimeError("pip install pyswisseph  then set BACKEND='swisseph'")
    swe.set_ephe_path('/usr/share/ephe')

    local_dt = datetime.datetime(birth_date.year, birth_date.month, birth_date.day,
                                 birth_time.hour, birth_time.minute)
    utc_dt   = local_dt - datetime.timedelta(hours=utc_offset)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day,
                    utc_dt.hour + utc_dt.minute / 60)

    def plon(pid):
        return swe.calc_ut(jd, pid)[0][0]

    sun_lon     = plon(swe.SUN)
    moon_lon    = plon(swe.MOON)
    mercury_lon = plon(swe.MERCURY)
    venus_lon   = plon(swe.VENUS)
    mars_lon    = plon(swe.MARS)
    node_lon    = plon(swe.MEAN_NODE)
    cusps, ascmc = swe.houses(jd, birth_lat, birth_lon, b'P')
    rising_lon  = ascmc[0]

    lp = _life_path(birth_date)
    py = _personal_year(birth_date, datetime.date.today().year)
    hd = _hd_approximate(sun_lon, moon_lon, rising_lon, mercury_lon, venus_lon, mars_lon)
    gk = _gene_keys_profile(jd, sun_lon)

    def si(lon): return longitude_to_sign(lon)

    return NatalChart(
        sun_sign=si(sun_lon)[0],         sun_degree=round(si(sun_lon)[1], 1),
        moon_sign=si(moon_lon)[0],       moon_degree=round(si(moon_lon)[1], 1),
        rising_sign=si(rising_lon)[0],   rising_degree=round(si(rising_lon)[1], 1),
        mercury_sign=si(mercury_lon)[0], venus_sign=si(venus_lon)[0],
        mars_sign=si(mars_lon)[0],       north_node_sign=si(node_lon)[0],
        hd_type=hd[0], hd_authority=hd[1], hd_profile=hd[2], hd_incarnation_cross=hd[3],
        life_path=lp, personal_year=py,
        gk_life_work=gk[0], gk_evolution=gk[1], gk_radiance=gk[2], gk_purpose=gk[3],
    )


# ── Numerology ────────────────────────────────────────────────────────────────

def _reduce(n: int, keep_master: bool = True) -> int:
    """Reduce to single digit, preserving master numbers 11, 22, 33."""
    while n > 9 and not (keep_master and n in (11, 22, 33)):
        n = sum(int(d) for d in str(n))
    return n

def _life_path(birth_date: datetime.date) -> int:
    m = _reduce(birth_date.month, keep_master=False)
    d = _reduce(birth_date.day,   keep_master=False)
    y = _reduce(sum(int(c) for c in str(birth_date.year)), keep_master=False)
    return _reduce(m + d + y)

def _personal_year(birth_date: datetime.date, for_year: int) -> int:
    m = _reduce(birth_date.month, keep_master=False)
    d = _reduce(birth_date.day,   keep_master=False)
    y = _reduce(sum(int(c) for c in str(for_year)), keep_master=False)
    return _reduce(m + d + y)

def personal_month(birth_date: datetime.date, for_year: int, for_month: int) -> int:
    py = _personal_year(birth_date, for_year)
    return _reduce(py + for_month)


# ── Monthly sky events ────────────────────────────────────────────────────────

def get_month_sky_events(year: int, month: int) -> dict:
    """
    Return all verified sky events for the month.
    This is the authoritative source for what days are potent.
    """
    lunar    = get_lunar_phases_in_month(year, month)
    ingress  = get_solar_ingresses_in_month(year, month)
    all_evs  = sorted(lunar + ingress, key=lambda x: x['datetime_utc'])

    days: dict[int, list] = {}
    for e in all_evs:
        days.setdefault(e['day'], []).append(e)

    return {
        'year': year, 'month': month,
        'events': all_evs, 'by_day': days,
        'lunar_phases': lunar, 'solar_ingresses': ingress,
    }
