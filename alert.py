import yfinance as yf
import pandas as pd
import requests
import os
import sys

# 텔레그램 설정
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("❌ 텔레그램 토큰 또는 Chat ID가 설정되지 않았습니다.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
        print("✅ 텔레그램 메시지 전송 완료")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def calculate_rsi(series, window=14):
    """RSI (Wilder / RMA 방식)"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_market_status():
    print("🔍 시장 데이터 분석 중... (V23.6 The Endgame)")
    
    try:
        # 데이터 수집 (QQQ 일봉 2년, 월봉 전체기간, SOXX 일봉 2년, 월봉 전체기간, TQQQ)
        qqq = yf.download("QQQ", interval="1d", period="2y", progress=False, auto_adjust=False)
        qqq_mo_data = yf.download("QQQ", interval="1mo", period="max", progress=False, auto_adjust=False)
        tqqq = yf.download("TQQQ", interval="1d", period="2y", progress=False, auto_adjust=False)
        soxx = yf.download("SOXX", interval="1d", period="2y", progress=False, auto_adjust=False)
        soxx_mo_data = yf.download("SOXX", interval="1mo", period="max", progress=False, auto_adjust=False)
        
        if qqq.empty or soxx.empty:
            print("❌ 데이터 수집 실패")
            return

        # MultiIndex 처리 (yfinance 최근 변경 대응)
        for df in [qqq, qqq_mo_data, tqqq, soxx, soxx_mo_data]:
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)

        # 1. 지표 계산
        # QQQ 주봉 RSI (금요일 마감 기준, 현재 진행형 포함)
        qqq_wk = qqq[['Close']].resample('W-FRI').last().dropna()
        qqq_wk['RSI'] = calculate_rsi(qqq_wk['Close'])
        qqq_rsi_wk = float(qqq_wk['RSI'].iloc[-1])

        # QQQ 월봉 RSI (period=max 데이터 사용)
        qqq_mo_data['RSI'] = calculate_rsi(qqq_mo_data['Close'])
        qqq_rsi_mo = float(qqq_mo_data['RSI'].iloc[-1]) if len(qqq_mo_data) >= 14 else 0

        # QQQ 월봉 120개월 이평선 이격도 (진짜 120개월 MA, min_periods=120)
        qqq_mo_data['MA120'] = qqq_mo_data['Close'].rolling(window=120, min_periods=120).mean()
        _qqq_ma120_s = qqq_mo_data['MA120'].dropna()
        _qqq_ma120 = float(_qqq_ma120_s.iloc[-1]) if not _qqq_ma120_s.empty else None
        qqq_mo_dev = (float(qqq_mo_data['Close'].iloc[-1]) / _qqq_ma120) - 1.0 if _qqq_ma120 else 0

        # QQQ MDD (1년 기준)
        qqq['Roll_Max'] = qqq['Close'].rolling(window=252, min_periods=1).max()
        qqq['DD'] = (qqq['Close'] / qqq['Roll_Max']) - 1.0
        qqq_mdd = float(qqq['DD'].iloc[-1])
        qqq_mdd_pct = qqq_mdd * 100
        qqq_price = float(qqq['Close'].iloc[-1])

        # TQQQ MDD (다운로드 전체 기간 기준 cummax)
        tqqq['Roll_Max'] = tqqq['Close'].cummax()
        tqqq['DD'] = (tqqq['Close'] / tqqq['Roll_Max']) - 1.0
        tqqq_mdd = float(tqqq['DD'].iloc[-1]) if not tqqq.empty else 0
        tqqq_mdd_pct = tqqq_mdd * 100

        # SOXX MDD (다운로드 전체 기간 기준 cummax - rolling 252일이면 1년 신고가 시 0% 오류 방지)
        soxx['Roll_Max'] = soxx['Close'].cummax()
        soxx['DD'] = (soxx['Close'] / soxx['Roll_Max']) - 1.0
        soxx_mdd = float(soxx['DD'].iloc[-1]) if not soxx.empty else 0
        soxx_mdd_pct = soxx_mdd * 100
        soxx_price = float(soxx['Close'].iloc[-1]) if not soxx.empty else 0

        # SOXX 주봉 RSI
        soxx_wk = soxx[['Close']].resample('W-FRI').last().dropna()
        soxx_wk['RSI'] = calculate_rsi(soxx_wk['Close'])
        soxx_rsi_wk = float(soxx_wk['RSI'].iloc[-1]) if len(soxx_wk) >= 14 else 0

        # SOXX 월봉 RSI 및 120개월 이평선 이격도 (period=max 데이터 사용, min_periods=120)
        soxx_mo_data['RSI'] = calculate_rsi(soxx_mo_data['Close'])
        soxx_rsi_mo = float(soxx_mo_data['RSI'].iloc[-1]) if len(soxx_mo_data) >= 14 else 0
        soxx_mo_data['MA120'] = soxx_mo_data['Close'].rolling(window=120, min_periods=120).mean()
        _soxx_ma120_s = soxx_mo_data['MA120'].dropna()
        _soxx_ma120 = float(_soxx_ma120_s.iloc[-1]) if not _soxx_ma120_s.empty else None
        soxx_mo_dev = (float(soxx_mo_data['Close'].iloc[-1]) / _soxx_ma120) - 1.0 if _soxx_ma120 else 0

        # 2. 알림 메시지 구성 (Logic V23.6 The Endgame)
        alert_triggered = False
        msg = "🔥 **[Global Fire V23.6] 긴급 브리핑** 🔥\n\n"
        
        # (1) RSI 및 이격도 광기 감시 (Circuit Breaker & Bubble Alert)
        is_level2_bubble = (qqq_mo_dev >= 1.0) or (soxx_mo_dev >= 1.0)
        is_level1_bubble = (qqq_rsi_wk >= 80) or (qqq_rsi_mo >= 80) or (soxx_rsi_wk >= 80) or (soxx_rsi_mo >= 80)
        is_circuit_breaker = is_level1_bubble or is_level2_bubble

        if is_circuit_breaker:
            trigger_str = []
            if qqq_rsi_wk >= 80: trigger_str.append(f"QQQ 주봉 RSI {qqq_rsi_wk:.1f}")
            if qqq_rsi_mo >= 80: trigger_str.append(f"QQQ 월봉 RSI {qqq_rsi_mo:.1f}")
            if soxx_rsi_wk >= 80: trigger_str.append(f"SOXX 주봉 RSI {soxx_rsi_wk:.1f}")
            if soxx_rsi_mo >= 80: trigger_str.append(f"SOXX 월봉 RSI {soxx_rsi_mo:.1f}")
            if qqq_mo_dev >= 1.0: trigger_str.append(f"QQQ 120월 이격도 {qqq_mo_dev*100:.1f}%")
            if soxx_mo_dev >= 1.0: trigger_str.append(f"SOXX 120월 이격도 {soxx_mo_dev*100:.1f}%")
            
            trigger_msg = ", ".join(trigger_str)

            if is_level2_bubble:
                msg += f"🚨 **[역사적 버블 경보] {trigger_msg} 돌파!**\n"
                msg += "👉 **ACTION:** 기존 목표 현금 비중에 **+20% 추가 확보**하여 비상 현금 비중 설정.\n"
                msg += "👉 **ACTION:** 매도 후 남은 TQQQ와 USD의 잔고 평가액이 정확히 50:50이 되도록 매도.\n"
                msg += "👉 **ACTION:** 신규 적립금 500만 원 전액 100% 현금(BOXX) 매수.\n"
                msg += "👉 **ACTION:** 확보된 비상금은 임의 주식 복구 금지 (스나이퍼용 대기).\n"
            else:
                msg += f"🔥 **[단기 과열 경보] {trigger_msg} 돌파!**\n"
                msg += "👉 **ACTION:** 현재 Level의 '기존 목표 현금 비중'에 미달하는 만큼만 단순 리밸런싱 매도.\n"
                msg += "👉 **ACTION:** 매도 후 남은 TQQQ와 USD의 잔고 평가액이 정확히 50:50이 되도록 매도.\n"
                msg += "👉 **ACTION:** 신규 적립금 500만 원 전액 100% 현금(BOXX) 매수.\n"
                msg += "👉 **ACTION:** 확보된 비상금은 임의 주식 복구 금지 (스나이퍼용 대기).\n"

            msg += "⚠️ **Tax Shield:** 수익금의 22%는 세금 통장(C)으로 격리.\n\n"
            alert_triggered = True

        # (2) MDD 하이브리드 스나이퍼 감시
        if qqq_mdd <= -0.15:
            msg += f"📉 **[스나이퍼 기회] QQQ MDD {qqq_mdd_pct:.1f}%**\n"
            
            if qqq_mdd <= -0.45:
                msg += "💣 **시스템 붕괴 (Last Bullet)**\n👉 **ACTION:** 보유 현금의 **40%** 영끌 투입!\n"
            elif qqq_mdd <= -0.35:
                msg += "🏦 **대세 하락장 (2022년 수준)**\n👉 **ACTION:** 보유 현금의 **30%** 투입.\n"
            elif qqq_mdd <= -0.25:
                msg += "🌪️ **중급 하락장 (코로나 초기 수준)**\n👉 **ACTION:** 보유 현금의 **20%** 투입.\n"
            elif qqq_mdd <= -0.15:
                msg += "📉 **일반적인 조정장**\n👉 **ACTION:** 보유 현금의 **10%** 투입.\n"
            
            msg += "💡 *월급 적립금 500만원도 100% 주식 매수에 몰빵 (TQQQ 50 : USD 50)*\n\n"
            alert_triggered = True

        # (3) TQQQ 긴급 상황
        if tqqq_mdd <= -0.3:
            msg += f"🚨 **[TQQQ 폭락] MDD {tqqq_mdd_pct:.1f}%**\n"
            msg += "👉 3배 레버리지 급락. 방어선 유지 점검.\n\n"
            alert_triggered = True
        
        # 3. 결과 전송
        _qqq_ma120_str = f"${_qqq_ma120:.2f}" if _qqq_ma120 else "N/A"
        _soxx_ma120_str = f"${_soxx_ma120:.2f}" if _soxx_ma120 else "N/A"

        status_block = (
            f"📊 *Status Check*\n"
            f"• QQQ: ${qqq_price:.2f} │ 주봉RSI {qqq_rsi_wk:.1f} / 월봉RSI {qqq_rsi_mo:.1f} │ 120월 이격도 {qqq_mo_dev*100:.1f}% ({_qqq_ma120_str}) │ MDD {qqq_mdd_pct:.2f}%\n"
            f"• SOXX: ${soxx_price:.2f} │ 주봉RSI {soxx_rsi_wk:.1f} / 월봉RSI {soxx_rsi_mo:.1f} │ 120월 이격도 {soxx_mo_dev*100:.1f}% ({_soxx_ma120_str}) │ MDD {soxx_mdd_pct:.2f}%\n"
            f"• TQQQ: MDD {tqqq_mdd_pct:.2f}%\n"
        )
        if alert_triggered:
            msg += status_block
            send_telegram(msg)
        else:
            # 생존 신고
            send_health_check = os.environ.get('SEND_DAILY_HEALTH', 'false').lower() == 'true'
            if send_health_check:
                health_msg = f"✅ *[일일 점검] 시장 정상 (V23.6)*\n\n"
                health_msg += status_block
                health_msg += "💡 평시 적립: 월급 500만 원은 Level 목표 비중에 맞춰 분할 투입."
                send_telegram(health_msg)
            print(f"✅ 시장 양호 (QQQ 주봉 RSI: {qqq_rsi_wk:.1f}, MDD: {qqq_mdd_pct:.1f}%) - 알림 미발송")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        send_telegram(f"⚠️ [System Error] V23.6 알림 스크립트 오류 발생:\n{e}")

if __name__ == "__main__":
    check_market_status()