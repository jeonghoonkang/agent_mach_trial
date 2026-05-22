# agent_mach_trial
Auto devel by LLM
# Gemma 4 & Telegram Userbot 기반 멀티 에이전트 메시징 시스템

본 프로젝트는 로컬 LLM인 **Gemma 4**와 텔레그램 개인 계정 자동화(**Userbot**) 라이브러리를 유기적으로 연동하여, 사용자의 자연어 지시를 이해하고 지정된 시간에 친구에게 메시지를 자동으로 전달하는 멀티 에이전트 시스템입니다.

---

## 고도화된 개발 프로세스 (5단계)

인터페이스 불일치 방지와 효율적인 협업을 위해 GitHub 저장소를 기반으로 아래의 5단계 파이프라인에 맞춰 개발을 진행합니다.

```text
[1단계: 인프라 & Contract 정의] -> [2단계: Gemma 4 NLU 개발] -> [3단계: DB & 스케줄러 구축]
                                                                         |
[5단계: 통합 E2E 동작 테스트] <- [4단계: Telethon 발송 & 통합] <----------+
```

1. **1단계: 인프라 설정 및 GitHub 인터페이스 정의 (1~2일 차)**
   - 에이전트 간 데이터 포맷 규격(`schemas/contract.py`)을 최우선 정의하여 저장소에 공유합니다.
   - Ollama를 통한 로컬 Gemma 4 서빙 환경 및 텔레그램 API 권한(`api_id`, `api_hash`) 환경변수 설정을 마칩니다.
2. **2단계: 에이전트별 분리 개발 및 GitHub 푸시 (2~3일 차)**
   - `feature/parser`, `feature/refiner` 브랜치를 생성하여 Gemma 4 프롬프트 엔지니어링 및 메시지 변형 로직을 독립 개발 후 Pull Request(PR)로 병합합니다.
3. **3단계: DB, 스케줄러 워커 개발 및 Mock 테스트 (3~4일 차)**
   - `feature/scheduler` 브랜치에서 SQLite DB 스키마 및 `APScheduler` 루프를 개발합니다.
   - 분석가 에이전트의 출력 Mock 데이터를 활용해 독립 연동 테스트를 검증합니다.
4. **4단계: Telethon 발송 연동 및 브랜치 통합 (4~5일 차)**
   - `feature/delivery` 브랜치에서 `Telethon` 라이브러리를 이용하여 스케줄러 신호에 맞춰 실제 발송하는 에이전트를 구축합니다.
   - 스팸 방지를 위한 무작위 딜레이 로직을 포함합니다.
5. **5단계: 통합 파이프라인 가동 및 최종 동작 테스트 (5~6일 차)**
   - 메인 브랜치로 모든 코드를 통합한 후, 사용자의 자연어 명령이 `분석가 -> 스케줄러 -> 발송 에이전트`까지 끊김 없이 흘러가 최종적으로 개인 계정 텔레그램으로 전달되는지 엔드투엔드(E2E) 테스트를 수행합니다.

---

## 저장소 디렉토리 구조 권장 사항

인터페이스 충돌 방지를 위해 아래 구조를 유지하여 개발을 진행합니다.

```text
agent_mach_trial/
├── .gitignore               # .env 및 *.session 파일 제외 필수 설정
├── .env.example             # 환경변수 템플릿 (api_id, api_hash 포함)
├── README.md                # 본 개발 가이드 문서
├── schemas/                 # Pydantic 기반 데이터 모델 인터페이스 정의
│   └── contract.py
├── parser_agent/            # 1. 분석가 에이전트 모듈
├── scheduler_agent/         # 2. 스케줄러 & DB 에이전트 모듈
└── delivery_agent/          # 3. 개인 계정 발송 에이전트 모듈
```

---

## 에이전트별 가이드라인 (System Instruction)

각 에이전트 개발자는 아래의 Instruction 사양을 시스템 프롬프트 또는 코드 규칙으로 필수 탑재해야 합니다.

### 1. 분석가 에이전트 (Parsing Agent)

**기반 기술:** 로컬 서빙된 Gemma 4 (`Ollama` 활용 권장)

**역할:** 유저의 모호한 자연어 지시 사항과 현재 시간을 기반으로 발송 정형 데이터를 추출합니다.

```text
[System Instruction]
당신은 사용자의 텔레그램 메시지 발송 지시를 분석하여 구조화된 JSON 데이터로 변환하는 '분석가 에이전트'입니다.

1. 사용자의 입력 문장에서 [수신자 식별자(@username, 이름, 전화번호)], [예약 발송 시간], [메시지 본문]을 정확히 추출하십시오.
2. 시간 표현이 상대적일 경우(예: '내일 아침 9시', '3분 뒤'), 함께 제공되는 '현재 기준 시간'을 바탕으로 계산하여 ISO 8601 포맷(YYYY-MM-DDTHH:mm:ssZ)의 절대 시간으로 변환하십시오.
3. 출력 형식이 손상되지 않도록 다른 부연 설명 없이 오직 사전에 약속된 JSON 포맷으로만 응답해야 합니다. Pydantic의 Structured Outputs 기술 활용을 권장합니다.
```

### 2. 스케줄러 및 DB 에이전트 (Scheduler Agent)

**기반 기술:** Python Backend (`SQLite`, `APScheduler`)

**역할:** 분석 결과물을 DB에 안전하게 적재하고, 시간이 되었을 때 발송 에이전트를 호출합니다.

```text
[Code-level Specification]
1. 분석가 에이전트가 넘겨준 JSON 데이터를 수신하여 SQLite 테이블(message_tasks)에 'PENDING' 상태로 적재합니다.
2. 1분 단위의 백그라운드 스케줄러 루프를 실행하여 발송 대상 조건(target_time <= 현재시간)이 충족되는 즉시 '개인 계정 발송 에이전트' 모듈을 트리거합니다.
3. 안전을 위해 동일 시간에 대량의 예약이 밀려 있을 경우, 큐(Queue) 시스템을 통해 메시지 간 일정한 간격을 두고 순차적으로 발송 신호를 넘겨주어야 합니다.
4. 발송 완료 후 피드백을 받아 DB 상태를 'SUCCESS' 또는 'FAILED'로 업데이트 처리합니다.
```

### 3. 개인 계정 발송 에이전트 (Telegram Userbot Agent)

**기반 기술:** Python `Telethon` 라이브러리, 개인 API Key (`api_id`, `api_hash`)

**역할:** 개인 계정 권한을 활용해 수신자에게 메시지를 물리적으로 전송합니다.

```text
[System Instruction & Constraints]
당신은 텔레그램 Client API(Telethon)를 제어하여 예약된 메시지를 내 계정의 이름으로 친구들에게 전송하는 '발송 에이전트'입니다.

1. [계정 보호 및 스팸 방지] 연속 발송으로 인한 텔레그램 계정 정지(Spam 차단)를 막기 위해, 메시지 발송 요청을 처리할 때마다 반드시 건당 최소 2~3초의 무작위 딜레이(Random Time Sleep)를 강제 적용하십시오.
2. 식별자가 이름 형태일 경우 내 연락처 목록을 검색하거나 매핑 테이블을 참고하여 유효한 대화방(Peer)을 찾은 뒤 전송해야 합니다.
3. 보안 강화를 위해 `api_id`, `api_hash`, `*.session` 파일은 절대 GitHub Public 저장소에 업로드되어서는 안 되며, 오직 로컬 환경변수(.env)로만 관리합니다.
```

---

## 에이전트 간 인터페이스 규격 (`schemas/contract.py`)

코드를 합쳤을 때 구조적 충돌을 차단하기 위해 아래의 Pydantic BaseModel 스키마 표준 계약을 준수하여 개발을 진행합니다.

```python
from datetime import datetime

from pydantic import BaseModel, Field


class MessageTask(BaseModel):
    """분석가 에이전트가 출력하고, 스케줄러가 입력받아 DB에 저장할 데이터 규격"""

    recipient_identifier: str = Field(..., description="텔레그램 수신자 이름, @username 또는 전화번호")
    target_time: datetime = Field(..., description="ISO 8601 표준 형식의 예약 발송 시간")
    raw_message: str = Field(..., description="송신할 메시지 본문 내용")


class DeliverySignal(BaseModel):
    """스케줄러가 발송 시간에 도달했을 때 발송 에이전트에게 전달할 데이터 규격"""

    task_id: int
    telethon_target: str
    final_text: str
```

---

## 실행을 위한 설정 및 실행 방법

### 1. Python 가상환경 및 의존성 설치

저장소 루트에서 아래 명령을 실행합니다.

```bash
cd /path/to/agent_mach_trial
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 환경변수 파일 준비

`.env.example`을 복사해 `.env`를 만들고 실제 값을 채웁니다.

```bash
cp .env.example .env
```

```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION_NAME=agent_mach_trial

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4

DATABASE_PATH=message_tasks.db
DELIVERY_DRY_RUN=true
DELIVERY_MIN_DELAY_SECONDS=2
DELIVERY_MAX_DELAY_SECONDS=3
```

`DELIVERY_DRY_RUN=true` 상태에서는 실제 텔레그램 메시지를 보내지 않고 콘솔에만 출력합니다. 처음 실행할 때는 반드시 dry-run으로 동작을 확인한 뒤 실제 발송으로 전환하는 것을 권장합니다.

현재 코드는 `.env` 파일을 자동 로드하지 않으므로, 실행 전에 아래 명령으로 환경변수를 셸에 로드합니다.

```bash
set -a
source .env
set +a
```

### 3. Ollama 및 Gemma 모델 준비

Ollama 서버를 실행합니다.

```bash
ollama serve
```

다른 터미널에서 사용할 모델을 내려받습니다.

```bash
ollama pull gemma4
```

로컬에 설치된 모델명이 다르면 `.env`의 `OLLAMA_MODEL` 값을 실제 모델명으로 바꿉니다.

### 4. 자연어 명령 파싱 및 예약 등록

가상환경과 환경변수를 로드한 뒤 자연어 명령을 입력합니다.

```bash
python main.py "내일 아침 9시에 @friend에게 회의 준비됐냐고 보내줘"
```

이 명령은 Parser Agent가 Ollama/Gemma를 호출해 `MessageTask` JSON으로 변환한 뒤, Scheduler Agent가 SQLite DB(`message_tasks.db`)에 예약 작업을 저장합니다.

### 5. 스케줄러 실행

예약 시간이 지난 작업을 한 번만 처리하려면 아래 명령을 사용합니다.

```bash
python -m scheduler_agent.cli run-once
```

APScheduler 기반 루프를 계속 실행하려면 아래 명령을 사용합니다.

```bash
python -m scheduler_agent.cli run
```

기본 실행 주기는 60초입니다. 다른 주기를 사용하려면 `--interval` 값을 지정합니다.

```bash
python -m scheduler_agent.cli run --interval 30
```

### 6. 발송 에이전트 단독 테스트

실제 텔레그램 발송 전에 dry-run으로 Delivery Agent만 테스트할 수 있습니다.

```bash
python -m delivery_agent.cli @friend "테스트 메시지입니다"
```

### 7. 실제 텔레그램 발송 전환

dry-run 확인이 끝나면 `.env`에서 아래 값을 변경합니다.

```env
DELIVERY_DRY_RUN=false
```

이후 환경변수를 다시 로드하고 스케줄러를 실행합니다.

```bash
set -a
source .env
set +a

python -m scheduler_agent.cli run
```

처음 실제 발송을 수행할 때 Telethon이 텔레그램 로그인 인증을 요구할 수 있습니다. 이때 생성되는 `*.session` 파일은 로컬에만 보관해야 하며, `.gitignore`에 의해 GitHub 업로드 대상에서 제외됩니다.

---

## 후속 진행 가이드

1. 위 구조에 맞춰 `.gitignore`, `.env.example`, `schemas/contract.py`를 우선 추가합니다.
2. 각 에이전트 디렉토리를 독립 모듈로 구성하고, 공통 계약은 `schemas/contract.py`만 참조하도록 유지합니다.
3. 텔레그램 인증 정보와 세션 파일은 로컬 환경에만 보관하고 GitHub에는 업로드하지 않습니다.
