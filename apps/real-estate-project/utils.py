import json


def load_json_to_dict(file_path):
    """
    지정된 경로의 JSON 파일을 읽어 파이썬 딕셔너리 객체로 변환합니다.

    Args:
      file_path (str): 읽어올 JSON 파일의 경로.

    Returns:
      dict: JSON 파일의 내용이 변환된 딕셔너리.
            파일이 존재하지 않거나 JSON 형식이 아닐 경우 None을 반환합니다.
    """
    try:
        # 'utf-8' 인코딩으로 파일을 엽니다 (한글 깨짐 방지).
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print(f"오류: '{file_path}' 파일이 올바른 JSON 형식이 아닙니다.")
        return None

if __name__ == "__main__":
    json_file_path = "./gu_codes.json"
    gu_code_data = load_json_to_dict(json_file_path)
    print(f"type(gu_code_data): {type(gu_code_data)}")
    print(f"gu_code_data: {gu_code_data}")

    if gu_code_data:
        print("JSON 파일을 성공적으로 불러왔습니다.")
        print("데이터 타입:", type(gu_code_data))
        print("-" * 20)
        for item in gu_code_data.get("seoul_top10_gu_codes", []):
            rank = item.get("rank")
            name = item.get("name")
            code = item.get("code")
            print(f"순위: {rank}, 이름: {name}, 코드: {code}")
