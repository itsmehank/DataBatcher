# db

공통 DB 도메인 디렉토리.

- `compose/`: DB 컨테이너 실행 정의
- `init/`: bootstrap 초기화 스크립트
- `migrations/`: Alembic migration 이력
- `docs/`: ERD/스키마/운영 가이드

현재 공용 bootstrap 범위:

- `compose/mysql-standalone/`: MySQL + DataBatcher/trading-view/real-estate bootstrap
- `compose/mongo-standalone/`: MongoDB + my-insight-archieve bootstrap

원칙:

- 공용 `db/`는 DB 인프라 bootstrap, 사용자/권한 provisioning, 컨테이너/볼륨 운영을 담당합니다.
- 앱은 런타임 연결 정보만 받아 사용합니다.
- 앱 도메인 seed(예: 관리자 계정 document, 기본 카테고리)는 각 앱이 계속 책임집니다.
