# Public Release Checklist

이 문서는 RealEstateProject를 공개 리포지토리 또는 공개 도메인 서비스로 전환하기 전 최종 점검 항목을 정리합니다.

## 1. Secrets and Credentials

- [ ] `.env` 파일이 git에 추적되지 않는다.
- [ ] 실제 DB 비밀번호, API 키, Flask secret이 코드/문서에 하드코딩되어 있지 않다.
- [ ] VM의 운영용 `.env`는 서버에만 존재하고 저장소에는 없다.

## 2. Runtime Safety

- [ ] Flask 앱이 `127.0.0.1:5001`에만 바인딩된다.
- [ ] 외부 트래픽은 Nginx 리버스 프록시를 통해 전달된다.
- [ ] `FLASK_DEBUG=0` 상태에서 운영한다.
- [ ] `RE_FLASK_SECRET`가 충분히 긴 랜덤 문자열로 설정되어 있다.

## 3. Database

- [ ] `python -m src.real_estate.cli validate-config --require-api-key` 성공
- [ ] required tables exist in `real_estate` (bootstrap or DBA manual apply completed)
- [ ] `db/init/03_real_estate_schema.sql`이 최신 스키마와 일치한다.
- [ ] 운영 DB 계정은 최소 권한 원칙을 따른다.

## 4. Tests and Verification

- [ ] `pytest -q tests -m "not db"` 통과
- [ ] `python -m py_compile src/real_estate/cli.py` 통과
- [ ] `python -m py_compile src/real_estate/backend/web_app.py` 통과
- [ ] 메인 화면(`/`)과 별칭(`/v2`)이 정상 응답한다.

## 5. Dependency and CI Security

- [ ] `requirements.txt`와 `web_ui/requirements.txt`가 최신 상태다.

## 6. Documents and Community Readiness

- [ ] `LICENSE`가 존재한다.
- [ ] `SECURITY.md`가 존재한다.
- [ ] `README.md`에 Nginx + Flask 배포 구조가 반영되어 있다.
- [ ] 운영 절차는 `docs/operations_runbook.md`와 일치한다.

## 7. Deployment

- [ ] 배포 후 `http://127.0.0.1:5001/` 응답 검증이 포함되어 있다.
- [ ] VM cron 또는 배포 스크립트가 `scripts/collect_daily.sh`를 등록한다.

## 8. Nice to Have

- [ ] Nginx 설정 파일이 `ops/nginx/real-estate.conf` 기준과 일치한다.
- [ ] `logs/` 디렉토리 보관 정책이 운영 정책과 맞는다.
- [ ] 장애 대응 절차를 운영 담당자가 공유받았다.
