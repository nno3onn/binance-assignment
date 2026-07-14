# Binance Market Data Operations Console

Binance의 **BTCUSDT**, **ETHUSDT** 실시간 거래 데이터를 수집하고, 최초 실행 및 서버 재시작 시 누락된 데이터를 복구할 수 있는 **Market Data Operations Console**입니다.

본 프로젝트는 단순 시세 조회 화면이 아니라 **데이터 수집 파이프라인의 운영 상태를 모니터링하는 내부 운영 대시보드**를 목표로 구현했습니다.

> 배포는 과제 필수 요구사항이 아니므로 제출 범위에서 제외했으며, 로컬 환경에서 실행 및 검증했습니다.

---

# 주요 기능

## 실시간 데이터 수집

- Binance WebSocket을 이용한 BTCUSDT, ETHUSDT 실시간 1분봉 수집
- Binance REST API를 이용한 최초 데이터 백필(Initial Backfill)
- 서버 재시작 시 Gap Detection 기반 누락 데이터 복구(Restart Recovery)

## 데이터 저장

- `(symbol, interval, open_time)` Unique Key 기반 Idempotent Upsert
- Runtime Status 관리
- Backfill Job History 관리
- Event History 관리

## 운영 대시보드

수집 시스템의 상태를 한눈에 확인할 수 있도록 다음 정보를 제공합니다.

- System Health
- Runtime Status
- Data Freshness
- Symbol Pipeline Status
- Gap Detection
- Backfill Job History
- Event History

## Dashboard API

- REST API
- Server-Sent Events(SSE) 기반 실시간 업데이트

---

# 기술 스택

| 구분           | 기술                                         |
| -------------- | -------------------------------------------- |
| Backend        | Python 3.12, FastAPI, SQLAlchemy, Alembic    |
| Frontend       | Next.js(App Router), TypeScript, TailwindCSS |
| State          | TanStack Query, Zustand                      |
| Database       | PostgreSQL                                   |
| Data Streaming | Server-Sent Events (SSE)                     |
| Visualization  | Recharts                                     |
| Test           | pytest, mypy, ruff, Vitest, ESLint           |
| Tool           | uv, Make                                     |

---

# 프로젝트 구조

```text
backend/
├── app/              # FastAPI 애플리케이션
├── migrations/       # Alembic Migration
└── tests/

frontend/
├── app/              # Next.js App Router
├── components/
├── lib/
└── tests/

docs/                 # 설계 문서
scripts/              # 실행 및 검증 스크립트
```

---

# 설치 및 실행

## 1. 프로젝트 클론

```bash
git clone https://github.com/USERNAME/binance-assignment.git
cd binance-assignment
```

> 제출 전 본인의 GitHub Repository 주소로 변경하세요.

---

## 2. PostgreSQL 준비

로컬 PostgreSQL을 실행한 뒤 데이터베이스를 생성합니다.

예시

```text
Host : localhost
Port : 5432
Database : binance_assignment
User : binance
Password : binance
```

---

## 3. Backend 실행

```bash
cd backend

cp .env.example .env

uv sync

uv run alembic upgrade head

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

필요한 경우 `backend/.env`의 `DATABASE_URL`을 자신의 PostgreSQL 환경에 맞게 수정합니다.

Backend

```
http://localhost:8000
```

Swagger

```
http://localhost:8000/docs
```

Health Check

```
http://localhost:8000/api/health
```

Dashboard Summary

```
http://localhost:8000/api/dashboard/summary
```

---

## 4. Frontend 실행

새 터미널에서 실행합니다.

```bash
cd frontend

npm ci

npm run dev
```

Frontend

```
http://localhost:3000
```

---

# 환경변수

실행에 필요한 주요 환경변수입니다.

| 변수                     | 예시                                                           | 설명             |
| ------------------------ | -------------------------------------------------------------- | ---------------- |
| DATABASE_URL             | postgresql://binance:binance@localhost:5432/binance_assignment | PostgreSQL 연결  |
| CORS_ORIGINS             | http://localhost:3000,http://127.0.0.1:3000                    | 허용 Origin      |
| SYMBOLS                  | BTCUSDT,ETHUSDT                                                | 수집 대상 심볼   |
| CANDLE_INTERVAL          | 1m                                                             | 캔들 간격        |
| INITIAL_BACKFILL_HOURS   | 24                                                             | 최초 백필 시간   |
| NEXT_PUBLIC_API_BASE_URL | http://localhost:8000                                          | Backend REST API |
| NEXT_PUBLIC_SSE_URL      | http://localhost:8000/api/dashboard/stream                     | SSE Endpoint     |

그 외 환경변수는 아래 파일을 참고합니다.

```
.env.example
backend/.env.example
```

---

# API

| Method | Endpoint                     | 설명              |
| ------ | ---------------------------- | ----------------- |
| GET    | /api/health                  | Health Check      |
| GET    | /api/dashboard/summary       | Dashboard Summary |
| GET    | /api/dashboard/symbols       | Symbol Status     |
| GET    | /api/dashboard/candles       | Candle 조회       |
| GET    | /api/dashboard/gaps          | Gap 조회          |
| GET    | /api/dashboard/backfill-jobs | Backfill Job 조회 |
| GET    | /api/dashboard/events        | Event History     |
| GET    | /api/dashboard/stream        | SSE Stream        |

---

# 테스트

전체 테스트

```bash
make check
```

검증 결과

| 항목           | 결과      |
| -------------- | --------- |
| make check     | 통과      |
| Backend Tests  | 78 Passed |
| Frontend Tests | 17 Passed |
| Frontend Build | 성공      |

---

# 주요 구현 내용

### 실시간 데이터 수집

Binance WebSocket을 이용하여 BTCUSDT, ETHUSDT의 실시간 1분봉 데이터를 수집하도록 구현했습니다.

### Initial Backfill

애플리케이션 최초 실행 시 Binance REST API를 이용하여 최근 데이터를 백필하도록 구현했습니다.

### Restart Recovery

서버 재시작 시 Gap Detection으로 누락 구간을 탐지하고 필요한 구간만 REST API로 복구하도록 구현했습니다.

### Runtime Status

심볼별 상태(INITIALIZING, LIVE, BACKFILLING, STALE, ERROR)를 관리하여 운영 상태를 실시간으로 확인할 수 있도록 구현했습니다.

### 데이터 저장

`(symbol, interval, open_time)` Unique Key 기반 Upsert를 적용하여 중복 저장을 방지했습니다.

### 구조 설계

Repository Pattern을 적용하여 데이터 접근 계층과 비즈니스 로직을 분리했습니다.

### Dashboard

REST API로 초기 데이터를 조회하고, SSE를 통해 실시간 상태를 갱신하도록 구현했습니다.

---

# 제한 사항

- Docker Compose 기반 실행은 포함되어 있으나 제출 환경에서는 검증하지 않았습니다.
- 실제 Binance와 PostgreSQL을 연결한 장시간 통합 테스트는 수행하지 않았습니다.
- 1000개 이상의 Gap Pagination은 구현하지 않았습니다.
- Playwright 등 Browser E2E 테스트는 포함하지 않았습니다.

---

# 상세 문서

보다 자세한 설계 내용은 아래 문서를 참고해 주세요.

- `docs/02-architecture.md`
- `docs/04-backfill-and-recovery.md`
- `docs/06-dashboard-design.md`
- `docs/09-reviewer-walkthrough.md`
