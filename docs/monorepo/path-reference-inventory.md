# 경로 참조 인벤토리 (3단계 사전 작업)

작성일: 2026-03-13

## 목적

`apps/ingest-databatcher` 이관 전에 구경로 참조를 전수 파악해, 누락 없이 경로를 교체하기 위한 기준 문서.

## 수집 방법

아래 명령으로 참조 후보를 추출했다.

```bash
# 운영 영향 파일(실행 경로 영향)
rg -n "python scripts/|python apps/ingest-databatcher/scripts/|apps/ingest-databatcher/ops/shell/|scheduler/" README.md AGENTS.md shell_scripts scheduler mysql-standalone/README.md

# 문서/가이드(운영 영향 낮음)
rg -n "scripts/|core/|collectors/|indicators/|savers/|config/" docs guides
```

초기 매치 수: **421**

업데이트(2026-03-14):

- 런타임 코드(`core/collectors/indicators/savers/scripts/tests`)는 `apps/ingest-databatcher/`로 이관 완료
- 운영 스크립트(`apps/ingest-databatcher/ops/shell/*.sh`)의 실행 경로는 1차 교체 완료
- 남은 항목은 문서/가이드의 예시 문자열 정리 중심

## 분류 요약

- **운영/실행 경로(필수 수정)**
  - `apps/ingest-databatcher/ops/shell/*.sh`
  - `apps/ingest-databatcher/ops/scheduler/windows/*.ps1`
  - `README.md`, `mysql-standalone/README.md`
- **코드 내 사용 예시/에러 메시지(권장 수정)**
  - `apps/ingest-databatcher/scripts/*.py`의 usage/help 문자열
- **테스트/가이드 문서(순차 수정)**
  - `apps/ingest-databatcher/tests/*.py`, `docs/*.md`, `guides/*.md`
- **기록성 문서(선택 수정)**
  - 과거 계획/회고 문서(실행 영향 없음)

## 우선 수정 대상 (P1/P2)

1. `apps/ingest-databatcher/ops/shell/`
2. `apps/ingest-databatcher/ops/scheduler/windows/`
3. 루트 `README.md`
4. `mysql-standalone/README.md`
5. 실제 실행에 사용되는 테스트/CI 파일

## 대표 참조 예시

- `apps/ingest-databatcher/ops/shell/weekly_all.sh`에서 `python apps/ingest-databatcher/scripts/...` 다수 호출
- `apps/ingest-databatcher/ops/scheduler/windows/run_daily.ps1`, `apps/ingest-databatcher/ops/scheduler/windows/run_weekly.ps1`에서 `apps/ingest-databatcher/ops/shell/...` 호출
- `README.md`의 실행 명령 대부분이 `apps/ingest-databatcher/scripts/...`, `apps/ingest-databatcher/ops/shell/...` 기준

## 교체 원칙

- 목표 경로: `apps/ingest-databatcher/...`
- 레거시 래퍼를 두지 않으므로 호출부를 직접 수정
- 교체 후 재검색으로 잔여 참조를 확인

검증 명령(범위 분리):

```bash
# 1) 운영 영향 파일은 구경로 0건을 목표로 한다.
rg -n "python scripts/|\"scripts/|`scripts/" README.md AGENTS.md shell_scripts scheduler mysql-standalone/README.md

# 2) docs/guides는 실행 영향 여부에 따라 순차 정리한다.
rg -n "scripts/|core/|collectors/|indicators/|savers/|config/" docs guides
```

주의:

- 설명 문서의 과거 회고 문구는 false positive 가능
- 실행 경로에 실제 영향을 주는 파일과 문서성 파일을 구분해서 처리
