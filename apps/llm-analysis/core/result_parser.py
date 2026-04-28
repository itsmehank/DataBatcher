"""
LLM 응답 → AnalysisResult / EntryParams Pydantic 모델 변환.

Phase 1 1.1.11에서 구현 예정. 본 파일은 골격 단계의 placeholder.
JSON 파싱 실패 시 1회 재시도, 그래도 실패하면 llm_calls.error에 기록.
Pydantic으로 classification 값, confidence 범위, pattern 값,
risk_flags 화이트리스트를 검증한다.
"""
