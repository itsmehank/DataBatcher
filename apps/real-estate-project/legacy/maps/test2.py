import folium
from geopy.geocoders import Nominatim

def create_map_with_address(address, output_filename="map.html"):
    """
    주어진 주소를 기반으로 지도에 마커를 표시하고 HTML 파일로 저장합니다.

    Args:
        address (str): 지도에 표시할 주소.
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
            # tiles 파라미터를 사용하여 지도 스타일을 변경할 수 있습니다.
            # - 'OpenStreetMap': 기본값
            # - 'CartoDB positron': 깔끔한 회색톤의 미니멀한 스타일 (추천)
            # - 'CartoDB dark_matter': 어두운 테마의 스타일
            # - 'Stamen Terrain': 지형과 식생이 강조된 스타일
            # - 'Stamen Toner': 흑백의 고대비 스타일
            m = folium.Map(
                location=[lat, lon],
                zoom_start=17, # zoom_start는 확대 레벨
                tiles='CartoDB positron'
            )

            # 해당 위치에 마커 추가
            folium.Marker(
                [lat, lon],
                popup=f"<i>{address}</i>", # 마커를 클릭했을 때 표시될 텍스트
                tooltip="여기에요!" # 마커에 마우스를 올렸을 때 표시될 텍스트
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
# 지도에 표시하고 싶은 주소를 입력합니다.
target_address = "서울특별시 강남구 논현동 67-20"
create_map_with_address(target_address)

# 다른 주소로도 테스트해볼 수 있습니다.
# create_map_with_address("부산광역시 해운대구 우동")
