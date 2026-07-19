# 📱 텔레그램 봇 설정 가이드

## 1. 텔레그램 봇 토큰 (TELEGRAM_TOKEN) 얻기

### Step 1: BotFather 찾기
1. 텔레그램 앱에서 `@BotFather` 검색
2. 봇과 대화 시작

### Step 2: 새 봇 생성
```
/newbot
```

### Step 3: 봇 이름 설정
- 봇 이름 입력 (예: "Global Fire CRO")
- 봇 사용자명 입력 (예: "global_fire_cro_bot" - 반드시 `_bot`으로 끝나야 함)

### Step 4: 토큰 받기
BotFather가 다음과 같은 메시지를 보냅니다:
```
Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
```

**이 토큰이 `TELEGRAM_TOKEN`입니다!** ⚠️ 절대 공개하지 마세요!

---

## 2. Chat ID 얻기 (3가지 방법)

### 방법 1: @userinfobot 사용 (가장 간단) ⭐
1. 텔레그램에서 `@userinfobot` 검색
2. 봇과 대화 시작 (`/start`)
3. 봇이 당신의 Chat ID를 알려줍니다
   ```
   Id: 123456789
   ```
   **이 숫자가 `CHAT_ID`입니다!**

### 방법 2: 봇에게 메시지 보낸 후 API로 확인
1. 위에서 만든 봇(예: `@global_fire_cro_bot`)에게 아무 메시지나 보냅니다
2. 브라우저에서 아래 URL 접속 (YOUR_TOKEN을 실제 토큰으로 교체):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
3. JSON 응답에서 `"chat":{"id":123456789}` 부분을 찾습니다
   - 이 숫자가 `CHAT_ID`입니다!

### 방법 3: Python 스크립트로 확인
```python
import requests
import os

TOKEN = "YOUR_TOKEN_HERE"  # BotFather에서 받은 토큰

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
response = requests.get(url)
data = response.json()

if data['ok']:
    for update in data['result']:
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            print(f"Chat ID: {chat_id}")
            print(f"이름: {update['message']['chat'].get('first_name', 'N/A')}")
            break
else:
    print("에러:", data)
```

---

## 3. 로컬 테스트 설정

### 방법 A: 환경 변수로 설정 (PowerShell)
```powershell
$env:TELEGRAM_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890"
$env:CHAT_ID="123456789"
$env:SEND_DAILY_HEALTH="true"
$env:ATH_ASSETS_KRW="150000000"  # V24.5: 대시보드 ATH와 동일하게 설정 (미설정 시 Level 1로 간주)
python alert.py
```

### 방법 B: 환경 변수로 설정 (CMD)
```cmd
set TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
set CHAT_ID=123456789
set SEND_DAILY_HEALTH=true
set ATH_ASSETS_KRW=150000000
python alert.py
```

### 방법 C: test_alert.bat 사용
1. `test_alert.bat` 실행
2. 프롬프트에서 토큰과 Chat ID 입력

---

## 4. 깃허브 시크릿 설정 (이미 했다면 스킵)

1. 깃허브 저장소 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 다음 시크릿 추가:
   - `TELEGRAM_TOKEN`: 봇 토큰
   - `CHAT_ID`: Chat ID
   - `SEND_DAILY_HEALTH`: `true` 또는 `false`
   - `ATH_ASSETS_KRW` (V24.5 신규): 대시보드(`app.py`)에 입력해둔 **"역대 최고 자산액(ATH)"**과 동일한 원화 숫자 (예: `150000000`). 이 값으로 알림 봇이 현재 Level을 판정하여, 이격도 100% 초과 버블 방어 룰이 Level 7(자산 4억 원) 이상에서만 발동하도록 게이트를 적용합니다. 자산이 늘어날 때마다(레벨업 시) 이 값도 함께 갱신해주세요. **미설정 시 0으로 간주되어 항상 Level 1(시드 펌핑 구간)로 취급됩니다.**

---

## 5. 테스트 메시지 보내기

### Python으로 테스트:
```python
import requests
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "✅ 테스트 메시지입니다!"
}

response = requests.post(url, json=payload)
print(response.json())
```

### curl로 테스트 (PowerShell):
```powershell
$token = "YOUR_TOKEN"
$chatId = "YOUR_CHAT_ID"
curl -X POST "https://api.telegram.org/bot$token/sendMessage" `
  -H "Content-Type: application/json" `
  -d "{\"chat_id\":$chatId,\"text\":\"✅ 테스트 메시지입니다!\"}"
```

---

## ⚠️ 보안 주의사항

1. **토큰과 Chat ID는 절대 공개하지 마세요!**
2. 깃허브에 커밋하지 마세요 (`.gitignore`에 `.env` 추가 권장)
3. 토큰이 유출되면 즉시 BotFather에서 `/revoke` 명령으로 재발급 받으세요

---

## 🔍 문제 해결

### "Unauthorized" 에러
- 토큰이 잘못되었습니다. BotFather에서 다시 확인하세요.

### "Chat not found" 에러
- Chat ID가 잘못되었거나, 봇에게 먼저 메시지를 보내지 않았습니다.
- 봇에게 `/start` 메시지를 보내고 다시 시도하세요.

### 메시지가 안 옴
- `SEND_DAILY_HEALTH`가 `false`로 설정되어 있을 수 있습니다.
- 또는 알림 조건이 충족되지 않았을 수 있습니다 (정상 상태면 알림 안 감).
