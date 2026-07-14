#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${SMOKE_API_BASE_URL:-${API_BASE_URL:-http://localhost:8000}}"
FRONTEND_URL="${SMOKE_FRONTEND_URL:-http://localhost:3000}"
RETRIES="${SMOKE_RETRIES:-20}"
RETRY_DELAY_SECONDS="${SMOKE_RETRY_DELAY_SECONDS:-2}"
CURL_TIMEOUT_SECONDS="${SMOKE_CURL_TIMEOUT_SECONDS:-5}"
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

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command not found: $1"
  fi
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local output_file="$3"
  local status_file="$4"
  local attempt

  for attempt in $(seq 1 "$RETRIES"); do
    if curl \
      --silent \
      --show-error \
      --location \
      --max-time "$CURL_TIMEOUT_SECONDS" \
      --output "$output_file" \
      --write-out "%{http_code}" \
      "$url" >"$status_file"; then
      local status
      status="$(cat "$status_file")"
      if [[ "$status" =~ ^2[0-9][0-9]$ ]]; then
        pass "$name responded with HTTP $status"
        return 0
      fi
    fi

    if [[ "$attempt" -lt "$RETRIES" ]]; then
      echo "[WAIT] $name not ready at $url (attempt $attempt/$RETRIES)"
      sleep "$RETRY_DELAY_SECONDS"
    fi
  done

  local final_status="unreachable"
  if [[ -s "$status_file" ]]; then
    final_status="$(cat "$status_file")"
  fi
  fail "$name did not return HTTP 2xx at $url after $RETRIES attempts (last status: $final_status)"
}

json_assert() {
  local file="$1"
  local expression="$2"
  local message="$3"
  python3 - "$file" "$expression" <<'PY'
import json
import sys

path, expression = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as fp:
    data = json.load(fp)
allowed = {"data": data, "isinstance": isinstance, "len": len, "list": list}
if not eval(expression, {"__builtins__": {}}, allowed):
    raise SystemExit(1)
PY
  pass "$message"
}

fetch_json() {
  local name="$1"
  local url="$2"
  local output_file="$3"
  local status_file="$TMP_DIR/status"
  wait_for_url "$name" "$url" "$output_file" "$status_file"
  python3 -m json.tool "$output_file" >/dev/null || fail "$name returned invalid JSON"
  pass "$name returned valid JSON"
}

check_sse() {
  local headers_file="$TMP_DIR/sse.headers"
  local body_file="$TMP_DIR/sse.body"
  local status_file="$TMP_DIR/sse.status"
  local curl_exit=0

  curl \
    --silent \
    --show-error \
    --no-buffer \
    --max-time "$CURL_TIMEOUT_SECONDS" \
    --output "$body_file" \
    --dump-header "$headers_file" \
    --write-out "%{http_code}" \
    "$API_BASE_URL/api/dashboard/stream" >"$status_file" || curl_exit=$?

  if [[ "$curl_exit" != "0" && "$curl_exit" != "28" ]]; then
    fail "SSE endpoint was not reachable"
  fi

  local status
  status="$(cat "$status_file")"
  [[ "$status" =~ ^2[0-9][0-9]$ ]] || fail "SSE endpoint returned HTTP $status"
  grep -qi "content-type: text/event-stream" "$headers_file" ||
    fail "SSE endpoint did not return text/event-stream"
  pass "SSE endpoint returned text/event-stream"
}

main() {
  require_command curl
  require_command python3

  echo "Smoke test configuration"
  echo "- API_BASE_URL=$API_BASE_URL"
  echo "- FRONTEND_URL=$FRONTEND_URL"
  echo "- RETRIES=$RETRIES"
  echo "- CURL_TIMEOUT_SECONDS=$CURL_TIMEOUT_SECONDS"

  local health_json="$TMP_DIR/health.json"
  local summary_json="$TMP_DIR/summary.json"
  local symbols_json="$TMP_DIR/symbols.json"
  local btc_candles_json="$TMP_DIR/btc-candles.json"
  local eth_candles_json="$TMP_DIR/eth-candles.json"
  local events_json="$TMP_DIR/events.json"
  local frontend_html="$TMP_DIR/frontend.html"

  fetch_json "Backend health" "$API_BASE_URL/api/health" "$health_json"
  json_assert "$health_json" "data.get('status') == 'ok'" "Backend health status is ok"

  fetch_json "Dashboard summary" "$API_BASE_URL/api/dashboard/summary" "$summary_json"
  json_assert "$summary_json" "'system_status' in data and isinstance(data.get('symbols'), list)" "Dashboard summary has system status and symbols"

  fetch_json "Dashboard symbols" "$API_BASE_URL/api/dashboard/symbols" "$symbols_json"
  json_assert "$symbols_json" "{item.get('symbol') for item in data} >= {'BTCUSDT', 'ETHUSDT'}" "Dashboard symbols include BTCUSDT and ETHUSDT"

  fetch_json "BTCUSDT candles" "$API_BASE_URL/api/dashboard/candles?symbol=BTCUSDT&interval=1m&limit=1" "$btc_candles_json"
  json_assert "$btc_candles_json" "len(data.get('candles', [])) >= 1" "BTCUSDT has at least one candle"

  fetch_json "ETHUSDT candles" "$API_BASE_URL/api/dashboard/candles?symbol=ETHUSDT&interval=1m&limit=1" "$eth_candles_json"
  json_assert "$eth_candles_json" "len(data.get('candles', [])) >= 1" "ETHUSDT has at least one candle"

  fetch_json "Dashboard events" "$API_BASE_URL/api/dashboard/events?limit=5" "$events_json"
  json_assert "$events_json" "isinstance(data.get('events'), list)" "Dashboard events endpoint returns event list"

  check_sse

  wait_for_url "Frontend root page" "$FRONTEND_URL" "$frontend_html" "$TMP_DIR/frontend.status"
  grep -q "Market Data Operations Console" "$frontend_html" ||
    fail "Frontend page did not contain Market Data Operations Console"
  pass "Frontend page contains Market Data Operations Console"

  if ! command -v docker >/dev/null 2>&1; then
    skip "Docker not found; smoke verified running HTTP services only"
  fi

  pass "Smoke test completed"
}

main "$@"
