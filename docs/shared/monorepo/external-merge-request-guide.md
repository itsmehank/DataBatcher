# 외부 레포 통합 요청 가이드

이 문서는 추후 외부 GitHub 레포를 이 모노레포(`DataBatcher`)의 `apps/` 하위로 통합 요청할 때 사용하는 템플릿이다.

## 요청 시 필수 정보 4가지

아래 4가지를 반드시 함께 전달한다.

1. GitHub 레포 URL
2. 병합 방식
   - `history` (히스토리 보존)
   - `squash` (스쿼시 병합)
3. 목표 경로명
   - 예: `apps/insight-archive`
4. 외부 레포 기본 브랜치
   - 예: `main`, `master`

누락 방지용 추가 권장 정보:

5. 레포 접근 정보
   - 예: `repo_access: public` 또는 `repo_access: private (access granted)`
6. 대상 경로가 이미 존재할 때 정책
   - 예: `target_exists_policy: abort | merge | overwrite`
7. 반영 방식
   - 예: `push_policy: push_to_main | commit_only`

## 복붙용 요청 템플릿

아래 필수 항목(최소 4개)이 없으면 작업이 보류될 수 있다.

```text
외부 프로젝트를 모노레포 하위로 통합해줘.
아래 문서 기준으로 진행해줘:
docs/shared/monorepo/external-project-merge-guide.md

- repo_url: <GitHub URL>
- merge_mode: <history | squash>
- target_path: apps/<project-name>
- source_branch: <main | master | ...>

# optional but recommended
- repo_access: <public | private>
- target_exists_policy: <abort | merge | overwrite>
- push_policy: <push_to_main | commit_only>
```

## 예시

```text
외부 프로젝트를 모노레포 하위로 통합해줘.
아래 문서 기준으로 진행해줘:
docs/shared/monorepo/external-project-merge-guide.md

- repo_url: https://github.com/example/insight-archive.git
- merge_mode: history
- target_path: apps/insight-archive
- source_branch: main
- repo_access: public
- target_exists_policy: abort
- push_policy: commit_only
```

Private 레포 예시:

```text
- repo_url: https://github.com/example/private-repo.git
- merge_mode: squash
- target_path: apps/private-repo
- source_branch: main
- repo_access: private (access granted)
- target_exists_policy: abort
- push_policy: push_to_main
```

## 통합 작업 시 기본 검증 기준

- 외부 코드는 `apps/<project-name>/` 하위에만 위치
- 경로/설정/ops 문서 정합화 완료
- 3307 기반 스모크 테스트 통과
- 기존 `apps/ingest-databatcher` 회귀 스모크 테스트 통과
- 단계별 커밋으로 롤백 가능한 상태
- 통합 작업 종료 시 `git status --short`가 clean
