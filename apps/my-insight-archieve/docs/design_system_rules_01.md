# 디자인 시스템 사용 규칙

## 토큰 사용 원칙

- 임의 HEX/px 직접 입력보다 토큰 우선
- 신규 컴포넌트는 기존 scale(4/8/12/16/24/32/48/72/96)에서만 간격 선택
- 색상은 중립 톤 + `--accent` 1색 중심 유지

## 핵심 토큰

- Color: `--bg-primary`, `--bg-secondary`, `--text-primary`, `--text-secondary`, `--accent`
- Radius: `--radius-page-card`, `--radius-card`, `--radius-control`, `--radius-pill`
- Shadow: `--shadow-soft`, `--shadow-hover`
- Layout: `--container-max`

## 컴포넌트 상태표

### Buttons

- default: 포인트 컬러 그라디언트
- hover: `translateY(-1px)` + 미세 밝기 조정
- focus: halo 노출
- disabled: 클릭 불가 + 시각적 비활성 처리

### Cards

- default: soft border + soft shadow
- hover: `translateY(-2px)` + shadow 강조
- empty: 단일 메시지 + 단일 행동 그룹

### Inputs

- default: neutral border
- focus: halo 중심 강조
- error: 텍스트/보더 대비 강화

## 카피 가이드

- 기능 설명형보다 행동 유도형 문장 사용
- 각 화면의 핵심 행동 CTA는 1~2개로 제한
- 한 블록 내 메시지는 2문장 이내 우선

## 반응형 규칙

- Desktop: 3열
- Tablet: 2열
- Mobile: 1열
- Mobile에서 액션 그룹은 세로 정렬
