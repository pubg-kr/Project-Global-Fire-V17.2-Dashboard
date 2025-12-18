import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import os
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURATION & PERSISTENCE
# ==========================================
st.set_page_config(page_title="PROJECT GLOBAL FIRE HQ", layout="wide", page_icon="🔥")

CONFIG_FILE = 'user_config.json'

# 기본값 설정
DEFAULT_CONFIG = {
    "cash_krw": 5000000,
    "cash_usd": 1000.0,
    "qty_a": 100,
    "avg_a": 50.0,
    "qty_b": 50,
    "avg_b": 70.0,
    "monthly_income": 4500000,
    "tg_token": "",
    "tg_chat_id": ""
}

# 설정 불러오기 함수
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

# 설정 저장 함수 (값이 바뀔 때마다 실행)
def save_config():
    config = {
        "cash_krw": st.session_state.cash_krw,
        "cash_usd": st.session_state.cash_usd,
        "qty_a": st.session_state.qty_a,
        "avg_a": st.session_state.avg_a,
        "qty_b": st.session_state.qty_b,
        "avg_b": st.session_state.avg_b,
        "monthly_income": st.session_state.monthly_income,
        "tg_token": st.session_state.tg_token,
        "tg_chat_id": st.session_state.tg_chat_id
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# 초기화: 세션 상태에 설정값 로드
if 'config_loaded' not in st.session_state:
    config = load_config()
    for key, value in config.items():
        st.session_state[key] = value
    st.session_state.config_loaded = True

# Phase Definition
PHASES = {
    "Phase 1": {"limit": 500000000, "stock_ratio": 0.8, "cash_ratio": 0.2, "desc": "공격 (Accumulation)"},
    "Phase 2": {"limit": 1000000000, "stock_ratio": 0.7, "cash_ratio": 0.3, "desc": "표준 (Standard)"},
    "Phase 3": {"limit": 2000000000, "stock_ratio": 0.6, "cash_ratio": 0.4, "desc": "방어 (Defense)"},
    "Phase 4": {"limit": 2500000000, "stock_ratio": 0.5, "cash_ratio": 0.5, "desc": "안착 (Landing)"},
    "Phase 5": {"limit": 99999999999, "stock_ratio": 0.4, "cash_ratio": 0.6, "desc": "은퇴 (Freedom)"}
}

USD_KRW = 1430.0 

# ==========================================
# 📡 TELEGRAM BOT FUNCTION
# ==========================================
def send_telegram_message(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
        return True
    except Exception as e:
        return False

# ==========================================
# 📥 SIDEBAR: USER INPUT (Auto-Save 적용)
# ==========================================
st.sidebar.header("💼 Asset Input")
st.sidebar.caption("※ 입력하면 자동 저장됩니다.")

# Cash Input
st.sidebar.subheader("💰 보유 현금")
st.sidebar.number_input("보유 현금 (KRW)", step=100000, format="%d", key="cash_krw", on_change=save_config)
st.sidebar.caption(f"👉 ₩{st.session_state.cash_krw:,.0f}") # 가독성용 텍스트

st.sidebar.number_input("보유 현금 (USD)", step=100.0, format="%.2f", key="cash_usd", on_change=save_config)

# Account A
st.sidebar.markdown("---")
st.sidebar.subheader("🔒 계좌 A (Vault)")
st.sidebar.number_input("TQQQ 수량 (A)", step=1, format="%d", key="qty_a", on_change=save_config)
st.sidebar.number_input("TQQQ 평단가 (A)", step=0.1, format="%.2f", key="avg_a", on_change=save_config)

# Account B
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 계좌 B (Shield)")
st.sidebar.number_input("TQQQ 수량 (B)", step=1, format="%d", key="qty_b", on_change=save_config)
st.sidebar.number_input("TQQQ 평단가 (B)", step=0.1, format="%.2f", key="avg_b", on_change=save_config)

# Monthly Input
st.sidebar.markdown("---")
st.sidebar.subheader("📅 월 투자금")
st.sidebar.number_input("월 입금액 (KRW)", step=100000, format="%d", key="monthly_income", on_change=save_config)
st.sidebar.caption(f"👉 ₩{st.session_state.monthly_income:,.0f}") # 가독성용 텍스트

# Daily Calculation Display
daily_amt = st.session_state.monthly_income / 20
st.sidebar.info(f"🗓️ **일일 자동 매수 설정액**\n\n**₩{daily_amt:,.0f}** (20거래일 기준)")


# Telegram Settings
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Telegram Bot")
st.sidebar.text_input("Bot Token", type="password", key="tg_token", on_change=save_config)
st.sidebar.text_input("Chat ID", key="tg_chat_id", on_change=save_config)

# ==========================================
# 📊 DATA FETCHING
# ==========================================
@st.cache_data(ttl=3600)
def get_market_data():
    try:
        tqqq = yf.Ticker("TQQQ")
        tqqq_price = tqqq.history(period="1d")['Close'].iloc[-1]
        
        qqq = yf.Ticker("QQQ")
        qqq_hist = qqq.history(period="1y", interval="1wk")
        delta = qqq_hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        qqq_price = qqq_hist['Close'].iloc[-1]
        return tqqq_price, current_rsi, qqq_price
    except:
        return 0, 0, 0

tqqq_price, rsi_val, qqq_val = get_market_data()

if tqqq_price == 0:
    st.error("데이터 로딩 실패. 잠시 후 다시 시도해주세요.")
    st.stop()

# ==========================================
# 🧮 CALCULATIONS
# ==========================================
# Session State 값 사용
total_cash_krw = st.session_state.cash_krw + (st.session_state.cash_usd * USD_KRW)
stock_val_usd = (st.session_state.qty_a + st.session_state.qty_b) * tqqq_price
stock_val_krw = stock_val_usd * USD_KRW
total_asset_krw = total_cash_krw + stock_val_krw

current_phase = "Phase 1"
for p, data in PHASES.items():
    if total_asset_krw <= data['limit']:
        current_phase = p
        break

target_stock_ratio = PHASES[current_phase]['stock_ratio']
target_cash_ratio = PHASES[current_phase]['cash_ratio']
current_stock_ratio = stock_val_krw / total_asset_krw if total_asset_krw > 0 else 0
current_cash_ratio = total_cash_krw / total_asset_krw if total_asset_krw > 0 else 0

total_invested_usd = (st.session_state.qty_a * st.session_state.avg_a) + (st.session_state.qty_b * st.session_state.avg_b)
total_invested_krw = total_invested_usd * USD_KRW
is_loss = total_asset_krw < total_invested_krw

# ==========================================
# 🧠 CRO INTELLIGENCE (LOGIC ENGINE)
# ==========================================
action_color = "blue"
action_msg = "대기"
detail_msg = ""

if is_loss:
    action_color = "red"
    action_msg = "🛑 HOLD (손실 구간)"
    detail_msg = "현재 총 자산이 원금보다 적습니다. RSI나 리밸런싱 신호가 와도 **절대 매도하지 마십시오.**"
elif rsi_val >= 80:
    action_color = "red"
    action_msg = "🚨 SELL (광기 구간)"
    sell_amount = total_asset_krw * (target_cash_ratio + 0.1) - total_cash_krw
    detail_msg = f"RSI 80 돌파. 현금 비중을 {int((target_cash_ratio+0.1)*100)}%까지 늘리십시오.\n"
    detail_msg += f"**매도 목표액:** 약 ₩{sell_amount:,.0f}"
elif rsi_val >= 75:
    action_color = "orange"
    action_msg = "🟡 STOP BUYING (과열)"
    detail_msg = "추가 매수를 멈추고 현금을 모으십시오."
elif abs(current_stock_ratio - target_stock_ratio) > 0.1:
    action_color = "orange"
    action_msg = "⚖️ REBALANCING (비중 조절)"
    if current_stock_ratio > target_stock_ratio:
        diff = stock_val_krw - (total_asset_krw * target_stock_ratio)
        detail_msg = f"주식 비중 과다. **계좌 B**에서 약 ₩{diff:,.0f} 매도하십시오."
    else:
        diff = (total_asset_krw * target_stock_ratio) - stock_val_krw
        detail_msg = f"주식 비중 미달. **계좌 B**에 약 ₩{diff:,.0f} 매수하십시오."
else:
    action_color = "green"
    action_msg = "🟢 BUY / HOLD (적립 구간)"
    buy_amount = 0
    if rsi_val < 60:
        if current_cash_ratio > target_cash_ratio:
            buy_amount = st.session_state.monthly_income * target_stock_ratio * 1.5
            detail_msg = f"RSI {rsi_val:.1f} (기회) + 현금 충분. **1.5배 부스터 가동.**\n"
        else:
            buy_amount = st.session_state.monthly_income * (target_stock_ratio + 0.1)
            detail_msg = f"RSI {rsi_val:.1f} (기회) + 현금 부족. **쥐어짜기(Squeeze) 모드.**\n"
    else:
        buy_amount = st.session_state.monthly_income * target_stock_ratio
        detail_msg = f"RSI {rsi_val:.1f} (표준). 정량 적립.\n"
    
    # 일일 매수액 계산 추가
    daily_buy_rec = buy_amount / 20
    detail_msg += f"**이번 달 총 매수 권장액:** ₩{buy_amount:,.0f}\n"
    detail_msg += f"👉 **매일 자동 주문(20일):** **₩{daily_buy_rec:,.0f}** 씩 설정하세요."

# Telegram Report Message
report_msg = f"""
🔥 *PROJECT GLOBAL FIRE REPORT* 🔥
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

📊 *Market Status*
• QQQ RSI: `{rsi_val:.1f}`
• TQQQ Price: `${tqqq_price:.2f}`

💰 *Portfolio Status*
• Total: `₩{total_asset_krw:,.0f}`
• Phase: `{current_phase}`
• Stock: `{current_stock_ratio*100:.1f}%` (Target: {target_stock_ratio*100}%)

🤖 *CRO Order*
**[{action_msg}]**
{detail_msg.replace('**','')}
"""

# ==========================================
# 🖥️ UI DISPLAY
# ==========================================
st.title("🏛️ PROJECT GLOBAL FIRE HQ")
st.markdown(f"**System Owner:** 30세 프로그래머 | **CRO:** Gemini | **Ver:** 17.8 (Auto-Save)")

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("총 자산 (KRW)", f"₩{total_asset_krw:,.0f}")
col2.metric("현재 Phase", f"{current_phase}", f"{PHASES[current_phase]['desc']}")
col3.metric("QQQ RSI (주봉)", f"{rsi_val:.1f}", delta_color="inverse")
col4.metric("QQQ 현재가", f"${qqq_val:.2f}", f"(₩{qqq_val*USD_KRW:,.0f})")

# Progress
phase_limit = PHASES[current_phase]['limit']
st.progress(min(total_asset_krw / phase_limit, 1.0))
st.caption(f"다음 단계까지: ₩{phase_limit - total_asset_krw:,.0f} 남음")

# CRO Signal Box
st.divider()
st.subheader("🤖 CRO Action Signal")
st.markdown(f"""
<div style="padding: 20px; border-radius: 10px; background-color: {'#ffebee' if action_color=='red' else '#e8f5e9' if action_color=='green' else '#fff3e0'}; border: 2px solid {action_color};">
    <h2 style="color: {action_color}; margin:0;">{action_msg}</h2>
    <p style="font-size: 1.2em; margin-top: 10px;">{detail_msg}</p>
</div>
""", unsafe_allow_html=True)

# Charts
st.divider()
col_l, col_r = st.columns(2)
with col_l:
    st.subheader("자산 배분 현황")
    fig = go.Figure(data=[go.Pie(labels=['TQQQ', 'Cash'], values=[stock_val_krw, total_cash_krw], hole=.4)])
    fig.update_layout(height=250, margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig, use_container_width=True)
with col_r:
    st.subheader("Phase 목표 배분")
    fig2 = go.Figure(data=[go.Pie(labels=['Target Stock', 'Target Cash'], values=[target_stock_ratio, target_cash_ratio], hole=.4, opacity=0.6)])
    fig2.update_layout(height=250, margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig2, use_container_width=True)

# Telegram Button
st.sidebar.markdown("---")
if st.sidebar.button("📱 CRO 보고서 전송"):
    if st.session_state.tg_token and st.session_state.tg_chat_id:
        success = send_telegram_message(st.session_state.tg_token, st.session_state.tg_chat_id, report_msg)
        if success:
            st.sidebar.success("보고서 전송 완료!")
        else:
            st.sidebar.error("전송 실패. Token/ID 확인 바람.")
    else:
        st.sidebar.warning("Token과 Chat ID를 입력하세요.")
