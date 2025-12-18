import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. 설정 및 상수 정의 (Configuration)
# ==========================================
st.set_page_config(page_title="Global Fire CRO V17.2", layout="wide", page_icon="🔥")

# Phase별 목표 비중 정의 (V17.2)
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
    """QQQ 주봉 데이터, RSI, MDD 계산"""
    ticker = "QQQ"
    # 주봉 데이터 가져오기 (충분한 기간)
    df = yf.download(ticker, interval="1wk", period="2y", progress=False)
    
    if df.empty:
        st.error("데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")
        return None, None, None, None

    # RSI 계산 (14주)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MDD 계산 (고점 대비 하락률)
    # 현재 시점 기준 전고점 찾기 (최근 1년)
    window = 52
    df['Roll_Max'] = df['Close'].rolling(window=window, min_periods=1).max()
    df['DD'] = (df['Close'] / df['Roll_Max']) - 1.0
    
    current_price = float(df['Close'].iloc[-1])
    current_rsi = float(df['RSI'].iloc[-1])
    current_dd = float(df['DD'].iloc[-1])
    
    return df, current_price, current_rsi, current_dd

def determine_phase(total_assets):
    """총 자산에 따른 Phase 결정"""
    for p in range(1, 6):
        if total_assets <= PHASE_CONFIG[p]['limit']:
            return p
    return 5

def format_krw(value):
    return f"{int(value):,}원"

# ==========================================
# 3. 사이드바: 사용자 입력 (User Input)
# ==========================================
st.sidebar.header("📝 자산 정보 입력")
st.sidebar.markdown("---")

monthly_contribution = st.sidebar.number_input("월 적립금 (투자금)", min_value=0, value=5000000, step=100000)

st.sidebar.subheader("잔고 현황")
tqqq_balance = st.sidebar.number_input("TQQQ 평가금액 (현재 잔고)", min_value=0, value=100000000, step=1000000)
cash_balance = st.sidebar.number_input("보유 현금 (RP/달러)", min_value=0, value=20000000, step=1000000)

st.sidebar.subheader("수익률 확인용")
total_principal = st.sidebar.number_input("총 원금 (투자 원금)", min_value=0, value=90000000, step=1000000, help="현재 손실 중인지 판단하기 위해 필요합니다.")

# 계산
total_assets = tqqq_balance + cash_balance
current_phase = determine_phase(total_assets)
target_stock_ratio = PHASE_CONFIG[current_phase]['target_stock']
target_cash_ratio = PHASE_CONFIG[current_phase]['target_cash']

current_stock_ratio = tqqq_balance / total_assets if total_assets > 0 else 0
current_cash_ratio = cash_balance / total_assets if total_assets > 0 else 0

is_loss = total_assets < total_principal # 손실 여부

# ==========================================
# 4. 메인 화면: 대시보드 (Dashboard)
# ==========================================
st.title("🔥 Global Fire CRO System")
st.markdown(f"**Ver 17.2 (Universal Logic)** | System Owner: **Busan Programmer**")

# --- 시장 데이터 로딩 ---
df, qqq_price, qqq_rsi, qqq_mdd = get_market_data()

if df is not None:
    # 1. 시장 상황판 (Market Status)
    st.header("1. 시장 상황판 (Market Status)")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("QQQ 현재가", f"${qqq_price:.2f}")
    
    with col2:
        rsi_color = "normal"
        if qqq_rsi >= 80: rsi_color = "inverse" # Red
        elif qqq_rsi < 60: rsi_color = "off" # Greenish concept
        st.metric("QQQ 주봉 RSI", f"{qqq_rsi:.1f}", delta=None)
        if qqq_rsi >= 80: st.error("🚨 광기 (Overbought)")
        elif qqq_rsi >= 75: st.warning("🔥 과열 (Warning)")
        elif qqq_rsi < 60: st.success("💰 기회 (Opportunity)")
        else: st.info("⚖️ 표준 (Neutral)")

    with col3:
        mdd_pct = qqq_mdd * 100
        st.metric("QQQ MDD (고점대비)", f"{mdd_pct:.2f}%")
        if mdd_pct <= -20: st.error("📉 위기 발생 (Crisis)")
        else: st.success("✅ 안정 (Stable)")

    # 2. 내 포트폴리오 진단 (My Portfolio)
    st.markdown("---")
    st.header("2. 포트폴리오 진단 (Diagnosis)")
    
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    p_col1.metric("현재 Phase", PHASE_CONFIG[current_phase]['name'])
    p_col2.metric("총 자산", format_krw(total_assets), delta=format_krw(total_assets - total_principal))
    p_col3.metric("TQQQ 비중", f"{current_stock_ratio*100:.1f}%", f"목표: {target_stock_ratio*100}%")
    p_col4.metric("현금 비중", f"{current_cash_ratio*100:.1f}%", f"목표: {target_cash_ratio*100}%")

    # 손실 여부 표시
    if is_loss:
        st.error(f"🛑 현재 계좌 손실 중 (-{total_principal - total_assets:,.0f}원) -> [절대 방패] 가동됨")
    else:
        st.success(f"✅ 현재 계좌 수익 중 (+{total_assets - total_principal:,.0f}원)")

    # 3. CRO 자동 판단 및 지시 (Decision Engine)
    st.markdown("---")
    st.header("3. CRO 실행 명령 (Action Protocol)")

    final_action = ""
    detail_msg = ""
    action_color = "blue" # default

    # --- V17.2 Logic Engine ---
    
    # Step 1: 생존 확인
    if is_loss:
        final_action = "🛑 HOLD (매도 금지)"
        detail_msg = "현재 계좌가 손실 중입니다. RSI가 높거나 리밸런싱 신호가 있어도 **절대 팔지 마십시오.** 신규 매수만 가능합니다."
        action_color = "red"
        
        # 손실 중일 때도 매수는 해야 하므로 아래 로직 체크 (단, 매도 신호는 무시)
        # RSI 80 이상이면 매수도 금지
        if qqq_rsi >= 80:
            final_action = "🛑 COMPLETE STOP (관망)"
            detail_msg = "손실 중이라 매도할 수 없지만, RSI가 80 이상(광기)이므로 **매수도 금지**합니다. 현금을 모으십시오."
        
        elif qqq_mdd <= -0.2:
            # 위기 대응 (손실 중이어도 물타기)
            input_cash = 0
            if qqq_mdd <= -0.5: input_cash = cash_balance
            elif qqq_mdd <= -0.3: input_cash = cash_balance * 0.3
            elif qqq_mdd <= -0.2: input_cash = cash_balance * 0.2
            final_action = f"📉 CRISIS BUY (위기 매수)"
            detail_msg = f"MDD {mdd_pct:.1f}% 돌파. 보유 현금의 일부({format_krw(input_cash)})를 즉시 투입하십시오."
            
        elif current_stock_ratio < (target_stock_ratio - 0.1):
            # 비중 미달 (손실 중이니 매수는 OK)
            buy_amt = (total_assets * target_stock_ratio) - tqqq_balance
            final_action = f"⚖️ REBALANCE BUY (비중 채우기)"
            detail_msg = f"TQQQ 비중이 {current_stock_ratio*100:.1f}%로 너무 낮습니다. {format_krw(buy_amt)} 매수하여 {target_stock_ratio*100}%를 맞추십시오."
        
        else:
            # 월급날 로직
            final_action += " / 월급 적립 대기"

    # Step 2: 광기 차단 (수익 중일 때만)
    elif qqq_rsi >= 80:
        # 목표 현금 + 10%p 만들기
        target_cash_panic = target_cash_ratio + 0.1
        target_cash_amt = total_assets * target_cash_panic
        sell_amt = cash_balance - target_cash_amt # 현금이 목표보다 적으면 마이너스 -> 매도해야 함
        
        # sell_amt가 음수여야 현금이 부족한 것 -> 아님. 현금을 늘려야 하니까 TQQQ를 팔아야 함.
        # 목표 현금 보유액: total_assets * 0.3 (Phase 1 기준)
        # 현재 현금: cash_balance
        # 필요 현금: target_cash_amt - cash_balance
        sell_needed = target_cash_amt - cash_balance
        
        if sell_needed > 0:
            final_action = "🚨 PANIC SELL (광기 매도)"
            detail_msg = f"RSI 80 돌파. 현금 비중을 {target_cash_panic*100:.0f}%까지 늘려야 합니다. TQQQ를 **{format_krw(sell_needed)}** 어치 매도하십시오."
            action_color = "red"
        else:
            final_action = "✅ HOLD (현금 충분)"
            detail_msg = f"RSI 80 상태이나, 이미 현금을 {target_cash_panic*100:.0f}% 이상 보유 중입니다. 매수하지 말고 대기하십시오."

    # Step 3: 위기 대응
    elif qqq_mdd <= -0.2:
        input_cash = 0
        ratio_str = ""
        if qqq_mdd <= -0.5: 
            input_cash = cash_balance
            ratio_str = "100%"
        elif qqq_mdd <= -0.3: 
            input_cash = cash_balance * 0.3
            ratio_str = "30%"
        elif qqq_mdd <= -0.2: 
            input_cash = cash_balance * 0.2
            ratio_str = "20%"
        
        final_action = "📉 CRISIS BUY (긴급 매수)"
        detail_msg = f"MDD {mdd_pct:.1f}% 기록. 보유 현금의 **{ratio_str} ({format_krw(input_cash)})**를 즉시 투입하십시오."
        action_color = "green"

    # Step 4: 리밸런싱
    elif current_stock_ratio > (target_stock_ratio + 0.1):
        sell_amt = tqqq_balance - (total_assets * target_stock_ratio)
        final_action = "⚖️ REBALANCE SELL (과열 방지)"
        detail_msg = f"TQQQ 비중({current_stock_ratio*100:.1f}%)이 허용 범위(+10%p)를 초과했습니다. **{format_krw(sell_amt)}** 매도하여 {target_stock_ratio*100}%로 맞추십시오."
        action_color = "orange"
        
    elif current_stock_ratio < (target_stock_ratio - 0.1):
        buy_amt = (total_assets * target_stock_ratio) - tqqq_balance
        final_action = "⚖️ REBALANCE BUY (저점 매수)"
        detail_msg = f"TQQQ 비중({current_stock_ratio*100:.1f}%)이 허용 범위(-10%p) 미달입니다. **{format_krw(buy_amt)}** 매수하여 {target_stock_ratio*100}%로 맞추십시오."
        action_color = "green"

    # Step 5: 월급날 루틴 (아무 특이사항 없을 때)
    else:
        final_action = "📅 MONTHLY ROUTINE (월급 적립)"
        action_color = "blue"
        
        buy_amount = 0
        if qqq_rsi >= 75:
            buy_amount = 0
            detail_msg = "RSI 75 이상(과열)입니다. 이번 달 월급은 **전액 현금(RP)**으로 보유하십시오."
        elif qqq_rsi >= 60:
            buy_amount = monthly_contribution * target_stock_ratio
            detail_msg = f"표준 구간입니다. 월급의 {target_stock_ratio*100:.0f}%인 **{format_krw(buy_amount)}**을 매수하십시오."
        else:
            # RSI 60 미만 (기회)
            if cash_balance > (total_assets * target_cash_ratio):
                # 부자 모드 (1.5배)
                base_buy = monthly_contribution * target_stock_ratio
                buy_amount = base_buy * 1.5
                detail_msg = f"RSI 60 미만 + 현금 충분(부자 모드). 표준 매수액의 1.5배인 **{format_krw(buy_amount)}**을 공격적으로 매수하십시오."
            else:
                # 거지 모드 (Target + 10%p)
                squeeze_ratio = min(target_stock_ratio + 0.1, 1.0)
                buy_amount = monthly_contribution * squeeze_ratio
                detail_msg = f"RSI 60 미만 + 현금 부족(쥐어짜기). 월급의 {squeeze_ratio*100:.0f}%인 **{format_krw(buy_amount)}**을 매수하십시오."

    # --- 결과 출력 ---
    st.info(f"💡 **CRO 판단 결과:** {final_action}")
    
    if action_color == "red":
        st.error(detail_msg)
    elif action_color == "green":
        st.success(detail_msg)
    elif action_color == "orange":
        st.warning(detail_msg)
    else:
        st.info(detail_msg)

    # 4. 참고용 차트 (Chart)
    st.markdown("---")
    with st.expander("📊 QQQ 주봉 차트 & RSI 확인하기"):
        # 캔들차트와 RSI를 Plotly로 그리기
        fig = go.Figure()
        
        # 캔들
        fig.add_trace(go.Candlestick(x=df.index,
                        open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'], name='QQQ'))
        
        fig.update_layout(title='QQQ Weekly Chart', yaxis_title='Price')
        st.plotly_chart(fig, use_container_width=True)
        
        # RSI 차트
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')))
        fig_rsi.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Overbought (80)")
        fig_rsi.add_hline(y=60, line_dash="dash", line_color="green", annotation_text="Opportunity (60)")
        fig_rsi.update_layout(title='QQQ Weekly RSI', yaxis_title='RSI', yaxis_range=[0, 100])
        st.plotly_chart(fig_rsi, use_container_width=True)

else:
    st.warning("데이터 로딩 중입니다...")