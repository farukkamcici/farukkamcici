"""Runs on my Mac (launchd, twice a day) with my own gh login, so private repos
count too. Writes only totals to data/github.json: contributions per year,
all-time commits, commits by hour of day (Istanbul time), and the share of
commits co-authored by an AI agent. No repo names or messages leave the machine."""
import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone

USER = "farukkamcici"
IST = timezone(timedelta(hours=3))
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
AI = re.compile(r"(?im)^co-authored-by:.*(claude|codex|anthropic|openai|copilot)")


def gql(q, v=None):
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": q, "variables": v or {}}).encode(),
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


created = gql("query($l:String!){user(login:$l){createdAt}}", {"l": USER})["user"]["createdAt"]
years = {}
for y in range(int(created[:4]), datetime.now(IST).year + 1):
    c = gql("query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){contributionsCollection(from:$f,to:$t){contributionCalendar{totalContributions}}}}",
            {"l": USER, "f": f"{y}-01-01T00:00:00Z", "t": f"{y}-12-31T23:59:59Z"})
    years[str(y)] = c["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

cal = gql("""query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}""",
          {"l": USER})["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
days = [d["contributionCount"] for w in cal for d in w["contributionDays"]]
streak = 0
for v in reversed(days):  # today may still be empty; don't break the streak for it
    if v == 0 and streak == 0 and v is days[-1]:
        continue
    if v == 0:
        break
    streak += 1
longest = run = 0
for v in days:
    run = run + 1 if v else 0
    longest = max(longest, run)

repos = gql("""query($l:String!){user(login:$l){repositories(first:100,ownerAffiliations:OWNER,isFork:false){totalCount nodes{name}}}}""", {"l": USER})["user"]["repositories"]
hours = [0] * 24
total = ai = 0
HIST = """query($o:String!,$n:String!,$c:String){repository(owner:$o,name:$n){defaultBranchRef{target{...on Commit{
  history(first:100,after:$c){pageInfo{hasNextPage endCursor} nodes{committedDate message author{name}}}}}}}}"""
for r in repos["nodes"]:
    cursor = None
    while True:
        ref = gql(HIST, {"o": USER, "n": r["name"], "c": cursor})["repository"]["defaultBranchRef"]
        if not ref:
            break
        h = ref["target"]["history"]
        for n in h["nodes"]:
            if "github-actions" in (n["author"]["name"] or ""):
                continue
            total += 1
            ai += bool(AI.search(n["message"]))
            hours[datetime.fromisoformat(n["committedDate"].replace("Z", "+00:00")).astimezone(IST).hour] += 1
        if not h["pageInfo"]["hasNextPage"]:
            break
        cursor = h["pageInfo"]["endCursor"]

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "github.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
data = {"contributions_by_year": years, "daily_30": days[-30:], "streak": streak, "longest_streak": longest, "commits": total, "repos": repos["totalCount"], "commits_by_hour": hours,
        "ai_share": round(100 * ai / total) if total else None, "updated": datetime.now(timezone.utc).isoformat(timespec="minutes")}
json.dump(data, open(out, "w"), indent=1)
print(json.dumps(data))
