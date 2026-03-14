# CODEOWNERS 초안

아래는 적용 제안안이다. 실제 GitHub 사용자/팀 핸들을 확정한 뒤 `.github/CODEOWNERS`로 반영한다.

```text
# DB 도메인
db/**                       @<db-owner>

# DataBatcher 앱
apps/ingest-databatcher/**  @<ingest-owner>

# 공통 패키지
packages/**                 @<platform-owner>

# 운영 스크립트/스케줄러
apps/ingest-databatcher/ops/shell/**            @<ops-owner>
scheduler/**                @<ops-owner>
```
