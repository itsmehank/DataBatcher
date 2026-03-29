import folium
from geopy.geocoders import Nominatim
from folium.features import DivIcon
import time
import os


def get_color_for_value(value):
    """
    주어진 값의 크기에 따라 다른 색상 코드를 반환합니다.
    - 0~10: 파랑
    - 10~15: 보라
    - 15~20: 주황
    - 20 이상: 빨강
    """
    if value < 10:
        return "#007BFF"  # 파랑 계열
    elif 10 <= value < 15:
        return "#6F42C1"  # 보라 계열
    elif 15 <= value < 20:
        return "#FD7E14"  # 주황 계열
    else:  # 20 이상
        return "#DC3545"  # 빨강 계열


def build_address_from_code(bjd_code, dong_name, jibun):
    """
    법정동 코드, 동명칭, 지번을 조합하여 전체 주소 문자열을 생성합니다.
    (현재 서울특별시의 일부 법정동 코드만 지원합니다.)

    Args:
        bjd_code (str): 5자리의 법정동 코드 (예: "11710" for 송파구).
        dong_name (str): 동 이름 (예: "송파동").
        jibun (str): 지번 (예: "94-5").

    Returns:
        str: 완성된 전체 주소 문자열 또는 None.
    """
    seoul_gu_codes = {
        # 서울특별시 법정동 코드 -> 구 이름 매핑
        "11110": "종로구", "11140": "중구", "11170": "용산구", "11200": "성동구", "11215": "광진구",
        "11230": "동대문구", "11260": "중랑구", "11290": "성북구", "11305": "강북구", "11320": "도봉구",
        "11350": "노원구", "11380": "은평구", "11410": "서대문구", "11440": "마포구", "11470": "양천구",
        "11500": "강서구", "11530": "구로구", "11545": "금천구", "11560": "영등포구", "11590": "동작구",
        "11620": "관악구", "11650": "서초구", "11680": "강남구", "11710": "송파구", "11740": "강동구",
    }

    gu_name = seoul_gu_codes.get(bjd_code)

    if gu_name:
        full_address = f"서울특별시 {gu_name} {dong_name} {jibun}"
        print(f"주소 생성 성공: {full_address}")
        return full_address
    else:
        print(f"오류: 지원하지 않는 법정동 코드('{bjd_code}')입니다.")
        return None


def create_map_with_multiple_addresses(address_list, value_list, output_dir=".", output_filename="map.html"):
    """
    주어진 주소와 값 목록을 기반으로 지도에 여러 개의 마커와 텍스트를 표시합니다.
    값의 크기에 따라 텍스트 색상이 변경됩니다.

    Args:
        address_list (list): 지도에 표시할 주소의 목록.
        value_list (list): 각 주소에 매칭하여 표시할 숫자 값의 목록.
        output_dir (str): HTML 파일을 저장할 디렉토리 경로.
        output_filename (str): 저장할 HTML 파일 이름.
    """
    if len(address_list) != len(value_list):
        print("오류: 주소 목록과 값 목록의 길이가 다릅니다.")
        return

    # 출력 디렉토리가 없으면 생성합니다.
    os.makedirs(output_dir, exist_ok=True)

    # 전체 파일 경로를 조합합니다.
    full_path = os.path.join(output_dir, output_filename)

    # 파일이 이미 존재하면 삭제합니다.
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            print(f"기존 파일 삭제: {full_path}")
        except OSError as e:
            print(f"오류: 기존 파일({full_path})을 삭제할 수 없습니다. - {e}")
            return

    geolocator = Nominatim(user_agent="my-multi-geocoder-app-color")

    locations = []
    for address, value in zip(address_list, value_list):
        try:
            if address is None:
                continue
            location = geolocator.geocode(address)
            if location:
                locations.append({
                    "address": address, "value": value,
                    "lat": location.latitude, "lon": location.longitude
                })
                print(f"좌표 변환 성공: '{address}' -> (위도: {location.latitude}, 경도: {location.longitude})")
            else:
                print(f"좌표 변환 실패: '{address}' 주소를 찾을 수 없습니다.")
            time.sleep(1)
        except Exception as e:
            print(f"'{address}' 처리 중 오류 발생: {e}")

    if not locations:
        print("유효한 좌표를 하나도 찾지 못했습니다.")
        return

    m = folium.Map(location=[37.5665, 126.9780], zoom_start=12)

    for loc in locations:
        lat, lon, value = loc['lat'], loc['lon'], loc['value']

        folium.Marker(
            [lat, lon],
            popup=f"<i>{loc['address']}</i>",
            tooltip=f"{loc['address']}: {value:.1f}%"
        ).add_to(m)

        color = get_color_for_value(value)
        display_text = f"{value:.1f}%"

        folium.Marker(
            location=[lat, lon],
            icon=DivIcon(
                icon_size=(150, 36),
                icon_anchor=(75, 18),
                html=f'<div style="width: 150px; text-align: center; font-size: 16pt; font-weight: bold; color: {color}; text-shadow: 1px 1px 2px white;">{display_text}</div>'
            )
        ).add_to(m)

    bounds = [[loc['lat'], loc['lon']] for loc in locations]
    if bounds:
        m.fit_bounds(bounds, padding=(50, 50))

    m.save(full_path)
    print(f"\n'{full_path}' 파일이 성공적으로 생성되었습니다.")


# --- 코드 실행 ---
# 1. 법정동 코드로부터 주소 생성 (예시)
built_address = build_address_from_code("11710", "송파동", "94-5")

# 2. 여러 주소와 값을 리스트 형태로 준비
target_addresses = [
    "서울특별시 강남구 논현동 67-20",  # 25.5 -> 빨강
    "서울특별시청",  # 18.2 -> 주황
    built_address,  # 12.0 -> 보라
    "서울특별시 노원구 상계동"  # 7.8 -> 파랑
]
target_values = [25.5, 18.2, 12.0, 7.8]

# 3. 함수를 호출하여 여러 위치가 표시된 지도를 생성
# 예: 'maps' 라는 폴더에 'seoul_map.html' 이라는 이름으로 저장
create_map_with_multiple_addresses(target_addresses, target_values, output_dir="maps", output_filename="seoul_map.html")
