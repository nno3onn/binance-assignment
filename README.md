# Binance Market Data Operations Console

Binance `BTCUSDT`, `ETHUSDT` 1분봉 데이터를 수집하고 수집 파이프라인 상태를 확인하는 운영 대시보드입니다.

가격 화면보다 `freshness`, `runtime status`, `gap`, `backfill/recovery`, `event log`를 중심에 둔 운영 콘솔로 구현했습니다. 배포는 과제 필수 요구사항이 아니므로 제출 범위에서 제외했습니다.

상세 설계는 [docs](docs)를 참고해 주세요.

## 주요 기능

- `BTCUSDT`, `ETHUSDT` 1분봉: 두 심볼을 기본 수집/조회 대상으로 사용합니다.
- Binance REST 초기 백필: 빈 DB에서 최근 `INITIAL_BACKFILL_HOURS` 구간을 백필합니다.
- Binance WebSocket 실시간 수집: kline message validation, DTO 변환, reconnect 구조를 제공합니다.
- Restart recovery: 재시작 후 탐지된 누락 구간만 REST로 복구합니다.
- Gap detection: expected 1분 interval 기준으로 missing candle 구간과 개수를 계산합니다.
- Idempotent upsert: `(symbol, interval, open_time)` unique key로 중복 candle row를 방지합니다.
- Runtime status: 심볼별 `INITIALIZING`, `LIVE`, `DEGRADED`, `BACKFILLING`, `STALE`, `ERROR` 상태를 관리합니다.
- FastAPI REST API: health, summary, symbols, candles, gaps, backfill jobs, events endpoint를 제공합니다.
- SSE: dashboard snapshot과 heartbeat를 `/api/dashboard/stream`으로 전송합니다.
- Next.js 운영 대시보드: freshness, pipeline status, gaps, backfill timeline, event log를 보여줍니다.

## 기술 스택

| 영역 | 기술 |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, uv |
| Frontend | Next.js App Router, TypeScript, Tailwind CSS, TanStack Query, Zustand, Recharts |
| Database | PostgreSQL |
| Testing | pytest, ruff, mypy, Vitest, ESLint, Prettier, Next.js build |
| Tooling | Make, shell scripts |

## 프로젝트 구조

```text
backend/   FastAPI, SQLAlchemy models, repository, Binance clients, services, tests
frontend/  Next.js dashboard, REST/SSE client, UI components, Vitest tests
docs/      설계, 대시보드, 백필/복구, 운영 문서
scripts/   check, smoke, recovery-drill scripts
```

## 설치 및 실행 방법

### 1. Clone 및 의존성 설치

```bash
git clone <REPOSITORY_URL>
cd binance-assignment
make bootstrap
```

### 2. Backend 환경변수 생성

FastAPI 직접 실행은 `backend/.env`를 읽습니다.

```bash
cd backend
cp .env.example .env
unset DATABASE_URL
```

`backend/.env` 핵심 값:

```bash
DATABASE_URL=postgresql://binance:binance@localhost:5432/binance_assignment
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. PostgreSQL 준비

로컬 PostgreSQL에 아래 DB 접속 정보가 준비되어 있어야 합니다.

```text
host=localhost
port=5432
database=binance_assignment
user=binance
password=binance
```

다른 계정이나 DB를 사용한다면 `backend/.env`의 `DATABASE_URL`만 수정합니다.

### 4. Migration 및 Backend 실행

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

확인:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/dashboard/summary
```

Swagger: `http://localhost:8000/docs`

### 5. Frontend 실행

새 터미널에서 실행합니다.

```bash
cd frontend
npm ci
npm run dev
```

Dashboard: `http://localhost:3000`

## 환경변수

핵심 변수만 정리했습니다. 전체 목록은 [.env.example](.env.example), [backend/.env.example](backend/.env.example)을 참고해 주세요.

| 변수명 | 예시 | 설명 |
|---|---|---|
| `DATABASE_URL` | `postgresql://binance:binance@localhost:5432/binance_assignment` | Backend DB 연결 URL |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | 허용할 frontend origin |
| `SYMBOLS` | `BTCUSDT,ETHUSDT` | 수집/조회 대상 심볼 |
| `CANDLE_INTERVAL` | `1m` | candle interval |
| `INITIAL_BACKFILL_HOURS` | `24` | 빈 DB 초기 백필 lookback 시간 |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Frontend REST API base URL |
| `NEXT_PUBLIC_SSE_URL` | `http://localhost:8000/api/dashboard/stream` | Frontend SSE endpoint |

## 테스트

```bash
make check
```

현재 검증 완료 항목:

| 항목 | 결과 |
|---|---|
| `make check` | 통과 |
| Backend tests | `76 passed` |
| Frontend tests | `17 passed` |
| Frontend build | 통과 |

## 주요 구현 내용

- 데이터 모델: `candles`, `symbol_runtime_status`, `backfill_jobs`, `application_events`
- Persistence: repository interface와 SQLAlchemy 구현체
- Backfill/Recovery: REST DTO를 domain model로 변환한 뒤 repository upsert 경로 사용
- Dashboard API: endpoint 내부에 비즈니스 로직을 두지 않고 service/repository 조합 사용
- Frontend realtime: REST 초기 조회 후 SSE snapshot으로 상태 갱신
