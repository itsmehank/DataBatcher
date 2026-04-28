# 운영 환경 작업 큐 (Operational Queue)

> 로컬에서 변경되었고 운영 환경(집 PC)에서도 적용이 필요한 작업을 기록한다.  
> 개발 환경과 운영 환경이 분리되어 있으므로, 코드 변경(git pull로 자동 반영)과 별개로 **DB 스키마·외부 설정·수동 마이그레이션** 등은 명시적으로 적용해야 한다.  
> 운영 환경에서 작업을 마치면 해당 항목을 "완료" 섹션으로 옮긴다.  
> 새 항목은 항상 "대기" 섹션 맨 위에 추가한다(최신순).
>
> 이 큐의 운영 방식은 ADR-010에서 정의된다.

---

## 환경 정보

### 개발 환경 (DEV)
- **디바이스**: Mac 노트북
- **OS**: macOS
- **셸**: bash / zsh
- **DataBatcher 경로**: (사용자가 채워넣을 것 — 예: `~/work/DataBatcher`)
- **DB**: 로컬 MySQL (Docker)
- **용도**: 코드 작성, 테스트 DB 검증, `_meta/` 문서 관리

### 운영 환경 (PROD)
- **디바이스**: 집 PC (24시간 가동)
- **OS**: Windows
- **셸**: PowerShell
- **스케줄러**: Windows Task Scheduler (`apps/ingest-databatcher/ops/scheduler/windows/*.ps1`)
- **DataBatcher 경로**: (사용자가 채워넣을 것 — 예: `C:\work\DataBatcher`)
- **DB**: MySQL 8.4.8 (Docker 컨테이너 — 컨테이너명 `mysql-standalone-mysql`)
  - 호스트에 `mysql`/`mysqldump` 클라이언트 없음 → 명령은 `docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" ...` 형태로 실행
- **MySQL 자격증명**: `.env`의 `MYSQL_ROOT_PASSWORD` 사용 (Q-001 적용 시 확인됨, 2026-04-26)
- **접속 방법**: 직접 / 원격 데스크톱 / SSH (사용자가 명시)
- **Daily cron 시각**:
  - US daily: 매일 08:00 KST 시작, 최대 6시간 소요 (~14:00 종료)
  - KR daily: 매일 19:00 KST 시작, 최대 30분 소요 (~19:30 종료)

> 비어 있는 항목은 처음 운영 환경 작업할 때 채워넣고 commit한다.

---

## 큐 운영 규칙

1. **새 항목은 "대기" 섹션 맨 위에 추가**. 형식은 Q-001을 템플릿으로 사용.
2. **위험도** 표시: 낮음(코드만, DB 무관) / 중간(DB 변경, 롤백 가능) / 높음(데이터 손실 가능, 백업 필수).
3. **타이밍 윈도우** 명시: cron 충돌 시간을 피해야 하는 작업은 안전 시각 명시.
4. **완료 후 이동**: 작업 완료 시 항목을 "완료" 섹션으로 이동, 완료일·확인 결과 추가.
5. **삭제 금지**: 완료된 항목도 삭제하지 않음. 운영 이력으로 남김.

---

## 대기 중인 작업

(현재 대기 중인 항목 없음. Q-002, Q-003은 Phase 1 1.1·1.3 단계에서 정식 등록 예정 — `_meta/phases/phase1_brief.md` §4.4, §8.7 참조.)

---

## 완료된 작업

### Q-001: P0.5 마이그레이션 적용 ✅ (등록: 2026-04-24, 완료: 2026-04-26)

**관련 commit**: `phase0_5/screener-refactor` 머지 commit (`410b5ac feat(screener): add conditions_met JSON per ADR-009 (P0.5)`)  
**관련 ADR**: ADR-009 (스크리너 개편 + `conditions_met` 컬럼 추가)  
**적용 일시**: 2026-04-26 18:18 KST (일요일)  
**적용 시점 HEAD**: `af28f9f docs(meta): add ADR-011 (Phase 1 CLI backend with conditional exception)`  
**적용 방식**: `docker exec -i mysql-standalone-mysql mysql -u root ...` (호스트 mysql 클라이언트 부재로 컨테이너 내부 실행)  
**자격증명**: `.env`의 `MYSQL_ROOT_PASSWORD` 사용  
**백업**: 생략 (사용자 지시, ADD COLUMN ... NULL의 멱등성 신뢰)  
**적용 소요**: 1.5초 (MySQL 8.4.8 INSTANT ADD COLUMN)

**검증 결과**:
- ✅ DESCRIBE 검증: KR/US 두 테이블 모두 `conditions_met JSON` 컬럼 확인
  - 위치: `AFTER is_blue_dot`
  - 타입: json, NULL 허용
  - COMMENT: `"ADR-009: per-condition pass/fail map"`
- ✅ ALTER 중 cron 충돌: 없음 (일요일이라 영향 cron 없음)
- ⏳ 추가 검증 (예정): 다음 KR/US daily cron 실행 후 `conditions_met` JSON에 8개 키가 채워지는지 확인 (별도 시점 검증 — Phase 1 1.1 단계 시작 직전)

**작업 환경**:
- PROD (Windows + PowerShell)
- DB: `mysql-standalone-mysql` Docker 컨테이너 (MySQL 8.4.8)

**메모**:
- Alembic은 이번에 다루지 않음. ADR-010 §5에 따라 운영 환경에 `alembic_version` 테이블 미생성. DEV·PROD `alembic_version` 동기화는 추후 별도 큐 항목으로 다룸.

---

*이 문서는 ADR-010이 정의하는 큐 운영 절차의 SSoT다.*