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
st.set_page_config(page_title="Global Fire CRO V22.4", layout="wide", page_icon="🔥")

PHASE_CONFIG = {
    0: {"limit": 100000000, "target_stock": 0.9, "target_cash": 0.1, "name": "Phase 0 (Seed)"},
    1: {"limit": 300000000, "target_stock": 0.8, "target_cash": 0.2, "name": "Phase 1 (Standard)"},
    2: {"limit": 700000000, "target_stock": 0.7, "target_cash": 0.3, "name": "Phase 2 (Defense)"},
    3: {"limit": 1500000000, "target_stock": 0.6, "target_cash": 0.4, "name": "Phase 3 (Critical Mass)"},
    4: {"limit": 2500000000, "target_stock": 0.5, "target_cash": 0.5, "name": "Phase 4 (Retirement Prep)"},
    5: {"limit": float('inf'), "target_stock": 0.4, "target_cash": 0.6, "name": "Phase 5 (Final Exit)"}
}

PROTOCOL_TEXT = """
### 📜 Master Protocol (요약) - Ver 22.4 Daily Defense
1.  **[헌법] 손실 중 매도 금지:** 계좌가 마이너스면 RSI가 100이어도 절대 팔지 않는다.
2.  **[겨울] 200일선 붕괴:** QQQ가 일봉 200선 아래로 내려가면 '겨울' 선포. (현금 비중 50% 미만일 때만 확보)
3.  **[봄의 귀환] 4주 분할 매수:** 겨울 → 봄 전환 시, 1개월간 분할 매수로 신중하게 진입한다.
4.  **[스나이퍼] 역피라미드:** 하락할수록 더 많이 산다 (10% -> 20% -> 30% -> 40%).
5.  **[광기] RSI 80:** (봄 시즌 중) 현금 비중을 Target + 10%까지 늘린다.
6.  **[듀얼] 50:50:** TQQQ와 USD 비중이 10%p 이상 벌어지면 리밸런싱.
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
        
        # [Ver 22.5] SOXX (반도체 지수 - 계절 판단용 & 차트용)
        soxx_dy = yf.download("SOXX", interval="1d", period="1y", progress=False, auto_adjust=False)
        soxx_wk = yf.download("SOXX", interval="1wk", period="2y", progress=False, auto_adjust=False)
        soxx_mo = yf.download("SOXX", interval="1mo", period="5y", progress=False, auto_adjust=False)
        
        # 매크로 지표 (VIX, 10년물, 3개월물) - 1년치 데이터 (추세 분석용)
        vix = yf.download("^VIX", period="1y", progress=False, auto_adjust=False)
        tnx = yf.download("^TNX", period="1y", progress=False, auto_adjust=False) # 10년물
        irx = yf.download("^IRX", period="1y", progress=False, auto_adjust=False) # 3개월물
        
        # 환율
        exch = yf.download("KRW=X", period="1d", progress=False, auto_adjust=False)
        
        if qqq_wk.empty or exch.empty or tqqq_wk.empty or usd_wk.empty or soxx_dy.empty: return None

        # MultiIndex 정리
        for d in [qqq_dy, qqq_wk, qqq_mo, tqqq_wk, tqqq_mo, usd_wk, usd_mo, soxx_dy, soxx_wk, soxx_mo, exch, vix, tnx, irx]:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)

        current_rate = float(exch['Close'].iloc[-1])
        
        # QQQ 지표 & 이동평균선
        qqq_price = float(qqq_wk['Close'].iloc[-1])
        
        # MA 계산 (일/주/월) - QQQ & SOXX & TQQQ & USD 일괄 처리
        for d in [qqq_dy, qqq_wk, qqq_mo, soxx_dy, soxx_wk, soxx_mo, tqqq_wk, tqqq_mo, usd_wk, usd_mo]:
            d['MA20'] = d['Close'].rolling(window=20).mean()
            d['MA40'] = d['Close'].rolling(window=40).mean() # 40주선 추가 (Winter Protocol)
            d['MA60'] = d['Close'].rolling(window=60).mean()
            d['MA200'] = d['Close'].rolling(window=200).mean() # 200일선 추가
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
        
        # VIX 5일 안착 여부 (참고용으로 유지)
        is_vix_trend = False
        if len(vix) >= 5:
            vix_recent_min = vix['Close'].tail(5).min()
            is_vix_trend = (vix_recent_min >= 20.0)
        else:
            is_vix_trend = (vix_val >= 20.0)

        # 금리차 역전 후 정상화 (참고용으로 유지)
        is_spread_normalization = False
        spread_series = None
        if not tnx.empty and not irx.empty:
            spread_series = tnx['Close'] - irx['Close']
            spread_recent = spread_series.tail(126) # 6개월
            was_inverted = (spread_recent < 0).any()
            is_positive_now = (spread_series.iloc[-1] >= 0)
            
            if was_inverted and is_positive_now:
                is_spread_normalization = True

        # [Ver 22.5] Winter Protocol & Spring Re-entry (Dual Check)
        is_winter_mode = False
        is_spring_reentry = False
        
        # 1. 현재 상태 체크 (QQQ & SOXX)
        qqq_ma200_dy = float(qqq_dy['MA200'].iloc[-1])
        qqq_price_dy = float(qqq_dy['Close'].iloc[-1])
        
        soxx_ma200_dy = float(soxx_dy['MA200'].iloc[-1])
        soxx_price_dy = float(soxx_dy['Close'].iloc[-1])
        
        # 하나라도 200일선 아래면 겨울
        if (not pd.isna(qqq_ma200_dy) and qqq_price_dy < qqq_ma200_dy) or \
           (not pd.isna(soxx_ma200_dy) and soxx_price_dy < soxx_ma200_dy):
            is_winter_mode = True
        
        # 2. Re-entry 감지 (어제는 겨울 -> 오늘은 봄 + 필터 충족)
        # 단, app.py는 실시간이므로 '현재'가 봄이어야 Re-entry 후보가 됨
        if not is_winter_mode and len(qqq_dy) >= 4:
             # 어제 상태 확인 (어제 종가 기준 하나라도 아래였어야 함)
             yesterday_qqq = float(qqq_dy['Close'].iloc[-2])
             yesterday_qqq_ma = float(qqq_dy['MA200'].iloc[-2])
             yesterday_soxx = float(soxx_dy['Close'].iloc[-2])
             yesterday_soxx_ma = float(soxx_dy['MA200'].iloc[-2])
             
             was_winter_yesterday = (yesterday_qqq < yesterday_qqq_ma) or (yesterday_soxx < yesterday_soxx_ma)
             
             # 만약 어제도 겨울이었고, 오늘 비로소 둘 다 위로 올라왔다면 -> Re-entry Check 시작
             # 하지만 'Re-entry'는 봄 초입 기간(약 1달)을 의미하므로, 
             # 여기서는 "완전히 안전한 봄인가?"를 판단하는 필터를 적용.
             
             # Filter: 3일 연속 유지 OR 3% 이상 상승 (QQQ 기준 or 둘다? -> QQQ 기준 적용)
             # QQQ가 시장 대표성이 크므로 QQQ 필터를 메인으로 함. (SOXX는 트리거 역할)
             
             # Filter 1: 3일 연속 200일선 위 (Time Filter)
             q_d0 = qqq_dy.iloc[-1]; q_d1 = qqq_dy.iloc[-2]; q_d2 = qqq_dy.iloc[-3]
             is_3days_safe = (q_d0['Close'] > q_d0['MA200']) and \
                             (q_d1['Close'] > q_d1['MA200']) and \
                             (q_d2['Close'] > q_d2['MA200'])
                             
             # Filter 2: 3% 이상 상승 (Price Filter)
             is_3pct_safe = qqq_price_dy >= (qqq_ma200_dy * 1.03)
             
             # 필터 통과 여부
             is_confirmed_spring = is_3days_safe or is_3pct_safe
             
             # Re-entry 모드 표시 조건:
             # 1. 기본 봄 조건 충족 (둘 다 > 200MA) -> 이미 is_winter_mode = False 상태
             # 2. 필터는 아직 통과 못했거나(불안), 갓 통과해서 진입해야 하는 시점.
             
             # 로직 단순화:
             # 겨울이 아니다 = 일단 봄.
             # 근데 필터를 통과 못했으면 -> "불안한 봄 (Wait)" or "Re-entry 대기"
             # 필터를 통과 했으면 -> "Re-entry 진입" (초기) or "완연한 봄"
             
             # 여기서는 '봄의 귀환' 메시지를 띄우기 위해, 
             # "어제는 겨울이었는데 오늘은 봄(필터 미확정 포함)" 이면 Re-entry 모드로 간주하고
             # 메인 로직에서 세부 가이드를 줌.
             
             if was_winter_yesterday:
                 is_spring_reentry = True
             
             # 추가: 만약 최근 20일 내에 골든크로스가 발생했다면 계속 Re-entry 모드로 볼 수도 있음.
             # 하지만 복잡도를 줄이기 위해, app.py에서는 '어제 vs 오늘' 변화만 감지하거나
             # 혹은 '필터 통과 여부' 정보를 리턴해서 메인에서 처리.

        # [Ver 20.2] CNN 공포탐욕지수 (Fear & Greed Index)
        fear_greed_value = 50  # 기본값 (중립)
        fear_greed_text = "Neutral"
        try:
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
            try:
                response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    fear_greed_value = int(data['data'][0]['value'])
                    fear_greed_text = data['data'][0]['value_classification']
            except:
                pass

        # [Ver 20.2] 버핏지수 (Buffett Indicator)
        buffett_indicator = 0
        m2_money_stock = 0
        try:
            wilshire_full = yf.download("^W5000FLT", period="5d", progress=False, auto_adjust=False)
            if not wilshire_full.empty:
                if isinstance(wilshire_full.columns, pd.MultiIndex):
                    wilshire_full.columns = wilshire_full.columns.get_level_values(0)
                wilshire_full_val = float(wilshire_full['Close'].iloc[-1])
                market_cap_trillion = wilshire_full_val / 1000
                us_gdp_trillion = 28.27
                buffett_indicator = (market_cap_trillion / us_gdp_trillion) * 100
                m2_money_stock = 21.17
            else:
                wilshire = yf.download("^W5000", period="5d", progress=False, auto_adjust=False)
                if not wilshire.empty:
                    if isinstance(wilshire.columns, pd.MultiIndex):
                        wilshire.columns = wilshire.columns.get_level_values(0)
                    wilshire_val = float(wilshire['Close'].iloc[-1])
                    market_cap_trillion = wilshire_val / 1000
                    us_gdp_trillion = 28.27
                    buffett_indicator = (market_cap_trillion / us_gdp_trillion) * 100
                    m2_money_stock = 21.17
        except:
            buffett_indicator = 0

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
            'is_winter_mode': is_winter_mode,
            'is_spring_reentry': is_spring_reentry,
            'qqq_ma200_dy': qqq_ma200_dy,
            'soxx_dy': soxx_dy,
            'soxx_wk': soxx_wk,
            'soxx_mo': soxx_mo,
            'tqqq_wk': tqqq_wk,
            'tqqq_mo': tqqq_mo,
            'usd_wk': usd_wk,
            'usd_mo': usd_mo,
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
st.markdown("**Ver 22.5 (Semiconductor Watch)** | System Owner: **Busan Programmer** | Benchmark: **QQQ & SOXX**")

# 데이터 로드 (초기화)
saved_data = load_data()

# Session State 초기화 (없으면 파일 값으로)
if "monthly_contribution" not in st.session_state:
    for key, val in saved_data.items():
        if key in saved_data:
            st.session_state[key] = saved_data[key]
        if "qty" in key or "avg" in key or "contribution" in key:
                try:
                    st.session_state[key] = float(st.session_state[key])
                except:
                    pass

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
        st.caption(f"👉 확인: **{format_krw(st.session_state.monthly_contribution)}**")
        
        st.markdown("---")
        
        # A계좌
        with st.expander("🏦 계좌 A: 금고 (장기)", expanded=True):
            st.number_input("A: TQQQ 보유 수량", min_value=0.0, step=0.01, key="a_tqqq_qty", format="%.2f")
            st.number_input("A: TQQQ 평균단가 (KRW)", min_value=0, step=100, key="a_tqqq_avg", format="%d")
            st.markdown("---")
            st.number_input("A: USD 보유 수량", min_value=0.0, step=0.01, key="a_usd_qty", format="%.2f")
            st.number_input("A: USD 평균단가 (KRW)", min_value=0, step=100, key="a_usd_avg", format="%d")
            
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
        submit_button = st.form_submit_button("💾 자산 정보 저장 및 업데이트", use_container_width=True)
        if submit_button:
            save_data()
            st.success("✅ 저장 완료!")
    
    # --- 자동 손익 판단 로직 ---
    tqqq_qty = st.session_state.a_tqqq_qty + st.session_state.b_tqqq_qty
    usd_qty = st.session_state.a_usd_qty + st.session_state.b_usd_qty
    
    tqqq_invested = (st.session_state.a_tqqq_qty * st.session_state.a_tqqq_avg) + \
                    (st.session_state.b_tqqq_qty * st.session_state.b_tqqq_avg)
    usd_invested = (st.session_state.a_usd_qty * st.session_state.a_usd_avg) + \
                   (st.session_state.b_usd_qty * st.session_state.b_usd_avg)
                   
    total_invested_krw = tqqq_invested + usd_invested
    
    total_tqqq_krw = tqqq_qty * tqqq_krw
    total_usd_krw = usd_qty * usd_stock_krw
    total_stock_krw = total_tqqq_krw + total_usd_krw
    
    profit_rate = 0.0
    if total_invested_krw > 0:
        profit_rate = ((total_stock_krw - total_invested_krw) / total_invested_krw) * 100
    
    is_loss = profit_rate < 1.5 if total_invested_krw > 0 else False

    # --- 계산 로직 ---
    total_cash_krw = (st.session_state.a_cash_krw + st.session_state.b_cash_krw + st.session_state.c_cash_krw) + \
                     ((st.session_state.a_cash_usd + st.session_state.b_cash_usd) * usd_krw_rate)
    total_assets = total_stock_krw + total_cash_krw
    
    # --- 1. 시장 상황판 (먼저 표시하여 변수 정의) ---
    st.header("1. 시장 상황판 (Market Status)")
    
    # [Ver 22.5] Winter Protocol Monitor
    with st.expander("🚨 계절 모니터링 (Season Check)", expanded=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            # 200일선 상태 (QQQ & SOXX)
            q_ma = mkt['qqq_dy']['MA200'].iloc[-1]
            q_pr = mkt['qqq_dy']['Close'].iloc[-1]
            q_st = "🟢 봄" if q_pr >= q_ma else "❄️ 겨울"
            
            s_ma = mkt['soxx_dy']['MA200'].iloc[-1]
            s_pr = mkt['soxx_dy']['Close'].iloc[-1]
            s_st = "🟢 봄" if s_pr >= s_ma else "❄️ 겨울"

            trend_status = "🟢 봄 (Spring)"
            if mkt['is_winter_mode']: trend_status = "🔴 겨울 (Winter)"
            
            st.markdown(f"""
            **시스템 계절 판단:**
            *   **종합 상태:** **[{trend_status}]** (둘 중 하나라도 겨울이면 겨울)
            *   **QQQ:** {q_st} (${q_pr:.2f} vs 200선 ${q_ma:.2f})
            *   **SOXX:** {s_st} (${s_pr:.2f} vs 200선 ${s_ma:.2f})
            """)
        with c2:
            season_manual = st.checkbox("❄️ 겨울 강제 선포", value=False, help="시스템 판단 외에 CRO 판단으로 겨울 모드를 강제할 때 체크")

    # Phase 결정 및 모드 설정
    current_phase = determine_phase(total_assets)
    base_target_stock = PHASE_CONFIG[current_phase]['target_stock']
    base_target_cash = PHASE_CONFIG[current_phase]['target_cash']
    
    # [Ver 22.5] 겨울 모드 발동 로직
    is_winter = mkt['is_winter_mode'] or season_manual
    
    if is_winter: 
        if not season_manual:
            st.toast(f"❄️ 겨울이 왔습니다! (200일선 붕괴) 방어 태세 전환.", icon="🥶")
        target_stock_ratio = 0.5 
        target_cash_ratio = 0.5 
        rsi_sell_threshold = 75 
        mode_label = "❄️ 겨울 모드 (Winter Protocol)"
    else:
        # 봄 모드 (정상 Glide Path)
        target_stock_ratio = base_target_stock
        target_cash_ratio = base_target_cash
        rsi_sell_threshold = 80
        mode_label = "🌸 봄 모드 (Spring Protocol)"
        
        # [Priority 2.5] 봄의 귀환 체크
        if mkt['is_spring_reentry']:
            # Re-entry 필터 통과 여부 확인 (3일 유지 or 3% 상승)
            q_d = mkt['qqq_dy']
            q_ma = q_d['MA200'].iloc[-1]
            q_pr = q_d['Close'].iloc[-1]
            
            # 필터 1: 3일 연속
            d0=q_d.iloc[-1]; d1=q_d.iloc[-2]; d2=q_d.iloc[-3]
            is_3days = (d0['Close']>d0['MA200']) and (d1['Close']>d1['MA200']) and (d2['Close']>d2['MA200'])
            
            # 필터 2: 3% 상승
            is_3pct = q_pr >= (q_ma * 1.03)
            
            if is_3days or is_3pct:
                st.toast("🌱 봄의 귀환! 필터 통과 (Re-entry Confirmed).", icon="✅")
                mode_label = "🌱 봄의 귀환 (Re-entry Confirmed)"
            else:
                st.toast("⚠️ 봄의 귀환 감지 (검증 대기중...)", icon="⏳")
                mode_label = "⏳ 봄의 귀환 (검증 대기: 3일 or +3%)"
    
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

    # USD Info
    u1, u2, u3, u4 = st.columns(4)
    u1.metric("USD 현재가", f"${mkt['usd_price']:.2f} ({format_krw(mkt['usd_price']*usd_krw_rate)})")
    u2.metric("USD 월봉 RSI", f"{mkt['usd_rsi_mo']:.1f}", "Month Trend")
    u3.metric("USD 주봉 RSI", f"{mkt['usd_rsi_wk']:.1f}", get_rsi_status(mkt['usd_rsi_wk']))
    u4.metric("USD MDD", f"{mkt['usd_mdd']*100:.2f}%", get_mdd_status(mkt['usd_mdd']))

    # Macro Info (참고용)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    vix = mkt['vix']
    vix_label = "✅ 안정" if vix < 20 else ("🚨 공포" if vix > 30 else "🛡️ 방어")
    m1.metric("VIX (변동성)", f"{vix:.2f}", vix_label)
    
    tnx = mkt['tnx']
    m2.metric("US 10Y (국채금리)", f"{tnx:.2f}%")
    
    spread = mkt['yield_spread']
    spread_msg = "✅ 정상" if spread > 0 else "🚨 역전"
    if mkt['is_spread_normalization']: spread_msg = "⚠️ 정상화 중"
    m3.metric("10Y-3M 금리차", f"{spread:.2f}%p", spread_msg)
    
    fg_val = mkt['fear_greed_value']
    fg_text = mkt['fear_greed_text']
    fg_emoji = "😐 중립" # Default
    if fg_val <= 25: fg_emoji = "😱 극도 공포"
    elif fg_val <= 45: fg_emoji = "😰 공포"
    elif fg_val <= 55: fg_emoji = "😐 중립"
    elif fg_val <= 75: fg_emoji = "😊 탐욕"
    else: fg_emoji = "🤑 극도 탐욕"
    m4.metric("공포탐욕지수", f"{fg_val}", fg_emoji)
    
    buffett = mkt['buffett_indicator']
    buffett_label = "✅ 적정"
    if buffett > 200: buffett_label = "💥 역사적 버블"
    elif buffett > 135: buffett_label = "🚨 고평가"
    m5.metric("버핏지수", f"{buffett:.1f}%", buffett_label)
    
    m6.empty() 

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

    # 1단: 통합 정보
    st.markdown("### 📊 통합 포트폴리오")
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
    
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
    row2_col1.metric("총 주식 평가금", format_krw(total_stock_krw))
    row2_col2.metric("총 현금 보유액", format_krw(total_cash_krw))
    
    tqqq_ratio_display = total_tqqq_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    usd_ratio_display = total_usd_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    tqqq_pct = int(tqqq_ratio_display * 100)
    usd_pct = int(usd_ratio_display * 100)
    row2_col3.metric("주식 비중", 
                     f"{current_stock_ratio*100:.1f}%", 
                     f"목표: {target_stock_ratio*100:.0f}% (TQ {tqqq_pct}:{usd_pct} USD)")
    row2_col4.metric("현금 비중", f"{current_cash_ratio*100:.1f}%", f"목표: {target_cash_ratio*100:.0f}%")

    # 2단: 상세 정보
    st.markdown("### 🚀 TQQQ & USD 상세")
    c_t1, c_t2, c_t3, c_u1, c_u2, c_u3 = st.columns(6)
    
    tqqq_avg = tqqq_invested / tqqq_qty if tqqq_qty > 0 else 0
    tqqq_profit = ((total_tqqq_krw - tqqq_invested) / tqqq_invested * 100) if tqqq_invested > 0 else 0
    c_t1.metric("TQQQ 수량", f"{tqqq_qty:.2f}주")
    c_t2.metric("TQQQ 평가금", format_krw(total_tqqq_krw))
    c_t3.metric("TQQQ 수익률", f"{tqqq_profit:.2f}%", "🔴" if tqqq_profit >= 0 else "🔵")

    usd_avg = usd_invested / usd_qty if usd_qty > 0 else 0
    usd_profit = ((total_usd_krw - usd_invested) / usd_invested * 100) if usd_invested > 0 else 0
    c_u1.metric("USD 수량", f"{usd_qty:.2f}주")
    c_u2.metric("USD 평가금", format_krw(total_usd_krw))
    c_u3.metric("USD 수익률", f"{usd_profit:.2f}%", "🔴" if usd_profit >= 0 else "🔵")

    st.markdown("---")
    if is_loss: st.error("🛑 [손실 중] 절대 방패 가동: 매도 금지 (헌법 제1조)")
    else: st.success("✅ [수익 중] 정상 로직 가동")

    # --- 3. CRO 실행 명령 ---
    st.markdown("---")
    st.header("3. CRO 실행 명령 (Action Protocol)")
    
    # 1. 월급 매수 가이드
    monthly_msg = ""
    monthly_color = "blue"
    
    # [Ver 22.3] Winter Protocol: 겨울엔 매수 금지 (단, -25% 스나이핑 시 참여 가능)
    if is_winter:
        if qqq_mdd <= -0.25:
             buy_amt_monthly = st.session_state.monthly_contribution
             monthly_msg = f"📉 **겨울장 스나이핑 (MDD -25%↓)**: 월급 100% ({format_krw(buy_amt_monthly)}) TQQQ & USD 분할 매수 (스나이퍼 지원사격)."
             monthly_color = "red"
        else:
             monthly_msg = f"❄️ **겨울 (Winter)**: 매수 금지. 월급 100% 현금(달러)으로 적립."
    else:
        # 봄 (Spring) - 기존 로직
        if qqq_rsi >= rsi_sell_threshold:
             monthly_msg = f"💤 **과열 (RSI {rsi_sell_threshold}+)**: 매수 금지. 월급은 현금 적립."
        elif qqq_rsi >= 60:
             buy_amt_monthly = st.session_state.monthly_contribution * target_stock_ratio
             monthly_msg = f"✅ **표준**: 월급의 {target_stock_ratio*100:.0f}% ({format_krw(buy_amt_monthly)}) 매수."
        else:
             # 기회 구간
             if total_cash_krw > (total_assets * target_cash_ratio):
                 buy_amt_monthly = (st.session_state.monthly_contribution * target_stock_ratio) * 1.5
                 monthly_msg = f"💰 **기회 (Cash Rich)**: 1.5배 가속 ({format_krw(buy_amt_monthly)}) 매수."
             else:
                 squeeze_ratio = min(target_stock_ratio + 0.1, 1.0)
                 buy_amt_monthly = st.session_state.monthly_contribution * squeeze_ratio
                 monthly_msg = f"🩸 **기회 (Squeeze)**: 쥐어짜기 ({format_krw(buy_amt_monthly)}) 매수."

    # 2. 보유 자산 운용
    final_action = ""
    detail_msg = ""
    action_color = "blue"
    
    # Dual Rebalance Check
    tqqq_ratio = total_tqqq_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    need_dual_rebalance = False
    dual_msg = ""
    if abs(tqqq_ratio - 0.5) > 0.1: # 10%p 차이
        need_dual_rebalance = True
        if tqqq_ratio > 0.5:
            dual_msg = "⚖️ **듀얼 리밸런싱:** TQQQ 일부 매도 -> USD 매수"
        else:
            dual_msg = "⚖️ **듀얼 리밸런싱:** USD 일부 매도 -> TQQQ 매수"

    # Action Logic
    if is_winter:
        # 겨울 행동 강령
        if current_cash_ratio < 0.5:
             sell_needed = (total_assets * 0.5) - total_cash_krw
             final_action = "❄️ WINTER DEFENSE (현금 확보)"
             detail_msg = f"겨울이 왔습니다. 현금 비중 50% 미만입니다.\n{format_krw(sell_needed)} 매도하여 현금 50%를 맞추십시오."
             action_color = "red"
        else:
             final_action = "❄️ WINTER HOLD (관망)"
             detail_msg = "겨울이지만 이미 현금 비중이 50% 이상입니다. 추가 매도 없이 관망하십시오."
             
        # 겨울에도 스나이핑은 작동 (-25% 부터)
        if qqq_mdd <= -0.25:
             # 역피라미드 비중 (Ver 22.3)
             input_cash = 0
             ratio_str = ""
             if qqq_mdd <= -0.45:
                 input_cash = total_cash_krw * 0.4
                 ratio_str="40% (Last Bullet)"
             elif qqq_mdd <= -0.35:
                 input_cash = total_cash_krw * 0.3
                 ratio_str="30%"
             elif qqq_mdd <= -0.25:
                 input_cash = total_cash_krw * 0.2
                 ratio_str="20% (Entry)"
            
             final_action = f"📉 WINTER SNIPER ({ratio_str})"
             detail_msg = f"겨울장 폭락(MDD {qqq_mdd*100:.1f}%) 기회입니다. 현금 {ratio_str} ({format_krw(input_cash)}) 투입."
             action_color = "green"

    else:
        # 봄 (Spring) 행동 강령
        
        # [Priority 2.5] 봄의 귀환 (Spring Re-entry)
        # 이번 주가 봄으로 바뀐 '첫 주'라면 분할 매수 가이드 출력
        if mkt['is_spring_reentry']:
            input_cash_total = (total_assets * target_stock_ratio) - total_stock_krw
            input_cash_weekly = input_cash_total / 4
            
            # 필터 상태 확인
            q_d = mkt['qqq_dy']
            q_ma = q_d['MA200'].iloc[-1]
            q_pr = q_d['Close'].iloc[-1]
            is_3days = (q_d.iloc[-1]['Close']>q_d.iloc[-1]['MA200']) and (q_d.iloc[-2]['Close']>q_d.iloc[-2]['MA200']) and (q_d.iloc[-3]['Close']>q_d.iloc[-3]['MA200'])
            is_3pct = q_pr >= (q_ma * 1.03)
            
            if not (is_3days or is_3pct):
                final_action = "⏳ RE-ENTRY WAIT (검증 대기)"
                detail_msg = f"겨울 종료 감지됨. 하지만 휩소 방지를 위해 필터 대기 중입니다.\n\n👉 **대기 조건:** (1) 3일 유지 OR (2) 3% 상승\n현재는 관망하십시오."
                action_color = "orange"
            else:
                final_action = "🌱 SPRING RE-ENTRY (봄의 귀환)"
                
                if qqq_rsi > 75:
                    detail_msg = f"필터 통과(진짜 봄). 4주 분할 진입 시점이나, RSI({qqq_rsi:.1f}) 과열로 금주는 Skip합니다. (다음 주 이월)"
                    action_color = "orange"
                else:
                    detail_msg = f"필터 통과(진짜 봄). 현금 4주 분할 투입을 시작합니다.\n\n👉 **금주 투입액 (1/4):** {format_krw(input_cash_weekly)} 매수\n⚠️ 200일선 다시 깨지면 즉시 중단 및 현금 50% 확보 (Abort Mission)."
                    action_color = "green"

        elif qqq_rsi >= 80:
            target_cash_panic = target_cash_ratio + 0.1
            sell_needed = (total_assets * target_cash_panic) - total_cash_krw
            if sell_needed > 0:
                final_action = "🚨 SPRING FEVER (광기 매도)"
                detail_msg = f"RSI 80 돌파. 현금 {format_krw(sell_needed)} 추가 확보 (Target + 10%)."
                action_color = "red"
            else:
                final_action = "✅ HOLD (현금 충분)"
                detail_msg = "광기 구간이나 현금이 충분합니다."

        elif qqq_mdd <= -0.15:
             # 봄엔 -15% 부터 스나이핑
             input_cash = 0
             ratio_str = ""
             if qqq_mdd <= -0.45:
                 input_cash = total_cash_krw * 0.4
                 ratio_str="40%"
             elif qqq_mdd <= -0.35:
                 input_cash = total_cash_krw * 0.3
                 ratio_str="30%"
             elif qqq_mdd <= -0.25:
                 input_cash = total_cash_krw * 0.2
                 ratio_str="20%"
             elif qqq_mdd <= -0.15:
                 input_cash = total_cash_krw * 0.1 # 봄엔 10% 짤짤이
                 ratio_str="10% (Spring Dip)"
            
             final_action = f"📉 SPRING SNIPER ({ratio_str})"
             detail_msg = f"봄 시즌 조정(MDD {qqq_mdd*100:.1f}%)입니다. 현금 {ratio_str} ({format_krw(input_cash)}) 투입."
             action_color = "green"

        elif current_stock_ratio > (target_stock_ratio + 0.1):
            sell_amt = total_stock_krw - (total_assets * target_stock_ratio)
            final_action = "⚖️ REBALANCE SELL"
            detail_msg = f"비중 초과. {format_krw(sell_amt)} 매도."
            action_color = "orange"
        
        elif need_dual_rebalance:
            final_action = "⚖️ DUAL REBALANCE"
            detail_msg = dual_msg
            action_color = "orange"
            
        else:
            final_action = "🧘 STABLING (관망)"
            detail_msg = "특이사항 없음. 포트폴리오 유지."

    # 손실 방어 (헌법)
    if is_loss and ("매도" in final_action or "SELL" in final_action or "DEFENSE" in final_action):
        final_action = "🛡️ LOSS PROTECTION (절대 방어)"
        detail_msg = f"시스템 매도 신호가 있으나, **현재 손실 중**이므로 헌법 제1조에 의거하여 **매도를 금지(HOLD)**합니다."
        action_color = "red"

    st.info(f"💡 **보유 자산 실행 (Asset Action):** {final_action}")
    
    if action_color == "red": st.error(detail_msg)
    elif action_color == "green": st.success(detail_msg)
    elif action_color == "orange": st.warning(detail_msg)
    else: st.info(detail_msg)
    
    st.markdown("---")
    st.caption("📅 **월급 투입 지침 (Monthly Input)**")
    if monthly_color == "red": st.error(monthly_msg)
    else: st.info(monthly_msg)

    # --- 4. 차트 (종목별 독립 Expander) ---
    st.markdown("---")
    st.header("4. 📊 차트 분석 (Technical Charts)")
    
    # 차트 그리기 함수 (공통)
    def draw_chart(df, title):
        if df is None or df.empty:
            st.warning(f"데이터가 없습니다 ({title})")
            return

        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Candle')])
        
        # MA Line Colors (40일선, 200일선 포함)
        ma_colors = {'MA20': 'orange', 'MA40': 'purple', 'MA60': 'blue', 'MA200': 'red'}
        
        for ma_name, color in ma_colors.items():
            if ma_name in df.columns:
                width = 2 if ma_name == 'MA40' else 1
                dash = 'dot' if ma_name == 'MA200' else 'solid'
                fig.add_trace(go.Scatter(x=df.index, y=df[ma_name], line=dict(color=color, width=width, dash=dash), name=ma_name))
        
        fig.update_layout(title=title, height=400, margin=dict(l=20, r=20, t=40, b=20), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        if 'RSI' in df.columns:
            fig_rsi = go.Figure(data=[go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'))])
            fig_rsi.add_hline(y=80, line_color="red", line_dash="dash")
            fig_rsi.add_hline(y=60, line_color="green", line_dash="dash")
            fig_rsi.update_layout(title=f'{title} - RSI', height=200, yaxis_range=[0, 100], margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_rsi, use_container_width=True)

    # 📊 QQQ 차트
    with st.expander("📊 QQQ (나스닥 100) 차트 확인", expanded=False):
        tab1, tab2, tab3 = st.tabs(["일봉 (Daily)", "주봉 (Weekly)", "월봉 (Monthly)"])
        with tab1:
            draw_chart(mkt['qqq_dy'], "QQQ Daily Chart")
        with tab2:
            draw_chart(mkt['qqq_wk'], "QQQ Weekly Chart")
        with tab3:
            draw_chart(mkt['qqq_mo'], "QQQ Monthly Chart")
    
    # 📊 SOXX 차트
    with st.expander("📊 SOXX (반도체 지수) 차트 확인", expanded=False):
        tab1, tab2, tab3 = st.tabs(["일봉 (Daily)", "주봉 (Weekly)", "월봉 (Monthly)"])
        with tab1:
            draw_chart(mkt['soxx_dy'], "SOXX Daily Chart")
        with tab2:
            draw_chart(mkt['soxx_wk'], "SOXX Weekly Chart")
        with tab3:
            draw_chart(mkt['soxx_mo'], "SOXX Monthly Chart")
    
    # 📊 TQQQ 차트
    with st.expander("📊 TQQQ (3배 레버리지) 차트 확인", expanded=False):
        tab1, tab2 = st.tabs(["주봉 (Weekly)", "월봉 (Monthly)"])
        with tab1:
            draw_chart(mkt['tqqq_wk'], "TQQQ Weekly Chart")
        with tab2:
            draw_chart(mkt['tqqq_mo'], "TQQQ Monthly Chart")
        st.caption("ℹ️ TQQQ 일봉 데이터는 성능 최적화를 위해 제공하지 않습니다.")
    
    # 📊 USD 차트
    with st.expander("📊 USD (반도체 2배) 차트 확인", expanded=False):
        tab1, tab2 = st.tabs(["주봉 (Weekly)", "월봉 (Monthly)"])
        with tab1:
            draw_chart(mkt['usd_wk'], "USD Weekly Chart")
        with tab2:
            draw_chart(mkt['usd_mo'], "USD Monthly Chart")
        st.caption("ℹ️ USD 일봉 데이터는 성능 최적화를 위해 제공하지 않습니다.")

    # --- 5. 릴리즈 노트 & 코어 로직 ---
    st.markdown("---")
    with st.expander("📅 릴리즈 노트", expanded=False):
        try:
            with open("ReleaseNotes.md", "r", encoding="utf-8") as f:
                st.markdown(f.read())
        except: pass
    
    with st.expander("🏛️ 코어 로직 (Master Protocol)", expanded=False):
        try:
            with open("TradingCoreLogic.md", "r", encoding="utf-8") as f:
                st.markdown(f.read())
        except: pass

else:
    st.warning("데이터 로딩 중... (잠시만 기다려주세요)")
