"""Draw assets/stats.svg from live GitHub data. Standard library only.

Run by .github/workflows/stats.yml (GITHUB_TOKEN is provided there).
Local preview with fake data:  python scripts/gen_stats.py --demo
"""
import datetime
import html
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "stats.svg"
USER = os.getenv("USERNAME") or os.getenv("GITHUB_REPOSITORY_OWNER") or "maoozgul20"
TOKEN = os.getenv("GITHUB_TOKEN", "")

BG, PANEL, DEEP = "#0d0e16", "#14162a", "#0f1124"
CYA, VIO, PNK = "#22d3ee", "#a78bfa", "#f472b6"
TXT, MUTE = "#d6dcff", "#8c92b5"
SANS = "Inter,'Segoe UI',Arial,sans-serif"
MONO = "'Fira Code',Consolas,monospace"
PALETTE = [CYA, VIO, PNK, "#fbbf24", "#60a5fa", "#34d399"]


def api(path, data=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(data).encode() if data else None,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"},
    )
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch():
    user = api(f"/users/{USER}")
    repos, page = [], 1
    while True:
        chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r.get("fork")]
    langs = {}
    for r in own:
        try:
            for lang, n in api(f"/repos/{USER}/{r['name']}/languages").items():
                langs[lang] = langs.get(lang, 0) + n
        except Exception:
            pass
    contrib = None
    try:
        q = {"query": 'query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{totalContributions}}}}',
             "variables": {"u": USER}}
        contrib = api("/graphql", q)["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except Exception:
        pass
    return {
        "repos": user.get("public_repos", len(own)),
        "stars": sum(r.get("stargazers_count", 0) for r in own),
        "followers": user.get("followers", 0),
        "contrib": contrib,
        "langs": langs,
    }


def fmt(n):
    return "-" if n is None else f"{n:,}"


def render(d):
    W, H = 1000, 250
    fonts = (Path(__file__).parent / "fonts.css").read_text() if (Path(__file__).parent / "fonts.css").exists() else ""
    total = sum(d["langs"].values()) or 1
    top = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:6]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    def fade(delay, dur=0.6):
        if delay == 0:
            return f'<animate attributeName="opacity" values="0;1" dur="{dur}s" fill="freeze"/>'
        T = delay + dur
        return f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{delay/T:.4f};1" dur="{T:.2f}s" fill="freeze"/>'

    b = [f'<rect width="{W}" height="{H}" rx="22" fill="url(#bg)"/><rect width="{W}" height="{H}" rx="22" fill="url(#dots)"/>',
         f'<text x="40" y="52" font-family="{SANS}" font-size="26" font-weight="700" fill="url(#ac)">GitHub stats</text>',
         f'<text x="960" y="50" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTE}">auto-updated {now} (UTC)</text>']
    tiles = [("PUBLIC REPOS", d["repos"], CYA), ("STARS EARNED", d["stars"], VIO),
             ("FOLLOWERS", d["followers"], PNK), ("CONTRIBUTIONS, LAST YEAR", d["contrib"], "#fbbf24")]
    for i, (lab, n, col) in enumerate(tiles):
        x = 40 + i * 232
        b.append(f'<g>{fade(0.2 + i * 0.15)}<rect x="{x}" y="72" width="218" height="82" rx="14" fill="{DEEP}" stroke="{col}" stroke-opacity=".6"/>'
                 f'<text x="{x+18}" y="98" font-family="{MONO}" font-size="10.5" fill="{MUTE}">{html.escape(lab)}</text>'
                 f'<text x="{x+18}" y="140" font-family="{SANS}" font-size="36" font-weight="700" fill="{col}">{fmt(n)}</text></g>')
    b.append(f'<text x="40" y="184" font-family="{SANS}" font-size="13" font-weight="700" fill="#fff">Top languages (by code size)</text>')
    b.append(f'<clipPath id="lc"><rect x="40" y="194" width="920" height="14" rx="7"><animate attributeName="width" values="0;0;920" keyTimes="0;.15;1" dur="1.6s" fill="freeze"/></rect></clipPath>')
    x, segs = 40.0, []
    for i, (lang, n) in enumerate(top):
        w = 920 * n / sum(v for _, v in top)
        segs.append(f'<rect x="{x:.1f}" y="194" width="{w:.1f}" height="14" fill="{PALETTE[i % len(PALETTE)]}"/>')
        x += w
    b.append(f'<g clip-path="url(#lc)">{"".join(segs)}</g>')
    lx = 40.0
    for i, (lang, n) in enumerate(top):
        label = f"{lang} {100 * n / total:.0f}%"
        b.append(f'<circle cx="{lx+5:.1f}" cy="228" r="4.5" fill="{PALETTE[i % len(PALETTE)]}"/>'
                 f'<text x="{lx+16:.1f}" y="232" font-family="{SANS}" font-size="12" fill="{TXT}">{html.escape(label)}</text>')
        lx += 28 + len(label) * 7.0
    b.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="21" fill="none" stroke="url(#ac)" stroke-opacity=".55" stroke-width="2"/>')
    defs = (f'{fonts}<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="#181a30"/></linearGradient>'
            f'<linearGradient id="ac" x1="0" x2="1"><stop offset="0" stop-color="{CYA}"/><stop offset=".5" stop-color="{VIO}"/><stop offset="1" stop-color="{PNK}"/></linearGradient>'
            f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="{VIO}" fill-opacity=".18"/></pattern>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="GitHub stats">'
            f'<defs>{defs}</defs>{"".join(b)}</svg>\n')


if __name__ == "__main__":
    if "--demo" in sys.argv:
        data = {"repos": 5, "stars": 3, "followers": 12, "contrib": 214,
                "langs": {"JavaScript": 52000, "HTML": 31000, "PHP": 18000, "CSS": 9000, "Python": 4000}}
    else:
        data = fetch()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(data), encoding="utf-8")
    print("wrote", OUT, {k: v for k, v in data.items() if k != "langs"}, list(data["langs"])[:6])
