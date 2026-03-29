import json
import os
from pathlib import Path

import folium
import requests
from folium.features import DivIcon

try:
    from project_config import get_env_str
except ImportError:
    def get_env_str(name, default=""):
        value = os.getenv(name)
        if value is None:
            return default
        return value

def _resolve_kakao_rest_api_key():
    primary = get_env_str("KAKAO_REST_API_KEY", "").strip()
    if primary:
        return primary
    return get_env_str("KAKAO_API_KEY", "").strip()


def _cache_file_path(cache_path=None):
    if cache_path:
        return Path(cache_path)
    default_path = get_env_str("KAKAO_COORD_CACHE_FILE", "")
    if default_path:
        return Path(default_path)
    project_root = Path(__file__).resolve().parents[1]
    return project_root / "map_images" / "kakao_geocode_cache.json"


def _load_coord_cache(cache_path=None):
    path = _cache_file_path(cache_path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_coord_cache(cache_data, cache_path=None):
    path = _cache_file_path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def get_kakao_coords(address, cache_data=None):
    """
    카카오 로컬 API를 사용하여 주소를 좌표(위도, 경도)로 변환합니다.
    """
    if cache_data is not None and address in cache_data:
        cached = cache_data.get(address) or {}
        lat = cached.get("lat")
        lon = cached.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)

    kakao_rest_api_key = _resolve_kakao_rest_api_key()
    if not kakao_rest_api_key:
        print("KAKAO_REST_API_KEY 환경 변수가 설정되지 않았습니다.")
        return None, None

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {kakao_rest_api_key}"}
    params = {"query": address}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # 200 OK가 아닐 경우 에러 발생
        result = response.json()

        if result.get('documents'):
            # 검색 결과가 있으면 첫 번째 결과의 좌표를 반환
            first_doc = result['documents'][0]
            lat = float(first_doc['y'])
            lon = float(first_doc['x'])
            if cache_data is not None:
                cache_data[address] = {"lat": lat, "lon": lon}
            return lat, lon
        else:
            # 결과가 없으면 None을 반환
            return None, None

    except requests.exceptions.RequestException as e:
        print(f"Kakao API 요청 중 오류 발생: {e}")
        return None, None
    except (KeyError, IndexError, ValueError) as e:
        print(f"Kakao API 응답 파싱 중 오류 발생: {e}")
        return None, None


def get_color_for_value(value):
    """
    주어진 값의 크기에 따라 다른 색상 코드를 반환합니다.
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
    """
    seoul_gu_codes = {
        "11110": "종로구", "11140": "중구", "11170": "용산구", "11200": "성동구", "11215": "광진구",
        "11230": "동대문구", "11260": "중랑구", "11290": "성북구", "11305": "강북구", "11320": "도봉구",
        "11350": "노원구", "11380": "은평구", "11410": "서대문구", "11440": "마포구", "11470": "양천구",
        "11500": "강서구", "11530": "구로구", "11545": "금천구", "11560": "영등포구", "11590": "동작구",
        "11620": "관악구", "11650": "서초구", "11680": "강남구", "11710": "송파구", "11740": "강동구",
    }
    code = ""
    if bjd_code is not None:
        raw = str(bjd_code).strip()
        if raw:
            try:
                code = str(int(float(raw)))
            except (TypeError, ValueError):
                code = raw
    gu_name = seoul_gu_codes.get(code)
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
    """
    if len(address_list) != len(value_list):
        print("오류: 주소 목록과 값 목록의 길이가 다릅니다.")
        return False

    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, output_filename)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            print(f"기존 파일 삭제: {full_path}")
        except OSError as e:
            print(f"오류: 기존 파일({full_path})을 삭제할 수 없습니다. - {e}")
            return False

    cache_data = _load_coord_cache()
    cache_changed = False

    locations = []
    for address, value in zip(address_list, value_list):
        if address is None:
            continue

        # 카카오 API를 사용하여 좌표 변환
        had_cache = address in cache_data
        lat, lon = get_kakao_coords(address, cache_data=cache_data)

        if lat is not None and lon is not None:
            locations.append({
                "address": address, "value": value,
                "lat": lat, "lon": lon
            })
            print(f"좌표 변환 성공: '{address}' -> (위도: {lat}, 경도: {lon})")
            if not had_cache:
                cache_changed = True
        else:
            print(f"좌표 변환 실패: '{address}' 주소를 찾을 수 없습니다.")

    if not locations:
        print("유효한 좌표를 하나도 찾지 못했습니다.")
        return False

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

    if cache_changed:
        _save_coord_cache(cache_data)

    return True


def enrich_records_with_coords(records, limit=None):
    if not records:
        return []

    max_count = len(records) if limit is None else min(limit, len(records))
    cache_data = _load_coord_cache()
    cache_changed = False

    enriched = []
    success_count = 0
    for index, record in enumerate(records):
        updated = dict(record)
        if index < max_count:
            address = build_address_from_code(updated.get("sggCd"), updated.get("umdNm"), updated.get("jibun"))
            if address:
                had_cache = address in cache_data
                lat, lon = get_kakao_coords(address, cache_data=cache_data)
                if lat is not None and lon is not None:
                    updated["lat"] = round(float(lat), 7)
                    updated["lng"] = round(float(lon), 7)
                    updated["address"] = address
                    success_count += 1
                    if not had_cache:
                        cache_changed = True
        enriched.append(updated)

    if cache_changed:
        _save_coord_cache(cache_data)

    print(f"좌표 보강 완료: 대상 {max_count}건 중 성공 {success_count}건")

    return enriched


# # --- 코드 실행 ---
# # 1. 테스트할 여러 주소와 값을 리스트 형태로 준비
# target_addresses = [
#     "서울특별시 강남구 논현동 67-20",
#     "서울특별시청",
#     "서울특별시 송파구 송파동 94-5",
#     "서울특별시 송파구 송파동 176-8"  # 이전에는 위 주소와 동일 좌표였음
# ]
# target_values = [25.5, 18.2, 12.0, 7.8]
#
# # 2. 함수를 호출하여 여러 위치가 표시된 지도를 생성
# create_map_with_multiple_addresses(target_addresses, target_values, output_dir="maps_kakao",
#                                    output_filename="seoul_map_kakao.html")
