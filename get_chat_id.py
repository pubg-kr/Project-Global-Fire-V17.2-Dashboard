"""
텔레그램 Chat ID 확인 스크립트
봇에게 메시지를 보낸 후 이 스크립트를 실행하면 Chat ID를 알려줍니다.
"""
import requests
import os
import sys
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def get_chat_id(token):
    """봇 토큰으로 Chat ID를 가져옵니다."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ API 에러: {data.get('description', 'Unknown error')}")
            return None
        
        updates = data.get('result', [])
        
        if not updates:
            print("⚠️  봇에게 아직 메시지를 보내지 않았습니다.")
            print("👉 먼저 텔레그램에서 봇에게 아무 메시지나 보내주세요!")
            print("   (예: /start 또는 '안녕')")
            return None
        
        # 가장 최근 메시지의 Chat ID 추출
        for update in reversed(updates):  # 최신부터 확인
            if 'message' in update:
                chat = update['message']['chat']
                chat_id = chat.get('id')
                chat_type = chat.get('type', 'unknown')
                first_name = chat.get('first_name', 'N/A')
                username = chat.get('username', 'N/A')
                
                print("=" * 50)
                print("✅ Chat ID를 찾았습니다!")
                print("=" * 50)
                print(f"📱 Chat ID: {chat_id}")
                print(f"👤 이름: {first_name}")
                print(f"🆔 사용자명: @{username}" if username != 'N/A' else "🆔 사용자명: 없음")
                print(f"📋 타입: {chat_type}")
                print("=" * 50)
                print(f"\n💡 이 값을 CHAT_ID 환경 변수에 설정하세요:")
                print(f"   set CHAT_ID={chat_id}")
                print()
                
                return chat_id
        
        print("⚠️  메시지를 찾을 수 없습니다.")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 에러: {e}")
        return None
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("📱 텔레그램 Chat ID 확인 도구")
    print("=" * 50)
    print()
    
    # 토큰 입력
    token = os.environ.get('TELEGRAM_TOKEN')
    
    if not token:
        print("⚠️  TELEGRAM_TOKEN 환경 변수가 설정되지 않았습니다.")
        print()
        token = input("텔레그램 봇 토큰을 입력하세요: ").strip()
        
        if not token:
            print("❌ 토큰이 입력되지 않았습니다.")
            sys.exit(1)
    
    print()
    print("🔍 Chat ID를 확인하는 중...")
    print("   (봇에게 메시지를 보내지 않았다면 먼저 보내주세요!)")
    print()
    
    chat_id = get_chat_id(token)
    
    if not chat_id:
        print()
        print("💡 해결 방법:")
        print("   1. 텔레그램에서 봇을 찾습니다")
        print("   2. 봇에게 '/start' 또는 아무 메시지나 보냅니다")
        print("   3. 이 스크립트를 다시 실행합니다")
        sys.exit(1)
