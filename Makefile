SHELL := /bin/bash

.PHONY: bootstrap up down logs lint typecheck test build check smoke reset-db recovery-drill

bootstrap:
	./scripts/bootstrap.sh

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

lint:
	./scripts/check.sh lint

typecheck:
	./scripts/check.sh typecheck

test:
	./scripts/test.sh

build:
	./scripts/check.sh build

check:
	./scripts/check.sh

smoke:
	./scripts/smoke.sh

reset-db:
	./scripts/reset-db.sh

recovery-drill:
	./scripts/recovery-drill.sh
