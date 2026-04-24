# 현재 진행 상황

> 이 문서는 프로젝트의 현재 상태를 한 페이지로 요약한다.  
> **새 AI 세션을 시작할 때 가장 먼저 읽는 문서**다.  
> Phase 종료 시, 또는 큰 변경 시 갱신한다. 가능한 한 짧게 유지한다.

---

## 현재 위치

**완료된 Phase**: Phase 0 (이미 완료된 기존 작업)

**진행 중인 Phase**: 없음 (Phase 1 시작 대기)

**다음 시작할 Phase**: **Phase 1 — LLM 분석 레이어 구축**

---

## Phase 0에서 완료된 것

- (1) 매일 배치 일봉 데이터 적재 (KOSPI, KOSDAQ, NYSE, NASDAQ)
- (2) 인디케이터 계산 (SMA, RS Line 등)
- (3) 미너비니 템플릿 필터링
- (4) 시각화 백엔드 + 프론트엔드 기본 구조
- 데이터는 로컬 MySQL에 저장됨
- 대시보드에서 종목 목록 + 일봉/주봉/RS Line 차트 조회 가능

---

## Phase 1에서 할 것 (요약)

LLM이 매일 미너비니 템플릿 통과 종목을 자동으로 분석하고, 진입/관찰/무시로 분류하며, 진입 종목에 대해 진입가·손절가·제안 비중을 산출하는 모듈을 구축한다.

**핵심 산출물**:
- `daily_analysis` 테이블 생성
- (5) 차트 분석 함수
- (6) 진입 파라미터 함수
- 일일 배치에 통합
- 분석 결과의 JSON 스키마 (GLOSSARY.md에 이미 정의됨)

**다음 단계**: Architect 세션에서 `_meta/phases/phase1_brief.md` 작성 → Builder 세션에서 구현 시작.

---

## 주요 결정 사항 (최근 / 중요한 것만)

- ADR-001: 4계층 아키텍처 채택
- ADR-002: LLM은 직접 주문 실행 안 함
- ADR-003: LLM 호출은 Anthropic API 사용 (Claude Code CLI 미사용)
- ADR-004: LLM 분석은 일일 배치만 (장중 실시간 미포함)
- ADR-005: 영속 문서 기반 거버넌스

전체 ADR은 `04_DECISIONS.md` 참조.

---

## 미해결 이슈 / 주의 사항

현재 없음.

(앞으로 추가 시: Phase별로 이슈가 발생하면 여기에 누적하고, 해결되면 ADR로 정리하거나 삭제한다.)

---

## 환경 / 설정 상태

- **개발 PC**: 사용자 로컬 PC, 24시간 가동 가능
- **DB**: 로컬 MySQL (Phase 0에서 셋업됨)
- **외부 접속**: 미설정 (Phase 3에서 Cloudflare Tunnel 또는 Tailscale 도입 예정)
- **Anthropic API 키**: Phase 1 시작 시 발급/등록 필요

---

## 빠른 참조 링크

- 헌법: `_meta/00_CONSTITUTION.md`
- 아키텍처: `_meta/01_ARCHITECTURE.md`
- 시나리오: `_meta/02_SCENARIO.md`
- 로드맵: `_meta/03_ROADMAP.md`
- 의사결정: `_meta/04_DECISIONS.md`
- 인터페이스: `_meta/05_GLOSSARY.md`

---

*마지막 업데이트: 2026-04-23 (프로젝트 시작 시점)*
