#!/usr/bin/env bash
set -euo pipefail

mode="${1:-all}"
UV_BIN="${UV_BIN:-$(command -v uv || true)}"
if [[ -z "$UV_BIN" && -x "$HOME/.local/bin/uv" ]]; then
  UV_BIN="$HOME/.local/bin/uv"
fi

require_uv() {
  if [[ -z "$UV_BIN" ]]; then
    echo "uv is required for backend checks. Install it from https://docs.astral.sh/uv/." >&2
    return 127
  fi
}

run_backend_lint() {
  if [[ -f backend/pyproject.toml ]]; then
    require_uv
    (cd backend && "$UV_BIN" run ruff check .)
    return 0
  fi
  echo "SKIP backend lint: backend scaffold not created yet (activates in T02)."
}

run_backend_typecheck() {
  if [[ -f backend/pyproject.toml ]]; then
    require_uv
    (cd backend && "$UV_BIN" run mypy app tests)
    return 0
  fi
  echo "SKIP backend typecheck: backend scaffold not created yet (activates in T02)."
}

run_backend_test() {
  if [[ -f backend/pyproject.toml ]]; then
    require_uv
    (cd backend && "$UV_BIN" run pytest)
    return 0
  fi
  echo "SKIP backend test: backend scaffold not created yet (activates in T02)."
}

run_frontend_lint() {
  if [[ -f frontend/package.json ]]; then
    echo "TODO T03: run frontend lint command from package.json"
    return 1
  fi
  echo "SKIP frontend lint: frontend scaffold not created yet (activates in T03)."
}

run_frontend_typecheck() {
  if [[ -f frontend/package.json ]]; then
    echo "TODO T03: run frontend typecheck command from package.json"
    return 1
  fi
  echo "SKIP frontend typecheck: frontend scaffold not created yet (activates in T03)."
}

run_frontend_test() {
  if [[ -f frontend/package.json ]]; then
    echo "TODO T03/T16+: run frontend tests."
    return 1
  fi
  echo "SKIP frontend test: frontend scaffold not created yet (activates in T03)."
}

run_frontend_build() {
  if [[ -f frontend/package.json ]]; then
    echo "TODO T03: run frontend build command from package.json"
    return 1
  fi
  echo "SKIP frontend build: frontend scaffold not created yet (activates in T03)."
}

case "$mode" in
  lint)
    run_backend_lint
    run_frontend_lint
    ;;
  typecheck)
    run_backend_typecheck
    run_frontend_typecheck
    ;;
  build)
    run_frontend_build
    ;;
  all)
    run_backend_lint
    run_backend_typecheck
    run_backend_test
    run_frontend_lint
    run_frontend_typecheck
    run_frontend_test
    run_frontend_build
    ;;
  *)
    echo "Unknown check mode: $mode" >&2
    exit 2
    ;;
esac
