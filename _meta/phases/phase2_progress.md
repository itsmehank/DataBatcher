# Phase 2 진행 기록

> Phase 2 sprint별 작업 기록. `phase2_brief.md`이 SSoT, 본 문서는 진행 상황.
> 양식 계승: `phase1_progress.md`

---

## Sprint 1: 엑셀 템플릿 + 생성 함수 (`phase2/sprint1-excel` 브랜치)

**시작**: 2026-05-11
**완료**: <Sprint 1 머지일>

### 1.A 구조 + 의존성 + 골격 (commit `d3abc1a`)

- `apps/llm-analysis/exporters/` 패키지 신설 + `__init__.py`
- `excel_exporter.py` 골격 — `ExcelExporter` 클래스 stub + `DailyAnalysisRow` dataclass (DAO 출력 모델)
- Sheet 1 컬럼 구성 — `ENTRY_CORE_COLS` 8 + `ENTRY_CONTEXTUAL_COLS` 8 + `ENTRY_EXTRA_COLS` 4
- `openpyxl>=3.1.0,<4.0` 의존성 추가 (`apps/llm-analysis/requirements.txt`)

### SSoT 점검 발견 사항 (Step 1.A 진입 시)

**EntryParams 16→17 필드 카운트 오류**:
- 코드 SSoT: `apps/llm-analysis/models/entry_params.py` 실제 17필드
- 거버넌스 문서 카운트: 16필드로 표기 (3 위치)
  - `apps/llm-analysis/models/entry_params.py` docstring "16개 필드"
  - `_meta/05_GLOSSARY.md` Part B.2 line 411 "필드 정의 (16필드)"
  - `_meta/05_GLOSSARY.md` Part B.2 line 472 "v1.1 (16필드)"
- 발견 경위: Phase 2 Sprint 1 1.A 진입 시 Builder SSoT 점검 (phase2_brief §11.2 정신 직접 적용)
- 컬럼 스킴 영향 없음 — Sprint 1 ENTRY 컬럼 스킴이 17필드 모두 cover (CORE 7 + CONTEXTUAL 8 + warnings 2 = 17)
- 카테고리: ADR-014 §1 (a) Implementation Detail 정밀화 (코드 실제 17, 문서 카운트만 오류 — 결정 본질 불변)
- 처리: Sprint F backlog #7 등록 (Sprint 1 범위 밖) — 별도 Architect 명령으로 거버넌스 문서 정정 예정

**DB 세션 import path 정정** (Step 1.A 진입 시):
- Architect 원 명령: `from db.session import get_session`
- 코드 SSoT 채택: `from core.db import make_session_factory`
- Step 1.B.1 DAO + 1.C.1 CLI에서 정정된 path 사용

### 1.B 본체 구현 (commit `2ac48b2`, `976eab6`, `be7a907`, `d87c18f`)

**1.B.1 DAO** (`2ac48b2`):
- `exporters/daily_analysis_dao.py` — `fetch_daily_analysis(session, target_date, region)`
- `_parse_json()` MySQL JSON 컬럼 dict 파싱 안전망 (PyMySQL 자동 파싱 + bytes/str 대응)
- region='both' → kr + us 통합 반환 (kr 우선)
- 정렬: `CASE classification WHEN 'entry' THEN 0 WHEN 'watch' THEN 1 WHEN 'ignore' THEN 2` + symbol
- 세션 lifecycle caller 책임 (`run_daily_analysis.py` 양식 계승)

**1.B.2-a Sheet 1 'Entry 후보'** (`976eab6`):
- `__init__` region 인자 추가 — 파일명 `daily_analysis_{date}_{region}.xlsx`
- `export()`: Workbook 생성 + 3 sheet (Sheet 2/3 intermediate placeholder)
- Sheet 1: header(CORE 8+EXTRA 4+CONTEXTUAL 8=20) + frozen B2 + hidden M~T + entry_params None 회색 fill(F2F2F2) + warnings multi-line + wrap_text
- 헬퍼: `_style_header`, `_apply_col_widths`, `_format_warnings_list`, `_format_risk_flags_multiline`, `_format_risk_flags_summary`, `_truncate_reasoning`

**1.B.2-b Sheet 2/3** (`be7a907`):
- Sheet 2: 7컬럼 + classification='watch' 필터 + classification_change_signal 빈 cell (후속 정밀화) + wrap_text
- Sheet 3: 8컬럼 + 전체 rows + risk_flags 요약("N건: top1, top2") + reasoning 200자 컷("...")

**1.B.3 단위 테스트 14건** (`d87c18f`):
- `tests/test_excel_exporter.py` — 9 검증 케이스를 함수 단위 14건으로 세분화 + `@pytest.mark.parametrize`
- NVST sample(05_GLOSSARY Part B.2) 17필드 정합 검증
- 회귀 0건 — 전체 pytest **146 passed** (132 베이스라인 + 14 신규)

### 1.C CLI + 시각 검증 + 본 문서 (commit `8d66cd7`, `<1.C.3 commit>`)

**1.C.1 CLI** (`8d66cd7`):
- `apps/llm-analysis/run_excel_export.py` 신규 — `--date`, `--region`, `--out-dir`
- `sys.path` 추가 + `from core.db import make_session_factory` (Architect 결정 B)
- 세션 lifecycle try/finally, 에러 시 traceback + exit 1
- 빈 결과 stderr 안내 + 빈 sheet 엑셀 그대로 생성
- `.gitignore`에 `apps/llm-analysis/out/` 추가

**1.C.2 sample 시각 검증** (commit 없음 — sample 파일은 `out/` 봉인):
- `out/daily_analysis_2026-05-01_us.xlsx` — Sheet 3: watch 1 + ignore 9 (= 10행)
- `out/daily_analysis_2026-05-06_us.xlsx` — Sheet 3: watch 1 + ignore 121 (= 122행)
- `out/daily_analysis_2026-05-04_both.xlsx` — Sheet 3: ignore 20 (kr 10 + us 10)
- 모든 sample에서 Entry 0건 안내 행 정합 (Phase 1.3 167행 표본에 entry 없음)
- 사용자 시각 검증 항목:
  - Sheet 1 안내 행, hidden columns M~T, frozen B2, 컬럼 width
  - Sheet 2 ALTO watch 행 reasoning wrap, risk_flags multi-line
  - Sheet 3 region 컬럼, classification 정렬, reasoning 200자 컷

**1.C.3 phase2_progress.md** (본 commit):
- 본 문서 신규 작성

### 완료 기준 (phase2_brief §3 Sprint 1)

- [x] 임의 거래일 엑셀 생성 성공 (sample 3건)
- [ ] 사용자 시각 검증 통과 ("메일에서 열어 핵심 정보 파악 가능") — 사용자 검증 대기
- [x] entry_params 17필드 모두 표기 (CORE 7 frozen + EXTRA 2 frozen + CONTEXTUAL 8 hidden + warnings 2 frozen)
- [x] 단위 테스트 14/14 통과 + 회귀 0건 (146 total passed)

### Sprint 1 commit 트레일

```
8d66cd7  phase2 sprint1.C.1: run_excel_export.py CLI 진입점
d87c18f  phase2 sprint1.B.3: ExcelExporter 단위 테스트 14건
be7a907  phase2 sprint1.B.2-b: Sheet 2 'Watch 후보' + Sheet 3 '전체 분석' 빌더
976eab6  phase2 sprint1.B.2-a: Sheet 1 'Entry 후보' 빌더 + export() + 헬퍼
2ac48b2  phase2 sprint1.B.1: daily_analysis DAO
d3abc1a  phase2 sprint1.A: excel_exporter 골격 + openpyxl 의존성
```

### 외부 평가 / 결정

(Sprint 1 진행 중 발생 시 추가)

---

(이후 Sprint 2·3, Sprint A·B·C·D·E·F 본 문서에 누적)
