# Future Tasks

> 마지막 검토일: 2026-03-19

향후 처리할 운영/보안 작업을 모아두는 디렉토리입니다.

## 문서 목록

| 문서 | 상태 | 착수 근거 | 의존성 |
|------|------|---------|--------|
| `trading-view-auth-plan.md` | 미착수 | 최소 인증 설계 및 구현 계획 수립 필요 | 없음 (우선순위 1) |
| `my-insight-security-hardening-plan.md` | 미착수 | 보안 강화 계획 수립 필요 | trading-view 완료 후 (우선순위 2) |
| `gcp-deployment-architecture.md` | 미착수 | GCP Compute Engine 기준 배포 구조 설계 필요 | 앱 준비 완료 후 (우선순위 3) |
| `security-policy-matrix.md` | 미착수 | 서비스별 네트워크/인증/권한 정책 통합 필요 | 모든 앱 준비 완료 후 (우선순위 4) |

> **상태 범주**: 미착수 | 진행중 | 완료 (현재 위 문서들은 모두 미착수 상태)

## 운영 원칙

- 지금 당장 구현하지 않는 항목도 의사결정 근거와 우선순위를 남긴다.
- 문서는 설계 초안이므로, 실제 구현 시점에 인프라 상태와 요구사항을 다시 검증한다.
- 앱 레벨 변경이 필요한 항목은 해당 프로젝트 문서와 함께 갱신한다.
- 인증 방식을 쿠키 기반으로 가져갈 경우, CSRF 대응 여부를 함께 검토한다.

## 다음 세션 시작 가이드

- 새 세션에서는 이 디렉토리의 문서를 우선 읽고 작업을 시작한다.
- 구현 착수 권장 순서:
  1. `trading-view-auth-plan.md`
  2. `my-insight-security-hardening-plan.md`
  3. `gcp-deployment-architecture.md`
  4. `security-policy-matrix.md`
- 인프라 실행 전에는 실제 도메인, 시크릿 저장 방식, VM 분리 수준을 다시 확인한다.
- 문서만으로 결정을 내리기 어려운 경우, 각 프로젝트의 `README.md`, `AGENTS.md`, 현재 코드 구현을 함께 검토한다.

## 관련 문서

- `plans/future-tasks/trading-view-auth-plan.md`: trading-view 인증 설계 및 구현 계획
- `plans/future-tasks/my-insight-security-hardening-plan.md`: my-insight 보안 강화 계획
- `plans/future-tasks/gcp-deployment-architecture.md`: GCP 배포 구조 및 네트워크 정책
- `plans/future-tasks/security-policy-matrix.md`: 서비스별 보안 정책 매트릭스
