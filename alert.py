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
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def check_market_status():
    print("🔍 시장 데이터 분석 중... (V19.0 Engine)")
    
    try:
        # 데이터 수집 (QQQ, TQQQ, VIX, TNX)
        qqq = yf.download("QQQ", interval="1wk", period="2y", progress=False)
        tqqq = yf.download("TQQQ", interval="1wk", period="2y", progress=False)
        vix = yf.download("^VIX", period="1d", progress=False)
        tnx = yf.download("^TNX", period="1d", progress=False)
        
        if qqq.empty:
            print("❌ 데이터 수집 실패")
            return

        # MultiIndex 처리
        for df in [qqq, tqqq, vix, tnx]:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 1. 지표 계산 (QQQ)
        qqq['RSI'] = calculate_rsi(qqq['Close'])
        current_rsi = float(qqq['RSI'].iloc[-1])
        
        qqq['Roll_Max'] = qqq['Close'].rolling(window=52, min_periods=1).max()
        qqq['DD'] = (qqq['Close'] / qqq['Roll_Max']) - 1.0
        current_mdd = float(qqq['DD'].iloc[-1])
        mdd_pct = current_mdd * 100

        # TQQQ 지표 (V19.0 추가)
        tqqq['Roll_Max'] = tqqq['Close'].rolling(window=52, min_periods=1).max()
        tqqq['DD'] = (tqqq['Close'] / tqqq['Roll_Max']) - 1.0
        tqqq_mdd = float(tqqq['DD'].iloc[-1]) if not tqqq.empty else 0
        tqqq_mdd_pct = tqqq_mdd * 100

        # Macro
        current_vix = float(vix['Close'].iloc[-1]) if not vix.empty else 0
        current_tnx = float(tnx['Close'].iloc[-1]) if not tnx.empty else 0
        current_price = float(qqq['Close'].iloc[-1])

        # 2. 알림 메시지 구성 (Logic V19.0)
        alert_triggered = False
        msg = "🔥 **[Global Fire V19.0] 긴급 브리핑** 🔥\n\n"
        
        # (1) RSI 감시 (광기/과열)
        if current_rsi >= 80:
            msg += "🚨 **[광기 경보] RSI 80 돌파!**\n"
            msg += "👉 **ACTION:** 현금 비중 [Target + 10%] 확보.\n"
            msg += "⚠️ **Tax Shield:** 실현 수익의 22%는 [계좌 C]로 격리.\n\n"
            alert_triggered = True
        elif current_rsi >= 75:
            msg += "🔥 **[과열 주의] RSI 75 돌파**\n"
            msg += "👉 신규 매수 금지 / 현금 비축.\n\n"
            alert_triggered = True

        # (2) MDD 감시 (위기 대응 4단계)
        if current_mdd <= -0.2:
            msg += f"📉 **[위기 발생] QQQ MDD {mdd_pct:.1f}%**\n"
            if current_mdd <= -0.5:
                msg += "💣 **대공황 (Great Depression)**\n👉 **ACTION:** 현금 100% (All-In) 투입!\n"
            elif current_mdd <= -0.4:
                msg += "🏦 **금융위기 (Financial Crisis)**\n👉 **ACTION:** 현금 30% 추가 투입.\n"
            elif current_mdd <= -0.3:
                msg += "🌪️ **폭락장 (Crash)**\n👉 **ACTION:** 현금 30% 투입.\n"
            else:
                msg += "📉 **조정장 (Correction)**\n👉 **ACTION:** 현금 20% 투입.\n"
            msg += "\n"
            alert_triggered = True

        # (3) TQQQ 긴급 상황 (V19.0 추가)
        if tqqq_mdd <= -0.3:
            msg += f"🚨 **[TQQQ 폭락] MDD {tqqq_mdd_pct:.1f}%**\n"
            msg += "👉 3배 레버리지 급락. 청산 위험 확인 필요.\n\n"
            alert_triggered = True

        # (4) Macro 감시 (VIX, TNX)
        if current_vix >= 30:
            msg += f"😱 **[공포 확산] VIX {current_vix:.1f}**\n👉 투매가 나오는 공포 구간입니다.\n\n"
            alert_triggered = True
        
        if current_tnx >= 4.5:
            msg += f"⚠️ **[금리 경고] US 10Y {current_tnx:.2f}%**\n👉 기술주(QQQ) 하방 압력 주의.\n\n"
            alert_triggered = True

        # 3. 결과 전송
        if alert_triggered:
            msg += f"📊 **Status Check**\nQQQ: ${current_price:.2f}\nRSI: {current_rsi:.1f}\nMDD: {mdd_pct:.2f}%\nTQQQ MDD: {tqqq_mdd_pct:.2f}%"
            send_telegram(msg)
        else:
            # 생존 신고 (Optional - 환경변수로 제어 가능)
            send_health_check = os.environ.get('SEND_DAILY_HEALTH', 'false').lower() == 'true'
            if send_health_check:
                health_msg = f"✅ **[일일 점검] 시장 정상**\n\n📊 QQQ: ${current_price:.2f}\nRSI: {current_rsi:.1f}\nMDD: {mdd_pct:.2f}%\nVIX: {current_vix:.1f}"
                send_telegram(health_msg)
            print(f"✅ 시장 양호 (RSI: {current_rsi:.1f}, MDD: {mdd_pct:.1f}%) - 알림 미발송")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        send_telegram(f"⚠️ [System Error] 알림 스크립트 오류 발생:\n{e}")

if __name__ == "__main__":
    check_market_status()
