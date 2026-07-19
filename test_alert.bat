@echo off
chcp 65001 >nul
echo ========================================
echo Alert.py 로컬 테스트 실행
echo ========================================
echo.

REM Python 확인
echo [1/3] Python 환경 확인 중...
python --version
if errorlevel 1 (
    echo 오류: Python을 찾을 수 없습니다!
    pause
    exit /b 1
)
echo Python 확인 완료!
echo.

REM Set environment variables
echo [2/3] 환경 변수 확인 중...
echo.

REM .env 파일이 있으면 읽어오기
if exist .env (
    echo [.env 파일 발견] 환경 변수를 로드합니다...
    for /f "usebackq eol=# tokens=*" %%a in (".env") do set "%%a"
)

if "%TELEGRAM_TOKEN%"=="" (
    echo 팁: 프로젝트 루트에 .env 파일을 만들고 토큰을 저장하면 매번 입력할 필요가 없습니다.
    set /p TELEGRAM_TOKEN=텔레그램 봇 토큰이 없습니다. 입력하세요: 
)
if "%CHAT_ID%"=="" (
    set /p CHAT_ID=Chat ID가 없습니다. 입력하세요: 
)
if "%ATH_ASSETS_KRW%"=="" (
    echo 참고: ATH_ASSETS_KRW(역대 최고 자산액)가 설정되지 않아 Level 1(시드 펌핑)로 간주됩니다. .env에 추가 권장.
)
set SEND_DAILY_HEALTH=true

echo [OK] 설정 완료!
echo.

REM Run alert script
echo [3/3] Alert 스크립트 실행 중...
echo.
python alert.py
echo.

echo ========================================
echo 테스트 완료!
echo ========================================
pause
