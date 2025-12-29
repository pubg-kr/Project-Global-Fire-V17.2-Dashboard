import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json
import os
import requests
from bs4 import BeautifulSoup

# ==========================================
# 0. 데이터 영구 저장 (Persistence)
# ==========================================
DATA_FILE = "portfolio_data.json"

def load_data():
    """JSON 파일에서 데이터 로드, 없으면 기본값 반환"""
    default_data = {
        "monthly_contribution": 5000000,
        "a_tqqq_qty": 1000.0,
        "a_tqqq_avg": 80000,
        "a_usd_qty": 0.0,
        "a_usd_avg": 0,
        "a_cash_krw": 0,
        "a_cash_usd": 0,
        "b_tqqq_qty": 200.0,
        "b_tqqq_avg": 85000,
        "b_usd_qty": 0.0,
        "b_usd_avg": 0,
        "b_cash_krw": 1000000,
        "b_cash_usd": 15000,
        "c_cash_krw": 0
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                loaded = json.load(f)
                # 마이그레이션: 구버전 데이터가 있으면 기본값으로 병합
                for k, v in default_data.items():
                    if k not in loaded:
                        loaded[k] = v
                return loaded
        except:
            return default_data
    return default_data

def save_data():
    """현재 Session State 값을 JSON으로 저장"""
    data = {
        "monthly_contribution": st.session_state.monthly_contribution,
        "a_tqqq_qty": st.session_state.a_tqqq_qty,
        "a_tqqq_avg": st.session_state.a_tqqq_avg,
        "a_usd_qty": st.session_state.a_usd_qty,
        "a_usd_avg": st.session_state.a_usd_avg,
        "a_cash_krw": st.session_state.a_cash_krw,
        "a_cash_usd": st.session_state.a_cash_usd,
        "b_tqqq_qty": st.session_state.b_tqqq_qty,
        "b_tqqq_avg": st.session_state.b_tqqq_avg,
        "b_usd_qty": st.session_state.b_usd_qty,
        "b_usd_avg": st.session_state.b_usd_avg,
        "b_cash_krw": st.session_state.b_cash_krw,
        "b_cash_usd": st.session_state.b_cash_usd,
        "c_cash_krw": st.session_state.c_cash_krw
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ==========================================
# 1. 설정 및 상수
# ==========================================
st.set_page_config(page_title="Global Fire CRO V20.0", layout="wide", page_icon="🔥")

PHASE_CONFIG = {
    0: {"limit": 100000000, "target_stock": 0.9, "target_cash": 0.1, "name": "Phase 0 (Seed)"},
    1: {"limit": 300000000, "target_stock": 0.8, "target_cash": 0.2, "name": "Phase 1 (Standard)"},
    2: {"limit": 700000000, "target_stock": 0.7, "target_cash": 0.3, "name": "Phase 2 (Defense)"},
    3: {"limit": 1500000000, "target_stock": 0.6, "target_cash": 0.4, "name": "Phase 3 (Critical Mass)"},
    4: {"limit": 2500000000, "target_stock": 0.5, "target_cash": 0.5, "name": "Phase 4 (Retirement Prep)"},
    5: {"limit": float('inf'), "target_stock": 0.4, "target_cash": 0.6, "name": "Phase 5 (Final Exit)"}
}

PROTOCOL_TEXT = """
### 📜 Master Protocol (요약) - Ver 20.0 Dual Engine
1.  **[헌법] 손실 중 매도 금지:** 계좌가 마이너스면 RSI가 100이어도 절대 팔지 않는다.
2.  **[듀얼] 50:50 황금비:** TQQQ(50%)와 USD(50%) 비중을 유지하며 리밸런싱한다.
3.  **[광기] RSI 80 (방어 75):** (수익 중일 때만) 현금 비중을 Target + 10%까지 늘린다.
4.  **[위기] MDD 최적화:** -15%부터 Sniper 현금 분할 투입 (-15, -25, -35, -45).
5.  **[경보] 버블 붕괴 감지:** VIX 20+ 안착 / 금리차 정상화 / 주봉 20선 이탈(2주) 시 방어 모드 발동.
"""

# ==========================================
# 2. 유틸리티 함수
# ==========================================
def calculate_indicators(df):
    """데이터프레임(주/월봉)을 받아 RSI와 MDD를 계산하여 반환"""
    if df.empty: return 0, 0
    
    # RSI 계산
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MDD 계산 (1년/52주 기준)
    window = 52 if len(df) >= 52 else len(df)
    df['Roll_Max'] = df['Close'].rolling(window=window, min_periods=1).max()
    df['DD'] = (df['Close'] / df['Roll_Max']) - 1.0
    
    return float(df['RSI'].iloc[-1]), float(df['DD'].iloc[-1])

def get_market_data():
    try:
        # QQQ (일봉/주봉/월봉)
        qqq_dy = yf.download("QQQ", interval="1d", period="1y", progress=False, auto_adjust=False)
        qqq_wk = yf.download("QQQ", interval="1wk", period="2y", progress=False, auto_adjust=False)
        qqq_mo = yf.download("QQQ", interval="1mo", period="5y", progress=False, auto_adjust=False)
        
        # TQQQ (주봉/월봉)
        tqqq_wk = yf.download("TQQQ", interval="1wk", period="2y", progress=False, auto_adjust=False)
        tqqq_mo = yf.download("TQQQ", interval="1mo", period="5y", progress=False, auto_adjust=False)

        # USD (주봉/월봉) - ProShares Ultra Semiconductors
        usd_wk = yf.download("USD", interval="1wk", period="2y", progress=False, auto_adjust=False)
        usd_mo = yf.download("USD", interval="1mo", period="5y", progress=False, auto_adjust=False)
        
        # 매크로 지표 (VIX, 10년물, 3개월물) - 1년치 데이터 (추세 분석용)
        vix = yf.download("^VIX", period="1y", progress=False, auto_adjust=False)
        tnx = yf.download("^TNX", period="1y", progress=False, auto_adjust=False) # 10년물
        irx = yf.download("^IRX", period="1y", progress=False, auto_adjust=False) # 3개월물
        
        # 환율
        exch = yf.download("KRW=X", period="1d", progress=False, auto_adjust=False)
        
        if qqq_wk.empty or exch.empty or tqqq_wk.empty or usd_wk.empty: return None

        # MultiIndex 정리
        for d in [qqq_dy, qqq_wk, qqq_mo, tqqq_wk, tqqq_mo, usd_wk, usd_mo, exch, vix, tnx, irx]:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)

        current_rate = float(exch['Close'].iloc[-1])
        
        # QQQ 지표 & 이동평균선
        qqq_price = float(qqq_wk['Close'].iloc[-1])
        
        # MA 계산 (일/주/월)
        for d in [qqq_dy, qqq_wk, qqq_mo]:
            d['MA20'] = d['Close'].rolling(window=20).mean()
            d['MA60'] = d['Close'].rolling(window=60).mean()
            calculate_indicators(d) # RSI, MDD 계산

        qqq_rsi_wk = float(qqq_wk['RSI'].iloc[-1])
        qqq_mdd = float(qqq_wk['DD'].iloc[-1])
        qqq_rsi_mo = float(qqq_mo['RSI'].iloc[-1])
        
        # TQQQ 지표
        tqqq_price = float(tqqq_wk['Close'].iloc[-1])
        tqqq_rsi_wk, tqqq_mdd = calculate_indicators(tqqq_wk)
        tqqq_rsi_mo, _ = calculate_indicators(tqqq_mo)

        # USD 지표
        usd_price = float(usd_wk['Close'].iloc[-1])
        usd_rsi_wk, usd_mdd = calculate_indicators(usd_wk)
        usd_rsi_mo, _ = calculate_indicators(usd_mo)
        
        # 매크로 데이터 분석 (Ver 19.3.2)
        vix_val = float(vix['Close'].iloc[-1]) if not vix.empty else 0
        tnx_val = float(tnx['Close'].iloc[-1]) if not tnx.empty else 0
        irx_val = float(irx['Close'].iloc[-1]) if not irx.empty else 0
        yield_spread = tnx_val - irx_val
        
        # VIX 5일 안착 여부 (최근 5일 최저가가 20 이상인지)
        is_vix_trend = False
        if len(vix) >= 5:
            vix_recent_min = vix['Close'].tail(5).min()
            is_vix_trend = (vix_recent_min >= 20.0)
        else:
            is_vix_trend = (vix_val >= 20.0)

        # 금리차 역전 후 정상화 (Normalization) 감지
        # 최근 6개월(약 126거래일) 내에 역전(-0.05 미만)이 있었는지 확인
        # 그리고 현재는 양수인지 확인
        is_spread_normalization = False
        spread_series = None
        if not tnx.empty and not irx.empty:
            # 인덱스 정렬 후 계산
            spread_series = tnx['Close'] - irx['Close']
            spread_recent = spread_series.tail(126) # 6개월
            was_inverted = (spread_recent < 0).any()
            is_positive_now = (spread_series.iloc[-1] >= 0)
            
            if was_inverted and is_positive_now:
                is_spread_normalization = True

        # [Ver 19.3.4] Trend Health Check (QQQ 주봉 20선 이탈)
        # 조건: QQQ 주가가 주봉 20선 아래로 내려가고 2주 이상 회복 못함
        is_trend_broken = False
        qqq_ma20_wk = float(qqq_wk['MA20'].iloc[-1])
        if len(qqq_wk) >= 2:
            last_two_weeks = qqq_wk.tail(2)
            # 최근 2주 모두 종가가 MA20 아래인지 확인
            is_trend_broken = ((last_two_weeks['Close'] < last_two_weeks['MA20'])).all()

        # [Ver 20.2] CNN 공포탐욕지수 (Fear & Greed Index)
        fear_greed_value = 50  # 기본값 (중립)
        fear_greed_text = "Neutral"
        try:
            # CNN Fear & Greed Index 웹 스크래핑
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", 
                                   headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                fear_greed_value = int(data['fear_and_greed']['score'])
                fear_greed_text = data['fear_and_greed']['rating']
        except:
            # Fallback: Alternative.me API (암호화폐 지수)
            try:
                response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    fear_greed_value = int(data['data'][0]['value'])
                    fear_greed_text = data['data'][0]['value_classification']
            except:
                pass  # API 실패 시 기본값 유지

        # [Ver 20.2] 버핏지수 (Buffett Indicator)
        # 공식: (Total Market Cap / GDP) × 100
        buffett_indicator = 0
        m2_money_stock = 0  # M2 통화량 (조 달러)
        
        try:
            # 방법 1: Wilshire 5000 Full Cap (시가총액 직접 반영)
            wilshire_full = yf.download("^W5000FLT", period="5d", progress=False, auto_adjust=False)
            
            if not wilshire_full.empty:
                if isinstance(wilshire_full.columns, pd.MultiIndex):
                    wilshire_full.columns = wilshire_full.columns.get_level_values(0)
                wilshire_full_val = float(wilshire_full['Close'].iloc[-1])
                
                # Wilshire 5000 Full Cap은 시가총액을 직접 반영 (단위: 십억 달러)
                # 지수값이 곧 시가총액 (Billion)
                market_cap_trillion = wilshire_full_val / 1000
                
                # 미국 GDP (2024년 4분기 기준 약 28.27조 달러)
                us_gdp_trillion = 28.27
                
                # 실제 미국 전체 시가총액 보정
                # Wilshire 5000 Full Cap 기준으로 계산 (보정 불필요)
                buffett_indicator = (market_cap_trillion / us_gdp_trillion) * 100
                
                # M2 통화량 (2024년 11월 기준 약 21.17조 달러)
                m2_money_stock = 21.17
            else:
                # Fallback: 기존 Wilshire 5000 사용
                wilshire = yf.download("^W5000", period="5d", progress=False, auto_adjust=False)
                if not wilshire.empty:
                    if isinstance(wilshire.columns, pd.MultiIndex):
                        wilshire.columns = wilshire.columns.get_level_values(0)
                    wilshire_val = float(wilshire['Close'].iloc[-1])
                    
                    # Wilshire 5000 지수 → 시가총액 근사 변환
                    # 현재 지수 ≈ 시가총액 (십억 달러)
                    market_cap_trillion = wilshire_val / 1000
                    us_gdp_trillion = 28.27
                    buffett_indicator = (market_cap_trillion / us_gdp_trillion) * 100
                    m2_money_stock = 21.17
        except:
            buffett_indicator = 0  # 실패 시 0

        return {
            'qqq_dy': qqq_dy,
            'qqq_wk': qqq_wk,
            'qqq_mo': qqq_mo,
            'qqq_price': qqq_price,
            'qqq_rsi_wk': qqq_rsi_wk,
            'qqq_rsi_mo': qqq_rsi_mo,
            'qqq_mdd': qqq_mdd,
            'tqqq_price': tqqq_price,
            'tqqq_rsi_wk': tqqq_rsi_wk,
            'tqqq_rsi_mo': tqqq_rsi_mo,
            'tqqq_mdd': tqqq_mdd,
            'usd_price': usd_price,
            'usd_rsi_wk': usd_rsi_wk,
            'usd_rsi_mo': usd_rsi_mo,
            'usd_mdd': usd_mdd,
            'usd_krw': current_rate,
            'vix': vix_val,
            'tnx': tnx_val,
            'yield_spread': yield_spread,
            'is_vix_trend': is_vix_trend,
            'is_spread_normalization': is_spread_normalization,
            'is_trend_broken': is_trend_broken,
            'qqq_ma20_wk': qqq_ma20_wk,
            'fear_greed_value': fear_greed_value,
            'fear_greed_text': fear_greed_text,
            'buffett_indicator': buffett_indicator,
            'm2_money_stock': m2_money_stock
        }
    except Exception as e:
        # st.error(f"Data Fetch Error: {e}")
        return None

def determine_phase(total_assets):
    if total_assets <= PHASE_CONFIG[0]['limit']: return 0
    for p in range(1, 6):
        if total_assets <= PHASE_CONFIG[p]['limit']: return p
    return 5

def format_krw(value):
    return f"{int(value):,}원"

# ==========================================
# 3. 메인 로직
# ==========================================
st.title("🔥 Global Fire CRO System")
st.markdown("**Ver 20.7 (Dual Engine Strategy)** | System Owner: **Busan Programmer** | Benchmark: **QQQ (All Indicators)**")

# 데이터 로드 (초기화)
saved_data = load_data()

# Session State 초기화 (없으면 파일 값으로)
if "monthly_contribution" not in st.session_state:
    for key, val in saved_data.items():
        # 저장된 값이 있으면 사용, 없으면 기본값 (안전장치)
        if key in saved_data:
            st.session_state[key] = saved_data[key]
        # 숫자형 데이터 강제 형변환 (스트림릿 에러 방지)
        if "qty" in key or "avg" in key or "contribution" in key:
                try:
                    st.session_state[key] = float(st.session_state[key])
                except:
                    pass # 이미 float이거나 변환 불가 시 패스

with st.expander("📜 Master Protocol (규정집)", expanded=False):
    st.markdown(PROTOCOL_TEXT)

mkt = get_market_data()

if mkt is not None:
    # 데이터 매핑
    qqq_price = mkt['qqq_price']
    tqqq_price = mkt['tqqq_price']
    usd_price = mkt['usd_price']
    usd_krw_rate = mkt['usd_krw']
    qqq_rsi = mkt['qqq_rsi_wk']
    qqq_mdd = mkt['qqq_mdd']
    
    # 차트용 데이터
    df_dy = mkt['qqq_dy']
    df_wk = mkt['qqq_wk']
    df_mo = mkt['qqq_mo']

    tqqq_krw = tqqq_price * usd_krw_rate  # TQQQ 현재가 (원화)
    usd_stock_krw = usd_price * usd_krw_rate # USD 현재가 (원화)

    # --- 사이드바 (Form 적용으로 입력 최적화) ---
    st.sidebar.header("📝 자산 정보")
    st.sidebar.info(f"💵 환율: **{int(usd_krw_rate):,}원/$**")
    
    with st.sidebar.form("asset_form"):
        # 월급 입력
        st.number_input("이번 달 투입금 (월급)", min_value=0, step=100000, key="monthly_contribution", format="%d")
        st.caption(f"👉 확인: **{format_krw(st.session_state.monthly_contribution)}**") # 가독성 헬퍼
        
        st.markdown("---")
        
        # A계좌
        with st.expander("🏦 계좌 A: 금고 (장기)", expanded=True):
            st.number_input("A: TQQQ 보유 수량", min_value=0.0, step=0.01, key="a_tqqq_qty", format="%.2f")
            st.number_input("A: TQQQ 평균단가 (KRW)", min_value=0, step=100, key="a_tqqq_avg", format="%d")
            st.markdown("---")
            st.number_input("A: USD 보유 수량", min_value=0.0, step=0.01, key="a_usd_qty", format="%.2f")
            st.number_input("A: USD 평균단가 (KRW)", min_value=0, step=100, key="a_usd_avg", format="%d")
            
            # A계좌 평가금 자동 계산
            a_tqqq_eval = st.session_state.a_tqqq_qty * tqqq_krw
            a_usd_eval = st.session_state.a_usd_qty * usd_stock_krw
            st.caption(f"📊 TQQQ: **{format_krw(a_tqqq_eval)}** / USD: **{format_krw(a_usd_eval)}**")
            
            st.number_input("A: 원화 예수금", min_value=0, step=100000, key="a_cash_krw", format="%d")
            st.caption(f"👉 {format_krw(st.session_state.a_cash_krw)}")
            
            st.number_input("A: 달러 예수금", min_value=0, step=100, key="a_cash_usd", format="%d")
            st.caption(f"👉 ${st.session_state.a_cash_usd:,.2f}")

        # B계좌
        with st.expander("⚔️ 계좌 B: 스나이퍼 (매매)", expanded=True):
            st.number_input("B: TQQQ 보유 수량", min_value=0.0, step=0.01, key="b_tqqq_qty", format="%.2f")
            st.number_input("B: TQQQ 평균단가 (KRW)", min_value=0, step=100, key="b_tqqq_avg", format="%d")
            st.markdown("---")
            st.number_input("B: USD 보유 수량", min_value=0.0, step=0.01, key="b_usd_qty", format="%.2f")
            st.number_input("B: USD 평균단가 (KRW)", min_value=0, step=100, key="b_usd_avg", format="%d")
            
            # B계좌 평가금 자동 계산
            b_tqqq_eval = st.session_state.b_tqqq_qty * tqqq_krw
            b_usd_eval = st.session_state.b_usd_qty * usd_stock_krw
            st.caption(f"📊 TQQQ: **{format_krw(b_tqqq_eval)}** / USD: **{format_krw(b_usd_eval)}**")
            
            st.number_input("B: 원화 예수금", min_value=0, step=100000, key="b_cash_krw", format="%d")
            st.caption(f"👉 {format_krw(st.session_state.b_cash_krw)}")
            
            st.number_input("B: 달러 예수금", min_value=0, step=100, key="b_cash_usd", format="%d")
            st.caption(f"👉 ${st.session_state.b_cash_usd:,.2f}")

        # C계좌 (V17.3 추가)
        with st.expander("🛡️ 계좌 C: 벙커 (세금/비상)", expanded=True):
            st.number_input("C: 원화 예수금 (수익금 22%)", min_value=0, step=100000, key="c_cash_krw", format="%d")
            st.caption(f"👉 {format_krw(st.session_state.c_cash_krw)}")

        st.markdown("---")
        # 폼 제출 버튼
        submit_button = st.form_submit_button("💾 자산 정보 저장 및 업데이트", use_container_width=True)
        if submit_button:
            save_data()
            st.success("✅ 저장 완료!")
    
    # --- 자동 손익 판단 로직 (Ver 20.0 Dual Engine) ---
    tqqq_qty = st.session_state.a_tqqq_qty + st.session_state.b_tqqq_qty
    usd_qty = st.session_state.a_usd_qty + st.session_state.b_usd_qty
    
    tqqq_invested = (st.session_state.a_tqqq_qty * st.session_state.a_tqqq_avg) + \
                    (st.session_state.b_tqqq_qty * st.session_state.b_tqqq_avg)
    usd_invested = (st.session_state.a_usd_qty * st.session_state.a_usd_avg) + \
                   (st.session_state.b_usd_qty * st.session_state.b_usd_avg)
                   
    total_invested_krw = tqqq_invested + usd_invested
    
    # [Ver 19.2] 손실 판단 기준 변경: 0% -> +1.5% (수수료 및 슬리피지 방어)
    total_tqqq_krw = tqqq_qty * tqqq_krw
    total_usd_krw = usd_qty * usd_stock_krw
    total_stock_krw = total_tqqq_krw + total_usd_krw
    
    profit_rate = 0.0
    if total_invested_krw > 0:
        profit_rate = ((total_stock_krw - total_invested_krw) / total_invested_krw) * 100
    
    is_loss = profit_rate < 1.5 if total_invested_krw > 0 else False

    # --- 계산 로직 ---
    # Session State 값을 사용하여 계산
    total_cash_krw = (st.session_state.a_cash_krw + st.session_state.b_cash_krw + st.session_state.c_cash_krw) + \
                     ((st.session_state.a_cash_usd + st.session_state.b_cash_usd) * usd_krw_rate)
    total_assets = total_stock_krw + total_cash_krw
    
    # --- 1. 시장 상황판 (먼저 표시하여 변수 정의) ---
    st.header("1. 시장 상황판 (Market Status)")
    
    # [Ver 19.3.2] 버블 경보 시스템 (정밀 타격)
    with st.expander("🚨 버블 붕괴 조기 경보 (Early Warning System)", expanded=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            spread_val = mkt['yield_spread']
            
            # 지표 상태 메시지 생성
            vix_status = "✅ 안정"
            if mkt['is_vix_trend']: vix_status = "🚨 위험 (5일 안착)"
            elif mkt['vix'] >= 20: vix_status = "⚠️ 주의 (20 돌파)"
            
            spread_status = "✅ 정상"
            if mkt['is_spread_normalization']: spread_status = "🚨 위험 (역전 후 정상화)"
            elif spread_val < 0: spread_status = "⚠️ 경고 (역전 중)"
            
            trend_status = "✅ 상승 추세"
            if mkt['is_trend_broken']: trend_status = "🚨 붕괴 (2주 연속 이탈)"
            
            st.markdown(f"""
            **자동 감시 지표 (Auto-Detection):**
            1. **장단기 금리차 (10Y-3M):** **{spread_val:.3f}%p** [{spread_status}]
               - *Trigger: 역전(-0.05 미만) 후 정상화(0 이상) 시*
            2. **VIX (공포지수):** **{mkt['vix']:.2f}** [{vix_status}]
               - *Trigger: 20.0 위에서 5거래일 안착 시*
            3. **추세 건강 (Trend Health):** **QQQ ${mkt['qqq_price']:.2f}** vs MA20 ${mkt['qqq_ma20_wk']:.2f} [{trend_status}]
               - *Trigger: 주봉 20선 하향 돌파 후 2주 이상 회복 실패 시*
            """)
        with c2:
            bubble_manual = st.checkbox("⚠️ 시장 이상 징후 강제 지정", value=False, help="시스템 감지 외에 '시장 너비 붕괴' 등을 사용자가 직접 느꼈을 때 체크하십시오.")

    # Phase 결정 및 모드 설정 (변수 확보 후 실행)
    current_phase = determine_phase(total_assets)
    base_target_stock = PHASE_CONFIG[current_phase]['target_stock']
    base_target_cash = PHASE_CONFIG[current_phase]['target_cash']
    
    # [Ver 19.3.2] 방어 모드 발동 로직 (VIX 5일 안착 or 금리차 정상화)
    is_emergency = bubble_manual or mkt['is_vix_trend'] or mkt['is_spread_normalization'] or mkt['is_trend_broken']
    
    if is_emergency: 
        if not bubble_manual:
            reasons = []
            if mkt['is_vix_trend']: reasons.append(f"VIX 기조적 상승({mkt['vix']:.1f})")
            if mkt['is_spread_normalization']: reasons.append(f"금리차 역전 후 정상화({mkt['yield_spread']:.3f}%p)")
            if mkt['is_trend_broken']: reasons.append(f"추세 붕괴(주봉 20선 이탈)")
            reason_text = ", ".join(reasons)
            st.toast(f"🚨 위험 신호 감지! [{reason_text}] 방어 모드 발동.", icon="🛡️")
            
        target_stock_ratio = base_target_stock - 0.1
        target_cash_ratio = base_target_cash + 0.1
        rsi_sell_threshold = 75 # 매도 기준 강화
        mode_label = "🛡️ 방어 모드 (Defensive)"
    else:
        target_stock_ratio = base_target_stock
        target_cash_ratio = base_target_cash
        rsi_sell_threshold = 80
        mode_label = "⚡ 일반 모드 (Normal)"
    
    current_stock_ratio = total_stock_krw / total_assets if total_assets > 0 else 0
    current_cash_ratio = total_cash_krw / total_assets if total_assets > 0 else 0

    # Helper for labels
    def get_rsi_status(rsi):
        if rsi >= 80: return "🚨 광기"
        elif rsi >= 75: return "🔥 과열"
        elif rsi < 60: return "💰 기회"
        return "표준"

    def get_mdd_status(mdd):
        return "📉 위기" if mdd <= -0.2 else "✅ 안정"

    # QQQ Info
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("QQQ 현재가", f"${qqq_price:.2f} ({format_krw(qqq_price*usd_krw_rate)})")
    q2.metric("QQQ 월봉 RSI", f"{mkt['qqq_rsi_mo']:.1f}", "Month Trend")
    q3.metric("QQQ 주봉 RSI", f"{qqq_rsi:.1f}", get_rsi_status(qqq_rsi))
    q4.metric("QQQ MDD", f"{qqq_mdd*100:.2f}%", get_mdd_status(qqq_mdd))
    
    # TQQQ Info
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("TQQQ 현재가", f"${tqqq_price:.2f} ({format_krw(tqqq_price*usd_krw_rate)})")
    t2.metric("TQQQ 월봉 RSI", f"{mkt['tqqq_rsi_mo']:.1f}", "Month Trend")
    t3.metric("TQQQ 주봉 RSI", f"{mkt['tqqq_rsi_wk']:.1f}", get_rsi_status(mkt['tqqq_rsi_wk']))
    t4.metric("TQQQ MDD", f"{mkt['tqqq_mdd']*100:.2f}%", get_mdd_status(mkt['tqqq_mdd']))

    # USD Info (Ver 20.0)
    u1, u2, u3, u4 = st.columns(4)
    u1.metric("USD 현재가", f"${mkt['usd_price']:.2f} ({format_krw(mkt['usd_price']*usd_krw_rate)})")
    u2.metric("USD 월봉 RSI", f"{mkt['usd_rsi_mo']:.1f}", "Month Trend")
    u3.metric("USD 주봉 RSI", f"{mkt['usd_rsi_wk']:.1f}", get_rsi_status(mkt['usd_rsi_wk']))
    u4.metric("USD MDD", f"{mkt['usd_mdd']*100:.2f}%", get_mdd_status(mkt['usd_mdd']))

    # Macro Info (V19.0 + Ver 20.2 확장)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    vix = mkt['vix']
    # VIX Label: 20 기준 (방어) / 30 기준 (공포/매수)
    vix_label = "✅ 안정" if vix < 20 else ("🚨 공포" if vix > 30 else "🛡️ 방어")
    m1.metric("VIX (변동성)", f"{vix:.2f}", vix_label)
    
    tnx = mkt['tnx']
    tnx_label = "양호" if tnx < 4.0 else "⚠️ 고금리 주의"
    m2.metric("US 10Y (국채금리)", f"{tnx:.2f}%", tnx_label)
    
    # Yield Spread
    spread = mkt['yield_spread']
    spread_msg = "✅ 정상" if spread > 0 else "🚨 역전 (Recession Warning)"
    if mkt['is_spread_normalization']: spread_msg = "⚠️ 붕괴 임박 (Normalization)"
    m3.metric("10Y-3M 금리차", f"{spread:.2f}%p", spread_msg)
    
    # [Ver 20.2] CNN 공포탐욕지수
    fg_val = mkt['fear_greed_value']
    fg_text = mkt['fear_greed_text']
    if fg_val <= 25:
        fg_emoji = "😱 극도 공포"
    elif fg_val <= 45:
        fg_emoji = "😰 공포"
    elif fg_val <= 55:
        fg_emoji = "😐 중립"
    elif fg_val <= 75:
        fg_emoji = "😊 탐욕"
    else:
        fg_emoji = "🤑 극도 탐욕"
    m4.metric("공포탐욕지수", f"{fg_val}", fg_emoji)
    
    # [Ver 20.2] 버핏지수
    buffett = mkt['buffett_indicator']
    if buffett > 0:
        if buffett < 90:
            buffett_label = "💎 저평가"
        elif buffett < 115:
            buffett_label = "✅ 적정"
        elif buffett < 135:
            buffett_label = "⚠️ 고평가"
        elif buffett < 200:
            buffett_label = "🚨 심각한 고평가"
        else:
            buffett_label = "💥 역사적 버블"
        m5.metric("버핏지수", f"{buffett:.1f}%", buffett_label)
    else:
        m5.metric("버핏지수", "N/A", "데이터 없음")
    
    m6.empty() # Spacer
    
    # [Ver 20.2] 지표 해석 가이드 (Expander 방식 - 즉시 펼침)
    with st.expander("📊 VIX 지수 해석 가이드 (변동성 지수)", expanded=False):
        st.markdown(f"""
        ### 현재 지수: **{vix:.2f}** ({vix_label})
        
        | 구간 | 의미 | 시장 상태 | 투자 전략 | 현재 상태 |
        |:---:|:---|:---|:---|:---:|
        | **~15** | ✅ **안정** | 매우 평온 | 정상 운용 | {'✅' if vix < 15 else ''} |
        | **15~20** | 😐 **보통** | 정상 변동성 | 정상 운용 | {'✅' if 15 <= vix < 20 else ''} |
        | **20~30** | 🛡️ **방어** | 변동성 증가 | **방어 모드 발동** | {'✅' if 20 <= vix < 30 else ''} |
        | **30~40** | 🚨 **공포** | 패닉 시작 | 🟢 **매수 기회 탐색** | {'✅' if 30 <= vix < 40 else ''} |
        | **40+** | 💥 **극도 공포** | 시스템 붕괴급 | 🟢 **적극 매수 (역발상)** | {'✅' if vix >= 40 else ''} |
        
        #### 📈 역사적 사례
        - **2008년 금융위기:** VIX **89.53** (역대 최고)
        - **2020년 코로나:** VIX **82.69**
        - **2022년 러시아 침공:** VIX **36.45**
        - **평상시:** VIX **12~18**
        
        #### 💡 CRO의 조언
        - **VIX 20 이상 5일 안착:** 시스템 **방어 모드** 자동 발동 (주식 목표 -10%p, RSI 매도 기준 75로 강화)
        - **VIX 30 이상:** 계좌 B(스나이퍼) 탄환 준비. MDD -15% 이상과 겹치면 **적극 매수**.
        - **VIX 40 이상:** 역사적 폭락장. **"남들이 공포할 때 탐욕하라"** 실천 시점.
        """)
    
    with st.expander("📊 CNN 공포탐욕지수 해석 가이드", expanded=False):
        st.markdown(f"""
        ### 현재 지수: **{fg_val}** ({fg_emoji})
        
        | 구간 | 의미 | 투자 전략 | 현재 상태 |
        |:---:|:---|:---|:---:|
        | **0~25** | 😱 **극도 공포 (Extreme Fear)** | 🟢 **적극 매수 기회** | {'✅' if fg_val <= 25 else ''} |
        | **25~45** | 😰 **공포 (Fear)** | 🟢 매수 검토 | {'✅' if 25 < fg_val <= 45 else ''} |
        | **45~55** | 😐 **중립 (Neutral)** | ⚪ 관망 | {'✅' if 45 < fg_val <= 55 else ''} |
        | **55~75** | 😊 **탐욕 (Greed)** | 🟡 경계 (비중 조정 검토) | {'✅' if 55 < fg_val <= 75 else ''} |
        | **75~100** | 🤑 **극도 탐욕 (Extreme Greed)** | 🔴 **매도/현금 확보** | {'✅' if fg_val > 75 else ''} |
        
        #### 💡 CRO의 조언
        - **극도 공포 (0~25):** 시장이 패닉 상태. 계좌 B(스나이퍼) 탄환 장전 시점.
        - **탐욕 (55~75):** 시장 과열 조짐. RSI와 함께 확인 필요.
        - **극도 탐욕 (75+):** RSI 80과 겹치면 **강력한 매도 신호**.
        """)
    
    with st.expander("📊 버핏지수 해석 가이드", expanded=False):
        st.markdown(f"""
        ### 현재 지수: **{buffett:.1f}%** ({buffett_label})
        
        | 구간 | 의미 | 시장 상태 | 현재 상태 |
        |:---:|:---|:---|:---:|
        | **~90%** | 💎 **현저한 저평가** | 강력 매수 기회 | {'✅' if buffett < 90 else ''} |
        | **90~115%** | ✅ **적정 가치** | 정상 밸류에이션 | {'✅' if 90 <= buffett < 115 else ''} |
        | **115~135%** | ⚠️ **다소 고평가** | 경계 구간 | {'✅' if 115 <= buffett < 135 else ''} |
        | **135~200%** | 🚨 **심각한 고평가** | 버블 경계 | {'✅' if 135 <= buffett < 200 else ''} |
        | **200%+** | 💥 **역사적 버블** | 2000년 닷컴버블 수준 | {'✅' if buffett >= 200 else ''} |
        
        #### 📈 역사적 사례
        - **1972년 (117%):** 폭락 직전 고점
        - **2000년 (153%):** 닷컴버블 붕괴
        - **2008년 (105%):** 금융위기 직전
        - **2021년 (215%):** 코로나 유동성 버블
        - **2024년 현재 ({buffett:.1f}%):** {'⚠️ 역사적 최고 수준' if buffett >= 200 else '고평가 구간'}
        
        #### 💡 CRO의 조언
        - **200% 이상:** 자산이 불어날수록 **현금 비중 확대 필수**. 보수적 글라이드 패스 전략이 빛을 발하는 시점.
        - **전략:** Phase 3 이상에서는 주식 비중을 60% 이하로 유지하여 버블 붕괴 시 방어력 확보.
        """)
    

    # --- 2. 포트폴리오 진단 ---
    st.markdown("---")
    st.header("2. 포트폴리오 진단 (Diagnosis)")
    
    if current_phase < 5:
        prev_limit = PHASE_CONFIG[current_phase-1]['limit'] if current_phase > 1 else 0
        next_limit = PHASE_CONFIG[current_phase]['limit']
        progress = (total_assets - prev_limit) / (next_limit - prev_limit)
        progress = max(0.0, min(1.0, progress))
        st.progress(progress, text=f"🚀 Level Up ({PHASE_CONFIG[current_phase+1]['name']}) 진행률: {progress*100:.1f}%")
    else:
        st.progress(1.0, text="🏆 Final Phase 달성! (은퇴 준비 완료)")

    # [Ver 20.4] 3단 레이어 포트폴리오 진단
    
    # === 1단: 통합 정보 (2줄 × 4컬럼) ===
    st.markdown("### 📊 통합 포트폴리오")
    
    # 첫 번째 줄: Phase, 자산, 원금, 수익률
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
    phase_info = PHASE_CONFIG[current_phase]
    
    row1_col1.metric("현재 Phase", f"{phase_info['name']}", f"{mode_label}")
    row1_col2.metric("총 자산", format_krw(total_assets))
    row1_col3.metric("통합 투자 원금", format_krw(total_invested_krw))
    
    if total_invested_krw > 0:
        st_emoji = "🔴" if not is_loss else "🔵"
        row1_col4.metric("통합 수익률", f"{profit_rate:.2f}%", f"{st_emoji} 상태")
    else:
        row1_col4.metric("통합 수익률", "0%", "대기")
    
    # 두 번째 줄: 주식평가금, 현금보유액, 주식비중, 현금비중
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
    
    row2_col1.metric("총 주식 평가금", format_krw(total_stock_krw))
    row2_col2.metric("총 현금 보유액", format_krw(total_cash_krw))
    
    # TQQQ:USD 비율
    tqqq_ratio_display = total_tqqq_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    usd_ratio_display = total_usd_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    tqqq_pct = int(tqqq_ratio_display * 100)
    usd_pct = int(usd_ratio_display * 100)
    row2_col3.metric("주식 비중", 
                     f"{current_stock_ratio*100:.1f}%", 
                     f"목표: {target_stock_ratio*100:.0f}% (TQ {tqqq_pct}:{usd_pct} USD)")
    row2_col4.metric("현금 비중", f"{current_cash_ratio*100:.1f}%", f"목표: {target_cash_ratio*100:.0f}%")

    # === 2단: TQQQ 상세 정보 ===
    st.markdown("### 🚀 TQQQ (나스닥 100 3배)")
    tq1, tq2, tq3, tq4, tq5, tq6 = st.columns(6)
    
    tqqq_qty = st.session_state.a_tqqq_qty + st.session_state.b_tqqq_qty
    tqqq_avg = tqqq_invested / tqqq_qty if tqqq_qty > 0 else 0
    tqqq_profit = ((total_tqqq_krw - tqqq_invested) / tqqq_invested * 100) if tqqq_invested > 0 else 0
    
    tq1.metric("보유 수량", f"{tqqq_qty:.2f}주")
    tq2.metric("평균 단가", format_krw(tqqq_avg))
    tq3.metric("현재가", format_krw(tqqq_krw))
    tq4.metric("투자 원금", format_krw(tqqq_invested))
    tq5.metric("평가 금액", format_krw(total_tqqq_krw))
    tq6.metric("수익률", f"{tqqq_profit:.2f}%", "🔴" if tqqq_profit >= 0 else "🔵")

    # === 3단: USD 상세 정보 ===
    st.markdown("### 💎 USD (반도체 2배)")
    us1, us2, us3, us4, us5, us6 = st.columns(6)
    
    usd_qty = st.session_state.a_usd_qty + st.session_state.b_usd_qty
    usd_avg = usd_invested / usd_qty if usd_qty > 0 else 0
    usd_profit = ((total_usd_krw - usd_invested) / usd_invested * 100) if usd_invested > 0 else 0
    
    us1.metric("보유 수량", f"{usd_qty:.2f}주")
    us2.metric("평균 단가", format_krw(usd_avg))
    us3.metric("현재가", format_krw(usd_stock_krw))
    us4.metric("투자 원금", format_krw(usd_invested))
    us5.metric("평가 금액", format_krw(total_usd_krw))
    us6.metric("수익률", f"{usd_profit:.2f}%", "🔴" if usd_profit >= 0 else "🔵")

    st.markdown("---")
    if is_loss: st.error("🛑 [손실 중] 절대 방패 가동: 매도 금지")
    else: st.success("✅ [수익 중] 정상 로직 가동")

    # --- 3. CRO 실행 명령 ---
    st.markdown("---")
    st.header("3. CRO 실행 명령 (Action Protocol)")
    
    sell_priority_acc = ""
    sell_guide_msg = ""
    
    # 매도 우선순위 결정 (Tax Shield: 평단가 높은 계좌 우선 매도)
    # Ver 20.0: 통합 수익률 기준으로 판단하므로 계좌별 평단 비교는 유지하되, TQQQ/USD 각각 고려 필요하나 복잡도 증가로 단순화
    avg_a = st.session_state.a_tqqq_avg
    avg_b = st.session_state.b_tqqq_avg
    
    if avg_a > avg_b and st.session_state.a_tqqq_qty > 0:
        sell_priority_acc = "A계좌 (The Vault)"
    else:
        sell_priority_acc = "B계좌 (The Sniper)"
    
    sell_guide_msg = f"👉 **세금 절감: 평단가가 높은 [{sell_priority_acc}]에서 매도하십시오.**"

    # Logic Engine V19.1.1 (Dual Pipeline: Asset & Monthly)
    
    # --- 1. 월급 매수 가이드 (Monthly Guide) - 독립 실행 ---
    monthly_msg = ""
    monthly_color = "blue"
    
    # [Ver 19.1] 전시 상황 (MDD -30% 이하) -> 무조건 100% 매수
    if qqq_mdd <= -0.3:
         buy_amt_monthly = st.session_state.monthly_contribution
         monthly_msg = f"📉 **전시 상황 (MDD {qqq_mdd*100:.1f}%)**: RSI 무시하고 월급 100% ({format_krw(buy_amt_monthly)}) TQQQ & USD 분할 매수."
         monthly_color = "red"
    else:
        # 평시 (RSI 기반)
        if qqq_rsi >= rsi_sell_threshold: # [Ver 19.3] 동적 임계값 적용 (80 or 75)
             monthly_msg = f"💤 **과열 (RSI {rsi_sell_threshold}+)**: 매수 금지. 월급은 현금으로 B계좌에 저축."
        elif qqq_rsi >= 60:
             buy_amt_monthly = st.session_state.monthly_contribution * target_stock_ratio
             monthly_msg = f"✅ **표준**: 월급의 {target_stock_ratio*100:.0f}% ({format_krw(buy_amt_monthly)}) 매수 (TQQQ:USD = 1:1)."
        else:
             # 기회 구간
             if total_cash_krw > (total_assets * target_cash_ratio):
                 buy_amt_monthly = (st.session_state.monthly_contribution * target_stock_ratio) * 1.5
                 monthly_msg = f"💰 **기회 (Cash Rich)**: 1.5배 가속 ({format_krw(buy_amt_monthly)}) 매수 (TQQQ:USD = 1:1)."
             else:
                 squeeze_ratio = min(target_stock_ratio + 0.1, 1.0)
                 buy_amt_monthly = st.session_state.monthly_contribution * squeeze_ratio
                 monthly_msg = f"🩸 **기회 (Squeeze)**: 쥐어짜기 ({format_krw(buy_amt_monthly)}) 매수 (TQQQ:USD = 1:1)."
    
    # [Ver 20.4] 일일 적립액 및 스마트 비율 계산
    if "매수" in monthly_msg and "금지" not in monthly_msg:
        # 매수 금액 추출 (전시 상황 or 평시)
        if qqq_mdd <= -0.3:
            buy_amt = st.session_state.monthly_contribution
        elif qqq_rsi >= 60:
            buy_amt = st.session_state.monthly_contribution * target_stock_ratio
        else:
            # 기회 구간
            if total_cash_krw > (total_assets * target_cash_ratio):
                buy_amt = (st.session_state.monthly_contribution * target_stock_ratio) * 1.5
            else:
                squeeze_ratio = min(target_stock_ratio + 0.1, 1.0)
                buy_amt = st.session_state.monthly_contribution * squeeze_ratio
        
        daily_amt = buy_amt / 20
        
        # [Ver 20.6] 스마트 리밸런싱 - 매도 없이 월 적립으로만 50:50 복원
        tqqq_current_ratio = total_tqqq_krw / total_stock_krw if total_stock_krw > 0 else 0.5
        usd_current_ratio = total_usd_krw / total_stock_krw if total_stock_krw > 0 else 0.5
        
        # 기본 50:50
        tqqq_input_ratio = 0.5
        usd_input_ratio = 0.5
        balance_msg = ""
        
        # 동적 조정: 현재 비중 차이에 따라 10:0 ~ 0:10까지 가능
        # 목표: 적은 쪽에 100% 투입하여 최대한 빠르게 리밸런싱
        ratio_gap = abs(tqqq_current_ratio - 0.5)
        
        if ratio_gap > 0.05:  # 5%p 이상 벌어졌을 때만 조정
            if tqqq_current_ratio > 0.5:  # TQQQ 과중 -> USD만 매수
                # TQQQ가 55%면 USD에 100% 투입
                # TQQQ가 70%면 USD에 100% 투입
                usd_input_ratio = 1.0
                tqqq_input_ratio = 0.0
                balance_msg = f"⚖️ **리밸런싱 모드**: TQQQ {tqqq_current_ratio*100:.1f}% → USD만 매수하여 50:50 복원 중"
            else:  # USD 과중 -> TQQQ만 매수
                tqqq_input_ratio = 1.0
                usd_input_ratio = 0.0
                balance_msg = f"⚖️ **리밸런싱 모드**: USD {usd_current_ratio*100:.1f}% → TQQQ만 매수하여 50:50 복원 중"
        
        tqqq_daily = daily_amt * tqqq_input_ratio
        usd_daily = daily_amt * usd_input_ratio
        
        monthly_msg += f"\n\n📅 **[일일 자동 적립 가이드 (20거래일 기준)]**\n"
        monthly_msg += f"- **총 일일 매수금:** {format_krw(daily_amt)}\n"
        monthly_msg += f"- **TQQQ ({int(tqqq_input_ratio*100)}%):** {format_krw(tqqq_daily)}\n"
        monthly_msg += f"- **USD ({int(usd_input_ratio*100)}%):** {format_krw(usd_daily)}\n"
        if balance_msg:
            monthly_msg += f"\n{balance_msg}"

    # --- 2. 보유 자산 운용 (Asset Management) ---
    final_action = ""
    detail_msg = ""
    action_color = "blue"
    
    # Ver 20.0 Dual Engine Rebalancing Logic
    # 1. TQQQ vs USD 비율 체크 (50:50)
    tqqq_ratio = total_tqqq_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    usd_ratio = total_usd_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    
    # 리밸런싱 트리거 (10%p 이상 벌어졌을 때 - 세금/수수료 최소화)
    need_dual_rebalance = False
    dual_msg = ""
    if abs(tqqq_ratio - 0.5) > 0.1:
        need_dual_rebalance = True
        if tqqq_ratio > 0.5:
            sell_target = "TQQQ"
            buy_target = "USD"
            amt = (total_tqqq_krw - total_usd_krw) / 2
        else:
            sell_target = "USD"
            buy_target = "TQQQ"
            amt = (total_usd_krw - total_tqqq_krw) / 2
        dual_msg = f"⚖️ **듀얼 리밸런싱:** {sell_target} {format_krw(amt)} 매도 -> {buy_target} 매수 (비중 5:5 맞춤)"

    if qqq_rsi >= rsi_sell_threshold: # [Ver 19.3] 동적 임계값 적용
        target_cash_panic = target_cash_ratio + 0.1
        target_cash_amt = total_assets * target_cash_panic
        sell_needed = target_cash_amt - total_cash_krw
        if sell_needed > 0:
            final_action = f"🚨 PANIC SELL (광기/방어 매도 - RSI {rsi_sell_threshold})"
            detail_msg = f"RSI {rsi_sell_threshold} 돌파. {format_krw(sell_needed)} 매도하여 현금 {target_cash_panic*100:.0f}% 확보.\n\n⚠️ TQQQ와 USD를 비중대로 매도하십시오.\n⚠️ [Tax Rule] 실현 수익금의 22%는 즉시 [계좌 C]로 이체하십시오."
            action_color = "red"
        else:
            final_action = "✅ HOLD (현금 충분)"
            detail_msg = f"RSI {rsi_sell_threshold}이나 현금이 충분합니다. 대기."

    elif qqq_mdd <= -0.15: # [Ver 19.3.3] 진입 시점 -15%로 최적화 (-15, -25, -35, -45)
        input_cash = 0
        ratio_str = ""
        level_str = ""
        
        if qqq_mdd <= -0.5: 
            input_cash = total_cash_krw # 남은 잔돈 처리
            ratio_str="100% (Last Bullet)"
            level_str = "지옥 (Hell)"
        elif qqq_mdd <= -0.45:
            input_cash = total_cash_krw * 0.2
            ratio_str="20% (All-In)"
            level_str = "시스템 붕괴 (All-In)"
        elif qqq_mdd <= -0.35:
            input_cash = total_cash_krw * 0.3
            ratio_str="30%"
            level_str = "금융위기"
        elif qqq_mdd <= -0.25:
            input_cash = total_cash_krw * 0.3
            ratio_str="30%"
            level_str = "약세장 (Bear Market)"
        elif qqq_mdd <= -0.15:
            input_cash = total_cash_krw * 0.2
            ratio_str="20%"
            level_str = "깊은 조정 (Deep Correction)"
            
        final_action = f"📉 CRISIS BUY ({level_str})"
        detail_msg = f"MDD {qqq_mdd*100:.1f}%. 현금 {ratio_str} ({format_krw(input_cash)}) 투입."
        if need_dual_rebalance:
            detail_msg += f"\n\n{dual_msg}"
        action_color = "green"

    elif current_stock_ratio > (target_stock_ratio + 0.1):
        sell_amt = total_stock_krw - (total_assets * target_stock_ratio)
        final_action = "⚖️ REBALANCE SELL (과열 방지)"
        detail_msg = f"비중 초과. {format_krw(sell_amt)} 매도.\n\n⚠️ TQQQ/USD 중 비중 높은 것을 우선 매도하십시오.\n⚠️ [Tax Rule] 실현 수익금의 22%는 즉시 [계좌 C]로 이체하십시오."
        if need_dual_rebalance:
            detail_msg += f"\n\n{dual_msg}"
        action_color = "orange"
        
    elif current_stock_ratio < (target_stock_ratio - 0.1):
        buy_amt = (total_assets * target_stock_ratio) - total_stock_krw
        final_action = "⚖️ REBALANCE BUY (저점 매수)"
        detail_msg = f"비중 미달. {format_krw(buy_amt)} 매수."
        if need_dual_rebalance:
            detail_msg += f"\n\n{dual_msg}"
        action_color = "green"

    else:
        if need_dual_rebalance:
            final_action = "⚖️ DUAL REBALANCE (엔진 균형)"
            detail_msg = dual_msg
            action_color = "orange"
        else:
            final_action = "🧘 STABLING (관망)"
            detail_msg = "특이사항 없음. 포트폴리오 유지."

    # --- 3. 최상위 헌법: 손실 방어 (Loss Protection) ---
    # 손실 중인데 '매도' 시그널이 떴다면 -> 강제로 'HOLD'로 변경
    if is_loss and ("매도" in final_action or "SELL" in final_action):
        final_action = "🛡️ LOSS PROTECTION (절대 방어)"
        detail_msg = f"시스템이 매도 신호를 감지했으나, **현재 손실 중**이므로 헌법 제1조에 의거하여 **매도를 금지(HOLD)**합니다."
        action_color = "red"
        # 매도 가이드 메시지 무효화
        sell_guide_msg = "🚫 **손실 중입니다. 매도 버튼에 손대지 마십시오.**"

    st.info(f"💡 **보유 자산 실행 (Asset Action):** {final_action}")
    
    if action_color == "red": st.error(detail_msg)
    elif action_color == "green": st.success(detail_msg)
    elif action_color == "orange": st.warning(detail_msg)
    else: st.info(detail_msg)
    
    # 월급 행동 출력 (항상 표시)
    st.markdown("---")
    st.caption("📅 **월급 투입 지침 (Monthly Input)**")
    if monthly_color == "red": st.error(monthly_msg)
    else: st.info(monthly_msg)

    if "매도" in final_action or "SELL" in final_action:
        st.markdown(f"🔥 {sell_guide_msg}")
    elif "매수" in final_action or "BUY" in final_action:
         st.markdown(f"💰 **매수는 [A계좌: 금고] 우선, 단기는 [B계좌] 활용**")

    # --- 4. 차트 ---
    st.markdown("---")
    with st.expander("📊 차트 확인 (Daily / Weekly / Monthly)", expanded=True):
        tab1, tab2, tab3 = st.tabs(["일봉 (Daily)", "주봉 (Weekly)", "월봉 (Monthly)"])
        
        def draw_chart(df, title):
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Candle')])
            
            # 이동평균선
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1), name='MA 20'))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='blue', width=1), name='MA 60'))
            
            fig.update_layout(title=title, height=400, margin=dict(l=20, r=20, t=40, b=20), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # RSI 차트
            fig_rsi = go.Figure(data=[go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'))])
            fig_rsi.add_hline(y=80, line_color="red", line_dash="dash")
            fig_rsi.add_hline(y=60, line_color="green", line_dash="dash")
            fig_rsi.update_layout(title=f'{title} - RSI', height=200, yaxis_range=[0, 100], margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_rsi, use_container_width=True)

        with tab1:
            draw_chart(df_dy, "QQQ Daily Chart")
        
        with tab2:
            draw_chart(df_wk, "QQQ Weekly Chart")
            
        with tab3:
            draw_chart(df_mo, "QQQ Monthly Chart")

    # --- 5. 릴리즈 노트 (Update History) ---
    st.markdown("---")
    with st.expander("📅 릴리즈 노트 (Update History)", expanded=False):
        try:
            with open("ReleaseNotes.md", "r", encoding="utf-8") as f:
                release_notes = f.read()
            st.markdown(release_notes)
        except Exception as e:
            st.warning("릴리즈 노트를 불러올 수 없습니다.")
    
    # --- 6. 코어 로직 (Master Protocol) ---
    st.markdown("---")
    with st.expander("🏛️ 코어 로직 (Master Protocol)", expanded=False):
        try:
            with open("TradingCoreLogic.md", "r", encoding="utf-8") as f:
                core_logic = f.read()
            st.markdown(core_logic)
        except Exception as e:
            st.warning("코어 로직 문서를 불러올 수 없습니다.")

else:
    st.warning("데이터 로딩 중... (잠시만 기다려주세요)")
