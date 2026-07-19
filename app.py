import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json
import os
from version import APP_VERSION, APP_VERSION_FULL, APP_NAME

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
        "d_cash_krw": 0,  # V24.4: 계좌 D (가족 생존 계좌) - 투자 절대 금지
        "ath_assets": 0,  # V23.3: 래칫 원칙을 위한 최고 자산액
        "sniper_mode_active": False  # V24.4: 스나이핑 원상복구(Break-Even Reload) 추적 플래그
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
        "d_cash_krw": st.session_state.d_cash_krw,
        "ath_assets": st.session_state.ath_assets,
        "sniper_mode_active": st.session_state.sniper_mode_active
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ==========================================
# 1. 설정 및 상수
# ==========================================
st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", layout="wide", page_icon="🔥")

# V24.5: Level 2(이격도) 버블 방어 발동 레벨 게이트. 이 레벨 미만(시드 펌핑 구간)에서는
# 120월 이격도 100% 초과 룰을 완전히 무시하고 공격적으로 자산을 불린다 (RSI 80 룰은 전 레벨 유지).
BUBBLE_LEVEL2_GATE = 7

# V24.1 Level Configuration
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

PROTOCOL_TEXT = f"""
### 📜 Master Protocol (요약) - Ver {APP_VERSION} The Ultimate Simple
0.  **[기준 지표/데이터 표준]** 모든 경보는 **QQQ 월봉(달러 차트)** 단일 기준. 주봉·SOXX는 참고용. MDD는 **수정종가(Adj Close)** 기준, 월봉 지표는 **월 마지막 거래일 종가**로 확정.
    **[우선순위]** 1순위: QQQ MDD -15% (전시/스나이퍼) > 2순위: QQQ 이격도 100% (역사적 버블, 🚨 Level {BUBBLE_LEVEL2_GATE} 이상 한정) > 3순위: QQQ 월봉 RSI 80 (단기 과열, 전 Level 공통)
1.  **[헌법] 손실 확정 절대 금지:** 계좌가 마이너스일 때는 절대 팔지 않는다.
2.  **[핵심] 스나이핑 원상복구 (Break-Even Reload):** 토스증권 이동평균법 하에서, 계좌 총주식 수익률이 **본전(0%) 이상**이 되는 순간 목표 현금 비중(Level 기준)으로 즉시 매도 복구. (트랜치 추적 불필요, 계좌 총수익률만 확인)
3.  **[광기 차단 및 버블 방어]:** 
    *   **Level 1 (단기과열, 전 Level 공통):** QQQ **월봉** RSI 80 도달 시, Level 목표 현금 비중만큼만 단순 리밸런싱 매도.
    *   **Level 2 (역사적 버블, 🚨 Level {BUBBLE_LEVEL2_GATE} 이상 한정 발동):** QQQ 120개월 이평선 이격도 100% 초과 시, 목표 현금 비중에 **+20% 추가 확보**. (Level 1~{BUBBLE_LEVEL2_GATE-1} 시드 펌핑 구간은 물타기 효율 극대화를 위해 이 룰을 완전히 무시)
    *   매도는 TQQQ/USD **현재 보유 비중대로 비례 매도** (50:50 강제 금지).
    *   **[세금 격리]:** 익절 매도 시 수익금의 22%는 즉시 계좌 C(파킹통장/CMA)로 격리 (재투자 금지).
4.  **[월 적립 평시]:** MDD -15% 이내일 땐 Level 목표 비중에 맞춰 500만원 쪼개서 분할 투입. (환율이 10년 평균 대비 +20% 이상이면 4주 분할 환전)
5.  **[월 적립 전시]:** QQQ MDD -15% 이하 스나이퍼 발동 시, 500만원 100% 주식 풀 투입. (MDD -15% 이내 회복 시 평시 복귀)
6.  **[월 적립 버블, 🚨 Level별 차등]:** Level {BUBBLE_LEVEL2_GATE} 이상에서 QQQ 월봉 RSI 80 또는 이격도 100% 초과 시, 비싼 주식 사지 않고 500만원 100% 현금(SGOV/BOXX) 투입. Level 1~{BUBBLE_LEVEL2_GATE-1} 구간은 FOMO 방지를 위해 버블 경보 중에도 500만원을 Level 목표 비중대로 기계적 매수 지속 (기존 보유 물량 리밸런싱 매도는 정상 집행).
7.  **[버블 경보 해제]:** 조건A: QQQ 월봉RSI 70↓ **AND** 이격도 100%↓ 동시 충족. 또는 조건B(치트키): QQQ MDD -15% 즉시 강제해제.
8.  **[버블 이후]:** 확보된 비상금은 스나이퍼용으로만 대기. ATH 갱신 시에도 **매도 리밸런싱 절대 금지** (신규 적립금으로만 비중 조절).
9.  **[승자의 질주]:** 매수는 항상 TQQQ:USD 50:50 기계적 투입.
10. **[래칫 원칙]:** ATH 기준으로 방어력(Level) 영구 고정. 레벨업 시 파라미터만 변경, 도달 즉시 팔지 않는다.
11. **[하이브리드 스나이퍼 - 최후의 보루]:** 보유 현금의 **15%는 영구 보존**하여 MDD -50% 이상 블랙스완 전까지 사용 금지. -15%~-45% 구간은 가용 현금(85%) 기준으로만 투입.
12. **[블랙 스완 & 가족 생존]:** 계좌 D(최소 12~24개월 생활비)는 투자와 완전 분리, 스나이퍼 총알로 전용 금지. ETF 내부 레버리지 외 신용융자/마진 등 외부 레버리지 절대 금지.
"""

# ==========================================
# 2. 유틸리티 함수
# ==========================================
def calculate_indicators(df, price_col='Close'):
    """RSI 및 MDD(Drawdown) 계산. price_col='Adj Close' 지정 시 수정종가 기준으로 MDD 계산 (원칙 0)."""
    if df.empty: return 0, 0
    col = price_col if price_col in df.columns else 'Close'
    delta = df[col].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['Roll_Max'] = df[col].cummax()
    df['DD'] = (df[col] / df['Roll_Max']) - 1.0
    return float(df['RSI'].iloc[-1]), float(df['DD'].iloc[-1])

def get_market_data():
    try:
        qqq_dy = yf.download("QQQ", interval="1d", period="2y", progress=False, auto_adjust=False)
        qqq_mo = yf.download("QQQ", interval="1mo", period="max", progress=False, auto_adjust=False)
        soxx_mo = yf.download("SOXX", interval="1mo", period="max", progress=False, auto_adjust=False)
        tqqq_wk = yf.download("TQQQ", interval="1wk", period="2y", progress=False, auto_adjust=False)
        usd_wk = yf.download("USD", interval="1wk", period="2y", progress=False, auto_adjust=False)
        soxx_dy = yf.download("SOXX", interval="1d", period="2y", progress=False, auto_adjust=False)
        exch = yf.download("KRW=X", period="1d", progress=False, auto_adjust=False)
        exch_10y = yf.download("KRW=X", period="10y", progress=False, auto_adjust=False)
        
        if qqq_dy.empty or exch.empty or tqqq_wk.empty or usd_wk.empty or soxx_dy.empty or qqq_mo.empty or soxx_mo.empty: return None

        for d in [qqq_dy, qqq_mo, soxx_mo, tqqq_wk, usd_wk, soxx_dy, exch, exch_10y]:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)

        current_rate = float(exch['Close'].iloc[-1])
        # [원칙 2-1] 환율 극단값 방어: 10년 평균 대비 +20% 이상이면 분할 환전 경보
        fx_10y_avg = float(exch_10y['Close'].mean()) if not exch_10y.empty else current_rate
        fx_deviation = (current_rate / fx_10y_avg) - 1.0 if fx_10y_avg else 0
        qqq_price = float(qqq_dy['Close'].iloc[-1])
        tqqq_price = float(tqqq_wk['Close'].iloc[-1])
        usd_price = float(usd_wk['Close'].iloc[-1])
        soxx_price = float(soxx_dy['Close'].iloc[-1])
        
        # QQQ 주봉 RSI (일봉 → W-FRI 리샘플링, 진행 중인 주 포함)
        qqq_wk_for_rsi = qqq_dy[['Open', 'High', 'Low', 'Close', 'Volume']].resample('W-FRI').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        calculate_indicators(qqq_wk_for_rsi)
        qqq_rsi_wk = float(qqq_wk_for_rsi['RSI'].iloc[-1])

        # QQQ 월봉 RSI (원칙 1-3: 월봉 RSI 80 단일 기준)
        qqq_rsi_mo, _ = calculate_indicators(qqq_mo)
        
        # QQQ 월봉 120개월 이평선 이격도 (period=max 데이터로 진짜 120개월 MA 계산)
        qqq_mo['MA120'] = qqq_mo['Close'].rolling(window=120, min_periods=120).mean()
        _qqq_ma120_series = qqq_mo['MA120'].dropna()
        _qqq_ma120 = float(_qqq_ma120_series.iloc[-1]) if not _qqq_ma120_series.empty else None
        qqq_mo_dev = (float(qqq_mo['Close'].iloc[-1]) / _qqq_ma120) - 1.0 if _qqq_ma120 else 0
        
        # MDD 및 RSI 계산 (원칙 0: QQQ MDD는 '수정종가(Adj Close)' 기준으로 노이즈 제거)
        calculate_indicators(qqq_dy, price_col='Adj Close')
        qqq_mdd = float(qqq_dy['DD'].iloc[-1])
        
        tqqq_rsi_wk, tqqq_mdd = calculate_indicators(tqqq_wk, price_col='Adj Close')
        usd_rsi_wk, usd_mdd = calculate_indicators(usd_wk, price_col='Adj Close')
        
        # SOXX RSI (일봉 → W-FRI 리샘플링) + MDD (cummax 전체 기간 기준)
        soxx_wk_for_rsi = soxx_dy[['Open', 'High', 'Low', 'Close', 'Volume']].resample('W-FRI').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        calculate_indicators(soxx_wk_for_rsi)
        soxx_rsi_wk = float(soxx_wk_for_rsi['RSI'].iloc[-1])

        # SOXX 월봉 RSI 및 120개월 이평선 이격도 (period=max 데이터로 진짜 120개월 MA 계산)
        soxx_rsi_mo, _ = calculate_indicators(soxx_mo)
        soxx_mo['MA120'] = soxx_mo['Close'].rolling(window=120, min_periods=120).mean()
        _soxx_ma120_series = soxx_mo['MA120'].dropna()
        _soxx_ma120 = float(_soxx_ma120_series.iloc[-1]) if not _soxx_ma120_series.empty else None
        soxx_mo_dev = (float(soxx_mo['Close'].iloc[-1]) / _soxx_ma120) - 1.0 if _soxx_ma120 else 0

        _soxx_dd_col = 'Adj Close' if 'Adj Close' in soxx_dy.columns else 'Close'
        soxx_dy['Roll_Max'] = soxx_dy[_soxx_dd_col].cummax()
        soxx_dy['DD'] = (soxx_dy[_soxx_dd_col] / soxx_dy['Roll_Max']) - 1.0
        soxx_mdd = float(soxx_dy['DD'].iloc[-1])

        return {
            'qqq_dy': qqq_dy, 'qqq_price': qqq_price,
            'qqq_rsi_wk': qqq_rsi_wk, 'qqq_rsi_mo': qqq_rsi_mo, 'qqq_mdd': qqq_mdd, 'qqq_mo_dev': qqq_mo_dev,
            'soxx_dy': soxx_dy, 'soxx_price': soxx_price, 'soxx_rsi_wk': soxx_rsi_wk, 'soxx_rsi_mo': soxx_rsi_mo, 'soxx_mdd': soxx_mdd, 'soxx_mo_dev': soxx_mo_dev,
            'tqqq_wk': tqqq_wk, 'tqqq_price': tqqq_price, 'tqqq_rsi_wk': tqqq_rsi_wk, 'tqqq_mdd': tqqq_mdd,
            'usd_wk': usd_wk, 'usd_price': usd_price, 'usd_rsi_wk': usd_rsi_wk, 'usd_mdd': usd_mdd,
            'usd_krw': current_rate, 'fx_10y_avg': fx_10y_avg, 'fx_deviation': fx_deviation
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
st.markdown(f"**Ver {APP_VERSION} (The Ultimate Simple)** | System Owner: **Busan Programmer** | Core Asset: **TQQQ & USD (Let them race)**")

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
            st.number_input("A: 달러 예수금 (SGOV/BOXX)", min_value=0, step=100, key="a_cash_usd", format="%d")

        with st.expander("⚔️ 계좌 B: 스나이퍼 (매매)", expanded=True):
            st.number_input("B: TQQQ 보유 수량", min_value=0.0, step=0.01, key="b_tqqq_qty", format="%.2f")
            st.number_input("B: TQQQ 평균단가 (KRW)", min_value=0, step=100, key="b_tqqq_avg", format="%d")
            st.markdown("---")
            st.number_input("B: USD 보유 수량", min_value=0.0, step=0.01, key="b_usd_qty", format="%.2f")
            st.number_input("B: USD 평균단가 (KRW)", min_value=0, step=100, key="b_usd_avg", format="%d")
            st.number_input("B: 원화 예수금", min_value=0, step=100000, key="b_cash_krw", format="%d")
            st.number_input("B: 달러 예수금 (SGOV/BOXX)", min_value=0, step=100, key="b_cash_usd", format="%d")

        with st.expander("🛡️ 계좌 C: 벙커 (세금/비상)", expanded=True):
            st.number_input("C: 원화 예수금 (수익금 22%, 파킹통장/CMA)", min_value=0, step=100000, key="c_cash_krw", format="%d")

        with st.expander("👨‍👩‍👧 계좌 D: 가족 생존 계좌 (투자 절대 금지)", expanded=False):
            st.number_input("D: 원화 생활비 (12~24개월분)", min_value=0, step=100000, key="d_cash_krw", format="%d", help="투자 계좌와 완벽히 분리. 스나이퍼 총알로 절대 전용 금지. 시스템 총자산/Level 계산에서 제외됩니다.")

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

    # [원칙 0] 마스터 인덱스: QQQ(달러 차트)만으로 버블 판정. SOXX는 표시 전용.
    qqq_rsi_mo = mkt['qqq_rsi_mo']
    soxx_rsi_mo = mkt['soxx_rsi_mo']
    soxx_rsi_wk_val = mkt['soxx_rsi_wk']
    qqq_mo_dev = mkt['qqq_mo_dev']
    soxx_mo_dev = mkt['soxx_mo_dev']

    # [V24.5] Level 2(이격도) 버블 방어는 Level {BUBBLE_LEVEL2_GATE} 이상(시드 펌핑 구간 이후)에서만 발동.
    # Level 1~{BUBBLE_LEVEL2_GATE-1} 구간은 월 적립금의 물타기 효율이 극대화되므로 이격도 룰을 완전히 무시한다.
    is_level2_bubble_raw = (qqq_mo_dev >= 1.0)
    is_level2_bubble = is_level2_bubble_raw and (current_level >= BUBBLE_LEVEL2_GATE)
    is_level1_bubble = (qqq_rsi_mo >= 80)
    is_circuit_breaker = is_level1_bubble or is_level2_bubble
    # [V24.5] 월 적립금 분배용: Level 1~{BUBBLE_LEVEL2_GATE-1}에서는 버블 경보 중에도 100% 현금 전환 없이
    # Level 목표 비중대로 기계적 매수를 지속 (FOMO 방지, 시드 펌핑 우선).
    is_seed_pumping_level = current_level < BUBBLE_LEVEL2_GATE

    # [원칙 0] 우선순위: 전시 상황(MDD -15% 이하)이면 버블 경보 목표 비중 조정 완전 무시
    if is_level2_bubble and qqq_mdd > -0.15:
        target_cash_ratio = min(1.0, target_cash_ratio + 0.20)
        target_stock_ratio = 1.0 - target_cash_ratio

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
    q2.metric("QQQ 주봉RSI(참고) / 월봉RSI(기준)", f"{qqq_rsi:.1f} / {qqq_rsi_mo:.1f}", get_rsi_label(qqq_rsi_mo))
    if mkt['qqq_mo_dev'] >= 1.0 and current_level < BUBBLE_LEVEL2_GATE:
        _qqq_dev_label = f"⚪ 버블(무시, LV<{BUBBLE_LEVEL2_GATE})"
    elif mkt['qqq_mo_dev'] >= 1.0:
        _qqq_dev_label = "🚨 버블"
    else:
        _qqq_dev_label = "안정"
    q3.metric("QQQ 120월 이격도", f"{mkt['qqq_mo_dev']*100:.1f}%", _qqq_dev_label)
    q4.metric("QQQ MDD", f"{qqq_mdd*100:.2f}%", get_mdd_label(qqq_mdd))

    # SOXX
    soxx_rsi_wk_val = mkt['soxx_rsi_wk']
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("SOXX 현재가", f"${mkt['soxx_price']:.2f} ({format_krw(mkt['soxx_price']*usd_krw_rate)})")
    s2.metric("SOXX 주봉 RSI", f"{soxx_rsi_wk_val:.1f}", get_rsi_label(soxx_rsi_wk_val))
    s3.metric("SOXX 120월 이격도", f"{mkt['soxx_mo_dev']*100:.1f}%", "🚨 버블" if mkt['soxx_mo_dev'] >= 1.0 else "안정")
    s4.metric("SOXX MDD", f"{mkt['soxx_mdd']*100:.2f}%", get_mdd_label(mkt['soxx_mdd']))

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

    if st.session_state.d_cash_krw > 0:
        st.caption(f"👨‍👩‍👧 **계좌 D (가족 생존 계좌, 시스템 계산 제외):** {format_krw(st.session_state.d_cash_krw)} — 투자 절대 금지, 스나이퍼 재원 전용 불가")
    
    # TQ:USD 비율 계산
    tqqq_ratio_in_stock = total_tqqq_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    usd_ratio_in_stock = total_usd_krw / total_stock_krw if total_stock_krw > 0 else 0.5
    tq_pct = int(tqqq_ratio_in_stock * 100)
    us_pct = int(usd_ratio_in_stock * 100)

    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
    row2_col1.metric("총 주식 평가금", format_krw(total_stock_krw))
    row2_col2.metric("총 현금(SGOV/BOXX)", format_krw(total_cash_krw))
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
    
    # [원칙 2-1] 환율 극단값 방어: 10년 평균 대비 +20% 이상이면 분할 환전 경보
    fx_deviation = mkt.get('fx_deviation', 0)
    is_fx_extreme = fx_deviation >= 0.20
    fx_warning = f"\n\n💱 **[환율 경보]** 현재 환율이 10년 평균({format_krw(mkt.get('fx_10y_avg', 0))}/$) 대비 **+{fx_deviation*100:.1f}%** 폭등 상태입니다. 이번 달 환전은 **4주 분할 환전**으로 진행하세요. (환율 예측 매매 아님, 심리적 방어 목적)" if is_fx_extreme else ""

    # 월급 적립 가이드
    monthly_msg = ""
    monthly_color = "blue"
    if qqq_mdd <= -0.15:
        monthly_msg = f"📉 **전시 상황 (MDD {qqq_mdd*100:.1f}%)**: 월급 100% ({format_krw(st.session_state.monthly_contribution)}) 주식 매수 (TQQQ 50 : USD 50). 현금 적립 금지!"
        monthly_color = "red"
    elif is_circuit_breaker and is_seed_pumping_level:
        # [V24.5] Level 1~{BUBBLE_LEVEL2_GATE-1} 시드 펌핑 구간: FOMO 방지를 위해 버블 경보 중에도
        # 신규 적립금을 100% 현금으로 돌리지 않고 Level 목표 비중대로 기계적 매수를 지속.
        buy_stock = st.session_state.monthly_contribution * target_stock_ratio
        buy_cash = st.session_state.monthly_contribution * target_cash_ratio
        monthly_msg = f"🌱 **버블 경보 중 시드 펌핑 유지 (LV<{BUBBLE_LEVEL2_GATE})**: 월급 {format_krw(st.session_state.monthly_contribution)}을 Level 목표비율대로 주식 {format_krw(buy_stock)} / 현금(SGOV/BOXX) {format_krw(buy_cash)} 배분 매수. (기존 보유 물량 리밸런싱 매도는 원칙대로 정상 집행)"
        monthly_color = "blue"
    elif is_circuit_breaker:
        monthly_msg = f"🚨 **버블 경보 발동 (LV{current_level}≥{BUBBLE_LEVEL2_GATE})**: 신규 적립금 100% ({format_krw(st.session_state.monthly_contribution)}) 현금(SGOV/BOXX) 매수! (주식 매수 금지)"
        monthly_color = "orange"
    else:
        buy_stock = st.session_state.monthly_contribution * target_stock_ratio
        buy_cash = st.session_state.monthly_contribution * target_cash_ratio
        monthly_msg = f"✅ **평시 적립**: 월급 {format_krw(st.session_state.monthly_contribution)}을 Level 목표비율에 맞춰 주식 {format_krw(buy_stock)} / 현금(SGOV/BOXX) {format_krw(buy_cash)} 배분 매수."
    monthly_msg += fx_warning
    
    # 매매/스나이핑 가이드
    final_action = ""
    detail_msg = ""
    action_color = "blue"
    
    # [원칙 3] Last Bullet: 보유 현금의 15%는 영구 보존, 가용 현금은 85%
    reserve_cash_krw = total_cash_krw * 0.15
    available_cash_krw = total_cash_krw * 0.85

    def _update_sniper_flag(new_val):
        """ATH 파일 직접 갱신과 충돌 없이 sniper_mode_active만 부분 업데이트 (원칙 1-2 추적용)"""
        st.session_state.sniper_mode_active = new_val
        try:
            with open(DATA_FILE, "r") as _f:
                _d = json.load(_f)
            _d['sniper_mode_active'] = new_val
            with open(DATA_FILE, "w") as _f:
                json.dump(_d, _f)
        except:
            pass

    # [원칙 1-2] 스나이핑 원상복구 추적: MDD -15% 이하가 한 번이라도 발생하면 플래그 ON,
    # 이후 사용자가 실제로 리로드(매도+자산정보 갱신)하여 현금 비중이 목표치를 회복하면 자동 OFF.
    if qqq_mdd <= -0.15 and not st.session_state.sniper_mode_active:
        _update_sniper_flag(True)
    elif st.session_state.sniper_mode_active and current_cash_ratio >= target_cash_ratio - 0.001:
        _update_sniper_flag(False)

    if is_loss:
        # [원칙 1-1] 손실 확정 절대 금지: 본전 미도달 상태에서는 리로드도 절대 발동하지 않음.
        if qqq_mdd <= -0.15:
            final_action = "🛡️ LOSS PROTECTION + 스나이퍼 대기 (본전 미도달)"
            detail_msg = "헌법 제1조: 현재 포트폴리오가 손실 구간이므로 매도는 금지되나, 하락장이므로 아래 [월급 투입 지침]에 따라 신규 적립금은 100% 주식에 몰빵합니다. 계좌 총수익률이 본전(0%)을 넘는 순간 목표 현금 비중으로 자동 리로드됩니다."
        else:
            final_action = "🛡️ LOSS PROTECTION (절대 방어)"
            detail_msg = "헌법 제1조: 현재 포트폴리오가 손실 구간이므로 **어떠한 경우에도 매도를 금지**합니다. (존버)"
        action_color = "red"
    else:
        if qqq_mdd <= -0.15:
            # [원칙 3] MDD Sniper (Last Bullet 적용)
            input_cash = 0
            ratio_str = ""
            base_str = ""
            if qqq_mdd <= -0.50:
                input_cash = reserve_cash_krw
                ratio_str = "최후의 보루 100%"
                base_str = "보유 현금의 15% (Last Bullet)"
            elif qqq_mdd <= -0.45:
                input_cash = available_cash_krw * 0.4; ratio_str = "40% (영끌)"; base_str = "가용 현금(85%)의"
            elif qqq_mdd <= -0.35:
                input_cash = available_cash_krw * 0.3; ratio_str = "30%"; base_str = "가용 현금(85%)의"
            elif qqq_mdd <= -0.25:
                input_cash = available_cash_krw * 0.2; ratio_str = "20%"; base_str = "가용 현금(85%)의"
            else:
                input_cash = available_cash_krw * 0.1; ratio_str = "10%"; base_str = "가용 현금(85%)의"

            final_action = f"🔫 MDD SNIPER ({ratio_str})"
            if qqq_mdd <= -0.50:
                detail_msg = f"💣 **블랙 스완 (MDD {qqq_mdd*100:.1f}%)!** {base_str} {format_krw(input_cash)} 전액 투입! (그동안 아껴둔 최후의 총알)"
            else:
                detail_msg = f"하락장 스나이퍼 발동! {base_str} {ratio_str} ({format_krw(input_cash)}) 투입. (Last Bullet 15%는 미사용 보존 중: {format_krw(reserve_cash_krw)})"
            action_color = "green"

        elif st.session_state.sniper_mode_active:
            # [핵심 룰] 스나이핑 원상복구 (Account Break-Even Reload): 시장 회복(MDD -15% 초과) + 계좌 본전 이상
            sell_needed_reload = max(0, (total_assets * target_cash_ratio) - total_cash_krw)
            final_action = "🔄 SNIPER RELOAD (스나이핑 원상복구)"
            detail_msg = f"과거 하락장에서 스나이핑한 자금이 본전(0%) 이상으로 회복되었습니다! {format_krw(sell_needed_reload)} 만큼 매도하여 현재 Level의 목표 현금 비중({target_cash_ratio*100:.1f}%)으로 즉시 복구하세요. (TQQQ/USD 현재 보유 비중대로 비례 매도, 토스 이동평균법 하에서 별도 트랜치 추적 불필요, 수익금 22% 세금 격리)"
            action_color = "orange"

        elif is_circuit_breaker:
            sell_needed = (total_assets * target_cash_ratio) - total_cash_krw
            
            trigger_str = []
            if is_level1_bubble: trigger_str.append(f"QQQ 월봉 RSI {qqq_rsi_mo:.1f}")
            if is_level2_bubble: trigger_str.append(f"QQQ 120월 이격도 {qqq_mo_dev*100:.1f}% (LV{current_level}≥{BUBBLE_LEVEL2_GATE})")
            
            trigger_msg = ", ".join(trigger_str)
            
            if sell_needed > 0:
                if is_level2_bubble:
                    final_action = "🚨 LEVEL 2 BUBBLE (역사적 버블 방어)"
                    detail_msg = f"[{trigger_msg}] 돌파! 목표 현금 비중에 **+20% 추가 확보** (총 {target_cash_ratio*100:.1f}%).\n{format_krw(sell_needed)} 만큼 매도하여 현금(SGOV/BOXX) 채움. (TQQQ/USD 현재 보유 비중대로 비례 매도, 수익금 22% 세금 격리 필수)"
                else:
                    final_action = "🔥 LEVEL 1 BUBBLE (단기 과열 방어)"
                    detail_msg = f"[{trigger_msg}] 돌파! Level {current_level}의 목표 현금 비중({target_cash_ratio*100:.1f}%) 확보를 위해 {format_krw(sell_needed)} 만큼만 매도하여 현금(SGOV/BOXX) 채움. (TQQQ/USD 현재 보유 비중대로 비례 매도, 수익금 22% 세금 격리 필수)"
                action_color = "orange"
            else:
                final_action = "✅ HOLD (현금 벙커 완충)"
                detail_msg = f"[{trigger_msg}] 광기 구간이나, 이미 목표 현금(SGOV/BOXX) 비중을 충족했습니다."
        
        else:
            final_action = "🧘 STABLING (관망)"
            detail_msg = "평시 구간입니다. '승자의 질주(Let Winners Run)'를 즐기며 기존 포지션을 유지하십시오. 듀얼 리밸런싱은 오직 '월 적립금(새 돈)'으로만 맞춥니다."
            if is_level2_bubble_raw:
                detail_msg += f"\n\n🌱 *[V24.5] 참고: QQQ 120월 이격도가 100%를 초과했지만, 현재 Level {current_level}은 시드 펌핑 구간(LV<{BUBBLE_LEVEL2_GATE})이므로 역사적 버블 방어 룰을 의도적으로 무시하고 공격적으로 자산을 불립니다.*"

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
