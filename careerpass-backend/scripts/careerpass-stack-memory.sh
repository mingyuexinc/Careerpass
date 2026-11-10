#!/usr/bin/env bash
# Sum RSS of CareerPass Compose services; optional alert threshold for co-host monitoring.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE=${COMPOSE_FILE:-"$BACKEND_DIR/../docker-compose.production.yml"}
ENV_FILE=${ENV_FILE:-"$BACKEND_DIR/.env.production"}
ALERT_MIB=${CAREERPASS_STACK_RSS_ALERT_MIB:-450}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "env file not found (set ENV_FILE)" >&2
  exit 2
fi

mapfile -t ids < <(
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps -q 2>/dev/null || true
)

if [[ ${#ids[@]} -eq 0 ]]; then
  echo "no compose containers running" >&2
  exit 3
fi

parse_usage_kib() {
  local line="$1"
  local used="${line%% / *}"
  if [[ "$used" == *GiB ]]; then
    local num="${used%GiB}"
    awk -v g="$num" 'BEGIN { printf "%.0f", g * 1024 * 1024 }'
  else
    local num="${used%MiB}"
    awk -v m="$num" 'BEGIN { printf "%.0f", m * 1024 }'
  fi
}

total_kib=0
while IFS= read -r line; do
  kib=$(parse_usage_kib "$line")
  total_kib=$((total_kib + kib))
done < <(docker stats --no-stream --format '{{.MemUsage}}' "${ids[@]}")

total_mib=$(( (total_kib + 1023) / 1024 ))
mem_avail_kb=""
if [[ -r /proc/meminfo ]]; then
  mem_avail_kb=$(awk '/^MemAvailable:/ { print $2 }' /proc/meminfo)
fi

echo "careerpass_stack_rss_mib=${total_mib}"
if [[ -n "$mem_avail_kb" ]]; then
  mem_avail_mib=$(( (mem_avail_kb + 1023) / 1024 ))
  echo "mem_available_mib=${mem_avail_mib}"
fi

if [[ "$total_mib" -gt "$ALERT_MIB" ]]; then
  echo "ALERT: CareerPass stack RSS ${total_mib} MiB exceeds threshold ${ALERT_MIB} MiB" >&2
  exit 1
fi

exit 0
