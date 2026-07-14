# Binance Market Data Operations Console

Binance의 `BTCUSDT`, `ETHUSDT` 1분봉 데이터를 수집하고, 수집 파이프라인의 상태를 운영자가 확인할 수 있도록 만든 Market Data Operations Console입니다.

이 과제는 단순한 코인 시세 조회 화면이 아니라, “데이터가 정상적으로 수집되고 있는가, 지연되었는가, 누락 구간이 있는가, 복구 가능한가”를 확인하는 운영 시스템으로 해석했습니다. 따라서 Dashboard의 중심도 가격 차트가 아니라 runtime status, freshness, gap, backfill, recovery, event log입니다.

## 핵심 기능

- `BTCUSDT`, `ETHUSDT` 1분봉 수집 구조  
  시스템 전반은 두 심볼과 `1m` interval을 기본 대상으로 설계되어 있습니다. 저장소, gap detection, dashboard API, dashboard UI 모두 심볼별 상태를 독립적으로 표현합니다.

- Binance WebSocket 실시간 수집  
  `backend/app/binance/websocket.py`에 Binance kline WebSocket client와 collector가 구현되어 있습니다. message validation, ping/pong keepalive, graceful shutdown, reconnect backoff, DTO 변환을 담당합니다. 단, 현재 Docker Compose 부팅 시 collector worker가 자동 실행되도록 연결되어 있지는 않습니다.

- Binance REST API 초기 백필  
  `InitialBackfillService`는 심볼에 저장된 candle이 없을 때 `INITIAL_BACKFILL_HOURS` 기간만큼 REST kline을 조회하고 `source=rest_backfill`로 저장합니다. 기본 lookback은 24시간입니다.

- 재시작 후 누락 구간 탐지 및 복구  
  `GapDetectionService`가 저장된 candle sequence와 expected 1분 interval을 비교해 누락 구간을 계산하고, `RestartRecoveryService`가 해당 gap만 REST로 복구합니다.

- idempotent upsert와 중복 방지  
  `candles`는 `(symbol, interval, open_time)` unique key를 사용합니다. Repository는 동일 candle이 반복 저장되어도 row를 중복 생성하지 않고 기존 row를 갱신합니다.

- 심볼별 runtime status  
  `INITIALIZING`, `LIVE`, `DEGRADED`, `BACKFILLING`, `STALE`, `ERROR` 상태를 저장하고 dashboard API/UI에서 심볼별로 보여줍니다.

- data freshness  
  runtime status의 `last_event_at`, `last_candle_open_time`, `lag_seconds`를 기반으로 각 심볼의 최신성 및 지연 상태를 표시합니다.

- gap detection  
  비어 있는 1분봉 구간의 시작/종료 시각과 missing candle count를 계산합니다. 운영자는 현재 복구가 필요한 구간을 Dashboard에서 확인할 수 있습니다.

- backfill job history  
  초기 백필과 재시작 복구 백필은 `backfill_jobs`에 기록됩니다. job type, status, target range, inserted/updated count, started/finished time을 보관합니다.

- application event history  
  WebSocket 연결/해제/재연결, invalid message, initial backfill, recovery 시작/완료/실패 같은 운영 이벤트를 append-only 형태로 기록합니다.

- REST dashboard API  
  FastAPI가 health, summary, symbols, candles, gaps, backfill jobs, events를 read-only endpoint로 제공합니다.

- SSE 실시간 dashboard snapshot  
  `/api/dashboard/stream`은 `dashboard_snapshot`, `heartbeat`, `error` event를 SSE로 전송합니다. Frontend는 REST로 초기 hydration을 한 뒤 SSE snapshot으로 summary/status를 갱신합니다.

- 운영 대시보드  
  Next.js Dashboard는 System Health, Data Freshness, Symbol Pipeline Status, Gap Detector, Backfill Timeline, Event Log, Source Mix를 우선 배치합니다.

- smoke test  
  `scripts/smoke.sh`는 실행 중인 backend/frontend를 대상으로 health, API, candles, SSE, frontend page를 검증합니다.

- recovery drill  
  `scripts/recovery-drill.sh`는 DB에 실제 gap을 주입하고, gap detection, recovery trigger, missing count 0, LIVE 복귀, duplicate 0을 검증하도록 작성되어 있습니다. recovery trigger는 현재 외부 URL 또는 command로 명시해야 합니다.

## 시스템 아키텍처

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

초기 백필 흐름:

1. 심볼별 저장된 candle 존재 여부를 확인합니다.
2. 비어 있으면 `INITIAL_BACKFILL_HOURS` 기준으로 Binance REST kline을 조회합니다.
3. REST DTO를 domain candle로 변환합니다.
4. Repository의 idempotent upsert 경로로 `source=rest_backfill` 저장합니다.
5. backfill job과 application event를 기록합니다.

실시간 수집 흐름:

1. Binance WebSocket kline stream을 구독합니다.
2. 수신 message를 validation하고 내부 DTO로 변환합니다.
3. runtime status/freshness를 갱신할 수 있도록 collector hook을 제공합니다.
4. candle 저장 경로는 idempotent persistence를 전제로 설계되어 있습니다.

재시작 복구 흐름:

1. 저장된 candle sequence와 expected 1분 interval을 비교합니다.
2. 누락된 open time 구간을 gap으로 계산합니다.
3. gap 구간만 Binance REST로 조회합니다.
4. `source=rest_backfill`로 bulk upsert합니다.
5. gap missing count가 0이 되고 심볼 상태가 LIVE로 돌아오는지 검증합니다.

## 기술 스택 및 개발 환경

설정 파일 기준입니다. 명시되지 않은 버전은 추측하지 않았습니다.

| 영역 | 기술 |
|---|---|
| Backend language | Python `>=3.12,<3.13` |
| Backend framework | FastAPI `>=0.116.0,<0.117.0` |
| ASGI server | `uvicorn[standard] >=0.35.0,<0.36.0` |
| DB ORM | SQLAlchemy `>=2.0.0,<3.0.0` |
| Migration | Alembic `>=1.16.0,<2.0.0` |
| PostgreSQL driver | `psycopg[binary] >=3.2.0,<4.0.0` |
| HTTP client | httpx `>=0.28.0,<0.29.0` |
| WebSocket client | websockets `>=15.0.0,<16.0.0` |
| Backend package manager | uv |
| Backend test/lint/type | pytest `>=8.4.0,<9.0.0`, ruff `>=0.12.0,<0.13.0`, mypy `>=1.16.0,<2.0.0` |
| Frontend runtime | Node.js `>=18.12.0`, npm `>=8.19.0` |
| Frontend framework | Next.js `13.5.11`, React `18.2.0` |
| Frontend language | TypeScript `5.8.3` |
| Styling | Tailwind CSS `3.4.17` |
| Data sync | TanStack Query `5.90.11` |
| State | Zustand `5.0.9` |
| Chart | Recharts `2.15.4` |
| Frontend test | Vitest `3.2.4` |
| Frontend lint/format | ESLint `8.57.1`, Prettier `3.6.2` |
| Container | Docker / Docker Compose |
| Command runner | Make |

## 사전 준비 사항

Docker 방식:

- Git
- Docker / Docker Compose
- Make

로컬 직접 실행 방식:

- Git
- Make
- Python 3.12
- uv
- Node.js `>=18.12.0`
- npm `>=8.19.0`
- PostgreSQL
- curl, python3

`jq`는 smoke test에 필요하지 않습니다.

## 설치 및 실행 방법

처음 clone한 리뷰어 기준 명령입니다. `<REPOSITORY_URL>`은 실제 제출 GitHub URL로 교체해야 합니다.

```bash
git clone <REPOSITORY_URL>
cd binance-assignment
cp .env.example .env
make bootstrap
make up
```

서비스 접속 URL:

| 항목 | URL |
|---|---|
| Dashboard | `http://localhost:3000` |
| Backend API base | `http://localhost:8000` |
| Swagger / OpenAPI | `http://localhost:8000/docs` |
| Health | `http://localhost:8000/api/health` |

로그 확인:

```bash
make logs
```

종료:

```bash
make down
```

주의: 현재 작업 환경에서는 Docker CLI가 없어 `docker compose config`, `make up`의 실제 build/up은 검증하지 못했습니다. `docker-compose.yml`은 PostgreSQL, FastAPI, Next.js를 실행하도록 정리되어 있지만, collector/backfill/recovery worker 자동 오케스트레이션은 아직 포함되어 있지 않습니다.

## 로컬 개발 실행 방법

Docker를 사용하지 않는 경우 PostgreSQL을 별도로 실행하고, `DATABASE_URL`을 backend가 접근 가능한 값으로 설정해야 합니다.

Backend:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Frontend production build/start:

```bash
cd frontend
npm run build
npm run start
```

## 환경변수

`.env.example`에 있는 값입니다. 별도 API key나 secret은 필요하지 않습니다. `POSTGRES_PASSWORD`는 로컬 개발용 예시값이므로 운영 환경에서는 교체해야 합니다.

### Application

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `APP_ENV` | `local` | 예 | 애플리케이션 실행 환경 표시 |
| `LOG_LEVEL` | `info` | 아니오 | 로그 레벨 |
| `TZ` | `UTC` | 예 | 컨테이너/프로세스 시간대 기준 |

### Binance REST

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `BINANCE_REST_BASE_URL` | `https://api.binance.com` | 예 | Binance REST API base URL |
| `BINANCE_REST_TIMEOUT_SECONDS` | `10` | 예 | REST 요청 timeout |
| `BINANCE_REST_RETRY_COUNT` | `3` | 예 | REST retry 횟수 |

### Binance WebSocket

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `BINANCE_WS_BASE_URL` | `wss://stream.binance.com:9443` | 예 | Binance WebSocket base URL |
| `BINANCE_WS_KEEPALIVE_SECONDS` | `30` | 예 | WebSocket keepalive 주기 |
| `BINANCE_WS_RETRY_COUNT` | `3` | 예 | WebSocket reconnect retry 횟수 |
| `SYMBOLS` | `BTCUSDT,ETHUSDT` | 예 | 수집/대시보드 대상 심볼 |
| `CANDLE_INTERVAL` | `1m` | 예 | candle interval |

### Initial backfill

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `INITIAL_BACKFILL_HOURS` | `24` | 예 | 빈 DB 최초 백필 lookback 시간 |

### Backend

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `BACKEND_HOST` | `0.0.0.0` | 아니오 | backend bind host 예시 |
| `BACKEND_PORT` | `8000` | 예 | backend port |
| `API_BASE_URL` | `http://localhost:8000` | 아니오 | script/API base URL 기본값 |

### Frontend API URL 및 SSE

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `FRONTEND_PORT` | `3000` | 예 | frontend port |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | 예 | frontend REST API base URL |
| `NEXT_PUBLIC_SSE_URL` | `http://localhost:8000/api/dashboard/stream` | 예 | frontend SSE endpoint |
| `DASHBOARD_SSE_INTERVAL_SECONDS` | `5` | 예 | backend SSE snapshot 전송 주기 |
| `DASHBOARD_SSE_HEARTBEAT_SECONDS` | `15` | 예 | backend SSE heartbeat 주기 |

### Database

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `POSTGRES_USER` | `binance` | 예 | PostgreSQL user |
| `POSTGRES_PASSWORD` | `binance` | 예 | PostgreSQL password 예시값 |
| `POSTGRES_DB` | `binance_assignment` | 예 | PostgreSQL database |
| `POSTGRES_HOST` | `postgres` | 예 | compose 내부 DB host |
| `POSTGRES_PORT` | `5432` | 예 | PostgreSQL port |
| `DATABASE_URL` | `postgresql://binance:binance@postgres:5432/binance_assignment` | 예 | DB 접속 URL |

### Smoke test

아래 값은 `.env.example`에는 없고 `scripts/smoke.sh`에서 override로 지원합니다.

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `SMOKE_API_BASE_URL` | `http://localhost:8000` | 아니오 | smoke test 대상 backend URL |
| `SMOKE_FRONTEND_URL` | `http://localhost:3000` | 아니오 | smoke test 대상 frontend URL |
| `SMOKE_RETRIES` | `20` | 아니오 | 서비스 준비 retry 횟수 |
| `SMOKE_RETRY_DELAY_SECONDS` | `2` | 아니오 | retry 간격 |
| `SMOKE_CURL_TIMEOUT_SECONDS` | `5` | 아니오 | curl timeout |

### Recovery drill

아래 값은 `.env.example`에는 없고 `scripts/recovery-drill.sh`에서 override로 지원합니다.

| 변수명 | 기본값 또는 예시 | 필수 | 용도 |
|---|---|---:|---|
| `BACKEND_URL` | `http://localhost:8000` | 아니오 | recovery drill 대상 backend URL |
| `FRONTEND_URL` | `http://localhost:3000` | 아니오 | recovery drill 대상 frontend URL |
| `DRILL_SYMBOL` | `BTCUSDT` | 아니오 | gap을 주입할 심볼 |
| `DRILL_INTERVAL` | `1m` | 아니오 | drill interval |
| `DRILL_GAP_SECONDS` | `70` | 아니오 | 삭제할 gap 길이 기준 |
| `DRILL_TIMEOUT_SECONDS` | `180` | 아니오 | polling timeout |
| `DRILL_RETRY_DELAY_SECONDS` | `5` | 아니오 | polling 간격 |
| `DRILL_RECOVERY_TRIGGER_URL` | 빈 값 | 조건부 | recovery를 HTTP로 트리거할 URL |
| `DRILL_RECOVERY_TRIGGER_METHOD` | `POST` | 아니오 | recovery trigger HTTP method |
| `DRILL_RECOVERY_COMMAND` | 빈 값 | 조건부 | recovery를 실행할 shell command |
| `DRILL_COLLECTOR_PAUSE_URL` | 빈 값 | 아니오 | 선택적 collector pause control URL |
| `DRILL_COLLECTOR_RESUME_URL` | 빈 값 | 아니오 | 선택적 collector resume control URL |

`DRILL_RECOVERY_TRIGGER_URL` 또는 `DRILL_RECOVERY_COMMAND` 중 하나가 없으면 recovery drill은 성공하지 않습니다.

## Dashboard 구성

| 영역 | 설명 | 선택 이유 |
|---|---|---|
| System Health Summary | 전체 상태, BTCUSDT/ETHUSDT 상태, API/DB 상태, SSE 상태를 카드로 표시 | 운영자가 장애 여부를 가장 먼저 판단해야 하기 때문 |
| Data Freshness | 심볼별 last event time, lag, freshness를 표시 | WebSocket이 연결되어 있어도 데이터가 stale일 수 있기 때문 |
| Symbol Pipeline Status | symbol, status, latest price, last event, freshness, connection state를 표로 표시 | 두 심볼 중 하나만 실패하는 상황을 빠르게 분리하기 위함 |
| Gap Detector | gap start/end와 missing candle count를 표시 | 재시작 복구가 필요한 구간을 직접 보여주기 위함 |
| Backfill Job Timeline | initial/restart recovery job, status, target range, recovered count를 표시 | 최초 백필과 복구 백필이 실제로 수행되었는지 증명하기 위함 |
| Recent Candle Chart | 최근 candle close price를 보조 차트로 표시 | 수집 대상이 실제 market data임을 확인하되, 가격판처럼 보이지 않게 보조 영역으로 둠 |
| Recent Event Log | occurred_at, severity, event type, message를 표시 | 연결/백필/복구 이벤트의 원인을 운영자가 추적하기 위함 |
| Source Mix | `websocket`과 `rest_backfill` 비율을 표시 | 실시간 수집과 복구 데이터의 lineage를 확인하기 위함 |

## API 및 SSE

실제 구현된 FastAPI endpoint입니다.

| Method | Path | 설명 | 주요 query parameter |
|---|---|---|---|
| `GET` | `/api/health` | API 상태와 설정된 symbol/interval 확인 | 없음 |
| `GET` | `/api/dashboard/summary` | 전체 dashboard summary 조회 | 없음 |
| `GET` | `/api/dashboard/symbols` | 심볼별 runtime status 조회 | 없음 |
| `GET` | `/api/dashboard/candles` | 특정 심볼의 최근 또는 기간 candle 조회 | `symbol` 필수, `interval=1m`, `limit=1..500`, `start`, `end` |
| `GET` | `/api/dashboard/gaps` | 현재 gap 목록과 missing count 조회 | `symbol` 선택, `interval=1m`, `start`, `end` |
| `GET` | `/api/dashboard/backfill-jobs` | 최근 backfill job 조회 | `limit=1..500` |
| `GET` | `/api/dashboard/events` | 최근 application event 조회 | `limit=1..500` |
| `GET` | `/api/dashboard/stream` | dashboard SSE stream | 없음 |

SSE event type:

| Event | 설명 |
|---|---|
| `dashboard_snapshot` | system health, 심볼 상태, active gap count, latest backfill status를 전송 |
| `heartbeat` | 데이터 변화가 없어도 연결 생존 여부를 전송 |
| `error` | snapshot 생성 실패 등 stream 내부 오류를 의미 있는 event로 전송 |

Frontend는 browser 기본 `EventSource` reconnect를 사용하며, 별도 broker나 Redis/Kafka는 사용하지 않습니다.

## 데이터 저장 및 중복 방지

- `candles`  
  `symbol`, `interval`, `open_time` unique constraint를 사용합니다. `source`는 `websocket`, `rest_backfill`만 허용합니다.

- UTC timestamp  
  repository는 candle, runtime status, backfill job, application event datetime을 UTC로 정규화합니다.

- upsert 방식  
  Repository의 `upsert_candle`, `bulk_upsert_candles`는 기존 candle이 있으면 가격/거래량/source를 갱신하고, 없으면 새 row를 생성합니다.

- `symbol_runtime_status`  
  심볼별 현재 상태, latest event/candle time, lag, error message를 저장합니다.

- `backfill_jobs`  
  `initial`, `restart_recovery` job type과 `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED` status를 저장합니다.

- `application_events`  
  운영 dashboard event log를 위한 append-only event history입니다. severity는 `INFO`, `WARNING`, `ERROR`로 제한됩니다.

## 백필 및 장애 복구

빈 DB 최초 실행:

1. 심볼별 latest candle을 확인합니다.
2. 저장된 candle이 없으면 initial backfill 대상입니다.
3. `INITIAL_BACKFILL_HOURS=24` 기본값 기준으로 최근 24시간을 REST 조회합니다.
4. 조회 결과를 `source=rest_backfill`로 저장합니다.

WebSocket 실시간 수집:

1. Binance kline stream message를 수신합니다.
2. 잘못된 message는 무시하고 event로 기록할 수 있습니다.
3. 정상 kline은 내부 DTO로 변환됩니다.
4. runtime status/freshness가 갱신될 수 있도록 collector hook을 제공합니다.

재시작 후 gap detection:

1. 저장된 candle open time 목록을 조회합니다.
2. expected 1분 open time 목록과 비교합니다.
3. 누락된 연속 구간을 gap으로 묶습니다.
4. missing candle count를 계산합니다.

REST recovery backfill:

1. gap detection 결과만 복구 대상으로 사용합니다.
2. Binance REST kline을 gap range 기준으로 조회합니다.
3. 실제 missing open time에 해당하는 candle만 저장합니다.
4. idempotent upsert로 중복 row를 방지합니다.
5. 복구 완료 후 missing count 0, LIVE 복귀, recovery event/job 기록을 확인할 수 있습니다.

제한 사항: 현재 recovery는 단일 REST 요청 limit 범위 중심으로 구현되어 있으며, 1000개 초과 대형 gap pagination 전략은 Known Limitations로 남아 있습니다.

## 테스트 및 검증 방법

Makefile 기준 명령입니다.

| 명령 | 검증 내용 |
|---|---|
| `make lint` | backend ruff, frontend ESLint/Prettier |
| `make typecheck` | backend mypy, frontend TypeScript |
| `make test` | backend pytest, frontend Vitest를 포함한 전체 test script |
| `make build` | frontend Next.js production build |
| `make check` | lint, typecheck, backend/frontend tests, frontend build 전체 |
| `make smoke` | 실행 중인 backend/frontend API, candles, SSE, page 확인 |
| `make recovery-drill` | 실행 중인 시스템에 gap을 주입하고 recovery 결과 검증 |

현재 확인된 검증 결과:

- Backend: `67 passed`
- Frontend: `17 passed`
- Frontend build 통과
- `make check` 통과

구분해서 볼 점:

- Docker Compose end-to-end build/up은 현재 작업 환경에 Docker CLI가 없어 검증하지 못했습니다.
- `make recovery-drill` 성공 경로는 실행 중인 서비스, DB 접근, recovery trigger가 필요하므로 현재 환경에서 성공 검증하지 못했습니다.

## Smoke Test

전제 조건:

- backend가 `SMOKE_API_BASE_URL`에서 응답해야 합니다.
- frontend가 `SMOKE_FRONTEND_URL`에서 응답해야 합니다.
- `BTCUSDT`, `ETHUSDT` 각각 최소 1개 이상의 candle이 저장되어 있어야 합니다.
- `curl`, `python3`가 필요합니다.

실행:

```bash
make smoke
```

override 예시:

```bash
SMOKE_API_BASE_URL=http://localhost:8000 \
SMOKE_FRONTEND_URL=http://localhost:3000 \
SMOKE_RETRIES=20 \
make smoke
```

검증 항목:

- `/api/health` 성공
- `/api/dashboard/summary` JSON 정상
- `/api/dashboard/symbols`에 `BTCUSDT`, `ETHUSDT` 존재
- `/api/dashboard/candles`에 심볼별 candle 1개 이상 존재
- `/api/dashboard/events` JSON 정상
- `/api/dashboard/stream`이 `text/event-stream` 반환
- frontend page가 `Market Data Operations Console` 포함

출력 방식:

- 성공: `[PASS]`
- 실패: `[FAIL]` 후 non-zero exit
- 선택적/환경 제약: `[SKIP]`

## Recovery Drill

전제 조건:

- backend, frontend, PostgreSQL이 실행 중이어야 합니다.
- 최근 candle 데이터가 있어야 합니다.
- host `psql` + `DATABASE_URL` 또는 Docker Compose `postgres` DB 접근이 필요합니다.
- recovery 실행을 위해 `DRILL_RECOVERY_TRIGGER_URL` 또는 `DRILL_RECOVERY_COMMAND`가 필요합니다.

실행 예시:

```bash
DATABASE_URL=postgresql://binance:binance@localhost:5432/binance_assignment \
DRILL_SYMBOL=BTCUSDT \
DRILL_GAP_SECONDS=70 \
DRILL_RECOVERY_COMMAND='<project-specific recovery command>' \
make recovery-drill
```

동작:

1. backend, frontend, SSE, DB readiness를 확인합니다.
2. 시작 시점의 latest candle, row count, duplicate count를 기록합니다.
3. `DRILL_SYMBOL`의 최근 candle 일부를 삭제해 실제 gap을 만듭니다.
4. `/api/dashboard/gaps`가 missing candle count를 보고하는지 확인합니다.
5. 설정된 recovery trigger를 실행합니다.
6. `restart_recovery` backfill job이 기록되고 완료되는지 확인합니다.
7. missing count가 0인지 확인합니다.
8. 심볼 상태가 `LIVE`로 복귀했는지 확인합니다.
9. recovery event가 기록되었는지 확인합니다.
10. `(symbol, interval, open_time)` duplicate row가 0인지 확인합니다.

recovery trigger가 없으면 drill은 성공하지 않고 `[FAIL]`로 종료합니다.

## 프로젝트 구조

```text
.
├── backend/
│   ├── app/api/                  # FastAPI dashboard REST/SSE
│   ├── app/binance/              # Binance REST/WebSocket client
│   ├── app/domain/               # domain enum/input
│   ├── app/models/               # SQLAlchemy ORM
│   ├── app/repositories/         # persistence interface/implementation
│   ├── app/services/             # backfill, recovery, gaps, status, events
│   ├── migrations/               # Alembic migrations
│   ├── tests/                    # backend tests
│   └── pyproject.toml
├── frontend/
│   ├── app/                      # Next.js App Router
│   ├── components/               # dashboard UI
│   ├── lib/                      # API/SSE/realtime/view model
│   ├── tests/                    # Vitest tests
│   └── package.json
├── docs/                         # 설계/운영/리뷰 문서
├── scripts/                      # check, smoke, recovery-drill
├── docker-compose.yml
├── Makefile
└── README.md
```

## 주요 설계 결정

- WebSocket 실시간 수집 + REST 복구 분리  
  실시간 stream은 최신성 확보에 유리하고, REST는 누락 구간을 재조회하는 데 적합합니다. 두 source를 분리해 장애 복구를 명확하게 만들었습니다.

- 1분봉 선택  
  과제 요구 범위에서 운영 상태, gap detection, recovery를 검증하기에 충분히 촘촘하면서도 구현 복잡도를 통제할 수 있는 단위입니다.

- SSE 선택  
  Dashboard는 서버에서 상태 snapshot을 단방향으로 받으면 충분합니다. WebSocket server나 broker 없이도 browser `EventSource`로 실시간성을 구현할 수 있어 범위 대비 운영성이 좋습니다.

- monorepo 및 단일 FastAPI 애플리케이션 구조  
  backend, frontend, docs, scripts를 한 저장소에서 관리해 과제 리뷰어가 구조와 검증 경로를 한 번에 확인할 수 있게 했습니다.

- idempotent persistence  
  WebSocket 재수신, REST 재시도, recovery 재실행이 발생해도 candle 중복이 생기지 않도록 repository와 DB constraint를 함께 사용했습니다.

- 운영 지표 중심 Dashboard  
  가격 차트보다 freshness, status, gap, backfill, event를 우선 배치해 운영팀이 매일 보는 콘솔처럼 설계했습니다.

- broker를 도입하지 않은 이유  
  현재 범위는 BTCUSDT/ETHUSDT 두 심볼의 운영 dashboard입니다. Redis/Kafka를 추가하면 제출 과제의 복잡도가 커지므로, REST + SSE + PostgreSQL 중심으로 단순하게 유지했습니다.

## AI 활용 방식

- `PRODUCT.md`, `AGENTS.md`, `TASKS.md`를 먼저 만들어 범위와 작업 순서를 고정했습니다.
- Task 단위로 구현하고 각 Task 후 검증 명령을 실행했습니다.
- 사람은 설계 방향, 범위 제한, 완료 조건, 검증 결과를 통제했습니다.
- AI는 반복 구현, 테스트 작성, 문서 갱신을 보조했습니다.
- `docs/08-ai-collaboration-log.md`에 Task별 AI 작업과 검증 결과를 기록했습니다.

## 알려진 제한 사항

| 제한 사항 | 현재 상태 | 개선 방향 |
|---|---|---|
| Docker Compose end-to-end 검증 | 현재 환경에 Docker CLI가 없어 실제 build/up을 검증하지 못했습니다. | CI 또는 Docker 가능 환경에서 `docker compose config`, `make up`, `make smoke`를 실행합니다. |
| worker 자동 오케스트레이션 | collector/backfill/recovery service code는 있으나 compose boot 시 자동 worker supervisor가 실행되지는 않습니다. | backend worker entrypoint를 추가해 initial backfill, collector, restart recovery를 실행합니다. |
| 실제 Binance/PostgreSQL 통합 검증 | 단위/계약 테스트는 mock/SQLite 중심이며 live Binance + PostgreSQL end-to-end는 현재 환경에서 검증하지 못했습니다. | Docker 기반 통합 테스트 또는 reviewer demo 환경을 추가합니다. |
| 1000개 초과 gap pagination | recovery는 현재 단일 REST limit 중심입니다. | gap range를 Binance REST limit에 맞춰 page 단위로 분할합니다. |
| SSE 주기적 snapshot 방식 | broker 없이 주기적으로 dashboard snapshot을 보냅니다. | 규모가 커지면 event-driven fanout 또는 broker를 검토합니다. |
| event history best-effort 처리 | 이벤트 기록 실패가 핵심 수집/복구 흐름을 막지 않도록 설계되어 있습니다. | 운영 환경에서는 event write 실패 metric/alert를 추가합니다. |
| 다중 인스턴스 환경 | 현재는 단일 API/DB 중심 설계입니다. | leader election, worker 분리, shared event broker를 검토합니다. |
| 실제 브라우저 E2E 검증 | Vitest와 Next build는 통과했지만 Playwright 같은 브라우저 E2E는 없습니다. | smoke에 browser-level check 또는 Playwright 시나리오를 추가합니다. |

## 리뷰어 빠른 확인 경로

5~10분 기준 추천 순서입니다.

1. README의 프로젝트 소개, 핵심 기능, Known Limitations를 확인합니다.
2. 정적 검증을 실행합니다.

   ```bash
   make check
   ```

3. Docker 환경이 있으면 서비스를 시작합니다.

   ```bash
   make up
   ```

4. Dashboard에 접속합니다.

   ```text
   http://localhost:3000
   ```

5. 저장된 candle 데이터가 있는 실행 환경에서 smoke test를 실행합니다.

   ```bash
   make smoke
   ```

6. DB 접근과 recovery trigger가 준비된 환경에서 recovery drill을 실행합니다.

   ```bash
   make recovery-drill
   ```

7. 주요 코드 경로를 확인합니다.
   - `backend/app/repositories/sqlalchemy_market_data.py`
   - `backend/app/services/backfill.py`
   - `backend/app/services/gaps.py`
   - `backend/app/services/recovery.py`
   - `backend/app/api/dashboard.py`
   - `backend/app/api/stream.py`
   - `frontend/components/dashboard/operations-dashboard.tsx`
   - `frontend/lib/dashboard-api.ts`
   - `frontend/lib/dashboard-stream.ts`
   - `frontend/lib/dashboard-realtime.ts`
   - `scripts/smoke.sh`
   - `scripts/recovery-drill.sh`
