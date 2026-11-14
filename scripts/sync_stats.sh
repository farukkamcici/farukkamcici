#!/bin/zsh
# Run by launchd twice a day: refresh all-time GitHub totals (private repos
# included, via my gh login) and push them. Only totals leave the machine.
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "$0")/.."
git pull --rebase -q
python3 scripts/export_stats.py >/dev/null
git add data/github.json
git diff --staged --quiet && exit 0
git commit -q -m "Update GitHub totals"
git push -q
