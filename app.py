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
        "a_tqqq": 80000000,
        "a_cash_krw": 0,
        "a_cash_usd": 0,
        "b_tqqq": 20000000,
        "b_cash_krw": 1000000,
        "b_cash_usd": 15000
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return default_data
    return default_data

def save_data():
    """현재 Session State 값을 JSON으로 저장"""
    data = {
        "monthly_contribution": st.session_state.monthly_contribution,
        "a_tqqq": st.session_state.a_tqqq,
        "a_cash_krw": st.session_state.a_cash_krw,
        "a_cash_usd": st.session_state.a_cash_usd,
        "b_tqqq": st.session_state.b_tqqq,
        "b_cash_krw": st.session_state.b_cash_krw,
        "b_cash_usd": st.session_state.b_cash_usd
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ==========================================
# 1. 설정 및 상수
# ==========================================
st.set_page_config(page_title="Global Fire CRO V17.7", layout="wide", page_icon="🔥")

PHASE_CONFIG = {
    1: {"limit": 500000000, "target_stock": 0.8, "target_cash": 0.2, "name": "Phase 1 (가속)"},
    2: {"limit": 1000000000, "target_stock": 0.7, "target_cash": 0.3, "name": "Phase 2 (상승)"},
    3: {"limit": 2000000000, "target_stock": 0.6, "target_cash": 0.4, "name": "Phase 3 (순항)"},
    4: {"limit": 2500000000, "target_stock": 0.5, "target_cash": 0.5, "name": "Phase 4 (안전)"},
    5: {"limit": float('inf'), "target_stock": 0.4, "target_cash": 0.6, "name": "Phase 5 (졸업)"}
}

PROTOCOL_TEXT = """
### 📜 Master Protocol (요약)
1. **손실 중 매도 금지:** 파란불엔 절대 팔지 않는다.
2. **RSI 80 광기:** 현금 비중을 Target + 10%까지 늘린다 (B계좌 매도).
3. **MDD 위기:** 현금을 투입하여 평단가를 낮춘다.
4. **월급 적립:** RSI 60 미만일 때 적극 매수한다.
"""

# ==========================================
# 2. 유틸리티 함수
# ==========================================
def get_market_data():
    try:
        df = yf.download("QQQ", interval="1wk", period="2y", progress=False)
        exch = yf.download("KRW=X", period="1d", progress=False)
        
        if df.empty or exch.empty: return None, None, None, None, None

        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if isinstance(exch.columns, pd.MultiIndex): exch.columns = exch.columns.get_level_values(0)

        current_rate = float(exch['Close'].iloc[-1])

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        window = 52
        df['Roll_Max'] = df['Close'].rolling(window=window, min_periods=1).max()
        df['DD'] = (df['Close'] / df['Roll_Max']) - 1.0
        
        return df, float(df['Close'].iloc[-1]), float(df['RSI'].iloc[-1]), float(df['DD'].iloc[-1]), current_rate
    except:
        return None, None, None, None, None

def determine_phase(total_assets):
    for p in range(1, 6):
        if total_assets <= PHASE_CONFIG[p]['limit']: return p
    return 5

def format_krw(value):
    return f"{int(value):,}원"

# ==========================================
# 3. 메인 로직
# ==========================================
st.title("🔥 Global Fire CRO System")
st.markdown("**Ver 17.7 (Local Persistence)** | System Owner: **Busan Programmer**")

# 데이터 로드 (초기화)
saved_data = load_data()

# Session State 초기화 (없으면 파일 값으로)
if "monthly_contribution" not in st.session_state:
    for key, val in saved_data.items():
        st.session_state[key] = val

with st.expander("📜 Master Protocol (규정집)", expanded=False):
    st.markdown(PROTOCOL_TEXT)

df, qqq_price, qqq_rsi, qqq_mdd, usd_krw_rate = get_market_data()

if df is not None:
    # --- 사이드바 (자동 저장 적용) ---
    st.sidebar.header("📝 자산 정보 (자동 저장됨)")
    st.sidebar.info(f"💵 환율: **{int(usd_krw_rate):,}원/$**")
    
    # 월급 입력
    st.sidebar.number_input("이번 달 투입금 (월급)", min_value=0, step=100000, key="monthly_contribution", on_change=save_data, format="%d")
    st.sidebar.caption(f"👉 확인: **{format_krw(st.session_state.monthly_contribution)}**") # 가독성 헬퍼
    
    st.sidebar.markdown("---")
    
    # A계좌
    with st.sidebar.expander("🏦 계좌 A: 금고 (장기)", expanded=True):
        st.number_input("A: TQQQ 평가금", min_value=0, step=1000000, key="a_tqqq", on_change=save_data, format="%d")
        st.caption(f"👉 {format_krw(st.session_state.a_tqqq)}")
        
        st.number_input("A: 원화 예수금", min_value=0, step=100000, key="a_cash_krw", on_change=save_data, format="%d")
        st.caption(f"👉 {format_krw(st.session_state.a_cash_krw)}")
        
        st.number_input("A: 달러 예수금", min_value=0, step=100, key="a_cash_usd", on_change=save_data, format="%d")
        st.caption(f"👉 ${st.session_state.a_cash_usd:,.2f}")

    # B계좌
    with st.sidebar.expander("⚔️ 계좌 B: 스나이퍼 (매매)", expanded=True):
        st.number_input("B: TQQQ 평가금", min_value=0, step=1000000, key="b_tqqq", on_change=save_data, format="%d")
        st.caption(f"👉 {format_krw(st.session_state.b_tqqq)}")
        
        st.number_input("B: 원화 예수금", min_value=0, step=100000, key="b_cash_krw", on_change=save_data, format="%d")
        st.caption(f"👉 {format_krw(st.session_state.b_cash_krw)}")
        
        st.number_input("B: 달러 예수금", min_value=0, step=100, key="b_cash_usd", on_change=save_data, format="%d")
        st.caption(f"👉 ${st.session_state.b_cash_usd:,.2f}")

    st.sidebar.markdown("---")
    status_option = st.sidebar.radio("계좌 상태", ["🔴 수익 중 (Profit)", "🔵 손실 중 (Loss)"], index=0)
    is_loss = "손실" in status_option

    # --- 계산 로직 ---
    # Session State 값을 사용하여 계산
    total_tqqq_krw = st.session_state.a_tqqq + st.session_state.b_tqqq
    total_cash_krw = (st.session_state.a_cash_krw + st.session_state.b_cash_krw) + \
                     ((st.session_state.a_cash_usd + st.session_state.b_cash_usd) * usd_krw_rate)
    total_assets = total_tqqq_krw + total_cash_krw
    
    current_phase = determine_phase(total_assets)
    target_stock_ratio = PHASE_CONFIG[current_phase]['target_stock']
    target_cash_ratio = PHASE_CONFIG[current_phase]['target_cash']
    
    current_stock_ratio = total_tqqq_krw / total_assets if total_assets > 0 else 0
    current_cash_ratio = total_cash_krw / total_assets if total_assets > 0 else 0

    # --- 1. 시장 상황판 ---
    st.header("1. 시장 상황판 (Market Status)")
    col1, col2, col3 = st.columns(3)
    
    qqq_krw = qqq_price * usd_krw_rate
    col1.metric("QQQ 현재가", f"${qqq_price:.2f}", f"({format_krw(qqq_krw)})")
    
    rsi_label = "표준 (Neutral)"
    if qqq_rsi >= 80: rsi_label = "🚨 광기 (Overbought)"
    elif qqq_rsi >= 75: rsi_label = "🔥 과열 (Warning)"
    elif qqq_rsi < 60: rsi_label = "💰 기회 (Opportunity)"
    col2.metric("QQQ 주봉 RSI", f"{qqq_rsi:.1f}", rsi_label)
    
    mdd_pct = qqq_mdd * 100
    mdd_label = "📉 위기 (Crisis)" if mdd_pct <= -20 else "✅ 안정 (Stable)"
    col3.metric("QQQ MDD", f"{mdd_pct:.2f}%", mdd_label)

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

    p1, p2, p3, p4 = st.columns(4)
    phase_info = PHASE_CONFIG[current_phase]
    
    p1.metric("현재 Phase", phase_info['name'], f"목표: TQQQ {int(phase_info['target_stock']*100)}% : 현금 {int(phase_info['target_cash']*100)}%")
    p2.metric("총 자산 (합산)", format_krw(total_assets))
    p3.metric("TQQQ 비중", f"{current_stock_ratio*100:.1f}%", f"목표: {target_stock_ratio*100}%")
    p4.metric("현금 비중", f"{current_cash_ratio*100:.1f}%", f"목표: {target_cash_ratio*100}%")

    if is_loss: st.error("🛑 [손실 중] 절대 방패 가동: 매도 금지")
    else: st.success("✅ [수익 중] 정상 로직 가동")

    # --- 3. CRO 실행 명령 ---
    st.markdown("---")
    st.header("3. CRO 실행 명령 (Action Protocol)")
    
    final_action = ""
    detail_msg = ""
    action_color = "blue"
    trade_guide = "👉 **거래는 [B계좌: 스나이퍼]에서 수행하십시오.**"

    # Logic Engine V17.7
    if is_loss:
        final_action = "🛑 HOLD (매도 금지)"
        detail_msg = "손실 중입니다. 절대 팔지 마십시오."
        action_color = "red"
        if qqq_rsi >= 80:
            final_action = "🛑 COMPLETE STOP (관망)"
            detail_msg = "손실 중 + RSI 80. 아무것도 하지 마십시오."
        elif qqq_mdd <= -0.2:
            input_cash = 0
            if qqq_mdd <= -0.5: input_cash = total_cash_krw
            elif qqq_mdd <= -0.3: input_cash = total_cash_krw * 0.3
            elif qqq_mdd <= -0.2: input_cash = total_cash_krw * 0.2
            final_action = "📉 CRISIS BUY (위기 매수)"
            detail_msg = f"MDD {mdd_pct:.1f}% 위기. 현금 투입: {format_krw(input_cash)}"
            action_color = "green"
        elif current_stock_ratio < (target_stock_ratio - 0.1):
            buy_amt = (total_assets * target_stock_ratio) - total_tqqq_krw
            final_action = "⚖️ REBALANCE BUY (비중 채우기)"
            detail_msg = f"비중 미달. {format_krw(buy_amt)} 매수."
            action_color = "green"
        else:
            final_action += " / 월급 적립 대기"

    elif qqq_rsi >= 80:
        target_cash_panic = target_cash_ratio + 0.1
        target_cash_amt = total_assets * target_cash_panic
        sell_needed = target_cash_amt - total_cash_krw
        if sell_needed > 0:
            final_action = "🚨 PANIC SELL (광기 매도)"
            detail_msg = f"RSI 80 돌파. {format_krw(sell_needed)} 매도하여 현금 {target_cash_panic*100:.0f}% 확보."
            action_color = "red"
        else:
            final_action = "✅ HOLD (현금 충분)"
            detail_msg = "RSI 80이나 현금이 충분합니다. 대기."

    elif qqq_mdd <= -0.2:
        input_cash = 0
        ratio_str = ""
        if qqq_mdd <= -0.5: input_cash = total_cash_krw; ratio_str="100%"
        elif qqq_mdd <= -0.3: input_cash = total_cash_krw * 0.3; ratio_str="30%"
        elif qqq_mdd <= -0.2: input_cash = total_cash_krw * 0.2; ratio_str="20%"
        final_action = "📉 CRISIS BUY (긴급 매수)"
        detail_msg = f"MDD {mdd_pct:.1f}%. 현금 {ratio_str} ({format_krw(input_cash)}) 투입."
        action_color = "green"

    elif current_stock_ratio > (target_stock_ratio + 0.1):
        sell_amt = total_tqqq_krw - (total_assets * target_stock_ratio)
        final_action = "⚖️ REBALANCE SELL (과열 방지)"
        detail_msg = f"비중 초과. {format_krw(sell_amt)} 매도."
        action_color = "orange"
        
    elif current_stock_ratio < (target_stock_ratio - 0.1):
        buy_amt = (total_assets * target_stock_ratio) - total_tqqq_krw
        final_action = "⚖️ REBALANCE BUY (저점 매수)"
        detail_msg = f"비중 미달. {format_krw(buy_amt)} 매수."
        action_color = "green"

    else:
        final_action = "📅 MONTHLY ROUTINE (월급 적립)"
        buy_amount = 0
        # 월급 적립 로직
        if qqq_rsi >= 75:
            detail_msg = "RSI 75 이상. 매수 금지 (현금 저축)."
        elif qqq_rsi >= 60:
            buy_amount = st.session_state.monthly_contribution * target_stock_ratio
            detail_msg = f"표준 구간. 월급의 {target_stock_ratio*100:.0f}% ({format_krw(buy_amount)}) 매수."
        else:
            if total_cash_krw > (total_assets * target_cash_ratio):
                buy_amount = (st.session_state.monthly_contribution * target_stock_ratio) * 1.5
                detail_msg = f"기회(RSI<60) + 현금부자. 1.5배 가속: {format_krw(buy_amount)} 매수."
            else:
                squeeze_ratio = min(target_stock_ratio + 0.1, 1.0)
                buy_amount = st.session_state.monthly_contribution * squeeze_ratio
                detail_msg = f"기회(RSI<60) + 현금부족. 쥐어짜기({squeeze_ratio*100:.0f}%): {format_krw(buy_amount)} 매수."
        
        # [요청] 일일 적립액 표시 (매수 금액이 0보다 클 때만)
        if buy_amount > 0:
            daily_amount = buy_amount / 20
            detail_msg += f" \n\n👉 **일일 자동적립 설정액 (20일 기준): {format_krw(daily_amount)}**"

    st.info(f"💡 **판단:** {final_action}")
    
    if action_color == "red": st.error(detail_msg)
    elif action_color == "green": st.success(detail_msg)
    elif action_color == "orange": st.warning(detail_msg)
    else: st.info(detail_msg)
    
    if "매도" in final_action or "SELL" in final_action:
        st.markdown(f"🔥 {trade_guide}")
    elif "매수" in final_action or "BUY" in final_action:
         st.markdown(f"💰 **매수는 [A계좌: 금고] 우선, 단기는 [B계좌] 활용**")

    # --- 4. 차트 ---
    st.markdown("---")
    with st.expander("📊 차트 확인 (QQQ & RSI)", expanded=True):
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(title='QQQ Weekly', height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        fig_rsi = go.Figure(data=[go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'))])
        fig_rsi.add_hline(y=80, line_color="red", line_dash="dash")
        fig_rsi.add_hline(y=60, line_color="green", line_dash="dash")
        fig_rsi.update_layout(title='RSI', height=250, yaxis_range=[0, 100], margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.warning("데이터 로딩 중... (잠시만 기다려주세요)")