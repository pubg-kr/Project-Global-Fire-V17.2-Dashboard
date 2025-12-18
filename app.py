import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. 설정 및 상수 정의 (Configuration)
# ==========================================
st.set_page_config(page_title="Global Fire CRO V17.4", layout="wide", page_icon="🔥")

# Phase별 목표 비중 정의
PHASE_CONFIG = {
    1: {"limit": 500000000, "target_stock": 0.8, "target_cash": 0.2, "name": "Phase 1 (가속)"},
    2: {"limit": 1000000000, "target_stock": 0.7, "target_cash": 0.3, "name": "Phase 2 (상승)"},
    3: {"limit": 2000000000, "target_stock": 0.6, "target_cash": 0.4, "name": "Phase 3 (순항)"},
    4: {"limit": 2500000000, "target_stock": 0.5, "target_cash": 0.5, "name": "Phase 4 (안전)"},
    5: {"limit": float('inf'), "target_stock": 0.4, "target_cash": 0.6, "name": "Phase 5 (졸업)"}
}

# ==========================================
# 2. 유틸리티 함수 (Functions)
# ==========================================

def get_market_data():
    """QQQ 데이터, RSI, MDD 및 환율 정보 가져오기"""
    try:
        # 1. QQQ 데이터
        df = yf.download("QQQ", interval="1wk", period="2y", progress=False)
        
        # 2. 환율 데이터 (USD/KRW)
        exch = yf.download("KRW=X", period="1d", progress=False)
        
        if df.empty or exch.empty:
            return None, None, None, None, None

        # MultiIndex 처리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if isinstance(exch.columns, pd.MultiIndex):
            exch.columns = exch.columns.get_level_values(0)

        # 환율 추출
        current_rate = float(exch['Close'].iloc[-1])

        # RSI 계산
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MDD 계산
        window = 52
        df['Roll_Max'] = df['Close'].rolling(window=window, min_periods=1).max()
        df['DD'] = (df['Close'] / df['Roll_Max']) - 1.0
        
        current_price = float(df['Close'].iloc[-1])
        current_rsi = float(df['RSI'].iloc[-1])
        current_dd = float(df['DD'].iloc[-1])
        
        return df, current_price, current_rsi, current_dd, current_rate
        
    except Exception as e:
        st.error(f"데이터 처리 중 오류: {e}")
        return None, None, None, None, None

def determine_phase(total_assets):
    for p in range(1, 6):
        if total_assets <= PHASE_CONFIG[p]['limit']:
            return p
    return 5

def format_krw(value):
    return f"{int(value):,}원"

# ==========================================
# 3. 메인 로직 및 UI
# ==========================================
st.title("🔥 Global Fire CRO System")
st.markdown(f"**Ver 17.4 (Dual Account Support)** | System Owner: **Busan Programmer**")

# 데이터 로딩
df, qqq_price, qqq_rsi, qqq_mdd, usd_krw_rate = get_market_data()

if df is not None:
    # --- 사이드바 (입력) ---
    st.sidebar.header("📝 자산 정보 입력")
    st.sidebar.info(f"💵 현재 환율: **1달러 = {int(usd_krw_rate):,}원**")
    
    monthly_contribution = st.sidebar.number_input("이번 달 투입금 (월급)", min_value=0, value=5000000, step=100000)
    st.sidebar.markdown("---")

    # [계좌 A] 입력
    with st.sidebar.expander("🏦 계좌 A: 금고 (장기보유)", expanded=True):
        st.caption("절대 팔지 않는 계좌 (평단가 낮음)")
        a_tqqq = st.number_input("A: TQQQ 평가금", min_value=0, value=80000000, step=1000000)
        a_cash_krw = st.number_input("A: 원화 예수금", min_value=0, value=0, step=100000)
        a_cash_usd = st.number_input("A: 달러 예수금", min_value=0, value=0, step=100)

    # [계좌 B] 입력
    with st.sidebar.expander("⚔️ 계좌 B: 스나이퍼 (매매용)", expanded=True):
        st.caption("리밸런싱 및 트레이딩 계좌 (평단가 높음)")
        b_tqqq = st.number_input("B: TQQQ 평가금", min_value=0, value=20000000, step=1000000)
        b_cash_krw = st.number_input("B: 원화 예수금", min_value=0, value=1000000, step=100000)
        b_cash_usd = st.number_input("B: 달러 예수금", min_value=0, value=15000, step=100)

    st.sidebar.markdown("---")
    status_option = st.sidebar.radio(
        "전체 계좌 수익 상태",
        ["🔴 수익 중 (Profit)", "🔵 손실 중 (Loss)"],
        index=0
    )
    is_loss = "손실" in status_option

    # --- 내부 자동 합산 로직 ---
    total_tqqq_krw = a_tqqq + b_tqqq
    total_cash_krw = (a_cash_krw + b_cash_krw) + ((a_cash_usd + b_cash_usd) * usd_krw_rate)
    total_assets = total_tqqq_krw + total_cash_krw
    
    # Phase 및 비중 계산
    current_phase = determine_phase(total_assets)
    target_stock_ratio = PHASE_CONFIG[current_phase]['target_stock']
    target_cash_ratio = PHASE_CONFIG[current_phase]['target_cash']
    
    current_stock_ratio = total_tqqq_krw / total_assets if total_assets > 0 else 0
    current_cash_ratio = total_cash_krw / total_assets if total_assets > 0 else 0

    # --- 메인 대시보드 ---
    
    # 1. 시장 상황판
    st.header("1. 시장 상황판 (Market Status)")
    col1, col2, col3 = st.columns(3)
    col1.metric("QQQ 현재가", f"${qqq_price:.2f}")
    
    rsi_label = "표준 (Neutral)"
    if qqq_rsi >= 80: rsi_label = "🚨 광기 (Overbought)"
    elif qqq_rsi >= 75: rsi_label = "🔥 과열 (Warning)"
    elif qqq_rsi < 60: rsi_label = "💰 기회 (Opportunity)"
    col2.metric("QQQ 주봉 RSI", f"{qqq_rsi:.1f}", rsi_label)
    
    mdd_pct = qqq_mdd * 100
    mdd_label = "📉 위기 (Crisis)" if mdd_pct <= -20 else "✅ 안정 (Stable)"
    col3.metric("QQQ MDD", f"{mdd_pct:.2f}%", mdd_label)

    # 2. 포트폴리오 진단
    st.markdown("---")
    st.header("2. 포트폴리오 진단 (Diagnosis)")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("현재 Phase", PHASE_CONFIG[current_phase]['name'])
    p2.metric("총 자산 (합산)", format_krw(total_assets))
    p3.metric("TQQQ 비중", f"{current_stock_ratio*100:.1f}%", f"목표: {target_stock_ratio*100}%")
    p4.metric("현금 비중", f"{current_cash_ratio*100:.1f}%", f"목표: {target_cash_ratio*100}%")
    
    # 계좌별 현황 표시
    st.caption(f"🏦 A계좌(금고): TQQQ {format_krw(a_tqqq)} / 현금 {format_krw(a_cash_krw + a_cash_usd*usd_krw_rate)}")
    st.caption(f"⚔️ B계좌(매매): TQQQ {format_krw(b_tqqq)} / 현금 {format_krw(b_cash_krw + b_cash_usd*usd_krw_rate)}")

    if is_loss:
        st.error("🛑 [손실 중] 절대 방패 가동: 매도 금지")
    else:
        st.success("✅ [수익 중] 정상 로직 가동")

    # 3. CRO 실행 명령
    st.markdown("---")
    st.header("3. CRO 실행 명령 (Action Protocol)")
    
    final_action = ""
    detail_msg = ""
    action_color = "blue"
    trade_account_msg = "👉 **거래는 [B계좌: 스나이퍼]에서 수행하십시오.**"

    # --- Logic Engine V17.4 ---
    
    if is_loss:
        final_action = "🛑 HOLD (매도 금지)"
        detail_msg = "손실 중입니다. 절대 팔지 마십시오."
        action_color = "red"
        
        if qqq_rsi >= 80:
            final_action = "🛑 COMPLETE STOP (관망)"
            detail_msg = "손실 중이나 RSI 80(광기)이므로 매수도 금지합니다."
        elif qqq_mdd <= -0.2:
            input_cash = 0
            if qqq_mdd <= -0.5: input_cash = total_cash_krw
            elif qqq_mdd <= -0.3: input_cash = total_cash_krw * 0.3
            elif qqq_mdd <= -0.2: input_cash = total_cash_krw * 0.2
            final_action = "📉 CRISIS BUY (위기 매수)"
            detail_msg = f"MDD {mdd_pct:.1f}% 위기. 현금의 일부({format_krw(input_cash)})를 투입하십시오."
            action_color = "green"
        elif current_stock_ratio < (target_stock_ratio - 0.1):
            buy_amt = (total_assets * target_stock_ratio) - total_tqqq_krw
            final_action = "⚖️ REBALANCE BUY (비중 채우기)"
            detail_msg = f"비중 미달. {format_krw(buy_amt)} 매수하여 {target_stock_ratio*100}%를 맞추십시오."
            action_color = "green"
        else:
            final_action += " / 월급 적립 대기"

    elif qqq_rsi >= 80:
        target_cash_panic = target_cash_ratio + 0.1
        target_cash_amt = total_assets * target_cash_panic
        sell_needed = target_cash_amt - total_cash_krw
        
        if sell_needed > 0:
            final_action = "🚨 PANIC SELL (광기 매도)"
            detail_msg = f"RSI 80 돌파. 현금 비중 {target_cash_panic*100:.0f}% 확보를 위해 TQQQ {format_krw(sell_needed)} 매도."
            action_color = "red"
        else:
            final_action = "✅ HOLD (현금 충분)"
            detail_msg = "RSI 80이나 현금이 충분합니다. 대기하십시오."

    elif qqq_mdd <= -0.2:
        input_cash = 0
        ratio_str = ""
        if qqq_mdd <= -0.5: input_cash = total_cash_krw; ratio_str="100%"
        elif qqq_mdd <= -0.3: input_cash = total_cash_krw * 0.3; ratio_str="30%"
        elif qqq_mdd <= -0.2: input_cash = total_cash_krw * 0.2; ratio_str="20%"
        
        final_action = "📉 CRISIS BUY (긴급 매수)"
        detail_msg = f"MDD {mdd_pct:.1f}%. 현금의 {ratio_str} ({format_krw(input_cash)}) 투입."
        action_color = "green"

    elif current_stock_ratio > (target_stock_ratio + 0.1):
        sell_amt = total_tqqq_krw - (total_assets * target_stock_ratio)
        final_action = "⚖️ REBALANCE SELL (과열 방지)"
        detail_msg = f"비중 초과. {format_krw(sell_amt)} 매도하여 {target_stock_ratio*100}% 복귀."
        action_color = "orange"
        
    elif current_stock_ratio < (target_stock_ratio - 0.1):
        buy_amt = (total_assets * target_stock_ratio) - total_tqqq_krw
        final_action = "⚖️ REBALANCE BUY (저점 매수)"
        detail_msg = f"비중 미달. {format_krw(buy_amt)} 매수하여 {target_stock_ratio*100}% 복귀."
        action_color = "green"

    else:
        final_action = "📅 MONTHLY ROUTINE (월급 적립)"
        buy_amount = 0
        if qqq_rsi >= 75:
            detail_msg = "RSI 75 이상. 매수 금지 (전액 현금 저축)."
        elif qqq_rsi >= 60:
            buy_amount = monthly_contribution * target_stock_ratio
            detail_msg = f"표준 구간. 월급의 {target_stock_ratio*100:.0f}%인 {format_krw(buy_amount)} 매수."
        else:
            if total_cash_krw > (total_assets * target_cash_ratio):
                buy_amount = (monthly_contribution * target_stock_ratio) * 1.5
                detail_msg = f"기회(RSI<60) + 현금부자. 1.5배 가속: {format_krw(buy_amount)} 매수."
            else:
                squeeze_ratio = min(target_stock_ratio + 0.1, 1.0)
                buy_amount = monthly_contribution * squeeze_ratio
                detail_msg = f"기회(RSI<60) + 현금부족. 쥐어짜기({squeeze_ratio*100:.0f}%): {format_krw(buy_amount)} 매수."

    st.info(f"💡 **판단:** {final_action}")
    
    # 메시지 출력
    if action_color == "red": st.error(detail_msg)
    elif action_color == "green": st.success(detail_msg)
    elif action_color == "orange": st.warning(detail_msg)
    else: st.info(detail_msg)
    
    # 매매 계좌 안내
    if "매도" in final_action or "SELL" in final_action:
        st.markdown(f"🔥 {trade_account_msg} (세금 절약)")
    elif "매수" in final_action or "BUY" in final_action:
         st.markdown(f"💰 **매수는 [A계좌: 금고]에 우선 적립하되, 단기 자금은 [B계좌]를 이용하십시오.**")
    
    # 차트 (생략 없이 동일하게 유지)
    st.markdown("---")
    with st.expander("📊 차트 확인"):
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(title='QQQ Weekly', height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        fig_rsi = go.Figure(data=[go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'))])
        fig_rsi.add_hline(y=80, line_color="red", line_dash="dash")
        fig_rsi.add_hline(y=60, line_color="green", line_dash="dash")
        fig_rsi.update_layout(title='RSI', height=300, yaxis_range=[0, 100])
        st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.warning("데이터 로딩 중... (잠시만 기다려주세요)")