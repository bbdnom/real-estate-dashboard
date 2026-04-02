import os
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
import pandas as pd
from PublicDataReader import TransactionPrice, Kbland
import PublicDataReader as pdr
import json
import requests as req
from datetime import datetime
import xmltodict

load_dotenv()

app = Flask(__name__, static_folder='client/dist', static_url_path='')

# API 키
DATA_GO_KR_KEY = os.getenv('DATA_GO_KR_KEY')
VWORLD_KEY = os.getenv('VWORLD_KEY')

# PublicDataReader 인스턴스 (KB는 키 불필요)
kb = Kbland()

# 실거래가 직접 호출용 엔드포인트 (구버전 = 승인됨)
TRADE_URLS = {
    ('아파트', '매매'): 'http://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade',
    ('아파트', '전월세'): 'http://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent',
    ('오피스텔', '매매'): 'http://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade',
    ('오피스텔', '전월세'): 'http://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent',
    ('연립다세대', '매매'): 'http://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade',
    ('연립다세대', '전월세'): 'http://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent',
    ('단독다가구', '매매'): 'http://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade',
    ('단독다가구', '전월세'): 'http://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent',
}


def fetch_trades_direct(property_type, trade_type, sigungu_code, year_month):
    """공공데이터 실거래가 직접 호출 (구버전 엔드포인트)"""
    url = TRADE_URLS.get((property_type, trade_type))
    if not url:
        return []

    params = {
        'serviceKey': DATA_GO_KR_KEY,
        'LAWD_CD': sigungu_code,
        'DEAL_YMD': year_month,
        'pageNo': '1',
        'numOfRows': '1000'
    }
    resp = req.get(url, params=params)
    if resp.status_code != 200:
        return {'error': f'API 응답 {resp.status_code}'}

    data = xmltodict.parse(resp.text)
    body = data.get('response', {}).get('body', {})
    items = body.get('items', {})
    if not items:
        return []
    item_list = items.get('item', [])
    if isinstance(item_list, dict):
        item_list = [item_list]
    return item_list

# 법정동코드 캐시
code_bdong = pdr.code_bdong()


@app.route('/')
def index():
    return send_from_directory('client/dist', 'index.html')


@app.route('/api/codes/sigungu')
def get_sigungu_codes():
    """시군구 코드 목록 반환"""
    codes = code_bdong[code_bdong['법정동코드'].str.len() == 10].copy()
    codes['시군구코드'] = codes['법정동코드'].str[:5]
    codes['시군구명'] = codes['시도명'] + ' ' + codes['시군구명']
    result = codes[['시군구코드', '시군구명']].drop_duplicates().sort_values('시군구명')
    return jsonify(result.to_dict('records'))


@app.route('/api/codes/dong')
def get_dong_codes():
    """법정동 코드 목록 반환 (시군구코드 필터)"""
    sigungu = request.args.get('sigungu', '')
    if not sigungu:
        return jsonify([])
    filtered = code_bdong[
        (code_bdong['법정동코드'].str[:5] == sigungu) &
        (code_bdong['법정동코드'].str.len() == 10)
    ].copy()
    result = filtered[['법정동코드', '읍면동명']].drop_duplicates().sort_values('읍면동명')
    return jsonify(result.to_dict('records'))


@app.route('/api/codes/search')
def search_codes():
    """통합 지역 검색 — 시군구+읍면동 한번에 검색"""
    q = request.args.get('q', '').strip()
    if not q or len(q) < 1:
        return jsonify([])

    codes = code_bdong[code_bdong['법정동코드'].str.len() == 10].copy()
    codes['시군구코드'] = codes['법정동코드'].str[:5]
    codes['전체명'] = codes['시도명'].str.strip() + ' ' + codes['시군구명'].str.strip() + ' ' + codes['읍면동명'].str.strip()

    matched = codes[codes['전체명'].str.contains(q, na=False)]
    result = matched[['시군구코드', '전체명', '읍면동명']].drop_duplicates().head(30)
    return jsonify(result.rename(columns={'시군구코드': 'sigungu', '전체명': 'fullName', '읍면동명': 'dong'}).to_dict('records'))


@app.route('/api/trades')
def get_trades():
    """실거래가 조회 (단일 월)"""
    property_type = request.args.get('property_type', '아파트')
    trade_type = request.args.get('trade_type', '매매')
    sigungu = request.args.get('sigungu', '11680')
    year_month = request.args.get('year_month', datetime.now().strftime('%Y%m'))

    try:
        result = fetch_trades_direct(property_type, trade_type, sigungu, year_month)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades/range')
def get_trades_range():
    """기간별 실거래가 조회"""
    property_type = request.args.get('property_type', '아파트')
    trade_type = request.args.get('trade_type', '매매')
    sigungu = request.args.get('sigungu', '11680')
    start = request.args.get('start', '202501')
    end = request.args.get('end', datetime.now().strftime('%Y%m'))

    try:
        all_items = []
        start_y, start_m = int(start[:4]), int(start[4:])
        end_y, end_m = int(end[:4]), int(end[4:])

        y, m = start_y, start_m
        while y * 100 + m <= end_y * 100 + end_m:
            ym = f'{y}{m:02d}'
            result = fetch_trades_direct(property_type, trade_type, sigungu, ym)
            if isinstance(result, list):
                all_items.extend(result)
            m += 1
            if m > 12:
                m = 1
                y += 1

        return jsonify(all_items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/kb/price-index')
def get_kb_price_index():
    """KB 아파트 매매가격지수"""
    region = request.args.get('region', '서울')
    try:
        df = kb.get_average_price(매물종별구분='01', 매매전세코드='01')
        if df is None or df.empty:
            return jsonify([])
        filtered = df[df['지역명'] == region][['날짜', '평균가격']].copy()
        filtered.columns = ['date', 'price']
        filtered['date'] = filtered['date'].astype(str).str[:10]
        filtered = filtered.sort_values('date')
        return jsonify(filtered.to_dict('records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/kb/jeonse-price')
def get_kb_jeonse_price():
    """KB 아파트 전세 평균가격"""
    region = request.args.get('region', '서울')
    try:
        df = kb.get_average_price(매물종별구분='01', 매매전세코드='02')
        if df is None or df.empty:
            return jsonify([])
        filtered = df[df['지역명'] == region][['날짜', '평균가격']].copy()
        filtered.columns = ['date', 'price']
        filtered['date'] = filtered['date'].astype(str).str[:10]
        filtered = filtered.sort_values('date')
        return jsonify(filtered.to_dict('records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/kb/lead50')
def get_kb_lead50():
    """KB 선도아파트 50 지수"""
    try:
        df = kb.get_lead_apartment_50_index()
        if df is None or df.empty:
            return jsonify([])
        df['date'] = df['날짜'].astype(str).str[:10]
        result = df[['date', '선도50지수', '전월대비증감률']].copy()
        result.columns = ['date', 'index', 'change']
        return jsonify(result.to_dict('records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/market')
def get_market_data():
    """시장 지표 (기준금리, 코스피, 코스닥, 환율)"""
    import requests as rq
    data = {}

    # 한국은행 ECOS - 기준금리
    bok_key = os.getenv('BOK_API_KEY')
    try:
        url = f'https://ecos.bok.or.kr/api/StatisticSearch/{bok_key}/json/kr/1/1/722Y001/M/202501/202612/0101000'
        r = rq.get(url, timeout=5)
        rows = r.json().get('StatisticSearch', {}).get('row', [])
        if rows:
            data['base_rate'] = {'value': rows[0].get('DATA_VALUE', '-'), 'date': rows[0].get('TIME', '')}
    except:
        data['base_rate'] = {'value': '-', 'date': ''}

    # 환율 (USD/KRW) - ECOS
    try:
        url = f'https://ecos.bok.or.kr/api/StatisticSearch/{bok_key}/json/kr/1/1/731Y001/D/20260401/20260403/0000001'
        r = rq.get(url, timeout=5)
        rows = r.json().get('StatisticSearch', {}).get('row', [])
        if rows:
            data['usd_krw'] = {'value': rows[-1].get('DATA_VALUE', '-'), 'date': rows[-1].get('TIME', '')}
    except:
        data['usd_krw'] = {'value': '-', 'date': ''}

    # 코스피/코스닥 - 네이버 금융 (간단 크롤링)
    try:
        r = rq.get('https://m.stock.naver.com/api/index/KOSPI/basic', timeout=5,
                    headers={'User-Agent': 'Mozilla/5.0'})
        d = r.json()
        data['kospi'] = {'value': d.get('closePrice', '-'), 'change': d.get('compareToPreviousClosePrice', '0'), 'rate': d.get('fluctuationsRatio', '0')}
    except:
        data['kospi'] = {'value': '-', 'change': '0', 'rate': '0'}

    try:
        r = rq.get('https://m.stock.naver.com/api/index/KOSDAQ/basic', timeout=5,
                    headers={'User-Agent': 'Mozilla/5.0'})
        d = r.json()
        data['kosdaq'] = {'value': d.get('closePrice', '-'), 'change': d.get('compareToPreviousClosePrice', '0'), 'rate': d.get('fluctuationsRatio', '0')}
    except:
        data['kosdaq'] = {'value': '-', 'change': '0', 'rate': '0'}

    return jsonify(data)


@app.route('/api/news')
def get_news():
    """네이버 부동산 뉴스 검색"""
    query = request.args.get('q', '부동산 정책')
    display = request.args.get('display', '20')

    import requests
    headers = {
        'X-Naver-Client-Id': os.getenv('NAVER_CLIENT_ID'),
        'X-Naver-Client-Secret': os.getenv('NAVER_CLIENT_SECRET')
    }
    params = {
        'query': query,
        'display': display,
        'sort': 'date'
    }
    try:
        resp = requests.get('https://openapi.naver.com/v1/search/news.json', headers=headers, params=params)
        resp.encoding = 'utf-8'
        data = resp.json()
        return jsonify(data.get('items', []))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/geocode')
def geocode():
    """V-World 주소 → 좌표 변환"""
    import requests
    address = request.args.get('address', '')
    if not address:
        return jsonify({'error': 'address required'}), 400

    try:
        params = {
            'service': 'address',
            'request': 'getcoord',
            'version': '2.0',
            'crs': 'epsg:4326',
            'address': address,
            'format': 'json',
            'type': 'road',
            'key': VWORLD_KEY
        }
        resp = requests.get('https://api.vworld.kr/req/address', params=params)
        data = resp.json()
        if data.get('response', {}).get('status') == 'OK':
            point = data['response']['result']['point']
            return jsonify({'lat': float(point['y']), 'lng': float(point['x'])})
        return jsonify({'error': 'not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/policy/news')
def get_policy_news():
    """국토교통부 부동산 정책 뉴스 (네이버 검색)"""
    query = request.args.get('q', '국토교통부 부동산 정책')
    display = request.args.get('display', '30')
    headers = {
        'X-Naver-Client-Id': os.getenv('NAVER_CLIENT_ID'),
        'X-Naver-Client-Secret': os.getenv('NAVER_CLIENT_SECRET')
    }
    params = {'query': query, 'display': display, 'sort': 'date'}
    try:
        resp = req.get('https://openapi.naver.com/v1/search/news.json', headers=headers, params=params)
        resp.encoding = 'utf-8'
        data = resp.json()
        items = data.get('items', [])
        import re
        result = []
        for item in items:
            title = re.sub('<[^>]+>', '', item.get('title', ''))
            desc = re.sub('<[^>]+>', '', item.get('description', ''))
            result.append({
                'title': title,
                'desc': desc,
                'link': item.get('originallink', item.get('link', '')),
                'date': item.get('pubDate', '')
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/policy/molit')
def get_molit_policy():
    """국토교통부 정책 분석 서비스 (data.go.kr)"""
    search = request.args.get('q', '')
    start_date = request.args.get('start', '2025-01-01')
    end_date = request.args.get('end', '2026-12-31')
    page = request.args.get('page', '1')
    rows = request.args.get('rows', '20')

    url = 'https://apis.data.go.kr/1613000/dataUsesPolicyAnls/getDataUsesPolicyList'
    params = {
        'serviceKey': DATA_GO_KR_KEY,
        'pageNo': page,
        'numOfRows': rows,
        'viewType': 'json',
        'startDate': start_date,
        'endDate': end_date,
    }
    if search:
        params['srchWord'] = search

    try:
        resp = req.get(url, params=params, timeout=10)
        if resp.status_code == 403:
            return jsonify({'error': 'API 승인 대기 중 (최대 24시간 소요)', 'source': 'fallback'}), 200
        data = resp.json()
        items = data.get('data', [])
        result = []
        for item in items:
            result.append({
                'date': item.get('regDate', ''),
                'title': item.get('title', ''),
                'category': item.get('category', ''),
                'keyword': item.get('keyword', ''),
                'url': item.get('url', ''),
                'source': item.get('pvsnInst', '국토교통부')
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/policy')
def get_policy():
    """부동산 정책 타임라인 (주요 정책 — 폴백)"""
    policies = [
        {"date": "2026-03-28", "title": "주택공급 활성화 대책", "desc": "수도권 30만호 추가 공급 계획 발표. 3기 신도시 착공 가속화, 재건축 안전진단 기준 완화.", "category": "공급"},
        {"date": "2026-03-20", "title": "전세사기 피해자 추가 지원", "desc": "전세사기 피해자 긴급 주거지원 6개월 연장. LH 공공임대 우선 입주 확대.", "category": "전세"},
        {"date": "2026-03-15", "title": "재개발 규제 완화 추가", "desc": "조합설립 요건 완화, 안전진단 면제 대상 확대. 1기 신도시 정비 가속화.", "category": "규제"},
        {"date": "2026-02-27", "title": "DSR 3단계 시행", "desc": "총부채원리금상환비율(DSR) 40% 규제 전 금융권 확대. 2금융권 포함.", "category": "대출"},
        {"date": "2026-02-15", "title": "재건축 초과이익환수제 완화", "desc": "초과이익 부담금 기본공제 1억→1.5억 상향. 부과 기준 완화.", "category": "규제"},
        {"date": "2026-02-01", "title": "주택 취득세 중과 완화", "desc": "다주택자 취득세 중과세율 인하. 2주택 8%→4%, 3주택 이상 12%→6%.", "category": "세금"},
        {"date": "2026-01-27", "title": "트럼프 상호관세 인상 위협", "desc": "한국 대상 관세 15%→25% 인상 위협. 수출기업 실적 악화, 건설경기 영향 우려.", "category": "거시"},
        {"date": "2026-01-20", "title": "기준금리 2.75% 동결", "desc": "한국은행 기준금리 동결. 물가 안정 우선, 하반기 인하 가능성 시사.", "category": "금리"},
        {"date": "2026-01-10", "title": "전세보증금 반환보증 요건 강화", "desc": "HUG 전세보증금 반환보증 가입 요건 강화. 보증료율 인상.", "category": "전세"},
        {"date": "2025-12-20", "title": "분양가 상한제 민간 확대 적용", "desc": "민간택지 분양가 상한제 적용 지역 추가. 서울 주요 재건축 단지 포함.", "category": "규제"},
        {"date": "2025-11-15", "title": "종부세 완화안 국회 통과", "desc": "종합부동산세 기본공제 9억→12억 상향. 다주택자 중과세율 인하.", "category": "세금"},
        {"date": "2025-10-30", "title": "공공분양 사전청약 2차", "desc": "3기 신도시 사전청약 2차 일정 확정. 하남교산, 인천계양, 남양주왕숙.", "category": "공급"},
        {"date": "2025-09-01", "title": "전월세신고제 계도기간 종료", "desc": "전월세 계약 30일 이내 신고 의무화. 미신고 시 과태료 부과.", "category": "전세"},
    ]
    return jsonify(policies)


@app.route('/api/trades/summary')
def get_trades_summary():
    """단지별 시세 요약 테이블"""
    sigungu = request.args.get('sigungu', '')
    start = request.args.get('start', '202601')
    end = request.args.get('end', datetime.now().strftime('%Y%m'))

    if not sigungu:
        return jsonify({'error': 'sigungu required'}), 400

    try:
        # 매매 데이터
        all_trades = []
        s_y, s_m = int(start[:4]), int(start[4:])
        e_y, e_m = int(end[:4]), int(end[4:])
        y, m = s_y, s_m
        while y * 100 + m <= e_y * 100 + e_m:
            ym = f'{y}{m:02d}'
            result = fetch_trades_direct('아파트', '매매', sigungu, ym)
            if isinstance(result, list):
                for r in result:
                    r['_trade'] = '매매'
                all_trades.extend(result)
            result2 = fetch_trades_direct('아파트', '전월세', sigungu, ym)
            if isinstance(result2, list):
                for r in result2:
                    r['_trade'] = '전월세'
                all_trades.extend(result2)
            m += 1
            if m > 12:
                m = 1
                y += 1

        if not all_trades:
            return jsonify([])

        df = pd.DataFrame(all_trades)

        # 단지별 집계
        summary = []
        for name, group in df.groupby('aptNm'):
            sell = group[group['_trade'] == '매매']
            rent = group[group['_trade'] == '전월세']

            sell_prices = pd.to_numeric(sell['dealAmount'].str.replace(',', ''), errors='coerce').dropna()
            rent_prices = pd.to_numeric(rent.get('deposit', pd.Series(dtype=float)).astype(str).str.replace(',', ''), errors='coerce').dropna() if 'deposit' in rent.columns else pd.Series(dtype=float)

            first_row = group.iloc[0]
            summary.append({
                'name': name,
                'area': first_row.get('excluUseAr', '-'),
                'buildYear': first_row.get('buildYear', '-'),
                'dong': first_row.get('umdNm', '-'),
                'sellMin': int(sell_prices.min()) if len(sell_prices) else None,
                'sellMax': int(sell_prices.max()) if len(sell_prices) else None,
                'sellCount': len(sell_prices),
                'rentMin': int(rent_prices.min()) if len(rent_prices) else None,
                'rentMax': int(rent_prices.max()) if len(rent_prices) else None,
                'rentCount': len(rent_prices),
            })

        summary.sort(key=lambda x: x.get('sellMax') or 0, reverse=True)
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reverse-geocode')
def reverse_geocode():
    """V-World 좌표 → 주소 변환 (역지오코딩)"""
    lat = request.args.get('lat', '')
    lng = request.args.get('lng', '')
    if not lat or not lng:
        return jsonify({'error': 'lat, lng required'}), 400

    try:
        params = {
            'service': 'address',
            'request': 'getAddress',
            'version': '2.0',
            'crs': 'epsg:4326',
            'point': f'{lng},{lat}',
            'format': 'json',
            'type': 'parcel',
            'key': VWORLD_KEY
        }
        resp = req.get('https://api.vworld.kr/req/address', params=params, timeout=5)
        data = resp.json()
        if data.get('response', {}).get('status') == 'OK':
            results = data['response']['result']
            if results:
                structure = results[0].get('structure', {})
                sido = structure.get('level1', '')
                sigungu = structure.get('level2', '')
                dong = structure.get('level4L', '')
                full_address = results[0].get('text', '')

                # 시군구코드 매칭
                matched = code_bdong[
                    (code_bdong['시도명'].str.strip() == sido) &
                    (code_bdong['시군구명'].str.strip() == sigungu) &
                    (code_bdong['법정동코드'].str.len() == 10)
                ]
                sigungu_code = ''
                if not matched.empty:
                    sigungu_code = matched.iloc[0]['법정동코드'][:5]

                return jsonify({
                    'sido': sido,
                    'sigungu': sigungu,
                    'dong': dong,
                    'address': full_address,
                    'sigunguCode': sigungu_code
                })
        return jsonify({'error': 'not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
