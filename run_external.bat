@echo off
echo ========================================
echo Streamlit 외부 접속 모드 시작
echo ========================================
echo.

REM 가상환경 활성화
echo [1/2] 가상환경 활성화 중... (test)
call test\Scripts\activate.bat
if errorlevel 1 (
    echo 오류: 가상환경 활성화 실패!
    pause
    exit /b 1
)
echo 가상환경 활성화 완료!
echo.

echo [2/2] Streamlit 서버 시작 중...
echo.
echo 서버 주소: 0.0.0.0 (모든 네트워크 인터페이스)
echo 포트: 8501
echo.
echo 로컬 접속: http://localhost:8501
echo 외부 접속: http://[공유기_외부IP]:8501
echo.
echo ========================================
echo.

streamlit run app.py --server.address 0.0.0.0 --server.port 8501

pause

