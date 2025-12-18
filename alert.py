import yfinance as yf
import pandas as pd
import requests
import os
import sys

# GitHub Secrets에서 가져올 변수들
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def check_market():
    # QQQ 데이터 가져오기
    df = yf.download("QQQ", interval="1wk", period="2y", progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

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
    
    current_rsi = float(df['RSI'].iloc[-1])
    current_mdd = float(df['DD'].iloc[-1])
    current_price = float(df['Close'].iloc[-1])

    msg = ""
    urgent = False

    # 1. 광기 감지 (RSI 80)
    if current_rsi >= 80:
        msg += f"🚨 [긴급] QQQ RSI {current_rsi:.1f} 돌파! (광기)\n👉 즉시 접속하여 현금 비중을 늘리십시오.\n"
        urgent = True
    
    # 2. 폭락 감지 (MDD -20%)
    if current_mdd <= -0.2:
        msg += f"📉 [위기] QQQ MDD {current_mdd*100:.1f}% 기록! (폭락)\n👉 즉시 접속하여 현금을 투입하십시오.\n"
        urgent = True
        
    # 3. 과열 경고 (RSI 75) - 참고용
    elif current_rsi >= 75:
        msg += f"🔥 [경고] QQQ RSI {current_rsi:.1f} 진입 (과열)\n👉 월급 적립 중단 및 현금 확보 준비.\n"
        urgent = True

    # 알림 발송
    if urgent:
        final_msg = f"[CRO 자동 알림]\nQQQ 현재가: ${current_price:.2f}\n\n{msg}\n🔗 대시보드 접속: https://share.streamlit.io/본인아이디/리포지토리명"
        send_telegram(final_msg)
        print("Alert Sent")
    else:
        print("Market is Normal. No alert sent.")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: Token or Chat ID missing")
    else:
        check_market()