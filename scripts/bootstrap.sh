#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrap harness"
echo "- Copy .env.example to .env if local overrides are needed."
echo "- TODO T02: install backend dependencies once backend is scaffolded."
echo "- TODO T03: install frontend dependencies once frontend is scaffolded."

if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
  echo "Docker Compose config is valid."
else
  echo "Docker is not installed or not on PATH; skipping compose validation." >&2
fi
