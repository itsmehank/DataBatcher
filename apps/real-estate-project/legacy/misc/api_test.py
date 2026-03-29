import requests
from project_config import get_env_str


def test_api_call(api_key, lawd_cd, deal_ymd):
    """
    주어진 파라미터로 국토교통부 연립다세대 매매 실거래가 API를 호출하고
    원본 XML 응답을 출력합니다.
    """
    base_url = "http://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"

    params = {
        'serviceKey': api_key,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'numOfRows': '100'  # 테스트용으로 적당한 개수 설정
    }

    print(f"--- API 요청 시작 ---")
    print(f"요청 URL (파라미터 포함): {requests.Request('GET', base_url, params=params).prepare().url}")
    print("---------------------\n")

    try:
        response = requests.get(base_url, params=params, timeout=10)

        print(f"HTTP Status Code: {response.status_code}\n")

        # 인코딩을 UTF-8로 명시적으로 설정하여 한글 깨짐 방지
        response.encoding = 'utf-8'

        print("--- API 원본 응답 (XML) ---")
        print(response.text)
        print("--------------------------")

    except requests.exceptions.RequestException as e:
        print(f"API 호출 중 네트워크 오류 발생: {e}")


if __name__ == '__main__':
    # --- 설정 ---
    # 사용하시는 API 키와 테스트할 지역/년월을 입력하세요.
    API_SERVICE_KEY = get_env_str("RE_API_SERVICE_KEY", "")
    TEST_LAWD_CD = '11110'  # 예: 서울시 종로구
    TEST_DEAL_YMD = '202401'  # 예: 2024년 1월

    if not API_SERVICE_KEY:
        raise ValueError("RE_API_SERVICE_KEY 환경 변수가 필요합니다.")

    test_api_call(api_key=API_SERVICE_KEY, lawd_cd=TEST_LAWD_CD, deal_ymd=TEST_DEAL_YMD)
