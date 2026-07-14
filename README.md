# Binance Market Data Operations Console

Binance의 **BTCUSDT**, **ETHUSDT** 실시간 거래 데이터를 수집하고, 최초 실행 및 서버 재시작 시 누락 데이터를 복구할 수 있는 **Market Data Operations Console**입니다.

본 프로젝트는 단순 시세 조회 화면이 아닌, **데이터 수집 파이프라인의 운영 상태를 모니터링하는 내부 운영 대시보드**를 목표로 구현했습니다.

> 배포는 과제 필수 요구사항이 아니므로 제출 범위에서 제외했으며, 로컬 실행 기준으로 검증했습니다.

---

# 주요 기능

## 1. 실시간 데이터 수집

- Binance WebSocket을 이용한 BTCUSDT, ETHUSDT 실시간 수집
- Binance REST API 기반 최초 데이터 백필
- 서버 재시작 시 누락 구간(Gap) 자동 복구

## 2. 데이터 저장

- `(symbol, interval, open_time)` Unique Key 기반 Idempotent Upsert
- Runtime Status 관리
- Backfill Job History 관리
- Event History 관리

## 3. 운영 대시보드

운영자가 수집 시스템을 확인할 수 있도록 다음 정보를 제공합니다.

- System Health
- Runtime Status
- Data Freshness
- Symbol Pipeline Status
- Gap Detection
- Backfill Job
- Event History

## 4. Dashboard API

- REST API
- SSE(Server-Sent Events) 기반 실시간 업데이트

---

# 기술 스택

| 구분          | 기술                                         |
| ------------- | -------------------------------------------- |
| Backend       | Python 3.12, FastAPI, SQLAlchemy, Alembic    |
| Frontend      | Next.js(App Router), TypeScript, TailwindCSS |
| State         | TanStack Query, Zustand                      |
| Database      | PostgreSQL                                   |
| Visualization | Recharts                                     |
| Test          | pytest, mypy, ruff, Vitest, ESLint           |
| Tool          | uv, Make                                     |

---

# 프로젝트 구조

```text
backend/
 ├── app/
 ├── migrations/
 ├── tests/

frontend/
 ├── app/
 ├── components/
 ├── lib/
 ├── tests/

docs/
scripts/
```

---

# 설치 및 실행

## 1. 저장소 클론

```bash
git clone <REPOSITORY_URL>
cd binance-assignment
```

---

## 2. Backend 설정

```bash
cd backend

cp .env.example .env

uv sync

uv run alembic upgrade head

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

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

---

## 3. Frontend 실행

새 터미널에서

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

| 변수                     | 예시                                                           |
| ------------------------ | -------------------------------------------------------------- |
| DATABASE_URL             | postgresql://binance:binance@localhost:5432/binance_assignment |
| CORS_ORIGINS             | http://localhost:3000,http://127.0.0.1:3000                    |
| SYMBOLS                  | BTCUSDT,ETHUSDT                                                |
| CANDLE_INTERVAL          | 1m                                                             |
| INITIAL_BACKFILL_HOURS   | 24                                                             |
| NEXT_PUBLIC_API_BASE_URL | http://localhost:8000                                          |
| NEXT_PUBLIC_SSE_URL      | http://localhost:8000/api/dashboard/stream                     |

기타 환경변수는

```
.env.example
backend/.env.example
```

파일을 참고합니다.

---

# API

| Method | Endpoint                     | 설명              |
| ------ | ---------------------------- | ----------------- |
| GET    | /api/health                  | Health Check      |
| GET    | /api/dashboard/summary       | Dashboard Summary |
| GET    | /api/dashboard/symbols       | Symbol Status     |
| GET    | /api/dashboard/candles       | Candle 조회       |
| GET    | /api/dashboard/gaps          | Gap 조회          |
| GET    | /api/dashboard/backfill-jobs | Backfill 작업     |
| GET    | /api/dashboard/events        | Event History     |
| GET    | /api/dashboard/stream        | SSE Stream        |

---

# 테스트

전체 검증

```bash
make check
```

검증 결과

| 항목           | 결과      |
| -------------- | --------- |
| make check     | 통과      |
| Backend Test   | 76 Passed |
| Frontend Test  | 17 Passed |
| Frontend Build | 성공      |

---

# 주요 구현 내용

### 실시간 수집

- Binance WebSocket을 이용해 실시간 Candle 데이터를 수집하도록 구현했습니다.

### 최초 백필

- 최초 실행 시 Binance REST API를 이용하여 최근 데이터를 저장하도록 구현했습니다.

### 재시작 복구

- Gap Detection을 통해 누락된 구간만 탐지하고 REST API를 이용하여 복구하도록 구현했습니다.

### 데이터 저장

- `(symbol, interval, open_time)` Unique Key 기반 Upsert를 적용하여 중복 저장을 방지했습니다.

### 구조 설계

- Repository Pattern을 적용하여 데이터 접근과 비즈니스 로직을 분리했습니다.

### Dashboard

- REST API로 초기 데이터를 조회하고, SSE를 통해 실시간 상태를 갱신하도록 구현했습니다.

---

# 제한 사항

- Docker Compose 전체 실행은 검증하지 못했습니다.
- 실제 Binance와 PostgreSQL을 연결한 장시간 통합 테스트는 수행하지 않았습니다.
- 1000개 이상의 Gap Pagination은 구현하지 않았습니다.
- Browser E2E 테스트는 포함하지 않았습니다.

---

# 상세 문서

보다 자세한 설계 내용은 아래 문서를 참고해주세요.

- `docs/02-architecture.md`
- `docs/04-backfill-and-recovery.md`
- `docs/06-dashboard-design.md`
- `docs/09-reviewer-walkthrough.md`
