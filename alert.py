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
    print("🔍 시장 데이터 분석 중... (V19.3.2 Engine)")
    
    try:
        # 데이터 수집 (QQQ, TQQQ, VIX, TNX, IRX)
        # VIX, TNX, IRX는 추세 분석을 위해 1년치 데이터 수집
        qqq = yf.download("QQQ", interval="1wk", period="2y", progress=False, auto_adjust=False)
        tqqq = yf.download("TQQQ", interval="1wk", period="2y", progress=False, auto_adjust=False)
        vix = yf.download("^VIX", period="1y", progress=False, auto_adjust=False)
        tnx = yf.download("^TNX", period="1y", progress=False, auto_adjust=False) # 10년물
        irx = yf.download("^IRX", period="1y", progress=False, auto_adjust=False) # 3개월물
        
        if qqq.empty:
            print("❌ 데이터 수집 실패")
            return

        # MultiIndex 처리
        for df in [qqq, tqqq, vix, tnx, irx]:
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
        current_irx = float(irx['Close'].iloc[-1]) if not irx.empty else 0
        current_spread = current_tnx - current_irx
        current_price = float(qqq['Close'].iloc[-1])

        # 버블 붕괴 감지 로직 (Ver 19.3.2)
        # 1. VIX 5일 안착 여부
        is_vix_trend = False
        if len(vix) >= 5:
            vix_recent_min = vix['Close'].tail(5).min()
            is_vix_trend = (vix_recent_min >= 20.0)
        
        # 2. 금리차 역전 후 정상화 (Normalization) 감지
        is_spread_normalization = False
        if not tnx.empty and not irx.empty:
            spread_series = tnx['Close'] - irx['Close']
            spread_recent = spread_series.tail(126) # 6개월
            was_inverted = (spread_recent < 0).any()
            is_positive_now = (spread_series.iloc[-1] >= 0)
            if was_inverted and is_positive_now:
                is_spread_normalization = True

        # 2. 알림 메시지 구성 (Logic V19.3.2)
        alert_triggered = False
        msg = "🔥 **[Global Fire V19.3.2] 긴급 브리핑** 🔥\n\n"
        
        # (0) 버블 붕괴 조기 경보 (최우선 순위)
        if is_vix_trend or is_spread_normalization:
            msg += "🚨 **[버블 붕괴 경보] 방어 모드 발동**\n"
            if is_vix_trend:
                msg += f"- 징후: VIX 기조적 상승 (20이상 5일 안착, 현재 {current_vix:.1f})\n"
            if is_spread_normalization:
                msg += f"- 징후: 금리차 역전 후 정상화 (Normalization, 현재 {current_spread:.2f}%p)\n"
            msg += "👉 **ACTION:** 주식 비중 -10%p 축소 / RSI 매도 기준 강화(75)\n\n"
            alert_triggered = True

        # (1) RSI 감시 (광기/과열)
        rsi_threshold = 75 if (is_vix_trend or is_spread_normalization) else 80
        
        if current_rsi >= rsi_threshold:
            status_label = "방어 매도" if rsi_threshold == 75 else "광기 경보"
            msg += f"🚨 **[{status_label}] RSI {current_rsi:.1f} 돌파!**\n"
            msg += "👉 **ACTION:** 현금 비중 [Target + 10%] 확보.\n"
            msg += "⚠️ **Tax Shield:** 실현 수익의 22%는 [계좌 C]로 격리.\n\n"
            alert_triggered = True
        elif current_rsi >= (rsi_threshold - 5): # 예: 70 or 75
             # 단순 과열은 경보까지는 아님
             pass

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

        # (3) TQQQ 긴급 상황
        if tqqq_mdd <= -0.3:
            msg += f"🚨 **[TQQQ 폭락] MDD {tqqq_mdd_pct:.1f}%**\n"
            msg += "👉 3배 레버리지 급락. 청산 위험 확인 필요.\n\n"
            alert_triggered = True

        # (4) Macro 감시 (VIX 급등)
        if current_vix >= 30:
            msg += f"😱 **[공포 확산] VIX {current_vix:.1f}**\n👉 투매가 나오는 공포 구간입니다. (공격 매수 준비)\n\n"
            alert_triggered = True
        
        # 3. 결과 전송
        if alert_triggered:
            # 하단 Status Bar에 매크로 지표 추가
            tnx_status = "⚠️ 고금리" if current_tnx >= 4.0 else "✅ 양호"
            spread_status = "✅ 정상"
            if is_spread_normalization: spread_status = "🚨 붕괴 임박"
            elif current_spread < 0: spread_status = "⚠️ 역전"

            msg += f"📊 **Status Check**\nQQQ: ${current_price:.2f}\nRSI: {current_rsi:.1f}\nMDD: {mdd_pct:.2f}%\n"
            msg += f"VIX: {current_vix:.1f}\nUS 10Y: {current_tnx:.2f}% ({tnx_status})\n10Y-3M: {current_spread:.2f}%p ({spread_status})"
            
            send_telegram(msg)
        else:
            # 생존 신고 (Optional - 환경변수로 제어 가능)
            send_health_check = os.environ.get('SEND_DAILY_HEALTH', 'false').lower() == 'true'
            if send_health_check:
                tnx_status = "⚠️ 고금리 주의" if current_tnx >= 4.0 else "✅ 양호"
                spread_status = "✅ 정상"
                if is_spread_normalization: spread_status = "🚨 붕괴 임박 (Normalization)"
                elif current_spread < 0: spread_status = "⚠️ 역전 경고"
                
                vix_status = "✅ 안정"
                if is_vix_trend: vix_status = "🚨 방어 모드 (5일 안착)"
                elif current_vix >= 20: vix_status = "⚠️ 주의"

                health_msg = f"✅ **[일일 점검] 시장 정상**\n\n"
                health_msg += f"📊 **QQQ**: ${current_price:.2f} (RSI {current_rsi:.1f})\n"
                health_msg += f"📉 **MDD**: {mdd_pct:.2f}%\n"
                health_msg += f"🛡️ **VIX**: {current_vix:.1f} ({vix_status})\n"
                health_msg += f"🏦 **US 10Y**: {current_tnx:.2f}% ({tnx_status})\n"
                health_msg += f"📉 **10Y-3M**: {current_spread:.2f}%p ({spread_status})"
                
                send_telegram(health_msg)
            print(f"✅ 시장 양호 (RSI: {current_rsi:.1f}, MDD: {mdd_pct:.1f}%) - 알림 미발송")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        send_telegram(f"⚠️ [System Error] 알림 스크립트 오류 발생:\n{e}")

if __name__ == "__main__":
    check_market_status()
