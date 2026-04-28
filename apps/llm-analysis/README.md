# llm-analysis

Phase 1 LLM 분석 레이어. 미너비니 템플릿 통과 종목에 대해 LLM이 차트 분석 후 `entry / watch / ignore` 분류 + 진입 파라미터를 산출한다.

**헌법 §2.2 분리 원칙**: 이 앱은 `apps/ingest-databatcher/`의 함수를 import하지 않는다. DB만 공유한다.

**관련 ADR**: ADR-009 (스키마), ADR-011 (CLI 백엔드), ADR-012 (자동 트리거)

**관련 Brief**: `_meta/phases/phase1_brief.md`

**LLM 백엔드**: 기본은 Claude Code CLI (Max 플랜). Anthropic API 백엔드도 추상화로 지원 (ADR-011). `config/settings.yaml`의 `llm_analysis.backend: "cli" | "api"`로 전환.

---

> Phase 1.3 완료 후 사용법(설치·실행·설정)을 이 섹션에 채운다.
