# Console 기본 화면 전환 최종 실행 계획안

> **Status: COMPLETED** — 2026-03-19
> 실행 결과: preview 라우트 4개(`/preview`, `/preview/minimal`, `/preview/editorial`, `/preview/console`), 템플릿 4개, partial 4개 삭제 완료.
> `/`, `/v2`는 변경 전부터 이미 `index_v2.html`(console) 렌더링 중이었음 확인.
> 5단계(실행 환경 일관화)는 별도 계획으로 분리됨.
> 원본 계획 누락 항목: `/preview/console` 라우트 및 `index_preview_console.html` 템플릿이 삭제 대상에 포함되어야 했으나 원본에서 누락되었음 — 이번 실행에서 함께 처리됨.

## 목적
- `console` 시안을 기본 메인 화면으로 확정한다.
- 사용하지 않는 프리뷰 페이지/라우트를 제거한다.
- 기존 분석 API와 상세 페이지 동작은 유지한다.
- 단계별 테스트를 통해 기능 회귀 없이 전환을 완료한다.

## 범위
- 포함:
  - 메인 라우트(`/`, `/v2`)를 `console` 템플릿으로 전환
  - 운영용 템플릿/partial 이름 정리(미사용 `preview` 네이밍 제거)
  - 미사용 프리뷰 템플릿/라우트 정리
  - 기능/화면 회귀 테스트
- 제외:
  - 분석 로직 자체 변경
  - DB 스키마/쿼리 변경
  - `building_detail` 기능 확장

## 최종 상태 정의 (Acceptance Criteria)
1. `/`와 `/v2`가 모두 console 기반 메인 화면을 렌더링한다.
2. `minimal`, `editorial`, 프리뷰 허브 관련 템플릿/라우트는 제거된다.
3. `/combined_analysis`, `/district_analysis`, `/get_districts`, `/building_detail` 기존 동작이 유지된다.
4. 결과 없음/오류/Kakao 지도 fallback 상태가 화면에서 정상 표시된다.
5. `.env` 기반 DB 환경에서 실행 시 기존 운영 화면과 동일하게 DB 조회가 가능하다.

## 실행 단계

### 1) 운영용 템플릿 승격 및 네이밍 정리
- 작업:
  - `console` 템플릿을 운영용 이름으로 정리
  - 공통 partial 중 실제 사용 파일을 운영용 네이밍으로 정리
  - 화면 내 `Preview`, `Hub`, 실험용 문구/링크 제거
- 완료 기준:
  - 운영 화면에서 실험용 문구가 보이지 않는다.

### 2) 기본 라우트 전환
- 작업:
  - `src/real_estate/backend/web_app.py`에서 `/`, `/v2`가 console 템플릿을 렌더링하도록 변경
  - 기존 분석/상세 라우트는 변경하지 않음
- 완료 기준:
  - `/`, `/v2` 모두 200 응답 + console 화면 렌더링

### 3) 기능 회귀 검증 (삭제 전)
- 자동 검증:
  - `python -m py_compile src/real_estate/backend/web_app.py`
  - Flask test client로 `/`, `/v2`, `/building_detail` 라우트 응답 확인
  - `/combined_analysis`, `/district_analysis`, `/get_districts` 응답 구조 확인
- 수동 검증:
  - 서울 전체 분석 1회 실행
  - 특정 구 분석 1회 실행
  - 특정 동 분석 1회 실행
  - 상세보기 버튼으로 `/building_detail` 열기
  - 결과 없음 상태 확인
  - 오류 상태 확인
  - Kakao 지도 렌더링 또는 fallback 확인
- 완료 기준:
  - 핵심 사용자 플로우(분석 -> 지도/표 -> 상세보기) 정상 동작

### 4) 미사용 프리뷰 정리
- 작업:
  - 제거 대상 템플릿 삭제:
    - `index_preview.html`
    - `index_preview_minimal.html`
    - `index_preview_editorial.html`
  - 제거 대상 라우트 삭제:
    - `/preview`
    - `/preview/minimal`
    - `/preview/editorial`
  - console 메인 전환 후 더 이상 사용하지 않는 preview 전용 파일 정리
- 완료 기준:
  - 미사용 프리뷰 경로 제거 후에도 `/`, `/v2` 및 핵심 API 동작 유지

### 5) 실행 환경 일관화
- 작업:
  - 서버 실행 시 `.env` 기반 DB 환경 변수가 실제 반영되도록 실행 방법 통일
  - 포트별 프로세스 환경 차이로 DB 접속 실패가 재발하지 않게 정리
- 완료 기준:
  - 운영/검증 포트 모두 동일 DB 설정으로 분석 요청 성공

## 테스트 체크리스트

### A. 라우트/렌더링
- [ ] `GET /` -> 200
- [ ] `GET /v2` -> 200
- [ ] `GET /building_detail?...` -> 기존과 동일 동작

### B. API 동작
- [ ] `POST /combined_analysis` -> `success/message/data` 구조 유지
- [ ] `POST /district_analysis` -> `success/message/data` 구조 유지
- [ ] `GET /get_districts?gu=...` -> `districts` 배열 반환

### C. 화면 상태
- [ ] 분석 성공 상태(요약 카드/지도/결과표)
- [ ] 결과 없음 상태
- [ ] 오류 상태
- [ ] Kakao key 없음 fallback 상태

### D. 사용자 플로우
- [ ] 서울 전체 분석 -> 결과표 확인 -> 상세보기 이동
- [ ] 특정 구/동 분석 -> 결과표 확인 -> 상세보기 이동

## 롤백 기준
- 다음 중 하나라도 충족 시 즉시 롤백 후 원인 분석:
  - `/` 또는 `/v2` 렌더링 실패
  - 분석 API 응답 구조 변경/파손
  - 상세보기 이동 실패
  - DB 환경 불일치로 분석 요청 실패 반복

## 산출물
- 운영 메인(console) 반영된 템플릿 및 라우트
- 미사용 프리뷰 코드 정리 반영
- 검증 로그(자동 + 수동 결과 요약)
