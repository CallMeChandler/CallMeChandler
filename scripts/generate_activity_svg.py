import json
import os
from datetime import datetime
from urllib.request import Request, urlopen

API_URL = "https://api.github.com/graphql"
USERNAME = os.environ.get("GITHUB_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT_DIR = os.environ.get("OUTPUT_DIR", "profile")

if not USERNAME:
    raise SystemExit("Missing GITHUB_USERNAME or GITHUB_REPOSITORY_OWNER")
if not TOKEN:
    raise SystemExit("Missing GITHUB_TOKEN")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            contributionLevel
            date
            weekday
          }
          firstDay
        }
      }
    }
  }
}
"""

payload = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode("utf-8")
req = Request(
    API_URL,
    data=payload,
    headers={
        "Authorization": f"bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "callmechandler-profile-calendar",
    },
)

with urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))

if "errors" in data:
    raise SystemExit("GraphQL error: " + json.dumps(data["errors"]))

calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total = calendar["totalContributions"]

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "text": "#e6edf3",
        "muted": "#7d8590",
        "border": "#30363d",
        "levels": {
            "NONE": "#161b22",
            "FIRST_QUARTILE": "#0e4429",
            "SECOND_QUARTILE": "#006d32",
            "THIRD_QUARTILE": "#26a641",
            "FOURTH_QUARTILE": "#39d353",
        },
    },
    "light": {
        "bg": "#ffffff",
        "text": "#24292f",
        "muted": "#57606a",
        "border": "#d0d7de",
        "levels": {
            "NONE": "#ebedf0",
            "FIRST_QUARTILE": "#9be9a8",
            "SECOND_QUARTILE": "#40c463",
            "THIRD_QUARTILE": "#30a14e",
            "FOURTH_QUARTILE": "#216e39",
        },
    },
}

CELL = 11
GAP = 3
PITCH = CELL + GAP
LEFT = 44
RIGHT = 18
HEADER_H = 28
MONTHS_H = 20
BOTTOM = 18
ROWS = 7
COLS = len(weeks)
GRID_W = COLS * PITCH - GAP
WIDTH = LEFT + GRID_W + RIGHT
HEIGHT = HEADER_H + MONTHS_H + ROWS * PITCH - GAP + BOTTOM

def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

month_labels = []
last_month = None
for col, week in enumerate(weeks):
    label = None
    for day in week["contributionDays"]:
        d = datetime.strptime(day["date"], "%Y-%m-%d").date()
        if last_month is None:
            last_month = d.month
            label = d.strftime("%b")
            break
        if d.month != last_month:
            last_month = d.month
            label = d.strftime("%b")
            break
    if label:
        month_labels.append((col, label))

weekday_labels = [("Mon", 1), ("Wed", 3), ("Fri", 5)]

def render(theme):
    grid_y = HEADER_H + MONTHS_H
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(USERNAME)} contribution calendar</title>',
        f'<desc id="desc">{total} contributions in the last year</desc>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="6" fill="{theme["bg"]}" stroke="{theme["border"]}"/>',
        f'<text x="14" y="19" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="14" font-weight="400" fill="{theme["text"]}">{total} contributions in the last year</text>',
    ]

    month_y = HEADER_H + 12
    for col, label in month_labels:
        x = LEFT + col * PITCH
        parts.append(
            f'<text x="{x}" y="{month_y}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="10" fill="{theme["muted"]}">{label}</text>'
        )

    for label, row in weekday_labels:
        y = grid_y + row * PITCH + CELL - 1
        parts.append(
            f'<text x="12" y="{y}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="10" fill="{theme["muted"]}">{label}</text>'
        )

    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            row = day["weekday"]
            x = LEFT + col * PITCH
            y = grid_y + row * PITCH
            fill = theme["levels"].get(day["contributionLevel"], theme["levels"]["NONE"])
            count = day["contributionCount"]
            noun = "contribution" if count == 1 else "contributions"
            tooltip = f'{count} {noun} on {day["date"]}'
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}"><title>{esc(tooltip)}</title></rect>'
            )

    parts.append("</svg>")
    return "".join(parts)

os.makedirs(OUT_DIR, exist_ok=True)
for theme_name, theme in THEMES.items():
    path = os.path.join(OUT_DIR, f"contribution-calendar-{theme_name}.svg")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render(theme))
