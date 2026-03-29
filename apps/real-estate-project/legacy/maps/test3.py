import folium
from geopy.geocoders import Nominatim
from folium.features import DivIcon

def create_map_with_address(address, display_text=None, output_filename="map.html"):
    """
    주어진 주소를 기반으로 지도에 마커와 텍스트를 표시하고 HTML 파일로 저장합니다.

    Args:
        address (str): 지도에 표시할 주소.
        display_text (str, optional): 좌표 위에 표시할 텍스트. Defaults to None.
        output_filename (str): 저장할 HTML 파일 이름.
    """
    try:
        # Nominatim을 사용하여 주소를 위도와 경도로 변환합니다. (지오코딩)
        # user_agent는 애플리케이션 식별을 위한 필수 값입니다.
        geolocator = Nominatim(user_agent="my-geocoder-app")
        location = geolocator.geocode(address)

        if location:
            # 주소 변환에 성공한 경우
            lat, lon = location.latitude, location.longitude
            print(f"'{address}'의 좌표는 (위도: {lat}, 경도: {lon}) 입니다.")

            # 해당 좌표를 중심으로 하는 folium 지도 객체 생성
            m = folium.Map(
                location=[lat, lon],
                zoom_start=17 # zoom_start는 확대 레벨
            )

            # 1. 항상 기본 마커(핀)를 먼저 추가합니다.
            folium.Marker(
                [lat, lon],
                popup=f"<i>{address}</i>",
                tooltip=address
            ).add_to(m)

            # 2. 표시할 텍스트가 있는 경우, 마커 위에 텍스트를 추가로 표시합니다.
            if display_text:
                folium.Marker(
                    location=[lat, lon],
                    icon=DivIcon(
                        icon_size=(150, 36),
                        icon_anchor=(75, 18), # 앵커를 아이콘의 정중앙으로 설정하여 핀의 위치와 정확히 겹치게 합니다.
                        # HTML 스타일에 text-align: center를 추가하여 텍스트를 중앙 정렬합니다.
                        html=f'<div style="width: 150px; text-align: center; font-size: 16pt; font-weight: bold; color: #E63462; text-shadow: 1px 1px 2px white;">{display_text}</div>'
                    )
                ).add_to(m)

            # 지도를 HTML 파일로 저장
            m.save(output_filename)
            print(f"'{output_filename}' 파일이 성공적으로 생성되었습니다. 파일을 열어 확인해보세요.")

        else:
            # 주소 변환에 실패한 경우
            print(f"오류: '{address}' 주소를 찾을 수 없습니다. 주소를 다시 확인해주세요.")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")


# --- 코드 실행 ---
# 지도에 표시하고 싶은 주소와 그 위에 나타낼 텍스트를 입력합니다.
target_address = "서울특별시 강남구 논현동 67-20"
create_map_with_address(target_address, display_text="20%")

# 텍스트 없이 마커만 표시하고 싶다면 아래처럼 호출하면 됩니다.
# create_map_with_address("부산광역시 해운대구 우동")
