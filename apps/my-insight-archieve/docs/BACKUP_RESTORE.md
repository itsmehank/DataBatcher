# Backup / Restore

## Backup 정책

- 엔드포인트: `POST /api/admin/backup/export`
- 관리자 인증 필수
- 백업 파일 위치: `backups/latest.archive.gz`
- 항상 최신 파일 1개만 유지

## Backup 동작

1. 백업 동시 실행 lock 확인
2. MongoDB 전체 컬렉션 데이터를 export
3. 임시 파일 생성 성공 시 기존 최신 파일 제거
4. 임시 파일을 `latest.archive.gz`로 교체
5. 실행 결과를 상태로 기록

## Restore 절차

현재 구현은 export 중심입니다. 복구는 수동 스크립트 또는 운영 도구를 통해 수행합니다.

권장 복구 절차:

1. 서비스 중지
2. `latest.archive.gz` 압축 해제
3. 컬렉션 단위 JSON 데이터를 MongoDB로 import
4. 서비스 재시작
5. 주요 API 헬스체크

운영 환경에서는 복구 자동화 스크립트를 별도로 관리하는 것을 권장합니다.
