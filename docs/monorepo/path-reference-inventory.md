# 경로 참조 인벤토리 (3단계 사전 작업)

작성일: 2026-03-13

## 목적

`apps/ingest-databatcher` 이관 전에 구경로 참조를 전수 파악해, 누락 없이 경로를 교체하기 위한 기준 문서.

## 수집 방법

아래 명령으로 참조 후보를 추출했다.

```bash
rg -n "scripts/|core/|collectors/|indicators/|savers/|config/" shell_scripts scheduler docs README.md tests scripts --glob '*.{md,sh,py,yml,yaml,bat,ps1}'
```

총 매치 수: **421**

## 분류 요약

- **운영/실행 경로(필수 수정)**
  - `shell_scripts/*.sh`
  - `scheduler/windows/*.ps1`
  - `README.md`, `mysql-standalone/README.md`
- **코드 내 사용 예시/에러 메시지(권장 수정)**
  - `scripts/*.py`의 usage/help 문자열
- **테스트/가이드 문서(순차 수정)**
  - `tests/*.py`, `docs/*.md`, `guides/*.md`
- **기록성 문서(선택 수정)**
  - 과거 계획/회고 문서(실행 영향 없음)

## 우선 수정 대상 (P1/P2)

1. `shell_scripts/`
2. `scheduler/windows/`
3. 루트 `README.md`
4. `mysql-standalone/README.md`
5. 실제 실행에 사용되는 테스트/CI 파일

## 대표 참조 예시

- `shell_scripts/weekly_all.sh`에서 `python scripts/...` 다수 호출
- `scheduler/windows/run_daily.ps1`, `scheduler/windows/run_weekly.ps1`에서 `shell_scripts/...` 호출
- `README.md`의 실행 명령 대부분이 `scripts/...`, `shell_scripts/...` 기준

## 교체 원칙

- 목표 경로: `apps/ingest-databatcher/...`
- 레거시 래퍼를 두지 않으므로 호출부를 직접 수정
- 교체 후 재검색으로 잔여 참조를 확인

검증 명령:

```bash
rg -n "scripts/|core/|collectors/|indicators/|savers/|config/" shell_scripts scheduler docs README.md tests scripts --glob '*.{md,sh,py,yml,yaml,bat,ps1}'
```

주의:

- 설명 문서의 과거 회고 문구는 false positive 가능
- 실행 경로에 실제 영향을 주는 파일과 문서성 파일을 구분해서 처리
