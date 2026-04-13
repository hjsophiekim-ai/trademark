@echo off
chcp 65001 > nul
title 상표 유사성 검토 시스템

echo.
echo  ============================================
echo    상표 유사성 검토 시스템 시작 중...
echo  ============================================
echo.

:: 현재 배치파일 위치로 이동
cd /d "%~dp0"

:: .env 파일 확인
if not exist ".env" (
    echo [경고] .env 파일이 없습니다. .env.example 을 복사해 설정하세요.
    pause
    exit /b 1
)

:: Python 확인 (3.13 우선, 없으면 기본 python)
where py >nul 2>&1
if %errorlevel% == 0 (
    py -3.13 --version >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON=py -3.13
    ) else (
        set PYTHON=py
    )
) else (
    set PYTHON=python
)

:: streamlit 설치 여부 확인
%PYTHON% -m streamlit --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [안내] 패키지 설치 중...
    %PYTHON% -m pip install -r requirements.txt --quiet
)

echo  브라우저가 자동으로 열립니다.
echo  종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.
echo.

:: Streamlit 실행
%PYTHON% -m streamlit run app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

pause
