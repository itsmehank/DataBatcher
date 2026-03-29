# Deprecated Templates

이 디렉토리의 템플릿은 **더 이상 라우트에서 사용되지 않습니다.**
향후 참고 또는 재사용 가능성을 위해 코드상으로만 보관합니다.

## 보관된 파일

### `index_v2.html`
- **역할**: 이전 메인 화면 (v2 디자인)
- **교체 시점**: 2026-03-19
- **교체 대상**: `index_console.html` (console 디자인이 기본 메인으로 승격)
- **특징**: 740줄 자체 완결형 템플릿. partial을 사용하지 않음.
- **복구 방법**: 이 파일을 `web_ui/templates/`로 이동하고, `web_app.py`의 `render_template("index_console.html", ...)`을 `render_template("index_v2.html", ...)`로 변경

## 주의사항
- 이 디렉토리의 파일은 Flask 라우트에서 참조하지 않습니다.
- 삭제해도 서비스에 영향이 없습니다.
- 수정이 필요한 경우, 먼저 운영 디렉토리(`web_ui/templates/`)로 복사한 뒤 작업하세요.
