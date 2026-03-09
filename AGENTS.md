# AGENTS.md

이 문서는 이 저장소에서 작업하는 에이전트(예: OpenCode, Cursor Agent, Copilot Agent)를 위한 실행/코딩 규칙이다.
아래 내용은 실제 코드 구조(`scripts/`, `core/`, `collectors/`, `indicators/`, `tests/`)를 기준으로 정리했다.

## 0) Language
- 기본 사용자 응답 언어는 한국어로 한다.
- 사용자가 다른 언어를 명시적으로 요청한 경우에만 해당 언어로 응답한다.

## 1) 프로젝트 개요
- 프로젝트 성격: 멀티 마켓 데이터 배치 수집기(KR/US/Crypto + 지표 계산 + MySQL 저장)
- 주요 런타임: Python + pandas + SQLAlchemy + PyMySQL
- 데이터 소스: pykrx, FinanceDataReader, yfinance, Binance API
- 엔트리포인트: `scripts/*.py` (일반적으로 CLI 스크립트 중심)
- 구성 로딩: `core/config_loader.py`의 `load_settings()`
- DB 엔진 관리: `core/db_manager.py`의 `DBManager` 싱글턴 패턴

## 2) 환경/실행 전제
- 가상환경 활성화 후 실행 권장
- 의존성 설치: `pip install -r requirements.txt`
- DB 연결 정보는 `DATABASE_URL` 또는 `config/settings*.yaml` 사용
- 로컬 DB는 보통 Docker Compose 사용: `docker compose -f docker/docker-compose.yml up -d`
- 스키마 초기화: `python scripts/init_db.py`

## 3) Build / Lint / Test 명령
이 저장소는 전형적인 "패키지 빌드" 프로젝트가 아니라 배치 스크립트 실행형이다.

### 3.1 Build 성격의 검증
- 엄밀한 build step은 없음
- 최소 문법 검증(권장): `python -m compileall core collectors indicators savers scripts tests`

### 3.2 Lint/Format
- 고정된 lint 도구 설정 파일(`pyproject.toml`, `setup.cfg`, `tox.ini`, `.flake8`, `ruff`)은 현재 없음
- 따라서 새 lint 도구를 강제 도입하지 말고, 기존 스타일/패턴을 우선 준수
- 필요 시 로컬 임시 점검은 가능하나, 레포 규칙으로 단정하지 말 것

### 3.3 Test (중요)
- pytest 기반 테스트 + 스크립트 기반 테스트가 혼합되어 있음

- 전체 pytest 실행:
  - `pytest -q tests scripts/tests`

- 단일 파일 실행(가장 자주 사용):
  - `pytest -q tests/test_pykrx_adapter.py`

- 단일 테스트 함수 실행(특히 중요):
  - `pytest -q tests/test_pykrx_adapter.py::test_normalize_price_columns_basic`

- 마커 기반 실행(integration만):
  - `pytest -q -m integration tests/test_pykrx_adapter.py`

- integration 제외 실행:
  - `pytest -q -m "not integration" tests`

- 스크립트형 테스트 실행 예:
  - `python tests/test_db_setup.py --create`
  - `python tests/run_all_tests.py`
  - `python tests/test_phase1_sync_symbol_master.py`

## 4) 단일 테스트 실행 가이드
- 빠른 단위 확인은 `pytest <file>::<test_name>` 우선
- DB 의존 테스트는 먼저 테스트 DB 준비:
  - `python tests/test_db_setup.py --create`
- DB/네트워크 의존 테스트는 느리고 flaky 가능성이 있으므로 범위를 최소화
- 새 기능 수정 시, 관련 테스트 파일 1개 + 관련 함수 1개를 먼저 핀포인트로 실행

## 5) 코드 스타일 가이드 (레포 관찰 기반)

### 5.1 Imports
- 파일 상단 `from __future__ import annotations`를 기본으로 사용
- import 순서 권장:
  1) 표준 라이브러리
  2) 서드파티
  3) 로컬 모듈(`core`, `collectors`, `indicators`, `savers`, `scripts`)
- 필요 시 스크립트에서 `ROOT` + `sys.path.insert(0, str(ROOT))` 패턴 사용 가능(기존 관례)
- 부수효과 등록 import(예: 지표 registry) 허용:
  - `from indicators.common import sma as _reg_sma  # noqa: F401`

### 5.2 포매팅
- 들여쓰기 4 spaces, 탭 사용 금지
- 함수/클래스 사이 빈 줄은 PEP 8 스타일(보통 2줄)
- 긴 로직은 단계 주석(STEP 1/2/3)으로 구분 가능(기존 스크립트 관례)
- 문자열 포매팅은 f-string 우선

### 5.3 타입 힌트
- 공개 함수/메서드 시그니처에는 타입 힌트 적극 사용
- `pd.DataFrame`, `dict[str, Any]`, `Optional[T]` 등 기존 표기와 일관성 유지
- 레거시/동적 구간에서는 과도한 타입 강제보다 런타임 안정성 우선

### 5.4 네이밍
- 함수/변수: `snake_case`
- 클래스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- DataFrame 변수명 관례:
  - 원본/중간: `df`, `df_price`, `df_full`, `df_long`
  - 결과/집계: `results`, `stats`, `count_*`

### 5.5 데이터/DB 처리
- 날짜 컬럼은 저장 전에 `pd.to_datetime(...).dt.date` 또는 `normalize` 처리
- 대량 입력은 `DBManager.upsert_dataframe()` 재사용 우선
- upsert 모드 의미를 명확히 유지:
  - `mode="upsert"`: 기존값 갱신
  - `mode="insert_only"`: 기존값 보존(중복 무시)
- SQL은 `sqlalchemy.text()` + 바인딩 파라미터 우선

### 5.6 에러 처리
- 사용자 실행 스크립트에서는 명확한 에러 메시지 + 적절한 종료 코드 사용
- 심볼 루프/배치 루프에서는 개별 실패를 로깅하고 전체 작업은 지속하는 패턴 선호
- 광범위 `except Exception`은 경계(main loop, 외부 API 호출부)에서만 제한적으로 사용
- 라이브러리성 함수는 가능하면 예외를 삼키지 말고 호출자에게 전파

### 5.7 로깅/출력
- 배치 진행 상황은 `print` 또는 `logging` 중 기존 파일 패턴을 따름
- 신규 대형 배치 스크립트는 `logging` 사용 권장, 실패 심볼 로그 파일 유지
- 사용자에게 필요한 요약(성공/실패 건수, 소요시간)을 마지막에 출력

## 6) 테스트 작성/수정 규칙
- pytest 테스트는 `tests/test_*.py`, `scripts/tests/test_*.py` 패턴 준수
- 네트워크 의존 테스트는 `@pytest.mark.integration`로 분리
- 테스트는 가능하면 독립/반복 실행 가능(idempotent)해야 함
- DB 테스트는 프로덕션 DB가 아닌 `trade_test` 사용(필수)

## 7) 스크립트 설계 규칙
- CLI 스크립트는 `parse_args()` + `main()` + `if __name__ == "__main__":` 구조 권장
- 옵션 검증 실패 시 빠르게 종료하고 사용 예시를 함께 제공
- 마켓/심볼 필터 옵션(`--all`, `--symbols`, `--market`, `--top`) 패턴 재사용

## 8) 설정 파일 규칙
- 기본 설정: `config/settings.yaml`
- 개발 오버레이: `config/settings.dev.yaml` (존재 시 merge)
- 환경 변수 `DATABASE_URL`이 DB URL 우선순위 최상위
- 민감정보는 코드 하드코딩 금지, `.env` 또는 환경변수 사용

## 9) Cursor/Copilot 규칙 반영 상태
- 확인 결과 아래 파일은 현재 저장소에 없음:
  - `.cursor/rules/`
  - `.cursorrules`
  - `.github/copilot-instructions.md`
- 따라서 본 문서가 에이전트 작업의 기본 규칙 문서 역할을 한다.

## 10) 작업 시 권장 체크리스트
- 변경 전: 영향 받는 스크립트/테이블/설정 키 확인
- 변경 중: 기존 upsert/insert_only 의미를 깨지 않는지 확인
- 변경 후: 최소 1개 단일 테스트 + 관련 스크립트 dry run/샘플 실행
- GitHub 업로드 전: `python scripts/preflight_repo_safety.py`로 민감정보/로컬 아티팩트 점검
- 문서화: 새 CLI 옵션/동작 변경 시 `AGENTS.md` 또는 관련 가이드 업데이트

## 11) 금지/주의
- 프로덕션성 데이터 삭제/초기화 명령 무단 실행 금지
- 테스트 편의 목적으로 `market` DB를 직접 정리하지 말 것
- 대규모 포맷팅 리팩터링(동작 무관 스타일 변경) 단독 커밋 지양
- 기존 한국어 로그/가이드 톤을 불필요하게 영어 중심으로 바꾸지 말 것
