# GCP Deployment Architecture

> 마지막 검토일: 2026-03-19

## 목적

- `db/`, `apps/ingest-databatcher/`, `apps/my-insight-archieve/`, `apps/trading-view-project/`의 GCP Compute Engine 배포 기준안을 정리한다.
- 현재 기준 추천 구조와 추후 확장 구조를 구분해 남긴다.

## 현재 추천 구조

### 기본안: 2 VM 구조

- `DB VM`
  - MySQL 전용 VM
  - 외부 공인 IP 직접 노출 최소화
  - 앱 VM 또는 허용된 운영자 IP에서만 접근 허용
  - **MongoDB 배치 옵션 (결정 전)**
    - **A) DB VM에 MySQL + MongoDB 함께 배치**: 단순하고 비용 효율적이나 MySQL과 리소스 경합 가능
    - **B) App VM에 my-insight 컨테이너와 MongoDB를 함께 배치**: 리소스 격리 및 독립 운영 가능하나 비용 증가
    - **C) MongoDB Atlas(매니지드) 사용**: 관리형 서비스로 운영 부담 최소화하나 외부 의존성 증가

- `App VM`
  - Reverse proxy(`nginx` 또는 `caddy`)
  - `apps/my-insight-archieve/` frontend/backend 컨테이너
  - `apps/trading-view-project/` frontend/backend 컨테이너
  - `apps/ingest-databatcher/` 배치 컨테이너 또는 systemd/cron 기반 프로세스
  - 외부 공개는 reverse proxy만 담당하고, 각 backend 컨테이너는 내부 네트워크에만 연결

### 이유

- DB를 앱과 분리해 장애 전파 범위를 줄인다.
- 웹앱 2개는 같은 VM에 컨테이너로 운영해 비용과 운영 복잡도를 낮춘다.
- 배치 앱은 외부 공개 서비스가 아니므로 초기에 별도 VM까지 분리할 필요는 낮다.

## 확장안

### 3 VM 구조

- `DB VM`: MySQL 전용
- `Web VM`: 웹앱 전용
- `Batch VM`: `ingest-databatcher` 전용

### 분리 조건

- 배치 작업이 CPU/메모리/디스크 IO를 크게 사용해 웹 응답 성능에 영향이 생길 때
- 배치 실행 빈도가 증가하거나 병렬 수집 작업이 많아질 때
- 웹과 배치의 운영 주기, 배포 주기, 접근 권한을 명확히 분리할 필요가 생길 때

## 라우팅 초안

- `insight.<domain>` -> `my-insight-archieve` frontend
- `insight-api.<domain>` 또는 내부 라우팅 -> `my-insight-archieve` backend
- `trading.<domain>` -> `trading-view-project` frontend
- `trading-api.<domain>` 또는 내부 라우팅 -> `trading-view-project` backend

## 네트워크 원칙

- 외부 공개 포트는 원칙적으로 `80/443`만 허용
- DB 포트 `3306`은 인터넷에 직접 공개하지 않음
- 배치 프로세스는 외부 인바운드 포트를 열지 않음
- SSH는 가능하면 GCP IAP + OS Login 사용, 불가피하면 허용 IP 제한
- App VM 내부에서도 frontend/backend/db 간 연결 범위는 컨테이너 네트워크 또는 로컬 바인딩으로 최소화

## 포트 인벤토리

| 서비스 | 포트 | 공개 여부 | 비고 |
|--------|------|---------|------|
| MySQL | 3306 | 비공개 | DB VM 내부, App VM에서만 접근 |
| my-insight MongoDB | 27017 | 비공개 | App VM 내부 컨테이너 |
| my-insight Backend | 4000 | 비공개 | App VM 내부 컨테이너 |
| my-insight Frontend | 3000 | 비공개 | App VM 내부 컨테이너 (nginx 뒤) |
| trading-view Backend | 8000 | 비공개 | App VM 내부 컨테이너 |
| trading-view Frontend | 80 | 비공개 | App VM 내부 컨테이너 (nginx 뒤) |
| Reverse Proxy (nginx) | 80/443 | 공개 | App VM 외부 공개 |

## 시크릿 원칙

- 운영용 비밀번호와 토큰은 `.env` 직접 배포보다 GCP Secret Manager 사용 우선
- DB root 계정과 앱 계정 분리
- 서비스별 최소 권한 계정 분리

## 추후 상세화 필요 항목

- 실제 도메인/서브도메인 매핑
- SSL 종료 위치(reverse proxy 또는 LB)
- 로그/모니터링/알림 구조
- 백업 보관 위치와 복구 절차
- 인스턴스 타입 및 디스크 용량 기준
- **CI/CD 경로 설계**: 코드 → Container Registry → VM 배포 경로 설계 필요 (GitHub Actions 또는 GCP Cloud Build 선택, 배포 파이프라인 구성)
- **컨테이너 운영 방식**: Docker Compose vs Kubernetes vs systemd 선택, 자동 재시작 정책
- **nginx 통합 방안**: my-insight 프로젝트에 nginx 설정 추가, 라우팅 규칙 통합

## 착수 전 체크리스트

- 실제 운영 대상이 `2 VM`인지 `3 VM`인지 확정
- GCP 프로젝트, VPC, 서브넷, 방화벽 정책 초안 준비
- 각 서비스 도메인/서브도메인 확정
- Secret Manager 사용 여부와 주입 방식 확정

## 완료 기준

- VM 역할과 서비스 배치 위치가 문서/다이어그램으로 확정됨
- 공개 포트와 비공개 포트가 서비스별로 정의됨
- reverse proxy, SSL 종료, 시크릿 저장 위치가 결정됨
- 배치 실행 위치와 DB 접근 경로가 확정됨

## 관련 문서

- `plans/future-tasks/security-policy-matrix.md`: 서비스별 네트워크/인증/권한 정책
- `plans/future-tasks/trading-view-auth-plan.md`: trading-view 인증 설계
- `plans/future-tasks/my-insight-security-hardening-plan.md`: my-insight 보안 강화
- `apps/my-insight-archieve/docker-compose.yml`: my-insight 컨테이너 구성
- `apps/trading-view-project/docker-compose.yml`: trading-view 컨테이너 구성
- `apps/trading-view-project/frontend/nginx.conf`: trading-view nginx 설정 예시
- `db/compose/mysql-standalone/docker-compose-mysql.yaml`: MySQL 컨테이너 구성
