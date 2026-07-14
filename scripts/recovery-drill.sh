#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
DATABASE_URL="${DATABASE_URL:-}"
POSTGRES_USER="${POSTGRES_USER:-binance}"
POSTGRES_DB="${POSTGRES_DB:-binance_assignment}"
DRILL_SYMBOL="${DRILL_SYMBOL:-BTCUSDT}"
DRILL_INTERVAL="${DRILL_INTERVAL:-1m}"
DRILL_GAP_SECONDS="${DRILL_GAP_SECONDS:-70}"
DRILL_TIMEOUT_SECONDS="${DRILL_TIMEOUT_SECONDS:-180}"
DRILL_RETRY_DELAY_SECONDS="${DRILL_RETRY_DELAY_SECONDS:-5}"
DRILL_RECOVERY_TRIGGER_URL="${DRILL_RECOVERY_TRIGGER_URL:-}"
DRILL_RECOVERY_TRIGGER_METHOD="${DRILL_RECOVERY_TRIGGER_METHOD:-POST}"
DRILL_RECOVERY_COMMAND="${DRILL_RECOVERY_COMMAND:-}"
DRILL_COLLECTOR_PAUSE_URL="${DRILL_COLLECTOR_PAUSE_URL:-}"
DRILL_COLLECTOR_RESUME_URL="${DRILL_COLLECTOR_RESUME_URL:-}"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

pass() {
  echo "[PASS] $1"
}

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

skip() {
  echo "[SKIP] $1"
}

info() {
  echo "[INFO] $1"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command not found: $1"
  fi
}

validate_identifier() {
  local name="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[A-Za-z0-9_]+$ ]]; then
    fail "$name contains unsupported characters: $value"
  fi
}

wait_until() {
  local label="$1"
  shift
  local deadline=$((SECONDS + DRILL_TIMEOUT_SECONDS))
  local attempt=1

  while true; do
    if "$@"; then
      pass "$label"
      return 0
    fi
    if (( SECONDS >= deadline )); then
      fail "$label timed out after ${DRILL_TIMEOUT_SECONDS}s"
    fi
    info "$label not ready (attempt $attempt)"
    attempt=$((attempt + 1))
    sleep "$DRILL_RETRY_DELAY_SECONDS"
  done
}

curl_json() {
  local name="$1"
  local url="$2"
  local output_file="$3"
  local status_file="$TMP_DIR/status"

  if ! curl \
    --silent \
    --show-error \
    --location \
    --max-time 10 \
    --output "$output_file" \
    --write-out "%{http_code}" \
    "$url" >"$status_file"; then
    return 1
  fi

  local status
  status="$(cat "$status_file")"
  [[ "$status" =~ ^2[0-9][0-9]$ ]] || return 1
  python3 -m json.tool "$output_file" >/dev/null || return 1
  return 0
}

json_condition() {
  local file="$1"
  local expression="$2"
  python3 - "$file" "$expression" "$DRILL_SYMBOL" "$DRILL_INTERVAL" <<'PY'
import json
import sys

path, expression, symbol, interval = sys.argv[1:5]
with open(path, "r", encoding="utf-8") as fp:
    data = json.load(fp)
allowed = {
    "any": any,
    "data": data,
    "interval": interval,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "sum": sum,
    "symbol": symbol,
}
if not eval(expression, {"__builtins__": {}}, allowed):
    raise SystemExit(1)
PY
}

fetch_and_assert() {
  local label="$1"
  local url="$2"
  local expression="$3"
  local file="$TMP_DIR/$(echo "$label" | tr ' /' '__').json"
  curl_json "$label" "$url" "$file" && json_condition "$file" "$expression"
}

db_scalar() {
  local sql="$1"
  if command -v psql >/dev/null 2>&1; then
    [[ -n "$DATABASE_URL" ]] || fail "DATABASE_URL is required when using host psql"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At -c "$sql"
    return 0
  fi
  if command -v docker >/dev/null 2>&1; then
    docker compose exec -T postgres psql \
      -U "$POSTGRES_USER" \
      -d "$POSTGRES_DB" \
      -v ON_ERROR_STOP=1 \
      -At \
      -c "$sql"
    return 0
  fi
  fail "No DB client available. Install psql or run with Docker Compose."
}

db_exec() {
  local sql="$1"
  if command -v psql >/dev/null 2>&1; then
    [[ -n "$DATABASE_URL" ]] || fail "DATABASE_URL is required when using host psql"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -c "$sql" >/dev/null
    return 0
  fi
  if command -v docker >/dev/null 2>&1; then
    docker compose exec -T postgres psql \
      -U "$POSTGRES_USER" \
      -d "$POSTGRES_DB" \
      -v ON_ERROR_STOP=1 \
      -q \
      -c "$sql" >/dev/null
    return 0
  fi
  fail "No DB client available. Install psql or run with Docker Compose."
}

quote_sql() {
  printf "%s" "$1" | sed "s/'/''/g"
}

call_optional_control() {
  local label="$1"
  local url="$2"
  if [[ -z "$url" ]]; then
    skip "$label URL not configured"
    return 0
  fi
  curl --silent --show-error --max-time 10 --request POST "$url" >/dev/null ||
    fail "$label request failed: $url"
  pass "$label request accepted"
}

trigger_recovery() {
  if [[ -n "$DRILL_RECOVERY_TRIGGER_URL" ]]; then
    curl \
      --silent \
      --show-error \
      --max-time 30 \
      --request "$DRILL_RECOVERY_TRIGGER_METHOD" \
      "$DRILL_RECOVERY_TRIGGER_URL" >/dev/null ||
      fail "Recovery trigger request failed: $DRILL_RECOVERY_TRIGGER_URL"
    pass "Recovery trigger request accepted"
    return 0
  fi

  if [[ -n "$DRILL_RECOVERY_COMMAND" ]]; then
    bash -lc "$DRILL_RECOVERY_COMMAND" ||
      fail "Recovery command failed: $DRILL_RECOVERY_COMMAND"
    pass "Recovery command completed"
    return 0
  fi

  fail "No recovery trigger configured. Set DRILL_RECOVERY_TRIGGER_URL or DRILL_RECOVERY_COMMAND."
}

check_sse() {
  local headers_file="$TMP_DIR/sse.headers"
  local status_file="$TMP_DIR/sse.status"
  local curl_exit=0
  curl \
    --silent \
    --show-error \
    --no-buffer \
    --max-time 5 \
    --output "$TMP_DIR/sse.body" \
    --dump-header "$headers_file" \
    --write-out "%{http_code}" \
    "$BACKEND_URL/api/dashboard/stream" >"$status_file" || curl_exit=$?
  [[ "$curl_exit" == "0" || "$curl_exit" == "28" ]] || return 1
  grep -qi "content-type: text/event-stream" "$headers_file"
}

check_frontend() {
  local html="$TMP_DIR/frontend.html"
  curl --silent --show-error --location --max-time 10 "$FRONTEND_URL" >"$html" &&
    grep -q "Market Data Operations Console" "$html"
}

main() {
  require_command curl
  require_command python3
  if ! command -v psql >/dev/null 2>&1 && ! command -v docker >/dev/null 2>&1; then
    fail "Recovery drill requires psql or Docker Compose for DB checks"
  fi
  validate_identifier "DRILL_SYMBOL" "$DRILL_SYMBOL"
  validate_identifier "DRILL_INTERVAL" "$DRILL_INTERVAL"

  local gap_candle_count=$(((DRILL_GAP_SECONDS + 59) / 60))
  if (( gap_candle_count < 1 )); then
    gap_candle_count=1
  fi

  echo "Recovery drill configuration"
  echo "- BACKEND_URL=$BACKEND_URL"
  echo "- FRONTEND_URL=$FRONTEND_URL"
  echo "- DRILL_SYMBOL=$DRILL_SYMBOL"
  echo "- DRILL_GAP_SECONDS=$DRILL_GAP_SECONDS"
  echo "- gap_candle_count=$gap_candle_count"
  echo "- DRILL_TIMEOUT_SECONDS=$DRILL_TIMEOUT_SECONDS"

  local symbol_sql
  local interval_sql
  symbol_sql="$(quote_sql "$DRILL_SYMBOL")"
  interval_sql="$(quote_sql "$DRILL_INTERVAL")"

  wait_until "Backend health ready" \
    fetch_and_assert "health" "$BACKEND_URL/api/health" "data.get('status') == 'ok'"
  wait_until "Frontend dashboard ready" check_frontend
  wait_until "SSE stream reachable" check_sse
  wait_until "Database ready" db_scalar "select 1"

  wait_until "Dashboard symbols include BTCUSDT and ETHUSDT" \
    fetch_and_assert "symbols" "$BACKEND_URL/api/dashboard/symbols" "{item.get('symbol') for item in data} >= {'BTCUSDT', 'ETHUSDT'}"
  wait_until "Drill symbol is LIVE before gap" \
    fetch_and_assert "live-before" "$BACKEND_URL/api/dashboard/symbols" "any(item.get('symbol') == symbol and item.get('status') == 'LIVE' for item in data)"
  wait_until "Drill symbol has candles" \
    fetch_and_assert "candles-before" "$BACKEND_URL/api/dashboard/candles?symbol=$DRILL_SYMBOL&interval=$DRILL_INTERVAL&limit=1" "len(data.get('candles', [])) >= 1"

  local before_count
  local before_latest
  local before_duplicates
  before_count="$(db_scalar "select count(*) from candles where symbol = '$symbol_sql' and interval = '$interval_sql';")"
  before_latest="$(db_scalar "select coalesce(max(open_time)::text, '') from candles where symbol = '$symbol_sql' and interval = '$interval_sql';")"
  before_duplicates="$(db_scalar "select count(*) from (select symbol, interval, open_time, count(*) from candles group by 1,2,3 having count(*) > 1) d;")"
  [[ "$before_count" =~ ^[0-9]+$ && "$before_count" -gt "$gap_candle_count" ]] ||
    fail "Not enough candles to create a gap for $DRILL_SYMBOL (count=$before_count)"
  [[ "$before_duplicates" == "0" ]] || fail "Duplicate candles already exist before drill: $before_duplicates"
  pass "Recorded starting row count=$before_count latest_open_time=$before_latest"
  pass "Duplicate candle count before drill is 0"

  call_optional_control "Collector pause" "$DRILL_COLLECTOR_PAUSE_URL"

  local deleted_file="$TMP_DIR/deleted-open-times.txt"
  db_scalar "delete from candles where id in (
      select id from candles
      where symbol = '$symbol_sql' and interval = '$interval_sql'
      order by open_time desc
      offset 2
      limit $gap_candle_count
    )
    returning open_time;" >"$deleted_file"

  local deleted_count
  deleted_count="$(wc -l <"$deleted_file" | tr -d ' ')"
  [[ "$deleted_count" -ge 1 ]] || fail "Gap injection deleted no candles"
  pass "Injected gap by deleting $deleted_count candle row(s)"
  info "Deleted open_time range: $(head -1 "$deleted_file") .. $(tail -1 "$deleted_file")"

  wait_until "Gap detector reports missing candles" \
    fetch_and_assert "gaps-detected" "$BACKEND_URL/api/dashboard/gaps?symbol=$DRILL_SYMBOL&interval=$DRILL_INTERVAL" "data.get('total_missing_candle_count', 0) >= 1"

  call_optional_control "Collector resume" "$DRILL_COLLECTOR_RESUME_URL"
  trigger_recovery

  wait_until "Restart recovery job recorded" \
    fetch_and_assert "recovery-job" "$BACKEND_URL/api/dashboard/backfill-jobs?limit=20" "any(job.get('symbol') == symbol and job.get('job_type') == 'restart_recovery' and job.get('status') in {'RUNNING', 'SUCCEEDED'} for job in data.get('jobs', []))"
  wait_until "Restart recovery job completed" \
    fetch_and_assert "recovery-completed" "$BACKEND_URL/api/dashboard/backfill-jobs?limit=20" "any(job.get('symbol') == symbol and job.get('job_type') == 'restart_recovery' and job.get('status') == 'SUCCEEDED' for job in data.get('jobs', []))"
  wait_until "Gap detector missing count is 0" \
    fetch_and_assert "gaps-recovered" "$BACKEND_URL/api/dashboard/gaps?symbol=$DRILL_SYMBOL&interval=$DRILL_INTERVAL" "data.get('total_missing_candle_count', 0) == 0"
  wait_until "Drill symbol returned to LIVE" \
    fetch_and_assert "live-after" "$BACKEND_URL/api/dashboard/symbols" "any(item.get('symbol') == symbol and item.get('status') == 'LIVE' for item in data)"
  wait_until "Recovery event recorded" \
    fetch_and_assert "events" "$BACKEND_URL/api/dashboard/events?limit=50" "any(event.get('symbol') == symbol and event.get('event_type') in {'recovery_started', 'recovery_completed'} for event in data.get('events', []))"

  local after_count
  local after_latest
  local after_duplicates
  after_count="$(db_scalar "select count(*) from candles where symbol = '$symbol_sql' and interval = '$interval_sql';")"
  after_latest="$(db_scalar "select coalesce(max(open_time)::text, '') from candles where symbol = '$symbol_sql' and interval = '$interval_sql';")"
  after_duplicates="$(db_scalar "select count(*) from (select symbol, interval, open_time, count(*) from candles group by 1,2,3 having count(*) > 1) d;")"

  [[ "$after_duplicates" == "0" ]] || fail "Duplicate candles after recovery: $after_duplicates"
  pass "Duplicate candle count after recovery is 0"
  [[ "$after_count" -ge "$before_count" ]] ||
    fail "Recovered row count did not return to start count (before=$before_count after=$after_count)"
  pass "Recovered row count is at least starting count"
  [[ "$after_latest" > "$before_latest" || "$after_latest" == "$before_latest" ]] ||
    fail "Latest candle regressed after recovery"
  pass "Latest candle did not regress after recovery"

  wait_until "Data collection continues after recovery" \
    fetch_and_assert "candles-after" "$BACKEND_URL/api/dashboard/candles?symbol=$DRILL_SYMBOL&interval=$DRILL_INTERVAL&limit=1" "len(data.get('candles', [])) >= 1"

  pass "Recovery drill completed"
}

main "$@"
