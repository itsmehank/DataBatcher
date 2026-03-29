#!/usr/bin/env python3
"""
웹 애플리케이션 테스트 스크립트
실제 DB 연결 없이 웹 UI 기능을 테스트합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime
import json
from project_config import get_flask_secret, find_available_port

app = Flask(__name__)
app.secret_key = get_flask_secret()

# 테스트용 더미 데이터
def generate_dummy_data(analysis_type='combined', district_name=None, count=10):
    """테스트용 더미 데이터 생성"""
    dummy_data = []
    
    for i in range(count):
        dummy_data.append({
            'rank': i + 1,
            'sggCd': f'1171{i%10}',
            'umdNm': district_name if district_name else f'테스트동{i+1}',
            'jibun': f'{100+i}-{i%10+1}',
            'buildYear': 2000 + (i % 20),
            'mhouseNm': f'테스트빌딩{i+1}',
            'surge_score': round(50.5 - i * 2.3, 2),
            'reliability_score': 15 - i,
            'latest_trade_ymd': '202408',
            'avg_dealAmount': 50000 + (i * 5000),
            'floor_type': '지상' if i % 2 == 0 else '지하'
        })
    
    return dummy_data

# 서울 구 목록 로드
def load_gu_codes():
    try:
        gu_codes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gu_codes.json')
        with open(gu_codes_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [item['name'] for item in data['seoul_top10_gu_codes']]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return ['송파구', '강남구', '서초구', '용산구', '성동구', '광진구', '마포구', '동작구', '영등포구', '강동구']

@app.route('/')
def index():
    gu_list = load_gu_codes()
    return render_template('index_v2.html', gu_list=gu_list, kakao_js_key='')

@app.route('/combined_analysis', methods=['POST'])
def combined_analysis():
    try:
        data = request.get_json()
        target_ymd = data.get('target_ymd')
        top_percent = float(data.get('top_percent', 1.0))
        analysis_period = int(data.get('analysis_period', 6))
        
        # 날짜 형식 검증
        datetime.strptime(target_ymd, '%Y%m')
        
        print(f"[TEST] Combined Analysis: {target_ymd}, {top_percent}%, {analysis_period}개월")
        
        # 테스트용 더미 데이터 생성
        dummy_results = generate_dummy_data('combined', count=15)
        
        return jsonify({
            'success': True,
            'message': f'[테스트 모드] 총 {len(dummy_results)}개의 급등 후보 건물을 발견했습니다.',
            'data': dummy_results
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': f'날짜 형식이 잘못되었습니다: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'분석 중 오류가 발생했습니다: {str(e)}'})

@app.route('/district_analysis', methods=['POST'])
def district_analysis():
    try:
        data = request.get_json()
        target_ymd = data.get('target_ymd')
        district_name = data.get('district_name')
        top_n = int(data.get('top_n', 10))
        analysis_period = int(data.get('analysis_period', 6))
        
        # 날짜 형식 검증
        datetime.strptime(target_ymd, '%Y%m')
        
        print(f"[TEST] District Analysis: {district_name}, {target_ymd}, {top_n}개, {analysis_period}개월")
        
        # 테스트용 더미 데이터 생성
        dummy_results = generate_dummy_data('district', district_name, count=min(top_n, 20))
        
        return jsonify({
            'success': True,
            'message': f'[테스트 모드] {district_name}에서 총 {len(dummy_results)}개의 급등 후보 건물을 발견했습니다.',
            'data': dummy_results
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': f'날짜 형식이 잘못되었습니다: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'분석 중 오류가 발생했습니다: {str(e)}'})

@app.route('/get_districts', methods=['GET'])
def get_districts():
    """특정 구의 동 목록을 가져오는 API"""
    gu_name = request.args.get('gu') or ''
    
    sample_districts = {
        '송파구': ['송파동', '잠실동', '문정동', '석촌동'],
        '강남구': ['압구정동', '청담동', '신사동', '논현동', '역삼동'],
        '서초구': ['반포동', '서초동', '방배동', '양재동'],
        '용산구': ['한남동', '이태원동', '용산동', '남영동'],
        '성동구': ['성수동', '왕십리동', '행당동', '금호동'],
        '광진구': ['자양동', '구의동', '광장동', '중곡동'],
        '마포구': ['상암동', '합정동', '홍대앞', '연남동'],
        '동작구': ['사당동', '대방동', '신대방동', '상도동'],
        '영등포구': ['여의도동', '당산동', '영등포동', '신길동'],
        '강동구': ['천호동', '성내동', '강일동', '둔촌동']
    }
    
    districts = sample_districts.get(gu_name, [])
    return jsonify({'districts': districts})

@app.route('/health')
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'healthy',
        'message': '웹 애플리케이션이 정상 작동 중입니다.',
        'test_mode': True
    })

if __name__ == '__main__':
    preferred_port = int(os.getenv("RE_WEB_TEST_PORT", "5002"))
    run_port = find_available_port(preferred_port)
    print("="*60)
    print("🚀 부동산 급등 분석 웹 UI 테스트 서버 시작")
    print("="*60)
    print(f"📍 접속 주소: http://localhost:{run_port}")
    print("🔧 테스트 모드: 더미 데이터 사용")
    print("💡 실제 DB 연결 없이 UI 기능을 테스트할 수 있습니다.")
    print("="*60)
    
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=run_port)
