# Guide Command Mapping (Monorepo)

작성일: 2026-03-14

## 목적

`apps/ingest-databatcher/docs/guides` 및 `apps/ingest-databatcher/docs/windows_scheduler_guide.md`에 남아있던 구경로 명령을 모노레포 경로로 통일하기 위한 매핑 기준.

## 적용 범위

- `apps/ingest-databatcher/docs/windows_scheduler_guide.md`
- `apps/ingest-databatcher/docs/guides/*.md`

초기 추출 건수(구경로 패턴): 410건

## 매핑 규칙

| 이전 | 변경 |
|---|---|
| `python scripts/<x>.py` | `python apps/ingest-databatcher/scripts/<x>.py` |
| `` `scripts/<x>.py` `` | `` `apps/ingest-databatcher/scripts/<x>.py` `` |
| `config/settings.yaml` | `apps/ingest-databatcher/config/settings.yaml` |
| `config/settings.dev.yaml` | `apps/ingest-databatcher/config/settings.dev.yaml` |
| `shell_scripts/<x>.sh` | `apps/ingest-databatcher/ops/shell/<x>.sh` |
| `scheduler/windows/<x>.ps1` | `apps/ingest-databatcher/ops/scheduler/windows/<x>.ps1` |

## 검증 기준

다음 패턴은 대상 문서에서 0건이어야 함:

```bash
rg -n 'python scripts/|`scripts/|bash shell_scripts/|config/settings.yaml|config/settings.dev.yaml' apps/ingest-databatcher/docs/windows_scheduler_guide.md apps/ingest-databatcher/docs/guides
```

참고:

- `apps/ingest-databatcher/ops/scheduler/windows/...`는 신규 경로이므로 검색에 잡혀도 정상이다.
