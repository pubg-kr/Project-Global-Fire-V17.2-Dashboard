import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json
import os

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
        "c_cash_krw": 0,
        "ath_assets": 0 # V23.3: 래칫 원칙을 위한 최고 자산액
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                loaded = json.load(f)
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
        "c_cash_krw": st.session_state.c_cash_krw,
        "ath_assets": st.session_state.ath_assets
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ==========================================
# 1. 설정 및 상수
# ==========================================
st.set_page_config(page_title="Global Fire CRO V23.3", layout="wide", page_icon="🔥")

# V23.3 Level Configuration
LEVEL_CONFIG = {
    1: {"limit": 50000000, "target_stock": 0.95, "target_cash": 0.05, "name": "LV. 1 (~5천만)"},
    2: {"limit": 100000000, "target_stock": 0.90, "target_cash": 0.10, "name": "LV. 2 (~1억)"},
    3: {"limit": 150000000, "target_stock": 0.875, "target_cash": 0.125, "name": "LV. 3 (~1.5억)"},
    4: {"limit": 200000000, "target_stock": 0.85, "target_cash": 0.15, "name": "LV. 4 (~2억)"},
    5: {"limit": 300000000, "target_stock": 0.825, "target_cash": 0.175, "name": "LV. 5 (~3억)"},
    6: {"limit": 400000000, "target_stock": 0.80, "target_cash": 0.20, "name": "LV. 6 (~4억)"},
    7: {"limit": 550000000, "target_stock": 0.775, "target_cash": 0.225, "name": "LV. 7 (~5.5억)"},
    8: {"limit": 700000000, "target_stock": 0.75, "target_cash": 0.25, "name": "LV. 8 (~7억)"},
    9: {"limit": 850000000, "target_stock": 0.725, "target_cash": 0.275, "name": "LV. 9 (~8.5억)"},
    10: {"limit": 1000000000, "target_stock": 0.70, "target_cash": 0.30, "name": "LV. 10 (~10억) [🎯 1차: 육아/퇴사]"},
    11: {"limit": 1250000000, "target_stock": 0.675, "target_cash": 0.325, "name": "LV. 11 (~12.5억)"},
    12: {"limit": 1500000000, "target_stock": 0.65, "target_cash": 0.35, "name": "LV. 12 (~15억)"},
    13: {"limit": 1750000000, "target_stock": 0.625, "target_cash": 0.375, "name": "LV. 13 (~17.5억)"},
    14: {"limit": 2000000000, "target_stock": 0.60, "target_cash": 0.40, "name": "LV. 14 (~20억)"},
    15: {"limit": 2300000000, "target_stock": 0.575, "target_cash": 0.425, "name": "LV. 15 (~23억) [🎯 2차: Coast FIRE]"},
    16: {"limit": 2600000000, "target_stock": 0.55, "target_cash": 0.45, "name": "LV. 16 (~26억)"},
    17: {"limit": 3000000000, "target_stock": 0.525, "target_cash": 0.475, "name": "LV. 17 (~30억)"},
    18: {"limit": float('inf'), "target_stock": 0.50, "target_cash": 0.50, "name": "LV. 18 (30억+) [🎯 Global FIRE]"}
}

PROTOCOL_TEXT = """
### 📜 Master Protocol (요약) - Ver 23.3 The Endgame
1.  **[헌법] 손실 확정 절대 금지:** 계좌가 마이너스일 때는 절대 팔지 않는다.
2.  **[스나이핑 원상복구]:** 폭락장 현금 투입 후 '본전'이 되면, 투입 현금 분량만큼만 매도하여 BOXX 복구.
3.  **[광기 차단]:** QQQ 주봉 RSI 80 도달 시, Level별 목표 현금 비중만큼만 매도하여 BOXX 충전.
4.  **[월 적립 평시]:** MDD -15% 이내일 땐 Level 목표 비중에 맞춰 500만원 쪼개서 분할 투입.
5.  **[월 적립 전시]:** MDD -15% 이하로 스나이퍼 발동 시, 500만원 100% 주식 (TQQQ 50:USD 50) 풀 투입.
6.  **[승자의 질주]:** 매수는 항상 50:50 기계적 투입. 절대 팔아서 억지로 50:50 비율 맞추지 않는다.
7.  **[래칫 원칙]:** 한 번 도달한 최고 계좌 자산(ATH)으로 방어력(Level) 영구 고정. 폭락해도 Level은 안 내린다.
"""

# ==========================================
# 2. 유틸리티 함수
# ==========================================
def calculate_indicators(df):
    if df.empty: return 0, 0
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    window = 252 if len(df) >= 252 else len(df)
    df['Roll_Max'] = df['Close'].rolling(window=window, min_periods=1).max()
    df['DD'] = (df['Close'] / df['Roll_Max']) - 1.0
    return float(df['RSI'].iloc[-1]), float(df['DD'].iloc[-1])

def get_market_data():
    try:
        qqq_dy = yf.download("QQQ", interval="1d", period="2y", progress=False, auto_adjust=False)
        qqq_mo = yf.download("QQQ", interval="1mo", period="5y", progress=False, auto_adjust=False)
        tqqq_wk = yf.download("TQQQ", interval="1wk", period="2y", progress=False, auto_adjust=False)
        usd_wk = yf.download("USD", interval="1wk", period="2y", progress=False, auto_adjust=False)
        soxx_dy = yf.download("SOXX", interval="1d", period="2y", progress=False, auto_adjust=False)
        exch = yf.download("KRW=X", period="1d", progress=False, auto_adjust=False)
        
        if qqq_dy.empty or exch.empty or tqqq_wk.empty or usd_wk.empty or soxx_dy.empty: return None

        for d in [qqq_dy, qqq_mo, tqqq_wk, usd_wk, soxx_dy, exch]:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)

        current_rate = float(exch['Close'].iloc[-1])
        qqq_price = float(qqq_dy['Close'].iloc[-1])
        tqqq_price = float(tqqq_wk['Close'].iloc[-1])
        usd_price = float(usd_wk['Close'].iloc[-1])
        soxx_price = float(soxx_dy['Close'].iloc[-1])
        
        # QQQ 주봉 RSI (일봉 → W-FRI 리샘플링, 진행 중인 주 포함)
        qqq_wk_for_rsi = qqq_dy[['Open', 'High', 'Low', 'Close', 'Volume']].resample('W-FRI').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        calculate_indicators(qqq_wk_for_rsi)
        qqq_rsi_wk = float(qqq_wk_for_rsi['RSI'].iloc[-1])

        # QQQ 월봉 RSI (원칙 1-3: 주봉 또는 월봉 RSI 80)
        qqq_rsi_mo, _ = calculate_indicators(qqq_mo)
        
        # MDD 및 RSI 계산
        calculate_indicators(qqq_dy)
        qqq_mdd = float(qqq_dy['DD'].iloc[-1])
        
        tqqq_rsi_wk, tqqq_mdd = calculate_indicators(tqqq_wk)
        usd_rsi_wk, usd_mdd = calculate_indicators(usd_wk)
        
        # SOXX RSI (일봉 → W-FRI 리샘플링) + MDD (cummax 전체 기간 기준)
        soxx_wk_for_rsi = soxx_dy[['Open', 'High', 'Low', 'Close', 'Volume']].resample('W-FRI').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        calculate_indicators(soxx_wk_for_rsi)
        soxx_rsi_wk = float(soxx_wk_for_rsi['RSI'].iloc[-1])

        soxx_dy['Roll_Max'] = soxx_dy['Close'].cummax()
        soxx_dy['DD'] = (soxx_dy['Close'] / soxx_dy['Roll_Max']) - 1.0
        soxx_mdd = float(soxx_dy['DD'].iloc[-1])

        return {
            'qqq_dy': qqq_dy, 'qqq_price': qqq_price,
            'qqq_rsi_wk': qqq_rsi_wk, 'qqq_rsi_mo': qqq_rsi_mo, 'qqq_mdd': qqq_mdd,
            'soxx_dy': soxx_dy, 'soxx_price': soxx_price, 'soxx_rsi_wk': soxx_rsi_wk, 'soxx_mdd': soxx_mdd,
            'tqqq_wk': tqqq_wk, 'tqqq_price': tqqq_price, 'tqqq_rsi_wk': tqqq_rsi_wk, 'tqqq_mdd': tqqq_mdd,
            'usd_wk': usd_wk, 'usd_price': usd_price, 'usd_rsi_wk': usd_rsi_wk, 'usd_mdd': usd_mdd,
            'usd_krw': current_rate
        }
    except Exception as e:
        return None

def determine_level(ath_assets):
    for level, config in sorted(LEVEL_CONFIG.items()):
        if ath_assets <= config['limit']: return level
    return 18

def format_krw(value):
    return f"{int(value):,}원"

# ==========================================
# 3. 메인 로직
# ==========================================
st.title("🔥 Global Fire CRO System")
st.markdown("**Ver 23.3 (The Endgame)** | System Owner: **Busan Programmer** | Core Asset: **TQQQ & USD (Let them race)**")

saved_data = load_data()
if "monthly_contribution" not in st.session_state:
    if "ath_assets" in saved_data:
        val = saved_data["ath_assets"]
        st.session_state.ath_assets = float(val) if isinstance(val, (int, float, str)) and str(val).replace('.', '', 1).isdigit() else 0
    else:
        st.session_state.ath_assets = 0

    for key, val in saved_data.items():
        if key != "ath_assets":
            st.session_state[key] = float(val) if isinstance(val, (int, float, str)) and str(val).replace('.', '', 1).isdigit() else val

# 래칫 ATH 내부 추적용 (widget-bound 변수 직접 수정 금지 우회)
if '_ath_internal' not in st.session_state:
    st.session_state._ath_internal = float(saved_data.get('ath_assets', 0))

with st.expander("📜 Master Protocol (규정집)", expanded=False):
    st.markdown(PROTOCOL_TEXT)

mkt = get_market_data()

if mkt is not None:
    qqq_price = mkt['qqq_price']
    tqqq_price = mkt['tqqq_price']
    usd_price = mkt['usd_price']
    usd_krw_rate = mkt['usd_krw']
    qqq_rsi = mkt['qqq_rsi_wk']
    qqq_mdd = mkt['qqq_mdd']
    
    tqqq_krw = tqqq_price * usd_krw_rate
    usd_stock_krw = usd_price * usd_krw_rate

    # --- 사이드바 ---
    st.sidebar.header("📝 자산 정보")
    st.sidebar.info(f"💵 환율: **{int(usd_krw_rate):,}원/$**")
    
    with st.sidebar.form("asset_form"):
        st.number_input("이번 달 투입금 (월급)", min_value=0, step=100000, key="monthly_contribution", format="%d")
        
        st.markdown("---")
        with st.expander("🏦 계좌 A: 금고 (장기)", expanded=True):
            st.number_input("A: TQQQ 보유 수량", min_value=0.0, step=0.01, key="a_tqqq_qty", format="%.2f")
            st.number_input("A: TQQQ 평균단가 (KRW)", min_value=0, step=100, key="a_tqqq_avg", format="%d")
            st.markdown("---")
            st.number_input("A: USD 보유 수량", min_value=0.0, step=0.01, key="a_usd_qty", format="%.2f")
            st.number_input("A: USD 평균단가 (KRW)", min_value=0, step=100, key="a_usd_avg", format="%d")
            st.number_input("A: 원화 예수금", min_value=0, step=100000, key="a_cash_krw", format="%d")
            st.number_input("A: 달러 예수금 (BOXX)", min_value=0, step=100, key="a_cash_usd", format="%d")

        with st.expander("⚔️ 계좌 B: 스나이퍼 (매매)", expanded=True):
            st.number_input("B: TQQQ 보유 수량", min_value=0.0, step=0.01, key="b_tqqq_qty", format="%.2f")
            st.number_input("B: TQQQ 평균단가 (KRW)", min_value=0, step=100, key="b_tqqq_avg", format="%d")
            st.markdown("---")
            st.number_input("B: USD 보유 수량", min_value=0.0, step=0.01, key="b_usd_qty", format="%.2f")
            st.number_input("B: USD 평균단가 (KRW)", min_value=0, step=100, key="b_usd_avg", format="%d")
            st.number_input("B: 원화 예수금", min_value=0, step=100000, key="b_cash_krw", format="%d")
            st.number_input("B: 달러 예수금 (BOXX)", min_value=0, step=100, key="b_cash_usd", format="%d")

        with st.expander("🛡️ 계좌 C: 벙커 (세금/비상)", expanded=True):
            st.number_input("C: 원화 예수금 (수익금 22%)", min_value=0, step=100000, key="c_cash_krw", format="%d")

        st.markdown("---")
        st.number_input("🚨 역대 최고 자산액 (All-Time High)", min_value=0.0, step=1000000.0, key="ath_assets", format="%.0f", help="래칫 원칙: 가장 높았던 자산액을 기준으로 레벨이 영구 고정됩니다.")

        submit_button = st.form_submit_button("💾 자산 정보 저장 및 업데이트", use_container_width=True)
        if submit_button:
            save_data()
            st.success("✅ 저장 완료!")
    
    # --- 자동 손익 판단 로직 ---
    tqqq_qty = st.session_state.a_tqqq_qty + st.session_state.b_tqqq_qty
    usd_qty = st.session_state.a_usd_qty + st.session_state.b_usd_qty
    
    tqqq_invested = (st.session_state.a_tqqq_qty * st.session_state.a_tqqq_avg) + (st.session_state.b_tqqq_qty * st.session_state.b_tqqq_avg)
    usd_invested = (st.session_state.a_usd_qty * st.session_state.a_usd_avg) + (st.session_state.b_usd_qty * st.session_state.b_usd_avg)
    total_invested_krw = tqqq_invested + usd_invested
    
    total_tqqq_krw = tqqq_qty * tqqq_krw
    total_usd_krw = usd_qty * usd_stock_krw
    total_stock_krw = total_tqqq_krw + total_usd_krw
    
    total_cash_krw = (st.session_state.a_cash_krw + st.session_state.b_cash_krw + st.session_state.c_cash_krw) + \
                     ((st.session_state.a_cash_usd + st.session_state.b_cash_usd) * usd_krw_rate)
    total_assets = total_stock_krw + total_cash_krw
    
    # 자동 래칫 원칙 갱신 (widget exception 방지: _ath_internal에 자동 추적 후 파일에 기록)
    effective_ath = max(st.session_state.ath_assets, st.session_state._ath_internal, total_assets)
    if effective_ath > st.session_state._ath_internal:
        st.session_state._ath_internal = effective_ath
        try:
            with open(DATA_FILE, "r") as _f:
                _d = json.load(_f)
            _d['ath_assets'] = effective_ath
            with open(DATA_FILE, "w") as _f:
                json.dump(_d, _f)
        except:
            pass

    profit_rate = ((total_stock_krw - total_invested_krw) / total_invested_krw * 100) if total_invested_krw > 0 else 0.0
    is_loss = profit_rate < 0

    # Level 결정 (ATH 기준 래칫)
    current_level = determine_level(effective_ath)
    target_stock_ratio = LEVEL_CONFIG[current_level]['target_stock']
    target_cash_ratio = LEVEL_CONFIG[current_level]['target_cash']

    current_stock_ratio = total_stock_krw / total_assets if total_assets > 0 else 0
    current_cash_ratio = total_cash_krw / total_assets if total_assets > 0 else 0

    # 광기 차단: 주봉 또는 월봉 RSI 80 이상 (원칙 1-3)
    qqq_rsi_mo = mkt['qqq_rsi_mo']
    is_circuit_breaker = (qqq_rsi >= 80) or (qqq_rsi_mo >= 80)

    # --- 1. 시장 상황판 ---
    st.header("1. 시장 상황판 (Market Status)")

    def get_rsi_label(rsi):
        if rsi >= 80: return "🚨 광기"
        elif rsi >= 75: return "🔥 과열"
        elif rsi < 60: return "💰 기회"
        return "표준"

    def get_mdd_label(mdd):
        if mdd <= -0.35: return "🔴 대폭락"
        elif mdd <= -0.25: return "🟠 중폭락"
        elif mdd <= -0.15: return "📉 스나이퍼"
        return "✅ 안정"

    # QQQ
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("QQQ 현재가", f"${qqq_price:.2f} ({format_krw(qqq_price*usd_krw_rate)})")
    q2.metric("QQQ 주봉 RSI", f"{qqq_rsi:.1f}", get_rsi_label(qqq_rsi))
    q3.metric("QQQ 월봉 RSI", f"{qqq_rsi_mo:.1f}", get_rsi_label(qqq_rsi_mo))
    q4.metric("QQQ MDD", f"{qqq_mdd*100:.2f}%", get_mdd_label(qqq_mdd))

    # SOXX
    soxx_rsi_wk_val = mkt['soxx_rsi_wk']
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("SOXX 현재가", f"${mkt['soxx_price']:.2f} ({format_krw(mkt['soxx_price']*usd_krw_rate)})")
    s2.metric("SOXX 주봉 RSI", f"{soxx_rsi_wk_val:.1f}", get_rsi_label(soxx_rsi_wk_val))
    s3.metric("SOXX MDD", f"{mkt['soxx_mdd']*100:.2f}%", get_mdd_label(mkt['soxx_mdd']))
    s4.metric("환율", f"{int(usd_krw_rate):,}원/$")

    # TQQQ
    tqqq_rsi_wk_val = mkt['tqqq_rsi_wk']
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("TQQQ 현재가", f"${tqqq_price:.2f} ({format_krw(tqqq_price*usd_krw_rate)})")
    t2.metric("TQQQ 주봉 RSI", f"{tqqq_rsi_wk_val:.1f}", get_rsi_label(tqqq_rsi_wk_val))
    t3.metric("TQQQ MDD", f"{mkt['tqqq_mdd']*100:.2f}%", get_mdd_label(mkt['tqqq_mdd']))
    t4.metric("USD MDD", f"{mkt['usd_mdd']*100:.2f}%", get_mdd_label(mkt['usd_mdd']))

    # USD
    usd_rsi_wk_val = mkt['usd_rsi_wk']
    u1, u2, u3, u4 = st.columns(4)
    u1.metric("USD 현재가", f"${usd_price:.2f} ({format_krw(usd_price*usd_krw_rate)})")
    u2.metric("USD 주봉 RSI", f"{usd_rsi_wk_val:.1f}", get_rsi_label(usd_rsi_wk_val))
    u3.metric("USD MDD", f"{mkt['usd_mdd']*100:.2f}%", get_mdd_label(mkt['usd_mdd']))
    u4.metric("SOXX MDD", f"{mkt['soxx_mdd']*100:.2f}%", get_mdd_label(mkt['soxx_mdd']))

    # --- 2. 포트폴리오 진단 ---
    st.markdown("---")
    st.header("2. 포트폴리오 진단 (Diagnosis)")
    
    if current_level < 18:
        prev_limit = LEVEL_CONFIG[current_level-1]['limit'] if current_level > 1 else 0
        next_limit = LEVEL_CONFIG[current_level]['limit']
        progress = (effective_ath - prev_limit) / (next_limit - prev_limit) if (next_limit - prev_limit) > 0 else 0
        st.progress(max(0.0, min(1.0, progress)), text=f"🚀 Level Up 진행률 → 다음 레벨까지 {format_krw(max(0, next_limit - effective_ath))}")
    else:
        st.progress(1.0, text="🏆 Final Level 달성! (Global FIRE)")

    # 자동 ATH 갱신 알림
    if effective_ath > st.session_state.ath_assets and st.session_state.ath_assets > 0:
        st.toast(f"🏆 새 최고 자산 갱신! {format_krw(effective_ath)} → 다음 저장 시 반영됩니다.", icon="🚀")

    st.markdown("### 📊 통합 포트폴리오")
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
    row1_col1.metric("현재 Level (래칫 룰)", f"{LEVEL_CONFIG[current_level]['name']}")
    row1_col2.metric("최고 자산 (ATH)", format_krw(effective_ath), "🔒 자동 추적 중")
    row1_col3.metric("현재 총 자산", format_krw(total_assets))
    row1_col4.metric("통합 수익률", f"{profit_rate:.2f}%", "🔴 손실 절대방어" if is_loss else "🔵 수익 순항")
    
    # TQ:USD 비율 계산
    tqqq_ratio_in_stock = total_tqqq_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    usd_ratio_in_stock = total_usd_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    tq_pct = int(tqqq_ratio_in_stock * 100)
    us_pct = int(usd_ratio_in_stock * 100)

    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
    row2_col1.metric("총 주식 평가금", format_krw(total_stock_krw))
    row2_col2.metric("총 현금(BOXX)", format_krw(total_cash_krw))
    row2_col3.metric("주식 비중", f"{current_stock_ratio*100:.1f}%",
                     f"목표: {target_stock_ratio*100:.1f}%  │  TQ {tq_pct}:{us_pct} USD")
    row2_col4.metric("현금 비중", f"{current_cash_ratio*100:.1f}%", f"목표: {target_cash_ratio*100:.1f}%")

    # TQQQ / USD 종목별 상세
    st.markdown("### 🚀 TQQQ & USD 종목 상세")
    c_t1, c_t2, c_t3, c_u1, c_u2, c_u3 = st.columns(6)

    tqqq_avg_price = tqqq_invested / tqqq_qty if tqqq_qty > 0 else 0
    tqqq_profit = ((total_tqqq_krw - tqqq_invested) / tqqq_invested * 100) if tqqq_invested > 0 else 0
    c_t1.metric("TQQQ 수량", f"{tqqq_qty:.2f}주")
    c_t2.metric("TQQQ 평가금", format_krw(total_tqqq_krw))
    c_t3.metric("TQQQ 수익률", f"{tqqq_profit:.2f}%", "🔴 수익" if tqqq_profit >= 0 else "🔵 손실")

    usd_avg_price = usd_invested / usd_qty if usd_qty > 0 else 0
    usd_profit = ((total_usd_krw - usd_invested) / usd_invested * 100) if usd_invested > 0 else 0
    c_u1.metric("USD 수량", f"{usd_qty:.2f}주")
    c_u2.metric("USD 평가금", format_krw(total_usd_krw))
    c_u3.metric("USD 수익률", f"{usd_profit:.2f}%", "🔴 수익" if usd_profit >= 0 else "🔵 손실")

    st.markdown("---")
    if is_loss: st.error("🛑 [손실 중] 절대 방패 가동: 헌법 제1조 – 어떠한 경우에도 매도 금지")
    else: st.success("✅ [수익 중] 정상 로직 가동")

    # --- 3. CRO 실행 명령 ---
    st.markdown("---")
    st.header("3. CRO 실행 명령 (Action Protocol)")
    
    # 월급 적립 가이드
    monthly_msg = ""
    monthly_color = "blue"
    if qqq_mdd <= -0.15:
        monthly_msg = f"📉 **전시 상황 (MDD {qqq_mdd*100:.1f}%)**: 월급 100% ({format_krw(st.session_state.monthly_contribution)}) 주식 매수 (TQQQ 50 : USD 50). 현금 적립 금지!"
        monthly_color = "red"
    else:
        buy_stock = st.session_state.monthly_contribution * target_stock_ratio
        buy_cash = st.session_state.monthly_contribution * target_cash_ratio
        monthly_msg = f"✅ **평시 적립**: 월급 {format_krw(st.session_state.monthly_contribution)}을 Level 목표비율에 맞춰 주식 {format_krw(buy_stock)} / 현금(BOXX) {format_krw(buy_cash)} 배분 매수."
    
    # 매매/스나이핑 가이드
    final_action = ""
    detail_msg = ""
    action_color = "blue"
    
    if is_loss:
        final_action = "🛡️ LOSS PROTECTION (절대 방어)"
        detail_msg = f"헌법 제1조: 현재 포트폴리오가 손실 구간이므로 **어떠한 경우에도 매도를 금지**합니다."
        action_color = "red"
    else:
        if qqq_mdd <= -0.15:
            # MDD Sniper
            input_cash = 0
            ratio_str = ""
            if qqq_mdd <= -0.45: input_cash = total_cash_krw * 0.4; ratio_str = "40% (영끌)"
            elif qqq_mdd <= -0.35: input_cash = total_cash_krw * 0.3; ratio_str = "30%"
            elif qqq_mdd <= -0.25: input_cash = total_cash_krw * 0.2; ratio_str = "20%"
            else: input_cash = total_cash_krw * 0.1; ratio_str = "10%"
            
            final_action = f"🔫 MDD SNIPER ({ratio_str})"
            detail_msg = f"하락장 스나이퍼 발동! 계좌 B의 보유 현금 {ratio_str} ({format_krw(input_cash)}) 투입."
            action_color = "green"
            
        elif is_circuit_breaker:
            sell_needed = (total_assets * target_cash_ratio) - total_cash_krw
            trigger_str = f"주봉 RSI {qqq_rsi:.1f}" if qqq_rsi >= 80 else f"월봉 RSI {qqq_rsi_mo:.1f}"
            if sell_needed > 0:
                final_action = "🚨 CIRCUIT BREAKER (광기 매도)"
                detail_msg = f"[{trigger_str}] 80 돌파! Level {current_level}의 목표 현금 비중({target_cash_ratio*100:.1f}%) 확보를 위해 {format_krw(sell_needed)} 만큼만 매도하여 현금(BOXX) 채움. (22% 세금 격리 필수)"
                action_color = "orange"
            else:
                final_action = "✅ HOLD (현금 벙커 완충)"
                detail_msg = f"[{trigger_str}] 광기 구간이나, 이미 목표 현금(BOXX) 비중을 충족했습니다."
        
        else:
            final_action = "🧘 STABLING (관망)"
            detail_msg = "평시 구간입니다. '승자의 질주(Let Winners Run)'를 즐기며 기존 포지션을 유지하십시오. 듀얼 리밸런싱은 오직 '월 적립금(새 돈)'으로만 맞춥니다."

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
    
    def draw_chart(df, title):
        if df is None or df.empty: return
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(title=title, height=400, margin=dict(l=20, r=20, t=40, b=20), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📊 QQQ (나스닥 100) 차트", expanded=False):
        draw_chart(mkt['qqq_dy'], "QQQ Daily Chart")
    with st.expander("📊 SOXX (반도체 지수) 차트", expanded=False):
        draw_chart(mkt['soxx_dy'], "SOXX Daily Chart")
    with st.expander("📊 TQQQ / USD 차트", expanded=False):
        c1, c2 = st.columns(2)
        with c1: draw_chart(mkt['tqqq_wk'], "TQQQ Weekly Chart")
        with c2: draw_chart(mkt['usd_wk'], "USD Weekly Chart")

    # --- 5. 릴리즈 노트 & 코어 로직 ---
    st.markdown("---")
    with st.expander("📅 릴리즈 노트", expanded=False):
        try:
            with open("ReleaseNotes.md", "r", encoding="utf-8") as f: st.markdown(f.read())
        except: pass
    
    with st.expander("🏛️ 코어 로직 (Master Protocol)", expanded=False):
        try:
            with open("TradingCoreLogic.md", "r", encoding="utf-8") as f: st.markdown(f.read())
        except: pass

else:
    st.warning("데이터 로딩 중... (잠시만 기다려주세요)")
