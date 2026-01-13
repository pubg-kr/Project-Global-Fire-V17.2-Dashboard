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
    """
    RSI (Wilder / RMA 방식)
    - 토스/영웅문 등 대부분의 플랫폼 RSI는 Wilder smoothing(RMA)에 가깝습니다.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # Wilder's smoothing: RMA = EMA(alpha=1/window, adjust=False)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_market_status():
    print("🔍 시장 데이터 분석 중... (V22.6 RSI Alignment)")
    
    try:
        # 데이터 수집 (QQQ, TQQQ, SOXX, VIX, TNX, IRX)
        # 일봉 200선을 위해 1년 이상 데이터 필요
        qqq = yf.download("QQQ", interval="1d", period="2y", progress=False, auto_adjust=False)
        tqqq = yf.download("TQQQ", interval="1d", period="2y", progress=False, auto_adjust=False)
        soxx = yf.download("SOXX", interval="1d", period="2y", progress=False, auto_adjust=False) # 반도체 지수 추가
        vix = yf.download("^VIX", period="1y", progress=False, auto_adjust=False)
        tnx = yf.download("^TNX", period="1y", progress=False, auto_adjust=False) # 10년물
        irx = yf.download("^IRX", period="1y", progress=False, auto_adjust=False) # 3개월물
        
        if qqq.empty or soxx.empty:
            print("❌ 데이터 수집 실패")
            return

        # MultiIndex 처리
        for df in [qqq, tqqq, soxx, vix, tnx, irx]:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 1. 지표 계산 (QQQ, SOXX)
        # - 일봉 RSI: 일봉 Close 기준
        # - 주봉 RSI: 토스/영웅문과 최대한 맞추기 위해, 일봉을 주간(W-FRI)으로 리샘플링하여 "이번 주 진행분"까지 포함
        qqq['RSI'] = calculate_rsi(qqq['Close'])
        qqq_wk = qqq[['Close']].resample('W-FRI').last().dropna()
        qqq_wk['RSI'] = calculate_rsi(qqq_wk['Close'])

        soxx_wk = soxx[['Close']].resample('W-FRI').last().dropna()
        soxx_wk['RSI'] = calculate_rsi(soxx_wk['Close'])

        qqq_rsi_day = float(qqq['RSI'].iloc[-1])
        qqq_rsi_wk = float(qqq_wk['RSI'].iloc[-1])
        soxx_rsi_wk = float(soxx_wk['RSI'].iloc[-1])

        # 디버깅 출력은 옵션 (기본 OFF)
        debug_rsi = os.environ.get('DEBUG_RSI', 'false').lower() == 'true'
        if debug_rsi:
            print(f"📊 [RSI] QQQ 일봉: {qqq_rsi_day:.2f} / 주봉(W-FRI, 진행주 포함): {qqq_rsi_wk:.2f}")
            print(f"📊 [RSI] SOXX 주봉(W-FRI, 진행주 포함): {soxx_rsi_wk:.2f}")
            print(f"📊 [데이터] QQQ 일봉 {len(qqq)}개 / 주봉 {len(qqq_wk)}개")
            print(f"📊 [날짜] QQQ 일봉 마지막 {qqq.index[-1]} / 주봉 마지막 {qqq_wk.index[-1]}")
        
        # MDD (1년 기준, 종목별)
        qqq['Roll_Max'] = qqq['Close'].rolling(window=252, min_periods=1).max()
        qqq['DD'] = (qqq['Close'] / qqq['Roll_Max']) - 1.0
        qqq_mdd = float(qqq['DD'].iloc[-1])
        qqq_mdd_pct = qqq_mdd * 100

        soxx['Roll_Max'] = soxx['Close'].rolling(window=252, min_periods=1).max()
        soxx['DD'] = (soxx['Close'] / soxx['Roll_Max']) - 1.0
        soxx_mdd = float(soxx['DD'].iloc[-1])
        soxx_mdd_pct = soxx_mdd * 100
        
        # [Ver 22.6] Winter Protocol: QQQ & SOXX Dual Check
        # QQQ MA200
        qqq['MA200'] = qqq['Close'].rolling(window=200).mean()
        qqq_price = float(qqq['Close'].iloc[-1])
        qqq_ma200 = float(qqq['MA200'].iloc[-1])
        
        # SOXX MA200
        soxx['MA200'] = soxx['Close'].rolling(window=200).mean()
        soxx_price = float(soxx['Close'].iloc[-1])
        soxx_ma200 = float(soxx['MA200'].iloc[-1])
        
        is_winter = False
        winter_cause = []
        
        # QQQ Check
        if not pd.isna(qqq_ma200):
            if qqq_price < qqq_ma200:
                is_winter = True
                winter_cause.append("QQQ")
        
        # SOXX Check
        if not pd.isna(soxx_ma200):
            if soxx_price < soxx_ma200:
                is_winter = True
                winter_cause.append("SOXX")

        # TQQQ 지표
        tqqq['Roll_Max'] = tqqq['Close'].rolling(window=252, min_periods=1).max()
        tqqq['DD'] = (tqqq['Close'] / tqqq['Roll_Max']) - 1.0
        tqqq_mdd = float(tqqq['DD'].iloc[-1]) if not tqqq.empty else 0
        tqqq_mdd_pct = tqqq_mdd * 100

        # Macro
        current_vix = float(vix['Close'].iloc[-1]) if not vix.empty else 0
        current_tnx = float(tnx['Close'].iloc[-1]) if not tnx.empty else 0
        current_irx = float(irx['Close'].iloc[-1]) if not irx.empty else 0
        current_spread = current_tnx - current_irx

        # 2. 알림 메시지 구성 (Logic V22.6)
        alert_triggered = False
        msg = "🔥 **[Global Fire V22.6] 긴급 브리핑** 🔥\n\n"
        
        # (0) 계절 변화 감지 (최우선 순위)
        season_status = "🔴 겨울 (Winter)" if is_winter else "🟢 봄 (Spring)"
        if is_winter:
             cause_str = ", ".join(winter_cause)
             msg += f"❄️ **[겨울 모드 작동 중]**\n"
             msg += f"- 원인: **{cause_str}** 200일선 붕괴\n"
             msg += f"- QQQ: ${qqq_price:.2f} vs ${qqq_ma200:.2f}\n"
             msg += f"- SOXX: ${soxx_price:.2f} vs ${soxx_ma200:.2f}\n"
             msg += "👉 **ACTION:** 현금 50% 확보 (부족 시 매도). 월급 전액 현금 적립.\n\n"
             
             # 겨울 진입 초기 알림 트리거 (QQQ 기준)
             if abs(qqq_price - qqq_ma200) / qqq_price < 0.01: 
                 alert_triggered = True
        
        # (1) RSI 감시 (광기/과열) - 봄에만 유효
        if not is_winter:
            rsi_threshold = 80
            if qqq_rsi_wk >= rsi_threshold:
                msg += f"🚨 **[광기 경보] 주봉 RSI {qqq_rsi_wk:.1f} 돌파!**\n"
                msg += "👉 **ACTION:** 현금 비중 [Target + 10%] 확보.\n"
                msg += "⚠️ **Tax Shield:** 실현 수익의 22%는 [계좌 C]로 격리.\n\n"
                alert_triggered = True

        # (2) MDD 감시 (스나이퍼 대응)
        # 겨울엔 -25% 부터, 봄엔 -15% 부터
        sniper_threshold = -0.25 if is_winter else -0.15
        
        if qqq_mdd <= sniper_threshold:
            msg += f"📉 **[스나이퍼 기회] QQQ MDD {qqq_mdd_pct:.1f}%**\n"
            
            # 역피라미드 비중 (Ver 22.4)
            if qqq_mdd <= -0.45:
                msg += "💣 **Last Bullet (시스템 붕괴)**\n👉 **ACTION:** 현금 40% (All-In) 투입!\n"
            elif qqq_mdd <= -0.35:
                msg += "🏦 **금융위기 (Panic)**\n👉 **ACTION:** 현금 30% 투입.\n"
            elif qqq_mdd <= -0.25:
                msg += "🌪️ **약세장 (Bear Market)**\n👉 **ACTION:** 현금 20% 투입.\n"
            elif qqq_mdd <= -0.15 and not is_winter:
                msg += "📉 **조정장 (Dip)**\n👉 **ACTION:** 현금 10% 짤짤이 투입.\n"
            
            msg += "\n"
            alert_triggered = True

        # (3) TQQQ 긴급 상황
        if tqqq_mdd <= -0.3:
            msg += f"🚨 **[TQQQ 폭락] MDD {tqqq_mdd_pct:.1f}%**\n"
            msg += "👉 3배 레버리지 급락. 청산 위험 확인 필요.\n\n"
            alert_triggered = True
        
        # 3. 결과 전송
        if alert_triggered:
            msg += f"📊 **Status Check**\nQQQ: ${qqq_price:.2f} (주봉 RSI {qqq_rsi_wk:.1f})\n"
            msg += f"SOXX: ${soxx_price:.2f} (주봉 RSI {soxx_rsi_wk:.1f})\n"
            msg += f"MDD: QQQ {qqq_mdd_pct:.2f}% / SOXX {soxx_mdd_pct:.2f}%\n"
            msg += f"VIX: {current_vix:.1f}\n10Y-3M: {current_spread:.2f}%p"
            
            send_telegram(msg)
        else:
            # 생존 신고
            send_health_check = os.environ.get('SEND_DAILY_HEALTH', 'false').lower() == 'true'
            if send_health_check:
                tnx_status = "⚠️ 고금리" if current_tnx >= 4.0 else "✅ 양호"
                spread_status = "✅ 정상"
                if current_spread < 0: spread_status = "⚠️ 역전"
                
                health_msg = f"✅ **[일일 점검] 시장 정상 ({season_status})**\n\n"
                health_msg += f"📊 **QQQ**: ${qqq_price:.2f} (주봉 RSI {qqq_rsi_wk:.1f})\n"
                health_msg += f"📊 **SOXX**: ${soxx_price:.2f} (주봉 RSI {soxx_rsi_wk:.1f})\n"
                health_msg += f"📉 **MDD**: QQQ {qqq_mdd_pct:.2f}% / SOXX {soxx_mdd_pct:.2f}%\n"
                health_msg += f"🛡️ **VIX**: {current_vix:.1f}\n"
                health_msg += f"📉 **10Y-3M**: {current_spread:.2f}%p ({spread_status})"
                
                send_telegram(health_msg)
            print(f"✅ 시장 양호 (주봉 RSI: {qqq_rsi_wk:.1f}, MDD: {qqq_mdd_pct:.1f}%) - 알림 미발송")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        send_telegram(f"⚠️ [System Error] 알림 스크립트 오류 발생:\n{e}")

if __name__ == "__main__":
    check_market_status()
