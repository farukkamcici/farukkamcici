"""Draws the profile README images.

dist/sky.svg                 a quiet sky band; colour, sun/moon, clouds and rain
                             follow Istanbul's real clock and weather
dist/stats-{light,dark}.svg  three numbers with small hand-sketched charts, and a
                             little crew of agents in the corner

Sources are optional: when one fails the last good value in data/cache.json is
used. All-time GitHub totals come from data/github.json (scripts/export_stats.py).
"""
import base64
import json
import math
import os
import random
import urllib.request
from html import escape
from datetime import datetime, timedelta, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
DIST = os.path.join(ROOT, "dist")
CACHE = os.path.join(ROOT, "data", "cache.json")
GITHUB = os.path.join(ROOT, "data", "github.json")
USER = os.environ.get("GH_USER", "farukkamcici")
TOKEN = os.environ.get("GH_TOKEN")
IST = timezone(timedelta(hours=3))
NOW = datetime.now(IST)
if os.environ.get("FORCE_HOUR"):  # previews only
    NOW = NOW.replace(hour=int(os.environ["FORCE_HOUR"]))
FORCE_WEATHER = os.environ.get("FORCE_WEATHER")
FONT_KEY = os.environ.get("FORCE_FONT", "bricolage")  # which assets/fonts/<key>-{400,600}.ttf to embed
FONT = "Brand, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"


# ------------------------------------------------------------------ data
def fetch(url, accept=None):
    h = {"User-Agent": "profile-readme"}
    if TOKEN and "api.github.com" in url:
        h["Authorization"] = f"bearer {TOKEN}"
    if accept:
        h["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
        return json.load(r)


def weather():
    d = fetch("https://api.open-meteo.com/v1/forecast?latitude=41.01&longitude=28.97&current=temperature_2m,weather_code,cloud_cover&timezone=Europe%2FIstanbul")["current"]
    code = d["weather_code"]
    if code in range(51, 68) or code in range(80, 83) or code >= 95:
        kind = "rain"
    elif code in range(71, 78) or code in (85, 86):
        kind = "snow"
    elif code in (45, 48) or d["cloud_cover"] >= 60:
        kind = "clouds"
    else:
        kind = "clear"
    return {"temp": round(d["temperature_2m"]), "kind": kind}


def stars():
    """Stars on every public repo, by month, plus mectrics release downloads."""
    repos, page = [], 1
    while True:
        batch = fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += [r["name"] for r in batch if not r["fork"] and r["stargazers_count"]]
        if len(batch) < 100:
            break
        page += 1
    months = {}
    for name in repos:
        page = 1
        while True:
            batch = fetch(f"https://api.github.com/repos/{USER}/{name}/stargazers?per_page=100&page={page}", "application/vnd.github.star+json")
            for s in batch:
                months[s["starred_at"][:7]] = months.get(s["starred_at"][:7], 0) + 1
            if len(batch) < 100:
                break
            page += 1
    rel = fetch(f"https://api.github.com/repos/{USER}/mectrics/releases?per_page=100")
    return {"total": sum(months.values()), "months": sorted(months.items()),
            "downloads": sum(a["download_count"] for r in rel for a in r["assets"])}


def collect():
    try:
        cache = json.load(open(CACHE))
    except (OSError, ValueError):
        cache = {}
    for key, fn in (("weather", weather), ("stars", stars)):
        try:
            cache[key] = fn()
        except Exception as e:
            print(f"{key}: {e!r}, keeping last good value")
    try:  # all-time totals from scripts/export_stats.py, private repos included
        cache["github"] = json.load(open(GITHUB))
    except (OSError, ValueError):
        pass
    for stale in ("busiest", "nba", "crew", "mectrics"):
        cache.pop(stale, None)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w"), indent=1, ensure_ascii=False)
    return cache


# ------------------------------------------------------------------ sky
SKIES = {  # gradient stops top→bottom, text, soft text
    "night": (["#0B1430", "#18224A", "#2A3266"], "#F2F4FA", "#A9B2D3"),
    "dawn": (["#3E4884", "#7A6A9E", "#C08A8F"], "#FFFFFF", "#F1E4EC"),
    "day": (["#6FAEE0", "#A6D0EE", "#DCEEF8"], "#0E2340", "#2E4A6E"),
    "dusk": (["#25285C", "#6A4A80", "#B86F7C"], "#FFFFFF", "#F2DCE0"),
}


def sky_kind(h):
    return "dawn" if 6 <= h < 8 else "day" if 8 <= h < 17 else "dusk" if 17 <= h < 20 else "night"


def font_face():
    out = []
    for w in (400, 600):
        with open(os.path.join(ROOT, "assets", "fonts", f"{FONT_KEY}-{w}.ttf"), "rb") as f:
            out.append(f"@font-face{{font-family:Brand;font-weight:{w};src:url(data:font/ttf;base64,{base64.b64encode(f.read()).decode()}) format('truetype')}}")
    return "".join(out)


def chip(x, y, text, fill, ink):
    w = 26 + len(text) * 7.15
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="28" rx="14" fill="{fill}"/>'
            f'<text x="{x + 13}" y="{y + 18.5}" class="chip" fill="{ink}">{escape(text)}</text>'), w


def sky(data):
    kind = sky_kind(NOW.hour)
    stops, text, soft = SKIES[kind]
    w = data.get("weather") or {"temp": None, "kind": "clear"}
    wk = FORCE_WEATHER or w["kind"]
    W, H = 840, 230
    rnd = random.Random(4)
    ox, oy = 790, 50
    if kind == "night":
        orb = (f'<circle cx="{ox}" cy="{oy}" r="56" fill="url(#glow)" opacity=".3"/>'
               f'<mask id="m"><rect width="{W}" height="{H}" fill="#fff"/><circle cx="{ox + 10}" cy="{oy - 7}" r="17" fill="#000"/></mask>'
               f'<circle cx="{ox}" cy="{oy}" r="19" fill="#F4F1E4" mask="url(#m)"/>')
        stars = "".join(f'<circle cx="{rnd.randint(420, 830)}" cy="{rnd.randint(10, 210)}" r="{rnd.choice([.7, .9, 1.2])}" fill="#fff" class="tw" style="animation-delay:{rnd.random() * 4:.1f}s"/>'
                        for _ in range(36))
    else:
        oy = {"day": 50, "dawn": 62, "dusk": 62}[kind]
        orb = f'<circle cx="{ox}" cy="{oy}" r="80" fill="url(#glow)" opacity=".55"/><circle cx="{ox}" cy="{oy}" r="22" fill="#FFF4D6"/>'
        stars = ""
    clouds = fx = ""
    if wk in ("clouds", "rain", "snow"):
        orb = orb.replace('opacity=".55"', 'opacity=".25"').replace('opacity=".3"', 'opacity=".15"')
        cf = "#FFFFFF" if kind == "day" else "#C9CEE6"
        clouds = "".join(f'<g class="drift" style="animation-duration:{d}s"><ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{cf}" opacity="{o}" filter="url(#blur)"/></g>'
                         for x, y, rx, ry, d, o in [(600, 46, 120, 20, 40, .3), (760, 110, 130, 22, 55, .32), (520, 180, 110, 16, 48, .2)])
    if wk == "rain":
        fx = "".join(f'<line x1="{x}" y1="{y}" x2="{x - 3}" y2="{y + 14}" class="rain" style="animation-delay:{rnd.random():.2f}s"/>'
                     for x, y in ((rnd.randint(0, 860), rnd.randint(-20, H)) for _ in range(80)))
    elif wk == "snow":
        fx = "".join(f'<circle cx="{rnd.randint(0, W)}" cy="{rnd.randint(-10, H)}" r="{rnd.choice([1, 1.5, 2])}" class="snow" style="animation-delay:{rnd.random() * 4:.1f}s"/>' for _ in range(70))

    cond = {"rain": "raining", "snow": "snowing", "clouds": "cloudy", "clear": "clear skies"}[wk]
    temp = f"{w['temp']}°, " if w.get("temp") is not None else ""
    meta = (f'<g transform="translate(40,196)">'
            f'<path d="M0,-11 c-3.6,0 -6,2.6 -6,5.8 c0,4.2 6,9.2 6,9.2 c0,0 6,-5 6,-9.2 c0,-3.2 -2.4,-5.8 -6,-5.8z" fill="{soft}"/><circle cx="0" cy="-5.4" r="2" fill="{stops[-1]}"/>'
            f'<text x="13" y="0" class="meta">Istanbul</text><rect x="86" y="-11" width="1.5" height="13" fill="{soft}" opacity=".5"/>'
            f'<text x="106" y="0" class="meta">Building Handlez with my agent bros</text></g>')
    weather_txt = (f'<text x="{ox - 34}" y="{oy + 2}" text-anchor="end" class="temp">{temp.rstrip(", ")}</text>'
                   f'<text x="{ox - 34}" y="{oy + 20}" text-anchor="end" class="cond">{cond}</text>')
    crew_css, crew_svg = crew(data, {"night": kind == "night", "moon": (ox, oy), "top": stops[0]})
    grad = "".join(f'<stop offset="{i / (len(stops) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(stops))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Faruk Kamçıcı. I turn data into apps, maps and small tools. Istanbul, {temp}{cond}. My agent bros huddle in the corner and now and then step out to talk.">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">{grad}</linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#FFF4D6"/><stop offset="1" stop-color="#FFF4D6" stop-opacity="0"/></radialGradient>
<filter id="blur" x="-50%" y="-100%" width="200%" height="300%"><feGaussianBlur stdDeviation="10"/></filter>
<clipPath id="c"><rect width="{W}" height="{H}" rx="18"/></clipPath>
</defs>
<style>
{font_face()}
.name{{font:600 46px {FONT};fill:{text};letter-spacing:-1.6px}}
.sub{{font:400 18px {FONT};fill:{soft};letter-spacing:-.1px}}
.meta{{font:400 14px {FONT};fill:{soft}}}.temp{{font:600 22px {FONT};fill:{text};letter-spacing:-.5px}}.cond{{font:400 13px {FONT};fill:{soft}}}
.tw{{animation:tw 4s ease-in-out infinite}}
@keyframes tw{{50%{{opacity:.2}}}}
.drift{{animation:drift ease-in-out infinite alternate}}
@keyframes drift{{to{{transform:translateX(26px)}}}}
.rain{{stroke:#DCE6FF;stroke-width:1;opacity:.25;animation:rain 1s linear infinite}}
@keyframes rain{{from{{transform:translate(0,-12px)}}to{{transform:translate(-6px,26px)}}}}
.snow{{fill:#fff;opacity:.7;animation:snow 4s linear infinite}}
@keyframes snow{{from{{transform:translate(0,-10px)}}to{{transform:translate(8px,30px)}}}}
{crew_css}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<g clip-path="url(#c)">
<rect width="{W}" height="{H}" fill="url(#g)"/>
{stars}<g class="moonfx">{orb}</g>{clouds}{fx}
<text x="38" y="72" class="name">Faruk Kamçıcı</text>
<text x="40" y="104" class="sub">I turn data into apps, maps and small tools.</text>
{meta}{weather_txt}
{crew_svg}
</g>
</svg>"""


# ------------------------------------------------------------------ sketch kit
class Pen:
    def __init__(self, seed):
        self.r = random.Random(seed)

    def j(self, a=1.0):
        return self.r.uniform(-a, a)

    def poly(self, pts, stroke, w=1.8, rough=.8, close=False, passes=2):
        out = []
        for k in range(passes):
            p = [(x + self.j(rough), y + self.j(rough)) for x, y in pts]
            if close:
                p.append((p[0][0] + self.j(rough), p[0][1] + self.j(rough)))
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in p)
            out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{w if k == 0 else w * .7:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="{1 if k == 0 else .5}"/>')
        return "".join(out)

    def hachure(self, pts, stroke, gap=5.0, angle=-41, w=1.1, opacity=.7):
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        rot = [(x * ca + y * sa, -x * sa + y * ca) for x, y in pts]
        ys = [p[1] for p in rot]
        out, y, n = [], min(ys) + gap / 2, len(rot)
        while y < max(ys):
            xs = sorted(x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                        for (x1, y1), (x2, y2) in ((rot[i], rot[(i + 1) % n]) for i in range(n))
                        if (y1 <= y < y2) or (y2 <= y < y1))
            for i in range(0, len(xs) - 1, 2):
                if xs[i + 1] - xs[i] < 1.5:
                    continue
                p1 = (xs[i] * ca - y * sa, xs[i] * sa + y * ca)
                p2 = (xs[i + 1] * ca - y * sa, xs[i + 1] * sa + y * ca)
                out.append(f'<path d="M{p1[0] + self.j(.5):.1f},{p1[1] + self.j(.5):.1f} L{p2[0] + self.j(.5):.1f},{p2[1] + self.j(.5):.1f}" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round" opacity="{opacity}"/>')
            y += gap + self.j(.3)
        return "".join(out)


# ------------------------------------------------------------------ stats row
THEMES = {
    "light": dict(ink="#1F2328", soft="#59636E", faint="#D1D9E0", bubble="#FFFFFF", a1="#2F9E44", a2="#1971C2", a3="#9C36B5",
                  crew=["#2F9E44", "#1971C2", "#9C36B5", "#E8590C", "#0C8599", "#C2255C", "#5F3DC4"]),
    "dark": dict(ink="#F0F6FC", soft="#9198A1", faint="#3D444D", bubble="#161B22", a1="#51CF66", a2="#4DABF7", a3="#DA77F2",
                 crew=["#51CF66", "#4DABF7", "#DA77F2", "#FF922B", "#3BC9DB", "#F06595", "#9775FA"]),
}
CW, GAP = 252, 42
CH_TOP, CH_BOT = 112, 172


def bars(pen, t, x, values, labels, color, every=1, gap_px=6):
    out = []
    mx = max(values) or 1
    bw = CW / len(values)
    for i, v in enumerate(values):
        h = max(2.5, v / mx * (CH_BOT - CH_TOP))
        bx = x + i * bw + gap_px / 2
        w = bw - gap_px
        box = [(bx, CH_BOT - h), (bx + w, CH_BOT - h), (bx + w, CH_BOT), (bx, CH_BOT)]
        if w > 9:
            out.append(pen.hachure(box, color, gap=4.5, opacity=.7))
        else:
            out.append(f'<rect x="{bx:.1f}" y="{CH_BOT - h:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{color}" opacity=".35"/>')
        out.append(pen.poly(box, color, 1.5 if w > 9 else 1.1, .4, close=True, passes=2 if w > 9 else 1))
        if labels[i] and i % every == 0:
            out.append(f'<text x="{bx + w / 2:.1f}" y="{CH_BOT + 18}" text-anchor="middle" class="ax">{labels[i]}</text>')
    return "".join(out)


def col_contrib(pen, t, x, g):
    years = g["contributions_by_year"]
    this_year = str(NOW.year)
    daily = g.get("daily_30") or []
    out = [f'<text x="{x}" y="46" class="num">{years.get(this_year, 0):,}</text>',
           f'<text x="{x}" y="74" class="lbl">contributions in {this_year},</text>',
           f'<text x="{x}" y="94" class="lbl">{g.get("streak", 0)} days in a row and counting</text>']
    if daily:
        out.append(bars(pen, t, x, daily, [""] * len(daily), t["a1"], gap_px=2.5))
        out.append(f'<text x="{x}" y="{CH_BOT + 18}" class="ax">last 30 days</text>'
                   f'<text x="{x + CW}" y="{CH_BOT + 18}" text-anchor="end" class="ax">today</text>')
    return "".join(out)


def col_commits(pen, t, x, g):
    h = g["commits_by_hour"]
    peak = h.index(max(h))
    out = [f'<text x="{x}" y="46" class="num">{g["commits"]:,}</text>',
           f'<text x="{x}" y="74" class="lbl">commits across {g["repos"]} repos, {g["ai_share"]}%</text>',
           f'<text x="{x}" y="94" class="lbl">co-written with AI agents</text>']
    labels = [f"{i:02d}:00" if i in (0, 12) else "" for i in range(24)]
    out.append(bars(pen, t, x, h, labels, t["a2"], gap_px=3))
    out.append(f'<text x="{x + CW}" y="{CH_BOT + 18}" text-anchor="end" class="ax">busiest {peak:02d}:00</text>')
    return "".join(out)


def col_stars(pen, t, x, s):
    """Stars as a running total: it only ever goes up."""
    months = s["months"]
    # start where it got going, so the line climbs instead of idling
    start = next((k for k, (_, v) in enumerate(months) if v >= max(3, s["total"] * .05)), 0)
    before = sum(v for _, v in months[:start])
    months = months[start:]
    first = datetime.strptime(months[0][0], "%Y-%m")
    span = (NOW.year - first.year) * 12 + NOW.month - first.month + 1
    per = dict(months)
    run, series, labels = before, [], []
    for k in range(span):
        m = (first.month - 1 + k) % 12 + 1
        y = first.year + (first.month - 1 + k) // 12
        run += per.get(f"{y}-{m:02d}", 0)
        series.append(run)
        labels.append(datetime(y, m, 1).strftime("%b"))
    out = [f'<text x="{x}" y="46" class="num">{s["total"]} ★</text>',
           f'<text x="{x}" y="74" class="lbl">stars on my public repos,</text>',
           f'<text x="{x}" y="94" class="lbl">{s["downloads"]:,} downloads of mectrics</text>']
    mx = max(series) or 1
    pts = [(x + i * CW / max(1, len(series) - 1), CH_BOT - v / mx * (CH_BOT - CH_TOP)) for i, v in enumerate(series)]
    out.append(pen.hachure(pts + [(x + CW, CH_BOT), (x, CH_BOT)], t["a3"], gap=4.5, opacity=.55))
    out.append(pen.poly(pts, t["a3"], 2.2, .5))
    out.append(pen.poly([(x, CH_BOT), (x + CW, CH_BOT)], t["faint"], 1.3, .3, passes=1))
    out.append(f'<text x="{x}" y="{CH_BOT + 18}" class="ax">{labels[0]} {first.year}</text>'
               f'<text x="{x + CW}" y="{CH_BOT + 18}" text-anchor="end" class="ax">now</text>')
    return "".join(out)


# --- the agent bros: one squared-off body, a colour and an accessory each, and a
# role that comes with the accessory. They live huddled in the bottom-right
# corner; once per loop they step out, play a short scene, and go back.
INK = "#111318"
CREW = [  # accessory, colour, role
    ("plain", "#FF5A3C", "lead"),
    ("glasses", "#FFB21E", "reviewer"),
    ("visor", "#22C55E", "ci"),
    ("headphones", "#2F80FF", "coder"),
    ("cap", "#8B5CF6", "intern"),
    ("shades", "#FF4FA0", "deployer"),
    ("bowtie", "#14B8A6", "docs"),
]
LEAD, REVIEWER, CI, CODER, INTERN, DEPLOYER, DOCS = range(7)


def scene_for(data):
    """Pick tonight's (or today's) scene from the real clock, weather and stats."""
    g = data.get("github") or {}
    contrib = sum((g.get("contributions_by_year") or {}).values())
    wk = FORCE_WEATHER or (data.get("weather") or {}).get("kind")
    streak = g.get("streak") or 0
    scenes = {
        "review": [(LEAD, "PR is up"), (CODER, "lgtm"), (CI, "tests green"), (REVIEWER, "one nit."), (REVIEWER, "...fine. lgtm")],
        "visitor": [(DOCS, "someone's here"), (LEAD, "act natural"), (DEPLOYER, "we're always this tidy"), (INTERN, "hi")],
        "readme": [(DOCS, "anyone updated the README?"), (LEAD, "we're in the README"), (DOCS, "oh.")],
        "stats": [(DOCS, f"{contrib:,} contributions"), (INTERN, "we did half of those"), (LEAD, "shh")],
        "night": [(LEAD, "he's asleep"), (INTERN, "finally"), (DEPLOYER, "deploy?"), (LEAD, "no.")],
        "friday": [(DEPLOYER, "friday deploy, who's in?"), (CI, "tests say no"), (REVIEWER, "I say no"), (LEAD, "absolutely not"),
                   (DEPLOYER, "already pushed"), (LEAD, "f*ck.")],
        "standup": [(LEAD, "standup. go"), (CODER, "shipping"), (INTERN, "learning"), (DEPLOYER, "vibing"), (LEAD, "great standup")],
        "ratelimit": [(CODER, "rate limited"), (LEAD, "again?"), (CODER, "#@%&!"), (DOCS, "language.")],
        "conflict": [(INTERN, "merge conflict"), (REVIEWER, "how many files?"), (INTERN, "yes"), (REVIEWER, "sh*t")],
        "flaky": [(CI, "test failed"), (CODER, "rerun it"), (CI, "passed"), (REVIEWER, "nobody touch anything")],
        "context": [(CODER, "context window full"), (CODER, "who am I"), (LEAD, "/compact"), (CODER, "ah. hi")],
        "weekend": [(INTERN, "it's the weekend"), (INTERN, "day off?"), (LEAD, "we're agents"), (INTERN, "ugh")],
        "monday": [(LEAD, "monday."), (DEPLOYER, "who scheduled this"), (CI, "the calendar"), (DEPLOYER, "wtf, calendar")],
        "streak": [(DOCS, f"{streak}-day streak"), (INTERN, "does he sleep?"), (CODER, "does he?"), (LEAD, "back to work")],
    }
    if os.environ.get("FORCE_SCENE") in scenes:  # previews only
        name = os.environ["FORCE_SCENE"]
    elif 0 <= NOW.hour < 6:
        name = "night"
    elif NOW.weekday() == 4 and NOW.hour >= 12:
        name = "friday"
    elif NOW.weekday() == 0 and NOW.hour < 12:
        name = "monday"
    elif NOW.weekday() >= 5 and NOW.hour % 6 < 2:
        name = "weekend"
    else:
        pool = ["review", "visitor", "readme", "stats", "standup", "ratelimit", "conflict", "flaky", "context"]
        if streak >= 7:
            pool.append("streak")
        name = pool[(NOW.timetuple().tm_yday * 12 + NOW.hour // 2) % len(pool)]
    return name, scenes[name]


def agent(acc, c, i):
    """Shared body: a square head with ear nubs and tall eyes, centred on 0,0.
    Eyes sit in a .gz group (glances) inside an .eye group (blinks)."""
    def eyes(inner):
        return f'<g class="gz{i}"><g class="eye">{inner}</g></g>'
    body = (f'<rect x="-21" y="-6" width="5" height="12" rx="1" fill="{c}"/><rect x="16" y="-6" width="5" height="12" rx="1" fill="{c}"/>'
            f'<rect x="-17" y="-16" width="34" height="32" rx="4" fill="{c}"/>')
    pills = eyes(f'<rect x="-8.5" y="-5" width="5" height="10" rx="1" fill="{INK}"/><rect x="3.5" y="-5" width="5" height="10" rx="1" fill="{INK}"/>')
    if acc == "glasses":
        return (body + eyes(f'<rect x="-8.5" y="-2.5" width="4" height="5" rx=".8" fill="{INK}"/><rect x="4.5" y="-2.5" width="4" height="5" rx=".8" fill="{INK}"/>')
                + f'<rect x="-12.5" y="-6" width="11" height="12" rx="2" fill="none" stroke="{INK}" stroke-width="2"/><rect x="1.5" y="-6" width="11" height="12" rx="2" fill="none" stroke="{INK}" stroke-width="2"/>')
    if acc == "visor":
        return (body + f'<clipPath id="vz"><rect x="-11" y="-4" width="22" height="8" rx="1.5"/></clipPath>'
                + eyes(f'<rect x="-11" y="-4" width="22" height="8" rx="1.5" fill="{INK}"/>')
                + f'<g clip-path="url(#vz)"><rect class="scan" x="-14" y="-4" width="4" height="8" fill="#9BFFC4" opacity=".75"/></g>')
    if acc == "headphones":
        return (body + pills + f'<path d="M-19,-6 C-19,-30 19,-30 19,-6" fill="none" stroke="{INK}" stroke-width="3.2"/>'
                f'<rect x="-23" y="-8" width="7" height="14" rx="1.5" fill="{INK}"/><rect x="16" y="-8" width="7" height="14" rx="1.5" fill="{INK}"/>')
    if acc == "cap":
        return body + pills + f'<rect x="-17" y="-22" width="34" height="9" rx="2" fill="{INK}"/><rect x="6" y="-15" width="20" height="4" rx="1" fill="{INK}"/>'
    if acc == "shades":
        return body + eyes(f'<rect x="-13" y="-4" width="11" height="8" rx="1.5" fill="{INK}"/><rect x="2" y="-4" width="11" height="8" rx="1.5" fill="{INK}"/><rect x="-3" y="-2" width="6" height="2" fill="{INK}"/>')
    if acc == "bowtie":
        return body + pills + f'<path d="M0,22 l-8,-5 v10z M0,22 l8,-5 v10z" fill="{INK}"/><rect x="-2" y="20" width="4" height="4" fill="{INK}"/>'
    return body + pills


def crew(data, ctx=None):
    ctx = ctx or {}
    n = len(CREW)
    name, lines = scene_for(data)
    # where they live: a small tight cluster in the bottom-right corner
    home = [(796 + 12 * math.cos(-math.pi / 2 + i * math.tau / n), 196 + 11 * math.sin(-math.pi / 2 + i * math.tau / n)) for i in range(n)]
    home_s = .5
    # where they stand for the scene
    if name == "visitor":  # they line up, very tidy
        stage = [(520 + k * 44, 132) for k in range(n)]
        stage_s = .82
    else:
        cx, cy, r = 610, 118, 68
        stage = [(cx + r * math.cos(-math.pi / 2 + i * math.tau / n), cy + r * math.sin(-math.pi / 2 + i * math.tau / n)) for i in range(n)]
        stage_s = .86

    # timeline, in seconds
    t_out0, t_out1 = 3.0, 4.8
    t_talk = 5.2
    D, typing = 2.9, .75
    t_end = t_talk + len(lines) * D
    t_back0, t_back1, late = t_end + .4, t_end + 2.2, 1.1
    # the sneak: once everyone is home, one of them slips out, edits the card
    # without a word, and hurries back. The edit stays until the loop restarts.
    if os.environ.get("FORCE_SNEAK"):  # previews only
        sneak = os.environ["FORCE_SNEAK"]
    elif ctx.get("night"):
        sneak = "moon"
    else:
        sneak = ["bros", "crown"][(NOW.timetuple().tm_yday * 12 + NOW.hour // 2) % 2]
    sneaker, target = {
        "bros": (DOCS, (414, 166)),
        "crown": (INTERN, (92, 20)),
        "moon": (INTERN, (808, 94)),
    }[sneak]
    s0 = t_back1 + late + 1.2
    s_peek0, s_peek1 = s0 + 1.0, s0 + 2.4
    s_arrive, s_fix = s0 + 3.3, s0 + 3.7
    s_leave, s_home = s0 + 4.6, s0 + 5.6
    L = s_home + 3.0
    pct = lambda t: f"{100 * t / L:.2f}%"
    late_one = (NOW.timetuple().tm_yday + NOW.hour) % n

    styles, figs, bubbles = [], [], []
    for i, (acc, col, _) in enumerate(CREW):
        hx, hy = home[i]
        sx, sy = stage[i]
        stagger = i * .08
        b0, b1 = t_back0 + stagger, t_back1 + stagger + (late if i == late_one else 0)
        H = f"transform:translate({hx:.1f}px,{hy:.1f}px) scale({home_s})"
        S = f"transform:translate({sx:.1f}px,{sy:.1f}px) scale({stage_s})"
        tail = f"{pct(b1)},100%{{{H}}}"
        if i == sneaker:
            hx2, hy2 = home[i]
            px, py = hx2 + .35 * (target[0] - hx2), hy2 + .35 * (target[1] - hy2)
            P = f"transform:translate({px:.1f}px,{py:.1f}px) scale(.7)"
            T = f"transform:translate({target[0]}px,{target[1]}px) scale(.7)"
            tail = f"{pct(b1)},{pct(s0)}{{{H}}}{pct(s_peek0)},{pct(s_peek1)}{{{P}}}{pct(s_arrive)},{pct(s_leave)}{{{T}}}{pct(s_home)},100%{{{H}}}"
        styles.append(f"@keyframes a{i}{{0%,{pct(t_out0 + stagger)}{{{H}}}{pct(t_out1 + stagger)},{pct(b0)}{{{S}}}{tail}}}"
                      f".a{i}{{{H};animation:a{i} {L:.1f}s cubic-bezier(.6,0,.2,1) infinite}}")
        # glances: everyone looks at whoever is talking; the speaker looks out at the visitor
        g_stops = ["0%{transform:none}", f"{pct(t_talk - .2)}{{transform:none}}"]
        hop = ["0%{transform:none}"]
        for k, (spk, _) in enumerate(lines):
            t0, t1 = t_talk + k * D, t_talk + (k + 1) * D
            if spk == i:
                # look at whoever you're answering; the opener looks at who answers next
                prev = next((lines[j][0] for j in range(k - 1, -1, -1) if lines[j][0] != i), None)
                nxt = next((lines[j][0] for j in range(k + 1, len(lines)) if lines[j][0] != i), None)
                who = prev if prev is not None else nxt
                tx, ty = stage[who] if who is not None else (sum(p[0] for p in stage) / n, sum(p[1] for p in stage) / n)
                vx, vy = tx - sx, ty - sy
                m = math.hypot(vx, vy) or 1
                dx, dy = 2.4 * vx / m, 1.6 * vy / m
                hop.append(f"{pct(t0)}{{transform:none}}{pct(t0 + .18)}{{transform:translateY(-5px)}}{pct(t0 + .4)}{{transform:none}}")
            else:
                vx, vy = stage[spk][0] - sx, stage[spk][1] - sy
                m = math.hypot(vx, vy) or 1
                dx, dy = 2.4 * vx / m, 1.6 * vy / m
            g_stops.append(f"{pct(t0 + .15)},{pct(t1 - .1)}{{transform:translate({dx:.1f}px,{dy:.1f}px)}}")
        g_stops.append(f"{pct(t_end + .2)}{{transform:none}}")
        if i == sneaker:  # a careful look around before going for it
            g_stops.append(f"{pct(s_peek0 + .1)}{{transform:none}}{pct(s_peek0 + .35)},{pct(s_peek0 + .7)}{{transform:translateX(-2.6px)}}"
                           f"{pct(s_peek0 + .95)},{pct(s_peek1 - .2)}{{transform:translateX(2.6px)}}{pct(s_peek1)}{{transform:none}}")
        g_stops.append("100%{transform:none}")
        hop.append("100%{transform:none}")
        styles.append(f"@keyframes g{i}{{{''.join(g_stops)}}}.gz{i}{{animation:g{i} {L:.1f}s ease-in-out infinite}}")
        styles.append(f"@keyframes h{i}{{{''.join(hop)}}}.h{i}{{animation:h{i} {L:.1f}s linear infinite}}")
        figs.append(f'<g class="a{i}"><g class="h{i}"><g class="blink" style="--d:{i * .7:.1f}s">{agent(acc, col, i)}</g></g></g>')

    for k, (spk, text) in enumerate(lines):
        t0, t1 = t_talk + k * D, t_talk + (k + 1) * D - .25
        sx, sy = stage[spk]
        w = 22 + len(text) * 7
        below = sy < 80
        by = sy + 24 if below else sy - 48
        bx = min(max(sx - w / 2, 8), 832 - w)
        tail = (f'<path d="M{sx - 4:.1f},{by + .5:.1f} l4,-6 l4,6z" fill="#FFFFFF"/>' if below
                else f'<path d="M{sx - 4:.1f},{by + 23.5:.1f} l4,6 l4,-6z" fill="#FFFFFF"/>')
        styles.append(f"@keyframes b{k}{{0%,{pct(t0)}{{opacity:0;transform:translateY(3px)}}{pct(t0 + .15)},{pct(t1)}{{opacity:1;transform:none}}{pct(t1 + .2)},100%{{opacity:0}}}}"
                      f".b{k}{{opacity:0;animation:b{k} {L:.1f}s linear infinite}}"
                      f"@keyframes d{k}{{0%,{pct(t0 + typing)}{{opacity:1}}{pct(t0 + typing + .05)},100%{{opacity:0}}}}.d{k}{{animation:d{k} {L:.1f}s linear infinite}}"
                      f"@keyframes x{k}{{0%,{pct(t0 + typing)}{{opacity:0}}{pct(t0 + typing + .05)},100%{{opacity:1}}}}.x{k}{{opacity:0;animation:x{k} {L:.1f}s linear infinite}}")
        bubbles.append(f'<g class="b{k}"><rect x="{bx:.1f}" y="{by:.1f}" width="{w:.1f}" height="24" rx="12" fill="#FFFFFF"/>{tail}'
                       f'<text x="{bx + w / 2:.1f}" y="{by + 16.5:.1f}" text-anchor="middle" class="say d{k}">• • •</text>'
                       f'<text x="{bx + w / 2:.1f}" y="{by + 16.5:.1f}" text-anchor="middle" class="say x{k}">{escape(text)}</text></g>')
    col = CREW[sneaker][1]
    # doodles: drawn on with the pen (pathLength=1), never popped in
    draw = (f"@keyframes dr{{0%,{pct(s_fix)}{{stroke-dashoffset:1}}{pct(s_fix + 1.0)},100%{{stroke-dashoffset:0}}}}"
            f".dr{{stroke-dasharray:1;stroke-dashoffset:1;animation:dr {L:.1f}s cubic-bezier(.45,.05,.35,1) infinite}}"
            f"@keyframes fxo{{0%,{pct(s_fix)}{{opacity:1}}{pct(L - 1.1)}{{opacity:1}}{pct(L - .3)},100%{{opacity:0}}}}.fx{{animation:fxo {L:.1f}s linear infinite}}")
    pen = Pen(97)

    def doodle(pts, w=2.2, rough=.9):
        out = []
        for k in range(2):
            p = [(x + pen.j(rough), y + pen.j(rough)) for x, y in pts]
            d = "M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in p)
            out.append(f'<path class="dr" pathLength="1" d="{d}" fill="none" stroke="{col}" stroke-width="{w if k == 0 else w * .6:.1f}" '
                       f'stroke-linecap="round" stroke-linejoin="round" opacity="{1 if k == 0 else .6}"/>')
        return "".join(out)

    if sneak == "bros":  # 'agent bros' sits at x 314..384 on the bottom line (Bricolage 14px)
        # a real cross-out: there and back over the word, a little loose
        zig = [(311, 191)]
        for k, x in enumerate(range(315, 389, 5)):
            zig.append((x, 186 if k % 2 else 195))
        for k, x in enumerate(range(386, 312, -6)):
            zig.append((x, 188 if k % 2 else 193.5))
        with open(os.path.join(ROOT, "assets", "fonts", "caveat-note.ttf"), "rb") as f:
            note_font = base64.b64encode(f.read()).decode()
        styles.append(draw + f"@font-face{{font-family:Note;src:url(data:font/ttf;base64,{note_font}) format('truetype')}}"
                      f"@keyframes wr{{0%,{pct(s_fix + .7)}{{clip-path:inset(-10px 100% -10px -4px)}}{pct(s_fix + 1.9)},100%{{clip-path:inset(-10px -4px -10px -4px)}}}}"
                      f".wr{{font:700 21px Note, 'Segoe Print', cursive;clip-path:inset(-10px 100% -10px -4px);animation:wr {L:.1f}s linear infinite}}")
        effect = (f'<g class="fx">{doodle(zig, 1.6, .5)}'
                  f'<text x="320" y="174" class="wr" fill="{col}" transform="rotate(-5 320 174)">coworkers</text></g>')
    elif sneak == "crown":  # a crown doodled on the F of the name
        crown = [(40, 33), (42, 20), (48, 28), (53, 15), (58, 28), (64, 20), (66, 33), (40, 33)]
        styles.append(draw)
        effect = f'<g class="fx" transform="rotate(-10 53 26)">{doodle(crown, 2.3, .6)}{doodle([(53, 10), (53.5, 10.5)], 3, .1)}</g>'
    else:  # lights out on the moon
        styles.append(f"@keyframes mo{{0%,{pct(s_fix)}{{opacity:1}}{pct(s_fix + .2)},{pct(L - .5)}{{opacity:.12}}100%{{opacity:1}}}}"
                      f".moonfx{{animation:mo {L:.1f}s steps(1,end) infinite}}")
        effect = ""
    css = ("".join(styles) +
           ".blink .eye{transform-box:fill-box;transform-origin:center;animation:eye 5s infinite;animation-delay:var(--d)}"
           "@keyframes eye{0%,93%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}"
           ".scan{animation:scan 2.2s ease-in-out infinite alternate}@keyframes scan{to{transform:translateX(24px)}}"
           f".say{{font:500 12.5px {FONT};fill:#1F2328}}.edit{{font:500 14px {FONT}}}")
    return css, effect + "".join(figs) + "".join(bubbles)


def stats(data, theme):
    t = THEMES[theme]
    pen = Pen(31)
    W, H = 840, 196
    g = data.get("github") or {}
    cols = []
    if g.get("contributions_by_year"):
        cols.append(lambda x: col_contrib(pen, t, x, g))
    if g.get("commits"):
        cols.append(lambda x: col_commits(pen, t, x, g))
    if data.get("stars"):
        cols.append(lambda x: col_stars(pen, t, x, data["stars"]))
    body = "".join(fn(x) for x, fn in zip([0, CW + GAP, 2 * (CW + GAP)], cols))
    s = data.get("stars") or {}
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{sum((g.get('contributions_by_year') or {}).values()):,} GitHub contributions; {g.get('commits', 0):,} commits, {g.get('ai_share', '')}% co-written with AI agents; {s.get('total', '')} stars">
<style>
{font_face()}
.num{{font:600 40px {FONT};fill:{t["ink"]};letter-spacing:-1.2px}}
.lbl{{font:400 15px {FONT};fill:{t["soft"]}}}
.ax{{font:400 13px {FONT};fill:{t["soft"]}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
{body}
</svg>"""


def main():
    data = collect()
    os.makedirs(DIST, exist_ok=True)
    open(os.path.join(DIST, "sky.svg"), "w").write(sky(data))
    for th in THEMES:
        open(os.path.join(DIST, f"stats-{th}.svg"), "w").write(stats(data, th))


if __name__ == "__main__":
    main()
