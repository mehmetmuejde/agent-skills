#!/usr/bin/env bash
# Soak test for a macOS app: sample the memory footprint over time and diff
# memory graphs taken after warm-up and at the end.
#
# Usage:
#   soak.sh -a <path/App.app/Contents/MacOS/App> [-d seconds] [-i seconds]
#           [-w seconds] [-o output-dir] [-m max-MB-per-hour] [-- app arguments…]
#
#   -a  app executable (inside the bundle, not the .app folder)
#   -d  sampling duration after warm-up (default 1800)
#   -i  sampling interval (default 10)
#   -w  warm-up before the first memory graph (default 60)
#   -o  output directory (default ./soak-<timestamp>)
#   -m  growth budget for analyze_soak.py in MB/hour (default 5)
#
# Exit code: 0 = no leaks and growth within budget, 1 = leaks or growth above
# budget, 2 = tool error. The app must be attachable by the current user:
# development-signed builds carry get-task-allow; a Developer ID build with the
# Hardened Runtime cannot be inspected without it.
set -eu

app=""
duration=1800
interval=10
warmup=60
outdir="soak-$(date +%Y%m%d-%H%M%S)"
max_mb_per_hour=5

while getopts "a:d:i:w:o:m:" opt; do
  case "$opt" in
    a) app="$OPTARG" ;;
    d) duration="$OPTARG" ;;
    i) interval="$OPTARG" ;;
    w) warmup="$OPTARG" ;;
    o) outdir="$OPTARG" ;;
    m) max_mb_per_hour="$OPTARG" ;;
    *) sed -n '5,14p' "$0"; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
[ "${1:-}" = "--" ] && shift

if [ -z "$app" ] || [ ! -x "$app" ]; then
  echo "error: -a must point to the app executable (…/Contents/MacOS/<name>)" >&2
  exit 2
fi

mkdir -p "$outdir"
script_dir="$(cd "$(dirname "$0")" && pwd)"

# Launch by executable path so LaunchServices can't pick another copy of the app.
"$app" "$@" >"$outdir/app-stdout.txt" 2>"$outdir/app-stderr.txt" &
pid=$!
cleanup() { kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "pid $pid, warm-up ${warmup}s, then sampling every ${interval}s for ${duration}s"
sleep "$warmup"
if ! kill -0 "$pid" 2>/dev/null; then
  echo "error: app exited during warm-up (see $outdir/app-stderr.txt)" >&2
  exit 2
fi

# With -outputGraph, leaks only writes the graph (exit 0); the leak scan runs on the file.
leaks "$pid" -outputGraph "$outdir/pre.memgraph" >/dev/null
footprint -p "$pid" --sample "$interval" --sample-duration "$duration" -f bytes \
  -j "$outdir/soak.json" >/dev/null
leaks "$pid" -outputGraph "$outdir/post.memgraph" >/dev/null
cleanup
trap - EXIT INT TERM

pre_rc=0
leaks "$outdir/pre.memgraph" >"$outdir/leaks-pre.txt" 2>&1 || pre_rc=$?
post_rc=0
leaks "$outdir/post.memgraph" >"$outdir/leaks-post.txt" 2>&1 || post_rc=$?

heap "$outdir/post.memgraph" -diffFrom="$outdir/pre.memgraph" -sortBySize \
  >"$outdir/heap-diff.txt" 2>&1 || true
leaks "$outdir/post.memgraph" -diffFrom="$outdir/pre.memgraph" \
  >"$outdir/leaks-new.txt" 2>&1 || true
vmmap -summary "$outdir/post.memgraph" >"$outdir/vmmap-summary.txt" 2>&1 || true

analyze_rc=0
python3 -I "$script_dir/analyze_soak.py" "$outdir/soak.json" \
  --max-mb-per-hour "$max_mb_per_hour" >"$outdir/summary.txt" 2>&1 || analyze_rc=$?
cat "$outdir/summary.txt"

{
  echo "leaks:     pre exit $pre_rc, post exit $post_rc (0 none, 1 leaks, >1 error)"
  grep -h -m1 "total leaked bytes" "$outdir/leaks-post.txt" || true
  grep -h -m1 "TOTAL" "$outdir/leaks-new.txt" | sed 's/^ */new since warm-up: /' || true
} | tee -a "$outdir/summary.txt"
echo "artifacts in $outdir: soak.json, pre/post.memgraph, heap-diff.txt, leaks-new.txt, vmmap-summary.txt"

if [ "$post_rc" -gt 1 ] || [ "$analyze_rc" -gt 1 ]; then exit 2; fi
if [ "$post_rc" -eq 1 ] || [ "$analyze_rc" -eq 1 ]; then exit 1; fi
exit 0
