# Security Policy

## Supported Versions

현재는 `main` 브랜치만 보안 업데이트를 제공합니다.

| Version | Supported |
| ------- | --------- |
| `main`  | Yes |
| others  | No |

## Reporting a Vulnerability

보안 취약점을 발견한 경우 공개 이슈로 바로 올리지 말고 먼저 비공개로 알려주세요.

- GitHub 계정: `itsmehank`
- 권장 방식: GitHub private vulnerability report 또는 비공개 연락
- 포함 정보:
  - 영향 범위
  - 재현 방법
  - 예상되는 위험도
  - 가능하면 최소 재현 예시

## Response Timeline

- 3영업일 이내 접수 확인
- 재현 가능 여부 확인 후 우선순위 분류
- 수정 가능 시 패치 및 공지 준비

## Disclosure Policy

유지관리자가 수정 또는 완화 방안을 준비하기 전까지는 취약점 내용을 공개하지 말아주세요.

## Operational Notes

- 실제 운영 시 Flask 앱은 외부에 직접 노출하지 말고 Nginx 등의 리버스 프록시 뒤에서 실행하세요.
- 모든 DB/API/Flask secret 값은 환경변수로만 주입해야 합니다.
- `deploy.yml` 사용 시 `VM_SSH_KNOWN_HOSTS`, `VM_HOST`, `VM_SSH_KEY` GitHub Secrets가 필요합니다.
