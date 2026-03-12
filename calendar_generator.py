"""
calendar_generator.py
─────────────────────────────────────────────────────────────────────────────
Takes the data packet and Claude-generated content, renders the Sacred Lunar
Calendar as a self-contained HTML file and optionally converts to PDF.
─────────────────────────────────────────────────────────────────────────────
"""

import calendar
import datetime
from pathlib import Path


# ── SVG icon library — matches reference HTML exactly ────────────────────────

SVG_DEFS = """<svg width="0" height="0" style="position:absolute;overflow:hidden">
<defs>
  <symbol id="ico-crescent" viewBox="0 0 32 32">
    <path d="M 16 5 A 11 11 0 1 1 16 27 A 7.5 7.5 0 1 0 16 5 Z"
      fill="none" stroke="currentColor" stroke-width="1.2"
      stroke-linejoin="round" stroke-linecap="round"/>
  </symbol>
  <symbol id="ico-new-moon" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="10" fill="none" stroke="currentColor" stroke-width="1.2"/>
  </symbol>
  <symbol id="ico-full-moon" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="10" fill="currentColor" stroke="currentColor" stroke-width="1.2"/>
    <path d="M11,12 Q13,10 15,12" fill="none" stroke="white" stroke-width="0.7" opacity="0.35"/>
    <path d="M18,19 Q20,17.5 22,19" fill="none" stroke="white" stroke-width="0.6" opacity="0.28"/>
  </symbol>
  <symbol id="ico-first-qtr" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="10" fill="none" stroke="currentColor" stroke-width="1.2"/>
    <line x1="16" y1="6" x2="16" y2="26" stroke="currentColor" stroke-width="0.8"/>
    <line x1="15" y1="6.5" x2="15" y2="25.5" stroke="currentColor" stroke-width="0.4" opacity="0.25"/>
    <line x1="13" y1="8" x2="13" y2="24" stroke="currentColor" stroke-width="0.4" opacity="0.2"/>
    <line x1="11" y1="10.5" x2="11" y2="21.5" stroke="currentColor" stroke-width="0.4" opacity="0.18"/>
  </symbol>
  <symbol id="ico-last-qtr" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="10" fill="none" stroke="currentColor" stroke-width="1.2"/>
    <line x1="16" y1="6" x2="16" y2="26" stroke="currentColor" stroke-width="0.8"/>
    <line x1="17" y1="6.5" x2="17" y2="25.5" stroke="currentColor" stroke-width="0.4" opacity="0.25"/>
    <line x1="19" y1="8" x2="19" y2="24" stroke="currentColor" stroke-width="0.4" opacity="0.2"/>
    <line x1="21" y1="10.5" x2="21" y2="21.5" stroke="currentColor" stroke-width="0.4" opacity="0.18"/>
  </symbol>
  <symbol id="ico-sun" viewBox="0 0 32 32">
    <rect x="3" y="3" width="26" height="26" rx="2" fill="none" stroke="currentColor" stroke-width="1.1"/>
    <text x="16" y="21" text-anchor="middle" font-size="16" font-family="Georgia,serif" fill="currentColor" stroke="none">&#9737;</text>
  </symbol>
  <symbol id="ico-venus" viewBox="0 0 32 32">
    <rect x="3" y="3" width="26" height="26" rx="2" fill="none" stroke="currentColor" stroke-width="1.1"/>
    <text x="16" y="21" text-anchor="middle" font-size="16" font-family="Georgia,serif" fill="currentColor" stroke="none">&#9792;</text>
  </symbol>
  <symbol id="ico-mercury" viewBox="0 0 32 32">
    <rect x="3" y="3" width="26" height="26" rx="2" fill="none" stroke="currentColor" stroke-width="1.1"/>
    <text x="16" y="21" text-anchor="middle" font-size="16" font-family="Georgia,serif" fill="currentColor" stroke="none">&#9791;</text>
  </symbol>
  <symbol id="ico-mars" viewBox="0 0 32 32">
    <rect x="3" y="3" width="26" height="26" rx="2" fill="none" stroke="currentColor" stroke-width="1.1"/>
    <text x="16" y="21" text-anchor="middle" font-size="16" font-family="Georgia,serif" fill="currentColor" stroke="none">&#9794;</text>
  </symbol>
  <symbol id="ico-jupiter" viewBox="0 0 32 32">
    <rect x="3" y="3" width="26" height="26" rx="2" fill="none" stroke="currentColor" stroke-width="1.1"/>
    <text x="16" y="21" text-anchor="middle" font-size="16" font-family="Georgia,serif" fill="currentColor" stroke="none">&#9795;</text>
  </symbol>
  <symbol id="ico-saturn" viewBox="0 0 32 32">
    <rect x="3" y="3" width="26" height="26" rx="2" fill="none" stroke="currentColor" stroke-width="1.1"/>
    <text x="16" y="21" text-anchor="middle" font-size="16" font-family="Georgia,serif" fill="currentColor" stroke="none">&#9796;</text>
  </symbol>
  <symbol id="ico-equinox" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="11" fill="none" stroke="currentColor" stroke-width="1.2"/>
    <path d="M16,5 A11,11 0 0,1 16,27 Z" fill="currentColor" stroke="none"/>
    <line x1="16" y1="5" x2="16" y2="27" stroke="currentColor" stroke-width="1.2"/>
    <line x1="4" y1="16" x2="28" y2="16" stroke="currentColor" stroke-width="1.2"/>
  </symbol>
  <symbol id="ico-solstice" viewBox="0 0 32 32">
    <circle cx="16" cy="12" r="5" fill="none" stroke="currentColor" stroke-width="1.2"/>
    <line x1="16" y1="3" x2="16" y2="5.5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="16" y1="18.5" x2="16" y2="21" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="6" y1="12" x2="8.5" y2="12" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="23.5" y1="12" x2="26" y2="12" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="8.7" y1="4.7" x2="10.5" y2="6.5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="21.5" y1="17.5" x2="23.3" y2="19.3" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="23.3" y1="4.7" x2="21.5" y2="6.5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="10.5" y1="17.5" x2="8.7" y2="19.3" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="3" y1="24" x2="29" y2="24" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
    <line x1="3" y1="27" x2="29" y2="27" stroke="currentColor" stroke-width="0.7" stroke-linecap="round" opacity="0.35"/>
  </symbol>
</defs>
</svg>"""


# ── Icon helper ───────────────────────────────────────────────────────────────

ICON_HTML = '<svg width="{size}" height="{size}" viewBox="0 0 32 32" fill="none" style="color:{color};display:block;flex-shrink:0"><use href="#ico-{icon}" fill="none"/></svg>'

def icon(name: str, size: int = 16, color: str = '#7a8c6e') -> str:
    return ICON_HTML.format(size=size, color=color, icon=name)


# ── CSS — matches reference HTML exactly ─────────────────────────────────────

CSS = """<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400;1,500&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --cream: #f7f3ed; --warm-white: #faf8f4; --parchment: #ede8df;
  --ink: #2c2a26; --ink-light: #5a5650; --ink-faint: #8a8278;
  --sage: #7a8c6e; --sage-dark: #4a5c40; --sage-light: #a8b89a;
  --moss: #3d4f35; --bark: #8c7355;
  --border: rgba(122,140,110,0.18); --border-ink: rgba(44,42,38,0.1);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#e8e4de; font-family:'Cormorant Garamond',Georgia,serif; }

.calendar { background:var(--warm-white); max-width:820px; margin:0 auto;
  box-shadow: 0 8px 48px rgba(0,0,0,0.18); }

/* ── COVER ── */
.cover { min-height:100vh; background:var(--cream); display:flex;
  flex-direction:column; align-items:center; justify-content:center;
  padding:80px 64px; position:relative; text-align:center; }
.cover::before { content:''; position:absolute; inset:0;
  background: radial-gradient(ellipse 70% 60% at 50% 40%,rgba(237,232,223,0.6) 0%,transparent 70%);
  pointer-events:none; }
.cover-inner { position:relative; z-index:1; max-width:480px; }
.cover-brand { font-family:'Jost',sans-serif; font-size:9px; font-weight:400;
  letter-spacing:0.58em; color:var(--sage); text-transform:uppercase; margin-bottom:52px;
  display:flex; align-items:center; justify-content:center; gap:16px; }
.cover-brand::before,.cover-brand::after { content:''; width:36px; height:1px;
  background:var(--sage-light); opacity:0.6; }
.cover-eyebrow { font-family:'Jost',sans-serif; font-size:9px; font-weight:400;
  letter-spacing:0.52em; color:var(--ink-faint); text-transform:uppercase; margin-bottom:14px; }
.cover-month { font-size:clamp(64px,11vw,88px); font-weight:300; color:var(--ink);
  line-height:0.88; letter-spacing:0.06em; margin-bottom:10px; }
.cover-year { font-size:20px; font-style:italic; color:var(--ink-faint);
  letter-spacing:0.2em; margin-bottom:48px; }
.cover-rule { width:48px; height:1px;
  background:linear-gradient(90deg,transparent,var(--sage-light),transparent);
  margin:0 auto 26px; }
.cover-woven { font-size:16px; font-style:italic; font-weight:300;
  color:var(--ink-faint); margin-bottom:6px; }
.cover-name { font-size:28px; font-weight:300; color:var(--moss); letter-spacing:0.04em; }
.cover-strip { position:absolute; bottom:0; left:0; right:0; background:white;
  border-top:1px solid var(--border-ink); padding:22px 64px;
  display:flex; align-items:center; justify-content:space-between; }
.strip-item { text-align:center; }
.strip-label { font-family:'Jost',sans-serif; font-size:8px; letter-spacing:0.42em;
  color:var(--sage); text-transform:uppercase; opacity:0.7; margin-bottom:4px; }
.strip-value { font-size:13px; font-weight:300; color:var(--moss); }
.strip-div { width:1px; height:26px; background:var(--border); }

/* ── BODY PAGES ── */
.page { padding:72px 64px; border-bottom:1px solid var(--border); }
.eyebrow { font-family:'Jost',sans-serif; font-size:9px; font-weight:500;
  letter-spacing:0.5em; color:var(--sage); text-transform:uppercase; margin-bottom:6px; opacity:0.75; }
h2 { font-size:32px; font-weight:300; color:var(--moss); margin-bottom:6px; }
.lead { font-size:19px; font-style:italic; color:var(--bark); line-height:1.75;
  margin-bottom:28px; font-weight:300; }
p { font-size:17px; font-weight:300; color:var(--ink-light); line-height:1.85; margin-bottom:18px; }
p strong { color:var(--ink); font-weight:400; }

/* ── PORTRAIT GRID ── */
.section-divider { height:1px; background:var(--border); margin:28px 0 0; opacity:0.6; }
.portrait-section-note { font-size:14px; font-style:italic; color:var(--ink-light);
  margin:6px 0 14px; line-height:1.6; }
.portrait-grid { display:grid; grid-template-columns:1fr 1fr; gap:1px;
  border:1px solid var(--border); margin:0 0 4px; background:var(--border); }
.portrait-cell { background:var(--warm-white); padding:22px 26px; }
.portrait-label { font-family:'Jost',sans-serif; font-size:8px; font-weight:500;
  letter-spacing:0.45em; color:var(--sage); text-transform:uppercase; margin-bottom:5px; opacity:0.7; }
.portrait-value { font-size:18px; font-weight:300; color:var(--moss); line-height:1.3; }
.portrait-sub { font-size:13px; font-style:italic; color:var(--ink-light); margin-top:3px; }

/* ── CALENDAR GRID ── */
.cal-header { display:grid; grid-template-columns:repeat(7,1fr); text-align:center; margin-bottom:2px; }
.cal-dow { font-family:'Jost',sans-serif; font-size:9px; font-weight:500;
  letter-spacing:0.28em; color:var(--sage); text-transform:uppercase; padding:10px 4px; opacity:0.7; }
.cal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:2px;
  grid-auto-rows:1fr; }
.cal-day { background:white; border:1px solid rgba(122,140,110,0.09);
  padding:10px 9px 8px; min-height:90px; height:100%;
  box-sizing:border-box; overflow:hidden; }
.cal-day.empty { background:transparent; border-color:transparent; visibility:hidden; }
.cal-day-num { font-family:'Jost',sans-serif; font-size:13px; font-weight:300;
  color:var(--ink-light); display:block; margin-bottom:6px; }
.cal-day.today { background:rgba(122,140,110,0.05); border-color:rgba(122,140,110,0.3); }
.cal-day.today .cal-day-num { color:var(--moss); font-weight:500; }
.cal-day.potent { background:rgba(122,140,110,0.10); border:1px solid rgba(74,92,64,0.35); }
.cal-day.potent .cal-day-num { color:var(--moss); font-weight:500; }
.potent-label { font-family:'Jost',sans-serif; font-size:7.5px; font-weight:500;
  letter-spacing:0.22em; text-transform:uppercase; color:var(--sage-dark);
  display:block; margin-bottom:3px; opacity:0.8; }
.cal-ev { font-size:10px; font-style:italic; color:var(--sage-dark);
  line-height:1.3; display:block; margin-top:1px; }
.cal-ev.alignment { font-style:normal; font-size:9.5px; color:var(--moss); opacity:0.75; }
.phase-icon { display:block; margin-bottom:2px; }
.cal-aspect { font-size:9.5px; font-style:italic; color:var(--sage-dark);
  line-height:1.3; display:block; margin-top:2px; opacity:0.8; }
.cal-aspect.trine      { color:#4a5c40; }
.cal-aspect.opposition { color:#8c7355; }
.cal-aspect.square     { color:#7a5a5a; }
.cal-aspect.sextile    { color:#4a5c70; }
.cal-aspect.conjunction{ color:#5a5050; }

/* ── KEY DATES ── */
.key-dates { margin:32px 0; }
.key-date { display:grid; grid-template-columns:72px 1fr; gap:24px;
  padding:22px 0; border-bottom:1px solid rgba(122,140,110,0.1); align-items:start; }
.key-date:last-child { border-bottom:none; }
.kd-date { font-family:'Jost',sans-serif; font-size:11px; font-weight:500;
  letter-spacing:0.18em; color:var(--sage-dark); text-transform:uppercase; padding-top:6px; }
.kd-icon { display:block; margin-bottom:8px; }
.kd-title { font-size:18px; font-weight:400; color:var(--moss); margin-bottom:4px; }
.kd-desc { font-size:15px; font-style:italic; color:var(--ink-light); line-height:1.7; margin:0; }
.kd-personal { font-size:14px; color:var(--sage-dark); margin-top:8px; line-height:1.65;
  padding:10px 14px; background:rgba(122,140,110,0.055); border-left:2px solid var(--sage-light); }

/* ── TRANSMISSION ── */
.transmission { margin:28px 0 0; }
.transmission p { font-size:17px; font-weight:300; font-style:normal; color:var(--ink);
  line-height:2.0; margin-bottom:28px; }
.transmission p:first-child { font-size:18px; }
.transmission p:last-child { margin-bottom:0; font-style:italic; color:var(--ink-light); }
.trans-pull { font-family:'Cormorant Garamond',Georgia,serif; font-size:23px;
  font-weight:400; font-style:normal; color:var(--moss); line-height:1.6;
  border-top:1px solid var(--sage-light); border-bottom:1px solid var(--sage-light);
  padding:28px 0; margin:32px 0; letter-spacing:0.01em; }

/* ── RITUAL ── */
.ritual-box { border:1px solid var(--border-ink); padding:36px 40px; margin:28px 0;
  background:rgba(237,232,223,0.25); }
.ritual-title { font-family:'Jost',sans-serif; font-size:9px; font-weight:500;
  letter-spacing:0.5em; color:var(--sage); text-transform:uppercase; margin-bottom:8px; opacity:0.75; }
.ritual-name { font-size:24px; font-weight:300; color:var(--moss); margin-bottom:14px; }
.ritual-ingredients { list-style:none; display:flex; flex-wrap:wrap; gap:8px; margin:14px 0; }
.ritual-ingredients li { font-size:14px; font-style:italic; color:var(--bark);
  border:1px solid var(--border-ink); padding:5px 14px; background:rgba(255,255,255,0.7); }

/* ── AFFIRMATION ── */
.affirmation { text-align:center; padding:52px 40px;
  border-top:1px solid var(--border); border-bottom:1px solid var(--border); margin:40px 0; }
.affirmation-label { font-family:'Jost',sans-serif; font-size:9px; letter-spacing:0.5em;
  color:var(--sage); text-transform:uppercase; margin-bottom:22px; opacity:0.7; }
.affirmation-text { font-size:25px; font-weight:300; color:var(--moss);
  line-height:1.6; font-style:italic; max-width:500px; margin:0 auto; }

/* ── ALIGNMENTS ── */
.alignments { margin:32px 0; }
.alignment-row { display:grid; grid-template-columns:52px 1fr; gap:24px;
  padding:24px 0; border-bottom:1px solid rgba(122,140,110,0.1); align-items:start; }
.alignment-row:last-child { border-bottom:none; }
.align-symbol { padding-top:4px; opacity:0.85; }
.align-header { display:flex; flex-wrap:wrap; align-items:baseline;
  gap:10px; margin-bottom:8px; }
.align-type { font-family:'Jost',sans-serif; font-size:10px; font-weight:500;
  letter-spacing:0.22em; text-transform:uppercase; padding:3px 10px;
  border:1px solid currentColor; border-radius:2px; }
.align-type.trine      { color:#4a5c40; }
.align-type.opposition { color:#8c7355; }
.align-type.square     { color:#7a5a5a; }
.align-type.sextile    { color:#4a5c70; }
.align-type.conjunction{ color:#5a5050; }
.align-planets { font-size:17px; font-weight:300; color:var(--moss); }
.align-date { font-family:'Jost',sans-serif; font-size:10px; color:var(--ink-faint);
  letter-spacing:0.12em; margin-left:auto; }
.align-desc { font-size:15px; font-style:italic; color:var(--ink-light);
  line-height:1.75; margin:0 0 8px; }
.align-personal { font-size:14px; color:var(--sage-dark); line-height:1.65;
  padding:10px 14px; background:rgba(122,140,110,0.055);
  border-left:2px solid var(--sage-light); }

.hd-grid { display:grid; grid-template-columns:1fr; gap:0; border:1px solid var(--parchment); }
.hd-cell { padding:24px 28px; border-bottom:1px solid var(--parchment); }
.hd-cell:last-child { border-bottom:none; }
.hd-cell-header { display:flex; align-items:baseline; gap:14px; margin-bottom:8px; }
.hd-cell-type { font-family:'Jost',sans-serif; font-size:9px; font-weight:500;
  letter-spacing:0.22em; text-transform:uppercase; color:var(--sage); }
.hd-cell-name { font-family:'Cormorant Garamond',Georgia,serif; font-size:21px;
  font-weight:400; color:var(--moss); }
.hd-cell-label { font-family:'Jost',sans-serif; font-size:10px; color:var(--ink-faint);
  letter-spacing:0.1em; margin-left:auto; }
.hd-cell-desc { font-size:14px; color:var(--ink-light); line-height:1.75; margin:0; }
/* ── FOOTER ── *//* ── FOOTER ── */
.footer { padding:64px; text-align:center; background:var(--cream); }
.footer p { font-size:14px; font-style:italic; color:var(--ink-light);
  line-height:1.8; max-width:380px; margin:0 auto 8px; }
.footer-brand { font-family:'Jost',sans-serif; font-size:9px; letter-spacing:0.5em;
  color:var(--sage); text-transform:uppercase; margin-top:28px; opacity:0.55; }
.footer-rule { width:40px; height:1px; background:var(--sage-light); margin:0 auto 28px; opacity:0.45; }
</style>"""


# ── Aspect data ───────────────────────────────────────────────────────────────

ASPECT_SYMBOLS = {
    'trine':       '<polygon points="20,4 36,32 4,32" stroke-width="1.3" opacity="0.85"/>',
    'opposition':  '<circle cx="10" cy="20" r="6"/><circle cx="30" cy="20" r="6"/><line x1="16" y1="20" x2="24" y2="20" stroke-width="1.0" opacity="0.6"/>',
    'square':      '<rect x="8" y="8" width="24" height="24" stroke-width="1.3" opacity="0.85"/>',
    'sextile':     '<line x1="20" y1="4" x2="20" y2="36" stroke-width="0.5" opacity="0.3"/><line x1="4" y1="20" x2="36" y2="20" stroke-width="0.5" opacity="0.3"/><polygon points="20,5 33,27 7,27" stroke-width="1.2" opacity="0.8"/><polygon points="20,35 7,13 33,13" stroke-width="1.2" opacity="0.8"/>',
    'conjunction': '<circle cx="15" cy="20" r="8" opacity="0.8"/><circle cx="25" cy="20" r="8" opacity="0.8"/>',
}
ASPECT_LABELS = {
    'trine': 'Trine △', 'opposition': 'Opposition ☍', 'square': 'Square □',
    'sextile': 'Sextile ⚹', 'conjunction': 'Conjunction ☌',
}
ASPECT_GLYPHS = {
    'trine': '△', 'opposition': '☍', 'square': '□',
    'sextile': '⚹', 'conjunction': '☌',
}


def _render_aspect_symbol(aspect_type: str) -> str:
    shapes = ASPECT_SYMBOLS.get(aspect_type, '')
    return (f'<svg viewBox="0 0 40 40" width="36" height="36" style="display:block">'
            f'<g stroke="#7a8c6e" fill="none" stroke-width="1.2" stroke-linecap="round">'
            f'{shapes}</g></svg>')


# ── Calendar grid builder ─────────────────────────────────────────────────────

def _build_calendar_grid(year: int, month: int, events_by_day: dict,
                          today: datetime.date,
                          potent_days: set = None,
                          aspect_by_day: dict = None) -> str:
    """
    potent_days   : set of int day numbers to highlight with gradient + label
    aspect_by_day : {day_int: [(aspect_type_str, label_str), ...]}
    """
    potent_days   = potent_days   or set()
    aspect_by_day = aspect_by_day or {}

    # Sunday-first: use Calendar(firstweekday=6) so padding 0s are placed correctly
    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)

    header = '<div class="cal-header">'
    for dow in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']:
        header += f'<div class="cal-dow">{dow}</div>'
    header += '</div>'

    grid = '<div class="cal-grid">'
    for week in weeks:
        for day in week:
            if day == 0:
                grid += '<div class="cal-day empty"></div>'
                continue

            is_today    = (datetime.date(year, month, day) == today)
            day_events  = events_by_day.get(str(day), [])
            day_aspects = aspect_by_day.get(day, [])
            is_potent   = day in potent_days

            if is_today:
                cls = 'cal-day today'
            elif is_potent:
                cls = 'cal-day potent'
            else:
                cls = 'cal-day'

            grid += f'<div class="{cls}">'

            # ✦ Most Potent label comes BEFORE the day number
            if is_potent:
                grid += '<span class="potent-label">&#10022; Most Potent</span>'

            grid += f'<span class="cal-day-num">{day}</span>'

            # Sky events
            for ev in day_events:
                ico         = ev.get('icon', '')
                ev_type     = ev.get('type', '')
                is_equinox  = 'equinox'  in ev_type.lower()
                is_solstice = 'solstice' in ev_type.lower()
                is_planet   = ico in ('sun','venus','mercury','mars','jupiter','saturn')

                if is_equinox:
                    grid += f'<span class="phase-icon">{icon("equinox", 14)}</span>'
                    grid += f'<span class="cal-ev">{ev_type}</span>'
                elif is_solstice:
                    grid += f'<span class="phase-icon">{icon("solstice", 14)}</span>'
                    grid += f'<span class="cal-ev">{ev_type}</span>'
                elif is_planet:
                    grid += f'<span class="cal-ev">{ev_type}</span>'
                else:
                    if ico:
                        grid += f'<span class="phase-icon">{icon(ico, 14)}</span>'
                    short = ev_type.replace(' Moon', '').replace('Sun enters ', '→ ')
                    grid += f'<span class="cal-ev">{short}</span>'

            # Aspect annotations
            for (asp_type, asp_label) in day_aspects:
                grid += f'<span class="cal-aspect {asp_type}">{asp_label}</span>'

            grid += '</div>'
    grid += '</div>'
    return header + grid


# ── Alignments section ────────────────────────────────────────────────────────

def render_alignments_section(alignments: list) -> str:
    if not alignments:
        return ''
    rows = ''
    for i, a in enumerate(alignments):
        aspect     = a.get('type', 'conjunction')
        last_style = ' style="border-bottom:none"' if i == len(alignments) - 1 else ''
        rows += f"""
  <div class="alignment-row"{last_style}>
    <div class="align-symbol">{_render_aspect_symbol(aspect)}</div>
    <div class="align-body">
      <div class="align-header">
        <span class="align-type {aspect}">{ASPECT_LABELS.get(aspect, aspect.title())}</span>
        <span class="align-planets">{a.get('planets', '')}</span>
        <span class="align-date">{a.get('date_range', '')}</span>
      </div>
      <p class="align-desc">{a.get('description', '') or a.get('personal', '')}</p>
      {('<div class="align-personal">' + a.get('personal', '') + '</div>') if a.get('personal') and a.get('description') and a.get('description') != a.get('personal') else ''}
    </div>
  </div>"""
    return f"""
<div class="page">
  <div class="eyebrow">Planetary Alignments</div>
  <h2>The geometry of the sky</h2>
  <p class="lead">The planets are in constant dialogue. These are the precise geometric conversations active in the sky this month — and what they are asking of you specifically.</p>
  <div class="alignments">{rows}
  </div>
</div>"""


# ── Main render function ───────────────────────────────────────────────────────

def render_calendar_html(
    person_name: str,
    birth_date: datetime.date,
    chart,
    year: int,
    month: int,
    packet: dict,
    content: dict,
    personal_year_name: str,
    personal_month_num: int,
    personal_month_name: str,
    alignments: list = None,
) -> str:
    month_name = datetime.date(year, month, 1).strftime('%B')
    month_abbr = datetime.date(year, month, 1).strftime('%b')
    today      = datetime.date.today()

    # ── Cover — inline style matches reference exactly ──
    cover = f"""
<div class="cover">
  <div class="cover-inner">
    <div class="cover-brand">Bath Haus</div>
    <div style="font-size:28px;color:#7a8c6e;opacity:0.55;margin-bottom:36px;letter-spacing:0.12em;">&#9789;</div>
    <div class="cover-eyebrow">Sacred Lunar Calendar</div>
    <div class="cover-month">{month_name}</div>
    <div class="cover-year">{year}</div>
    <div class="cover-rule"></div>
    <div class="cover-woven">Woven for</div>
    <div class="cover-name">{person_name}</div>
  </div>
  <div class="cover-strip">
    <div class="strip-item">
      <div class="strip-label">Personal Year</div>
      <div class="strip-value">Year {chart.personal_year} · {personal_year_name}</div>
    </div>
    <div class="strip-div"></div>
    <div class="strip-item">
      <div class="strip-label">Personal Month</div>
      <div class="strip-value">Month {personal_month_num} · {personal_month_name}</div>
    </div>
    <div class="strip-div"></div>
    <div class="strip-item">
      <div class="strip-label">Sun · Moon · Rising</div>
      <div class="strip-value">{chart.sun_sign} · {chart.moon_sign} · {chart.rising_sign}</div>
    </div>
    <div class="strip-div"></div>
    <div class="strip-item">
      <div class="strip-label">Human Design</div>
      <div class="strip-value">{chart.hd_type}</div>
    </div>
  </div>
</div>"""

    # ── Portrait ──
    # Gene Keys labels from personalization module
    from personalization import gene_key_label, GENE_KEY_GIFTS
    gk_lw_gift  = GENE_KEY_GIFTS.get(chart.gk_life_work, '')
    gk_ev_gift  = GENE_KEY_GIFTS.get(chart.gk_evolution, '')
    gk_rad_gift = GENE_KEY_GIFTS.get(chart.gk_radiance, '')
    gk_pur_gift = GENE_KEY_GIFTS.get(chart.gk_purpose, '')

    # Top 8-cell grid: astrology + numerology (no HD here — has own row below)
    portrait_cells = [
        ('Sun Sign',                       chart.sun_sign,        f"{chart.sun_degree}°"),
        ('Rising Sign',                    chart.rising_sign,     ''),
        ('Moon Sign',                      chart.moon_sign,       ''),
        ('North Node',                     chart.north_node_sign, ''),
        ('Life Path',                      str(chart.life_path),  ''),
        ('Mercury · Venus · Mars',         f"{chart.mercury_sign} · {chart.venus_sign} · {chart.mars_sign}", ''),
        (f'Personal Year {year}',          f'{chart.personal_year} — {personal_year_name}', ''),
        (f'Personal Month',                f'{personal_month_num} — {personal_month_name}', ''),
    ]
    portrait_html = '<div class="portrait-grid">'
    for label, value, sub in portrait_cells:
        portrait_html += f"""
    <div class="portrait-cell">
      <div class="portrait-label">{label}</div>
      <div class="portrait-value">{value}</div>
      {"<div class='portrait-sub'>" + sub + "</div>" if sub else ""}
    </div>"""
    portrait_html += '</div>'

    # HD row — 4 compact squares (same visual language as Gene Keys)
    try:
        from astro_calc import (
            get_hd_type_meaning, get_hd_authority_meaning,
            get_hd_profile_meaning, get_hd_cross_meaning,
        )
        hd_keyword_cells = [
            ('Type',              chart.hd_type,
             get_hd_type_meaning(chart.hd_type)[0]),
            ('Authority',         chart.hd_authority,
             get_hd_authority_meaning(chart.hd_authority)[0]),
            ('Profile',           chart.hd_profile,
             get_hd_profile_meaning(chart.hd_profile)[0]),
            ('Incarnation Cross', chart.hd_incarnation_cross,
             get_hd_cross_meaning(chart.hd_incarnation_cross)[0]),
        ]
    except Exception:
        hd_keyword_cells = [
            ('Type',    chart.hd_type,              ''),
            ('Authority', chart.hd_authority,       ''),
            ('Profile', chart.hd_profile,           ''),
            ('Cross',   chart.hd_incarnation_cross, ''),
        ]

    hd_squares_html = '<div class="portrait-grid hd-squares">'
    for label, value, keyword in hd_keyword_cells:
        hd_squares_html += f"""
    <div class="portrait-cell">
      <div class="portrait-label">Human Design · {label}</div>
      <div class="portrait-value">{value}</div>
      {"<div class='portrait-sub'>" + keyword + "</div>" if keyword else ""}
    </div>"""
    hd_squares_html += '</div>'

    # Gene Keys section — all 4 activations
    gk_rows = [
        ("Life's Work",  chart.gk_life_work,  gk_lw_gift,
         "The gift you came to embody in your work and outer expression"),
        ("Evolution",    chart.gk_evolution,  gk_ev_gift,
         "The evolutionary gift that grounds and stabilises your life's work"),
        ("Radiance",     chart.gk_radiance,   gk_rad_gift,
         "Your unconscious gift — the quality others receive from your presence"),
        ("Purpose",      chart.gk_purpose,    gk_pur_gift,
         "Your deepest gift — the frequency you anchor in the world simply by being"),
    ]
    gk_html = '<div class="portrait-grid">'
    for activation, gate, gift, desc in gk_rows:
        gk_html += f"""
    <div class="portrait-cell">
      <div class="portrait-label">Gene Key {gate} · {activation}</div>
      <div class="portrait-value">{gift}</div>
      <div class="portrait-sub">{desc}</div>
    </div>"""
    gk_html += '</div>'

    # ── Human Design page (now inline in portrait — kept for reference only) ──
    hd_page = ''  # replaced by hd_squares_html in portrait_section
    if False:  # disabled
      try:
        from astro_calc import (
            get_hd_type_meaning, get_hd_authority_meaning,
            get_hd_profile_meaning, get_hd_cross_meaning,
        )
        hd_cells_data = [
            ('TYPE',              chart.hd_type,
             get_hd_type_meaning(chart.hd_type)[0],
             get_hd_type_meaning(chart.hd_type)[1]),
            ('AUTHORITY',         chart.hd_authority,
             get_hd_authority_meaning(chart.hd_authority)[0],
             get_hd_authority_meaning(chart.hd_authority)[1]),
            ('PROFILE',           chart.hd_profile,
             get_hd_profile_meaning(chart.hd_profile)[0],
             get_hd_profile_meaning(chart.hd_profile)[1]),
            ('INCARNATION CROSS', chart.hd_incarnation_cross,
             get_hd_cross_meaning(chart.hd_incarnation_cross)[0],
             get_hd_cross_meaning(chart.hd_incarnation_cross)[1]),
        ]
        hd_cells_html = ''
        for cell_type, cell_name, cell_label, cell_desc in hd_cells_data:
            hd_cells_html += f"""
  <div class="hd-cell">
    <div class="hd-cell-header">
      <span class="hd-cell-type">{cell_type}</span>
      <span class="hd-cell-name">{cell_name}</span>
      <span class="hd-cell-label">{cell_label}</span>
    </div>
    <p class="hd-cell-desc">{cell_desc}</p>
  </div>"""
        hd_page = f"""
<div class="page">
  <div class="eyebrow">Human Design</div>
  <h2>Your energetic blueprint</h2>
  <p class="lead">Human Design reveals how your energy moves through the world — how you are designed to make decisions, engage your gifts, and fulfil the purpose encoded in your birth.</p>
  <div class="hd-grid">{hd_cells_html}
  </div>
</div>"""
      except Exception:
        hd_page = ''

    portrait_section = f"""
<div class="page">
  <div class="eyebrow">Your Sacred Blueprint</div>
  <h2>Who you are in the stars</h2>
  <p class="lead">This calendar is woven from the specific coordinates of your arrival.
  Every transmission, every bath ritual, every key date is filtered through this exact lens.</p>
  {portrait_html}
  <div class="section-divider"></div>
  <div class="eyebrow" style="margin-top:28px;">Human Design</div>
  <p class="portrait-section-note">Your energetic blueprint — how you are designed to move through the world.</p>
  {hd_squares_html}
  <div class="section-divider"></div>
  <div class="eyebrow" style="margin-top:28px;">Gene Keys Profile</div>
  <p class="portrait-section-note">The four gates of illumination encoded in your birth. Each holds a Shadow, a Gift, and a Siddhi.</p>
  {gk_html}
</div>"""

    # ── Transmission ──
    trans = content.get('transmission', {})
    body_paras = trans.get('body', [])
    # Para 2 (index 1) becomes a pull-quote if it exists and is short enough
    trans_html = ''
    for i, p in enumerate(body_paras):
        if i == 1 and len(p) < 280:
            trans_html += f'<div class="trans-pull">{p}</div>'
        else:
            trans_html += f'<p>{p}</p>'
    transmission_section = f"""
<div class="page">
  <div class="eyebrow">Monthly Transmission</div>
  <h2>{month_name} — {trans.get('title', '')}</h2>
  <div class="transmission">{trans_html}</div>
</div>"""

    # ── Key dates — ALL icons shown (lunar AND planet glyphs, matching reference) ──
    key_dates_html = '<div class="key-dates">'
    for kd in content.get('key_dates', []):
        ico_name = kd.get('icon', '')
        ico_html = f'<span class="kd-icon">{icon(ico_name, 26)}</span>' if ico_name else ''
        key_dates_html += f"""
  <div class="key-date">
    <div class="kd-date">{month_abbr} {kd['day']}</div>
    <div>
      {ico_html}
      <div class="kd-title">{kd['event']}</div>
      <p class="kd-desc">{kd['description']}</p>
      <div class="kd-personal">{kd['personal']}</div>
    </div>
  </div>"""
    key_dates_html += '</div>'

    key_dates_section = f"""
<div class="page">
  <div class="eyebrow">Cosmic Events</div>
  <h2>Your {month_name}, mapped</h2>
  <p class="lead">Every significant movement of the sky this month — and what it means specifically for you.</p>
  {key_dates_html}
</div>"""

    # ── Alignments ──
    alignments_section = render_alignments_section(alignments or [])

    # ── Calendar grid — potent days + aspect annotations ──
    # Potent = days with REAL sky events from packet['by_day'] (authoritative source).
    # We do NOT use Claude's key_dates here — Claude can hallucinate day numbers.
    potent_days: set = set()
    for day_str, evs in packet.get('by_day', {}).items():
        for ev in evs:
            ico     = ev.get('icon', '')
            ev_type = ev.get('type', '').lower()
            if (ico in ('new-moon', 'full-moon', 'first-qtr', 'last-qtr',
                        'equinox', 'solstice')
                    or 'equinox' in ev_type or 'solstice' in ev_type):
                potent_days.add(int(day_str))

    # Aspect annotations on the grid from alignment data
    aspect_by_day: dict = {}
    for a in (alignments or []):
        asp   = a.get('type', '')
        glyph = ASPECT_GLYPHS.get(asp, '')
        pa    = a.get('planet_a', '')
        pb    = a.get('planet_b', '')

        peak  = a.get('peak_day')
        start = a.get('start_day')

        if peak:
            aspect_by_day.setdefault(peak, []).append((asp, f"{glyph} {pa}·{pb} exact"))
        if start and start != peak:
            aspect_by_day.setdefault(start, []).append((asp, f"{glyph} {pa}·{pb}"))

    grid = _build_calendar_grid(
        year, month, packet['by_day'], today, potent_days, aspect_by_day
    )
    grid_section = f"""
<div class="page">
  <div class="eyebrow">{month_name} {year}</div>
  <h2>The month at a glance</h2>
  {grid}
</div>"""

    # ── Rituals ──
    rituals_html = ''
    for r in content.get('bath_rituals', []):
        ingredients = ''.join(f'<li>{i}</li>' for i in r.get('ingredients', []))
        rituals_html += f"""
  <div class="ritual-box">
    <div class="ritual-title">{r.get('trigger', '')} · {month_name} {r.get('day', '')}</div>
    <div class="ritual-name">{r.get('name', '')}</div>
    <p>{r.get('description', '')}</p>
    <ul class="ritual-ingredients">{ingredients}</ul>
    <p><strong>Intention:</strong> {r.get('intention', '')}</p>
  </div>"""

    rituals_section = f"""
<div class="page">
  <div class="eyebrow">Sacred Water Rituals</div>
  <h2>Your bath prescriptions for {month_name}</h2>
  <p class="lead">Rituals tuned to the most potent lunar moments — and to the specific frequencies moving through you this month.</p>
  {rituals_html}
</div>"""

    # ── Affirmation ──
    affirmation_section = f"""
<div class="page">
  <div class="affirmation">
    <div class="affirmation-label">Your {month_name} Affirmation</div>
    <div class="affirmation-text">"{content.get('affirmation', '')}"</div>
  </div>
</div>"""

    # ── Footer ──
    footer = f"""
<div class="footer">
  <div class="footer-rule"></div>
  <svg width="22" height="22" viewBox="0 0 32 32" fill="none" style="color:#7a8c6e;display:block;margin:0 auto 22px">
    <use href="#ico-crescent" fill="none"/>
  </svg>
  <p>This calendar was woven specifically for {person_name}.<br>It will not exist for anyone else in quite this way.</p>
  <p style="margin-top:12px;opacity:0.6;">{content.get('closing_note', '')}</p>
  <div class="footer-brand">Bath Haus · Sacred Lunar Calendar · {year}</div>
</div>"""

    # ── Assemble — wrapped in .calendar div matching reference ──
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{person_name} — {month_name} {year} · Sacred Lunar Calendar</title>
{CSS}
</head>
<body>
{SVG_DEFS}
<div class="calendar">
{cover}
{portrait_section}
{transmission_section}
{key_dates_section}
{alignments_section}
{grid_section}
{rituals_section}
{affirmation_section}
{footer}
</div>
</body>
</html>"""


def save_html(html: str, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path


def convert_to_pdf(html_path: str, pdf_path: str) -> str:
    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
        return pdf_path
    except ImportError:
        raise RuntimeError(
            "weasyprint not installed. Run: pip install weasyprint\n"
            "On Mac: brew install pango libffi"
        )
