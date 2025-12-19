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
        "a_cash_krw": 0,
        "a_cash_usd": 0,
        "b_tqqq_qty": 200.0,
        "b_tqqq_avg": 85000,
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
        "a_cash_krw": st.session_state.a_cash_krw,
        "a_cash_usd": st.session_state.a_cash_usd,
        "b_tqqq_qty": st.session_state.b_tqqq_qty,
        "b_tqqq_avg": st.session_state.b_tqqq_avg,
        "b_cash_krw": st.session_state.b_cash_krw,
        "b_cash_usd": st.session_state.b_cash_usd,
        "c_cash_krw": st.session_state.c_cash_krw
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ==========================================
# 1. 설정 및 상수
# ==========================================
st.set_page_config(page_title="Global Fire CRO V17.9", layout="wide", page_icon="🔥")

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
        # QQQ (주봉/월봉)
        qqq_wk = yf.download("QQQ", interval="1wk", period="2y", progress=False)
        qqq_mo = yf.download("QQQ", interval="1mo", period="5y", progress=False)
        
        # TQQQ (주봉/월봉)
        tqqq_wk = yf.download("TQQQ", interval="1wk", period="2y", progress=False)
        tqqq_mo = yf.download("TQQQ", interval="1mo", period="5y", progress=False)
        
        # 환율
        exch = yf.download("KRW=X", period="1d", progress=False)
        
        if qqq_wk.empty or exch.empty or tqqq_wk.empty: return None

        # MultiIndex 정리
        for d in [qqq_wk, qqq_mo, tqqq_wk, tqqq_mo, exch]:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)

        current_rate = float(exch['Close'].iloc[-1])
        
        # QQQ 지표
        qqq_price = float(qqq_wk['Close'].iloc[-1])
        qqq_rsi_wk, qqq_mdd = calculate_indicators(qqq_wk)
        qqq_rsi_mo, _ = calculate_indicators(qqq_mo)
        
        # TQQQ 지표
        tqqq_price = float(tqqq_wk['Close'].iloc[-1])
        tqqq_rsi_wk, tqqq_mdd = calculate_indicators(tqqq_wk)
        tqqq_rsi_mo, _ = calculate_indicators(tqqq_mo)
        
        return {
            'qqq_df': qqq_wk,
            'qqq_price': qqq_price,
            'qqq_rsi_wk': qqq_rsi_wk,
            'qqq_rsi_mo': qqq_rsi_mo,
            'qqq_mdd': qqq_mdd,
            'tqqq_price': tqqq_price,
            'tqqq_rsi_wk': tqqq_rsi_wk,
            'tqqq_rsi_mo': tqqq_rsi_mo,
            'tqqq_mdd': tqqq_mdd,
            'usd_krw': current_rate
        }
    except Exception as e:
        return None

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
st.markdown("**Ver 17.9 (Deep Analytics & UI Reform)** | System Owner: **Busan Programmer**")

# 데이터 로드 (초기화)
saved_data = load_data()

# Session State 초기화 (없으면 파일 값으로)
if "monthly_contribution" not in st.session_state:
    for key, val in saved_data.items():
        st.session_state[key] = val

with st.expander("📜 Master Protocol (규정집)", expanded=False):
    st.markdown(PROTOCOL_TEXT)

mkt = get_market_data()

if mkt is not None:
    # 데이터 매핑
    qqq_price = mkt['qqq_price']
    tqqq_price = mkt['tqqq_price']
    usd_krw_rate = mkt['usd_krw']
    qqq_rsi = mkt['qqq_rsi_wk']
    qqq_mdd = mkt['qqq_mdd']
    df = mkt['qqq_df'] # 차트용

    tqqq_krw = tqqq_price * usd_krw_rate  # TQQQ 현재가 (원화)

    # --- 사이드바 (자동 저장 적용) ---
    st.sidebar.header("📝 자산 정보 (자동 저장됨)")
    st.sidebar.info(f"💵 환율: **{int(usd_krw_rate):,}원/$**")
    
    # 월급 입력
    st.sidebar.number_input("이번 달 투입금 (월급)", min_value=0, step=100000, key="monthly_contribution", on_change=save_data, format="%d")
    st.sidebar.caption(f"👉 확인: **{format_krw(st.session_state.monthly_contribution)}**") # 가독성 헬퍼
    
    st.sidebar.markdown("---")
    
    # A계좌
    with st.sidebar.expander("🏦 계좌 A: 금고 (장기)", expanded=True):
        st.number_input("A: TQQQ 보유 수량", min_value=0.0, step=0.01, key="a_tqqq_qty", on_change=save_data, format="%.2f")
        st.number_input("A: TQQQ 평균단가 (KRW)", min_value=0, step=100, key="a_tqqq_avg", on_change=save_data, format="%d")
        
        # A계좌 평가금 자동 계산
        a_tqqq_eval = st.session_state.a_tqqq_qty * tqqq_krw
        st.caption(f"📊 평가금: **{format_krw(a_tqqq_eval)}**")
        
        st.number_input("A: 원화 예수금", min_value=0, step=100000, key="a_cash_krw", on_change=save_data, format="%d")
        st.caption(f"👉 {format_krw(st.session_state.a_cash_krw)}")
        
        st.number_input("A: 달러 예수금", min_value=0, step=100, key="a_cash_usd", on_change=save_data, format="%d")
        st.caption(f"👉 ${st.session_state.a_cash_usd:,.2f}")

    # B계좌
    with st.sidebar.expander("⚔️ 계좌 B: 스나이퍼 (매매)", expanded=True):
        st.number_input("B: TQQQ 보유 수량", min_value=0.0, step=0.01, key="b_tqqq_qty", on_change=save_data, format="%.2f")
        st.number_input("B: TQQQ 평균단가 (KRW)", min_value=0, step=100, key="b_tqqq_avg", on_change=save_data, format="%d")
        
        # B계좌 평가금 자동 계산
        b_tqqq_eval = st.session_state.b_tqqq_qty * tqqq_krw
        st.caption(f"📊 평가금: **{format_krw(b_tqqq_eval)}**")
        
        st.number_input("B: 원화 예수금", min_value=0, step=100000, key="b_cash_krw", on_change=save_data, format="%d")
        st.caption(f"👉 {format_krw(st.session_state.b_cash_krw)}")
        
        st.number_input("B: 달러 예수금", min_value=0, step=100, key="b_cash_usd", on_change=save_data, format="%d")
        st.caption(f"👉 ${st.session_state.b_cash_usd:,.2f}")

    # C계좌 (V17.3 추가)
    with st.sidebar.expander("🛡️ 계좌 C: 벙커 (세금/비상)", expanded=True):
        st.number_input("C: 원화 예수금 (수익금 22%)", min_value=0, step=100000, key="c_cash_krw", on_change=save_data, format="%d")
        st.caption(f"👉 {format_krw(st.session_state.c_cash_krw)}")

    st.sidebar.markdown("---")
    
    # --- 자동 손익 판단 로직 ---
    total_qty = st.session_state.a_tqqq_qty + st.session_state.b_tqqq_qty
    total_invested_krw = (st.session_state.a_tqqq_qty * st.session_state.a_tqqq_avg) + \
                         (st.session_state.b_tqqq_qty * st.session_state.b_tqqq_avg)
    
    avg_price_krw = total_invested_krw / total_qty if total_qty > 0 else 0
    is_loss = tqqq_krw < avg_price_krw if total_qty > 0 else False
    
    profit_rate = 0.0
    if total_qty > 0:
        profit_rate = ((tqqq_krw - avg_price_krw) / avg_price_krw) * 100

    # --- 계산 로직 ---
    # Session State 값을 사용하여 계산
    total_tqqq_krw = a_tqqq_eval + b_tqqq_eval # 자동 계산된 값 사용
    total_cash_krw = (st.session_state.a_cash_krw + st.session_state.b_cash_krw + st.session_state.c_cash_krw) + \
                     ((st.session_state.a_cash_usd + st.session_state.b_cash_usd) * usd_krw_rate)
    total_assets = total_tqqq_krw + total_cash_krw
    
    current_phase = determine_phase(total_assets)
    target_stock_ratio = PHASE_CONFIG[current_phase]['target_stock']
    target_cash_ratio = PHASE_CONFIG[current_phase]['target_cash']
    
    current_stock_ratio = total_tqqq_krw / total_assets if total_assets > 0 else 0
    current_cash_ratio = total_cash_krw / total_assets if total_assets > 0 else 0

    # --- 1. 시장 상황판 ---
    st.header("1. 시장 상황판 (Market Status)")
    
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

    # 포트폴리오 핵심 지표 (7-Column Layout)
    p1, p2, p3, p4, p5, p6, p7 = st.columns(7)
    phase_info = PHASE_CONFIG[current_phase]
    
    # 1. Phase
    p1.metric("현재 Phase", phase_info['name'], f"목표: {int(phase_info['target_stock']*100)}:{int(phase_info['target_cash']*100)}")
    
    # 2. 총 자산
    p2.metric("총 자산 (합산)", format_krw(total_assets))
    
    # 3. 통합 수량 (New)
    p3.metric("통합 보유 수량", f"{total_qty:,.2f}주")

    # 4. 통합 평단
    p4.metric("통합 평단가", format_krw(avg_price_krw))
    
    # 5. 현재 수익률
    if total_qty > 0:
        st_emoji = "🔴" if not is_loss else "🔵"
        p5.metric("현재 수익률", f"{profit_rate:.2f}%", f"{st_emoji} 상태")
    else:
        p5.metric("현재 수익률", "0%", "대기")

    # 6. TQQQ 비중
    p6.metric("TQQQ 비중", f"{current_stock_ratio*100:.1f}%", f"목표: {target_stock_ratio*100}%")
    
    # 7. 현금 비중
    p7.metric("현금 비중", f"{current_cash_ratio*100:.1f}%", f"목표: {target_cash_ratio*100}%")

    if is_loss: st.error("🛑 [손실 중] 절대 방패 가동: 매도 금지")
    else: st.success("✅ [수익 중] 정상 로직 가동")

    # --- 3. CRO 실행 명령 ---
    st.markdown("---")
    st.header("3. CRO 실행 명령 (Action Protocol)")
    
    final_action = ""
    detail_msg = ""
    action_color = "blue"
    
    # 매도 우선순위 결정 (Tax Shield: 평단가 높은 계좌 우선 매도)
    avg_a = st.session_state.a_tqqq_avg
    avg_b = st.session_state.b_tqqq_avg
    
    if avg_a > avg_b and st.session_state.a_tqqq_qty > 0:
        sell_priority_acc = "A계좌 (The Vault)"
        sell_guide_msg = f"👉 **세금 절감: 평단가가 높은 [{sell_priority_acc}]에서 매도하십시오.** (A평단 {format_krw(avg_a)} > B평단 {format_krw(avg_b)})"
    else:
        sell_priority_acc = "B계좌 (The Sniper)"
        sell_guide_msg = f"👉 **세금 절감: 평단가가 높은 [{sell_priority_acc}]에서 매도하십시오.** (B평단 {format_krw(avg_b)} >= A평단 {format_krw(avg_a)})"

    # Logic Engine V17.9 (Refactored for Safety & Continuity)
    # 1단계: 기본 액션 결정 (매수/매도/존버)
    if qqq_rsi >= 80:
        target_cash_panic = target_cash_ratio + 0.1
        target_cash_amt = total_assets * target_cash_panic
        sell_needed = target_cash_amt - total_cash_krw
        if sell_needed > 0:
            final_action = "🚨 PANIC SELL (광기 매도)"
            detail_msg = f"RSI 80 돌파. {format_krw(sell_needed)} 매도하여 현금 {target_cash_panic*100:.0f}% 확보.\n\n⚠️ [Tax Rule] 실현 수익금의 22%는 즉시 [계좌 C]로 이체하십시오."
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
        detail_msg = f"비중 초과. {format_krw(sell_amt)} 매도.\n\n⚠️ [Tax Rule] 실현 수익금의 22%는 즉시 [계좌 C]로 이체하십시오."
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

    # 2단계: 손실 방어 로직 (Override)
    # 손실 중인데 '매도' 시그널이 떴다면 -> 강제로 'HOLD'로 변경
    if is_loss and ("매도" in final_action or "SELL" in final_action):
        final_action = "🛑 LOSS PROTECTION (손실 중 매도 금지)"
        detail_msg = f"원래는 '{final_action}' 신호이나, 현재 손실 중이므로 매도를 금지합니다. (절대 원칙)\n\n👉 **매도 없이 홀딩하거나, 여유 자금이 있다면 적립식 매수를 계속하십시오.**"
        action_color = "red"
        # 매도 가이드 메시지 무효화
        sell_guide_msg = "🚫 **손실 중입니다. 매도 버튼에 손대지 마십시오.**"

    st.info(f"💡 **판단:** {final_action}")
    
    if action_color == "red": st.error(detail_msg)
    elif action_color == "green": st.success(detail_msg)
    elif action_color == "orange": st.warning(detail_msg)
    else: st.info(detail_msg)
    
    if "매도" in final_action or "SELL" in final_action:
        st.markdown(f"🔥 {sell_guide_msg}")
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

    # --- 5. 릴리즈 노트 (Update History) ---
    st.markdown("---")
    with st.expander("📅 릴리즈 노트 (Update History)", expanded=False):
        st.markdown("""
        ### Ver 17.9 (Current) - Deep Analytics & UI Reform
        - **🤖 자동 손익 판단 엔진**: 수동 라디오 버튼 삭제. 보유 수량과 평단가를 기반으로 실시간 손익 상태(수익/손실) 자동 판별.
        - **⚡ 실시간 평가금 계산**: TQQQ 수량 × 실시간 현재가(원화) 연동으로 1원 단위까지 정확한 자산 가치 산출.
        - **📈 심층 시장 분석 (Deep Analytics)**: TQQQ의 주봉/월봉 RSI 및 MDD 지표 추가 (QQQ와 동일 수준 분석).
        - **🛡️ Loss Protection (절대 방패)**: 손실 구간 진입 시 모든 매도 시그널을 강제로 차단하고 홀딩/적립을 유도하는 안전장치 강화.
        - **🖥️ UI/UX 전면 개편**:
            - 포트폴리오 진단 섹션 7-Column 확장 (통합 수량, 평단, 수익률 등 핵심 지표 일렬 배치).
            - 가격 표시 방식 개선 (달러/원화 병기).
            - Tax Shield 로직 고도화 (A/B 계좌 평단 비교 후 절세 매도 가이드).

        ### Ver 17.8 - The Tax Shield
        - **🛡️ 계좌 C (The Bunker) 신설**: 세금 및 비상금 격리용 계좌 추가 (수익금의 22% 자동 이체 규칙).
        - **🧾 Tax Shield 로직 탑재**: 광기 매도/리밸런싱 매도 시 세금 격리(22%) 알림 메시지 출력.
        - **🧮 자산 로직 고도화**: 총 자산 계산에 계좌 C 포함하여 Phase 판단 정확도 향상.
        - **📝 릴리즈 노트 추가**: 앱 내에서 업데이트 내역 확인 기능 추가.

        ### Ver 17.7 (Local Persistence)
        - **💾 데이터 영구 저장**: 브라우저를 닫아도 자산 데이터가 유지되도록 로컬 저장소(JSON) 연동.
        - **⚡ 속도 개선**: 데이터 로딩 최적화.

        ### Ver 17.6
        - 🛠️ **안정화 패치**: V17.5 이슈 롤백 및 로직 검증.
        - 📖 **사용 가이드**: 업데이트 사용 가이드 문서화.

        ### Ver 17.5
        - ✨ **기능 개선**: 사용자 피드백 반영 및 UI 가독성 패치.

        ### Ver 17.4 - The Dual Account
        - **🏦 2계좌 전략 (Two-Account Strategy) 도입**:
            - **계좌 A (The Vault)**: 무한 적립 전용 (매도 금지).
            - **계좌 B (The Sniper)**: 트레이딩 및 리밸런싱 전용.
        - 세금 문제 회피 및 매매 효율성 증대.

        ### 초기 버전 (Early Access)
        - **🔔 텔레그램 알림**: 위기 상황(MDD) 발생 시 알림 봇 기능 추가.
        - **💱 환율 연동**: 달러/원화 자동 환산 및 통합 자산 계산.
        - **📊 차트 시각화**: QQQ 주봉, RSI, MDD 동적 차트 구현.
        """)

else:
    st.warning("데이터 로딩 중... (잠시만 기다려주세요)")