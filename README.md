# Binance Market Data Operations Console

Binance의 `BTCUSDT`, `ETHUSDT` 1분봉 데이터를 수집하고, 수집 파이프라인의 운영 상태를 확인하기 위한 Market Data Operations Console입니다.

이 과제는 단순 가격 조회 화면이 아니라 “데이터가 정상 수집되고 있는가, 지연되었는가, 누락 구간이 있는가, 복구 가능한가”를 확인하는 내부 운영 시스템으로 해석했습니다. 따라서 Dashboard의 중심은 가격 차트가 아니라 runtime status, freshness, gap, backfill, recovery, event log입니다.

배포는 과제 필수 요구사항이 아니므로 제출 범위에서 제외했습니다. 이 저장소는 GitHub Repository 제출과 로컬 실행 검증을 기준으로 정리되어 있습니다.

## 주요 기능

- `BTCUSDT`, `ETHUSDT` 1분봉 기준 데이터 모델
- Binance REST client와 초기 백필 서비스
- Binance WebSocket client와 실시간 collector 구조
- 재시작 후 누락 구간을 계산하는 gap detection service
- gap 구간만 REST로 복구하는 restart recovery service
- `(symbol, interval, open_time)` unique key 기반 idempotent candle upsert
- `INITIALIZING`, `LIVE`, `DEGRADED`, `BACKFILLING`, `STALE`, `ERROR` runtime status
- backfill job history와 application event history
- FastAPI read-only dashboard API
- SSE 기반 dashboard snapshot stream
- Next.js 운영 대시보드 UI
- smoke test와 recovery drill script

## 아키텍처

```mermaid
flowchart LR
  BWS["Binance WebSocket"] --> COL["Collector"]
  BREST["Binance REST API"] --> BF["Initial Backfill"]
  BREST --> REC["Restart Recovery"]
  COL --> ST["Runtime Status / Events"]
  COL --> DB[("PostgreSQL")]
  BF --> DB
  REC --> DB
  ST --> DB
  DB --> API["FastAPI REST API"]
  API --> SSE["SSE Stream"]
  API --> UI["Next.js Operations Dashboard"]
  SSE --> UI
```

주요 흐름:

1. 초기 백필은 빈 DB에서 최근 `INITIAL_BACKFILL_HOURS` 구간을 Binance REST로 조회해 `source=rest_backfill`로 저장합니다.
2. WebSocket collector는 Binance kline message를 validation하고 내부 DTO로 변환합니다.
3. runtime status는 심볼별 freshness, last event time, lag를 추적합니다.
4. gap detection은 expected 1분 interval과 저장된 candle sequence를 비교합니다.
5. restart recovery는 탐지된 gap만 REST로 복구하고 idempotent upsert로 중복을 방지합니다.
6. Dashboard API와 SSE stream은 운영 콘솔에 필요한 summary, symbol status, gaps, jobs, events를 제공합니다.

## 개발 환경

| 영역 | 기술 |
|---|---|
| Backend | Python `>=3.12,<3.13`, FastAPI, SQLAlchemy, Alembic, PostgreSQL, uv |
| Backend 검증 | pytest, ruff, mypy |
| Frontend | Node.js `>=18.12.0`, npm `>=8.19.0`, Next.js App Router, TypeScript, Tailwind CSS |
| Frontend 검증 | ESLint, Prettier, Vitest, Next.js production build |
| 데이터 연동 | REST, SSE, TanStack Query, browser EventSource |
| 시각화 | Recharts |
| 선택 실행 환경 | Docker / Docker Compose |

필수 도구:

- Git
- Make
- Python 3.12
- uv
- Node.js `>=18.12.0`
- npm `>=8.19.0`
- PostgreSQL

Docker 없이도 로컬 실행이 가능합니다.

## 설치 방법

```bash
git clone <REPOSITORY_URL>
cd binance-assignment
make bootstrap
```

`<REPOSITORY_URL>`은 제출한 GitHub Repository URL로 교체합니다.

## 로컬 실행 방법

로컬 실행은 PostgreSQL, Backend, Frontend 순서로 진행합니다.

### 1. PostgreSQL 준비

Docker 없이 실행하는 경우 로컬 PostgreSQL에 아래 database/user가 준비되어 있어야 합니다.

```text
database: binance_assignment
user: binance
password: binance
host: localhost
port: 5432
```

예시:

```bash
createdb binance_assignment
```

이미 다른 계정이나 DB를 사용한다면 `backend/.env`의 `DATABASE_URL`만 해당 값으로 바꾸면 됩니다.

### 2. Backend 실행

FastAPI 직접 실행 시 설정 파일은 루트 `.env`가 아니라 `backend/.env`입니다.

```bash
cd backend
cp .env.example .env
```

`backend/.env`에서 로컬 직접 실행용 DB URL을 확인합니다.

```bash
DATABASE_URL=postgresql://binance:binance@localhost:5432/binance_assignment
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

실제 OS 환경변수 `DATABASE_URL`이 설정되어 있으면 `backend/.env`보다 우선합니다. 이전에 Docker Compose용 값을 export했다면 먼저 해제합니다.

```bash
unset DATABASE_URL
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

확인:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/dashboard/summary
```

Swagger / OpenAPI:

```text
http://localhost:8000/docs
```

### 3. Frontend 실행

새 터미널에서 실행합니다.

```bash
cd frontend
npm ci
npm run dev
```

접속:

```text
http://localhost:3000
```

Frontend가 호출하는 기본 Backend URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SSE_URL=http://localhost:8000/api/dashboard/stream
```

### Docker Compose 실행

Docker Compose 실행 파일은 포함되어 있지만, 현재 작업 환경에는 Docker CLI가 없어 전체 build/up은 검증하지 못했습니다.

Docker Compose 내부 backend 컨테이너는 `docker-compose.yml`에서 아래 DB URL을 사용하도록 override됩니다.

```bash
DATABASE_URL=postgresql+psycopg://binance:binance@postgres:5432/binance_assignment
```

Docker 사용 가능 환경에서의 실행 명령:

```bash
cp .env.example .env
make up
```

주의: Docker Compose end-to-end 실행은 미검증 상태입니다. 검증된 기본 경로는 로컬 PostgreSQL + Backend 직접 실행 + Frontend 직접 실행입니다.

## 환경변수

환경별 설정 위치:

| 실행 환경 | 설정 위치 | DB host |
|---|---|---|
| 로컬 Backend 직접 실행 | `backend/.env` | `localhost:5432` |
| Docker Compose | 루트 `.env` 또는 `.env.example` + `docker-compose.yml` override | `postgres:5432` |
| Railway 등 외부 배포 | 제출 범위 제외. 사용 시 플랫폼 환경변수 | 플랫폼 제공 값 |

Backend 주요 환경변수:

| 변수명 | 기본값 또는 예시 | 설명 |
|---|---|---|
| `APP_ENV` | `local` | 실행 환경 표시 |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | 허용할 frontend origin 목록 |
| `DATABASE_URL` | `postgresql://binance:binance@localhost:5432/binance_assignment` | 로컬 직접 실행용 DB URL |
| `SYMBOLS` | `BTCUSDT,ETHUSDT` | 수집/대시보드 대상 심볼 |
| `CANDLE_INTERVAL` | `1m` | candle interval |
| `INITIAL_BACKFILL_HOURS` | `24` | 빈 DB 최초 백필 lookback 시간 |
| `BINANCE_REST_BASE_URL` | `https://api.binance.com` | Binance REST base URL |
| `BINANCE_REST_TIMEOUT_SECONDS` | `10` | REST timeout |
| `BINANCE_REST_RETRY_COUNT` | `3` | REST retry count |
| `BINANCE_WS_BASE_URL` | `wss://stream.binance.com:9443` | Binance WebSocket base URL |
| `BINANCE_WS_KEEPALIVE_SECONDS` | `30` | WebSocket keepalive 주기 |
| `BINANCE_WS_RETRY_COUNT` | `3` | WebSocket reconnect retry count |
| `DASHBOARD_SSE_INTERVAL_SECONDS` | `5` | SSE snapshot 주기 |
| `DASHBOARD_SSE_HEARTBEAT_SECONDS` | `15` | SSE heartbeat 주기 |

Frontend 주요 환경변수:

| 변수명 | 기본값 또는 예시 | 설명 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend REST API base URL |
| `NEXT_PUBLIC_SSE_URL` | `http://localhost:8000/api/dashboard/stream` | Backend SSE endpoint |

루트 `.env.example`은 Docker Compose와 script 실행 예시를 위한 파일입니다. 로컬 FastAPI 직접 실행에서는 `backend/.env.example`을 복사해 `backend/.env`로 사용합니다.

## 테스트 및 검증

전체 검증:

```bash
make check
```

개별 검증:

```bash
make lint
make typecheck
make test
make build
```

현재 검증 완료 항목:

| 항목 | 결과 |
|---|---|
| `make check` | 통과 |
| Backend tests | `76 passed` |
| Frontend tests | `17 passed` |
| Frontend build | 통과 |

Smoke test:

```bash
make smoke
```

`make smoke`는 실행 중인 backend/frontend와 최소 candle 데이터가 필요합니다.

Recovery drill:

```bash
make recovery-drill
```

`make recovery-drill`은 실행 중인 backend/frontend/PostgreSQL, 최근 candle 데이터, DB 접근, recovery trigger 설정이 필요합니다. 현재 환경에서는 성공 경로를 검증하지 않았습니다.

## Known Limitations

| 제한 사항 | 현재 상태 |
|---|---|
| 배포 | 과제 필수 요구사항이 아니므로 제출 범위에서 제외했습니다. README에는 실제 동작을 보장하지 않는 배포 URL을 포함하지 않습니다. |
| Docker Compose end-to-end | Docker CLI가 없는 환경이라 `docker compose config`, `make up`, `make smoke`까지의 전체 Docker 경로는 검증하지 못했습니다. |
| worker 자동 오케스트레이션 | collector/backfill/recovery service code는 있으나 Compose 부팅 시 별도 worker supervisor가 자동 실행되도록 묶여 있지는 않습니다. |
| live Binance + PostgreSQL 통합 검증 | 단위/계약 테스트는 mock/SQLite 중심입니다. 실제 Binance와 PostgreSQL을 연결한 장시간 end-to-end 검증은 별도 환경이 필요합니다. |
| 대형 gap pagination | recovery는 현재 단일 REST limit 범위 중심입니다. 1000개 초과 gap은 page 분할 전략이 필요합니다. |
| 브라우저 E2E | Vitest와 Next.js build는 통과했지만 Playwright 같은 browser-level E2E는 없습니다. |
| 다중 인스턴스 운영 | 단일 API/DB 중심 설계입니다. 운영 확장 시 worker 분리, leader election, broker 등을 검토해야 합니다. |

## GitHub 제출 체크리스트

- [ ] GitHub Repository가 Public인지 확인
- [ ] 최신 변경사항이 모두 commit/push 되었는지 확인
- [ ] `README.md`가 로컬 실행 기준으로 최신인지 확인
- [ ] `backend/.env` 같은 실제 비밀/로컬 설정 파일이 commit되지 않았는지 확인
- [ ] `make check`가 로컬에서 통과하는지 확인
- [ ] Backend 직접 실행 후 `http://localhost:8000/api/health`가 200인지 확인
- [ ] Backend 직접 실행 후 `http://localhost:8000/api/dashboard/summary`가 빈 DB에서도 200인지 확인
- [ ] Frontend 실행 후 `http://localhost:3000`에서 Dashboard가 열리는지 확인
- [ ] 제출 링크가 GitHub Repository URL인지 확인

