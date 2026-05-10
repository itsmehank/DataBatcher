# 새 PC 셋업 체크리스트

> 이 문서는 2026-05-05 기준 작성된 임시 가이드다.
> Phase 1.2 완료 후 로컬 PC를 새 기기로 변경하는 시점에 사용한다.
> 셋업 완료 + Phase 1.3 진입 가이드 시작 시점에 본 문서는 삭제하거나 archive로 이동한다.

---

## 사전 준비물 (이전 PC에서 백업했어야 할 것)

다음이 안전한 곳(USB / 1Password / 클라우드)에 있어야 함:

- [ ] `<DataBatcher>/.env` 파일 백업 (DB + KRX 인증 11개 키)
- [ ] `<DataBatcher>/apps/llm-analysis/.env` 파일 백업 (DATABASE_URL + ANTHROPIC_API_KEY)
- [ ] DEV DB dump 파일 (`trade_dump_20260505.sql` 또는 유사명)
- [ ] Anthropic Max 플랜 로그인 정보 (이메일/계정)
- [ ] (선택) `nvst_b6_eval_input.json` — 1.3 진입 후 v1.1 fix 재평가 시 사용
- [ ] (선택) Web Claude의 두 차례 NVST Evaluator 평가 결과 텍스트

위 백업이 누락된 항목 있으면 새 PC 셋업 진행 어려움. 사전 확인 필수.

---

## 새 PC 셋업 단계

### 1. Git clone + 브랜치 checkout

```bash
git clone git@github.com:itsmehank/DataBatcher.git
cd DataBatcher
git checkout phase1/1.2-entry-params

# 검증: 다음 5개 commit이 보여야 함
git log --oneline -5
# 92a8b77 docs(meta): governance drift fix — 6 items (Phase 1.2 → 1.3 prep)
# dd09e2d feat(llm-analysis): Phase 1.2 트랙 B — calculate_entry_params 구현 + B.5.5 검증
# abbaeb2 (이전 commit α — ADR-013 ETF 제외 트랙 A)
# 4cf9c2b (Phase 1.1 거버넌스 인계)
# f0d6f57 (Phase 1.1 (5) analyze_chart v2 lock)
```

### 2. `.env` 파일 2개 복원

백업한 `.env` 파일을 다음 위치에 복사:
- `<DataBatcher>/.env`
- `<DataBatcher>/apps/llm-analysis/.env`

검증:

```bash
ls -la .env apps/llm-analysis/.env
# 둘 다 존재 확인

# 키 존재 확인 (값은 출력 안 함)
grep -c "MYSQL_ROOT_PASSWORD" .env  # 1
grep -c "DATABASE_URL" .env  # 1
grep -c "ANTHROPIC_API_KEY" apps/llm-analysis/.env  # 1
```

### 3. Docker 셋업

```bash
# Docker Desktop 설치 (Mac이면 brew install --cask docker)
# 실행 후
docker-compose up -d

# MySQL 컨테이너 기동 확인
docker ps | grep mysql
# 예상: grafana-with-db-mysql 또는 mysql-standalone-mysql 컨테이너 실행 중
```

만약 docker-compose 파일 위치가 다르면 README.md 또는 CLAUDE.md 참조.

### 4. DEV DB 복원

```bash
# 백업한 dump 파일 import
docker exec -i <컨테이너명> mysql \
  -u root -p"$MYSQL_ROOT_PASSWORD" \
  trade < trade_dump_20260505.sql

# 검증
docker exec <컨테이너명> mysql -u root -p"$MYSQL_ROOT_PASSWORD" \
  -e "USE trade; SHOW TABLES;" | head -20

# 핵심 테이블 행수 확인
docker exec <컨테이너명> mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "
SELECT 'us_stock_prices' AS t, COUNT(*) AS rows FROM trade.us_stock_prices
UNION SELECT 'minervini_screen_results_us', COUNT(*) FROM trade.minervini_screen_results_us
UNION SELECT 'daily_analysis_us', COUNT(*) FROM trade.daily_analysis_us
UNION SELECT 'llm_calls', COUNT(*) FROM trade.llm_calls;"
# 예상: 모두 0이 아닌 값. daily_analysis_us ~369, llm_calls ~441
```

### 5. Python 환경 셋업

```bash
# Python 3.x 설치 확인
python3 --version

# 가상환경 권장
cd apps/llm-analysis
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# 단위 테스트 동작 확인
pytest tests/ -v
# 예상: 98/98 passed (또는 그에 가까운 결과)
```

이외 apps/ingest-databatcher/도 별도 환경 셋업 필요할 수 있음. README.md 참조.

### 6. Claude Code CLI 재로그인 (Max 플랜)

```bash
# Claude Code CLI 설치 (Mac이면 brew install anthropic/tap/claude-code 또는 공식 설치 가이드)
# 설치 후
claude login
# 백업해둔 Anthropic Max 플랜 이메일/계정으로 로그인
```

검증:

```bash
claude --version
# 또는 simple 호출 테스트
echo "hello" | claude --print
```

### 7. 동작 검증 — NVST 단일 종목 dry-run

```bash
cd <DataBatcher>/apps/llm-analysis
python scripts/run_single_symbol.py \
  --symbol NVST --region US --date 2026-01-13 \
  --dry-run

# 예상: 에러 없이 실행. 입력 페이로드 출력 후 종료.
# 만약 DB 연결 에러: .env의 DATABASE_URL 확인
# 만약 데이터 없음 에러: dump import 안 됐을 가능성, Step 4 재확인
```

### 8. 다음 단계 — Phase 1.3 진입

위 1~7 모두 정상이면 1.3 작업 시작 가능 상태.

새 Web Claude 채팅 시작 후 다음 첫 메시지로 1.3 진입 가이드 Architect 세션 시작:

```
이번 세션은 미너비니 반자동 트레이딩 보조 시스템의 Phase 1.3 진입 가이드 작성 (Architect 세션)이다.
역할은 ADR-005가 정의한 "Architect" — _meta/ 거버넌스 문서 + Phase brief 작성/갱신 담당.

## 0. 컨텍스트 복원

먼저 다음 거버넌스 문서를 순서대로 읽어 컨텍스트를 복원하라:

1. _meta/06_CURRENT_STATE.md — 현재 위치 (1.2 게이트 통과, 1.3 진입 대기)
2. _meta/00_CONSTITUTION.md — 절대 원칙
3. _meta/04_DECISIONS.md — ADR-001~013 (특히 ADR-009/011/012/013)
4. _meta/05_GLOSSARY.md — Part B.1.7, Part B.2 (entry_params 13필드, risk_flags 12 taxonomy)
5. _meta/phases/phase1_brief.md — Phase 1 SSoT, 특히 §3.3 (1.3 단계), §6.3 v1 lock 결과 + v1.1 fix, §8 배치 통합, §9.1 1.3 게이트, §11.4-bis 실제 발견 이슈
6. _meta/phases/phase1_progress.md — 1.1 + 1.2 트랙 A·B 진행 기록 (B.5.5 결과 포함)
7. _meta/operational_queue.md — Q-002 상태

## 1. 작업 목적

Phase 1.3 진입 가이드 작성. 산출물:
(a) 1.3 단계 Builder 인계 프롬프트 (개발 환경 Mac에서 새 Claude Code 세션이 첫 메시지로 사용할 텍스트)
(b) Q-003 운영 큐 항목 텍스트 초안 (Builder가 phase1_progress.md에 기록 후 Architect가 operational_queue.md에 정식 등록)

## 2. 1.3 단계 작업 범위 (요약)

phase1_brief §3.3의 1.3.1~1.3.11 + 신규 추가 작업:
- 신규 1.3.0: (6) v1.1 fix 3가지 (06_CURRENT_STATE §L, brief §6.3 §4, brief §11.4-bis.2)
- 1.3.1~1.3.8: run_daily_analysis.py + 모니터링 4종 (ADR-012 §3) + Task Scheduler 등록
- 1.3.9~1.3.11: 7거래일 누적 + 사용자 검토 + Phase 1 종료 게이트 평가

## 3. 시작

지금 Step 0 (컨텍스트 복원)부터 시작하라.
완료 후 1.3 진입 가이드 작성 방향성을 사용자에게 확인 후 진행하라.
```

---

## 문제 발생 시 트러블슈팅

### Git clone에서 SSH 인증 실패

```bash
# SSH 키 새 PC에서 생성 + GitHub에 등록
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub
# GitHub Settings → SSH and GPG keys에 추가
```

또는 HTTPS 사용:

```bash
git clone https://github.com/itsmehank/DataBatcher.git
```

### Docker 컨테이너 이름 차이

이전 PC와 새 PC에서 docker-compose가 만드는 컨테이너 이름이 다를 수 있음. 다음으로 확인:

```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```

위 가이드의 `<컨테이너명>`을 실제 이름으로 치환.

### Python 버전 호환성 문제

`apps/llm-analysis/requirements.txt`가 특정 Python 버전 요구하면, 새 PC에서 동일 버전 사용 권장.

```bash
# 이전 PC에서 사용한 버전 확인 (백업 시점에 메모해뒀다면)
# 또는 README.md / pyproject.toml 참조
```

### MySQL dump import 에러

가능한 원인:
- dump 파일이 다른 인코딩 (utf8mb4 vs utf8)
- 컨테이너 내부 MySQL 버전 차이
- ROUTINES/TRIGGERS 권한 문제

대응:
```bash
# dump 파일 인코딩 확인
file trade_dump_20260505.sql

# 권한 부여
docker exec <컨테이너명> mysql -u root -p"$MYSQL_ROOT_PASSWORD" \
  -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';"
```

### Claude Code CLI 로그인 실패

```bash
# 캐시 초기화
claude logout
claude login
```

또는 공식 문서 참조: https://docs.anthropic.com/en/docs/claude-code

### NVST dry-run에서 데이터 없음 에러

DB import가 정상인지 재확인:

```bash
docker exec <컨테이너명> mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "
SELECT date, close, volume FROM trade.us_stock_prices
WHERE symbol='NVST' AND date='2026-01-13';"
# 1행 출력되어야 함
```

---

## 셋업 완료 후

이 문서는 임시 가이드이므로 본 셋업이 완료되고 1.3 작업이 정상 진행되면 다음 중 하나로 처리:

- (a) 삭제 (`git rm new_pc_setup_checklist.md` + commit)
- (b) `_meta/phases/archive/` 같은 디렉토리로 이동 (히스토리 보존)
- (c) 그대로 두고 README에서 참조 (향후 다른 PC 변경 시 재사용)

권고: (a) 또는 (b). 본 가이드는 시점 specific하므로 메인 트리에 오래 두면 stale 가능성.
