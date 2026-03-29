# 웹 페이지에 요청을 보내기 위한 'requests' 라이브러리를 가져옵니다.
import requests

# 내용을 가져오고 싶은 웹 페이지의 주소를 변수에 저장합니다.
url = "https://www.disco.re/"

try:
    # 지정된 URL에 GET 요청을 보냅니다.
    response = requests.get(url)

    # 요청이 성공했는지 확인합니다. (상태 코드가 200이 아니면 오류를 발생시킵니다)
    response.raise_for_status()

    # 요청이 성공했다면, 페이지의 전체 HTML 내용을 가져와서 출력합니다.
    print("===== 페이지 내용 가져오기 성공! =====")
    print(response.text)
    print("=======================================")

except requests.exceptions.RequestException as e:
    # 네트워크 문제, 잘못된 URL 등 요청 중에 오류가 발생하면 메시지를 출력합니다.
    print(f"오류가 발생했습니다: {e}")

