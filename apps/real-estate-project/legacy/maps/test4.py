import folium
from geopy.geocoders import Nominatim
from folium.features import DivIcon
import time


def create_map_with_multiple_addresses(address_list, value_list, output_filename="map.html"):
    """
    주어진 주소와 값 목록을 기반으로 지도에 여러 개의 마커와 텍스트를 표시합니다.

    Args:
        address_list (list): 지도에 표시할 주소의 목록.
        value_list (list): 각 주소에 매칭하여 표시할 값의 목록.
        output_filename (str): 저장할 HTML 파일 이름.
    """
    if len(address_list) != len(value_list):
        print("오류: 주소 목록과 값 목록의 길이가 다릅니다.")
        return

    geolocator = Nominatim(user_agent="my-multi-geocoder-app")

    locations = []
    for address, value in zip(address_list, value_list):
        try:
            location = geolocator.geocode(address)
            if location:
                locations.append({
                    "address": address,
                    "value": value,
                    "lat": location.latitude,
                    "lon": location.longitude
                })
                print(f"성공: '{address}' -> (위도: {location.latitude}, 경도: {location.longitude})")
            else:
                print(f"실패: '{address}' 주소를 찾을 수 없습니다.")
            # API 요청 제한을 피하기 위해 약간의 지연 시간을 줍니다.
            time.sleep(1)
        except Exception as e:
            print(f"'{address}' 처리 중 오류 발생: {e}")

    if not locations:
        print("유효한 좌표를 하나도 찾지 못했습니다.")
        return

    # 모든 좌표를 포함하는 지도의 중심을 계산합니다.
    avg_lat = sum(loc['lat'] for loc in locations) / len(locations)
    avg_lon = sum(loc['lon'] for loc in locations) / len(locations)

    # 지도 객체 생성
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)

    # 각 위치에 마커와 텍스트 추가
    for loc in locations:
        lat, lon = loc['lat'], loc['lon']

        # 1. 기본 마커(핀) 추가
        folium.Marker(
            [lat, lon],
            popup=f"<i>{loc['address']}</i>",
            tooltip=f"{loc['address']}: {loc['value']}"
        ).add_to(m)

        # 2. 텍스트 추가
        folium.Marker(
            location=[lat, lon],
            icon=DivIcon(
                icon_size=(150, 36),
                icon_anchor=(75, 18),
                html=f'<div style="width: 150px; text-align: center; font-size: 16pt; font-weight: bold; color: #E63462; text-shadow: 1px 1px 2px white;">{loc["value"]}</div>'
            )
        ).add_to(m)

    # 모든 마커가 보이도록 지도 경계를 자동으로 조절
    bounds = [[loc['lat'], loc['lon']] for loc in locations]
    m.fit_bounds(bounds, padding=(50, 50))

    m.save(output_filename)
    print(f"\n'{output_filename}' 파일이 성공적으로 생성되었습니다.")


# --- 코드 실행 ---
# 여러 주소와 값을 리스트 형태로 준비합니다.
target_addresses = [
    "서울특별시 강남구 논현동 67-20",
    "서울특별시청",
    "N서울타워"
]
target_values = ["20%", "55%", "80%"]

# 함수를 호출하여 여러 위치가 표시된 지도를 생성합니다.
create_map_with_multiple_addresses(target_addresses, target_values)
