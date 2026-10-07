#!/usr/bin/env bash
# Drive load at the API so the HPA scales and Grafana has something to draw.
#   ./scripts/load-test.sh [url] [seconds] [concurrency]
# Name: Hemang | Enrollment number: 24bcs10209
set -euo pipefail

URL="${1:-http://localhost:8000}"
DURATION="${2:-60}"
CONCURRENCY="${3:-10}"

echo "load-testing $URL for ${DURATION}s with ${CONCURRENCY} workers"
end=$(( $(date +%s) + DURATION ))

worker() {
  while [ "$(date +%s)" -lt "$end" ]; do
    curl -s -o /dev/null "$URL/api/tasks"
    curl -s -o /dev/null "$URL/health"
    curl -s -o /dev/null -X POST -H 'Content-Type: application/json' \
      -d '{"title":"load-test"}' "$URL/api/tasks"
  done
}

for _ in $(seq 1 "$CONCURRENCY"); do worker & done
wait
echo "done. check:  kubectl get hpa -n stacks -w"
