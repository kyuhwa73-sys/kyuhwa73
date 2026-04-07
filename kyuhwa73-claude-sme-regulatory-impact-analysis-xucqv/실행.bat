@echo off
chcp 65001 > nul
echo ============================================
echo  중소기업 규제영향 분석 시스템
echo  Streamlit UI 실행
echo ============================================
echo.

:: 패키지 설치 확인
python -m pip install streamlit plotly pandas -q

echo.
echo  브라우저가 자동으로 열립니다.
echo  종료하려면 이 창에서 Ctrl+C 를 누르세요.
echo.

python -m streamlit run app.py
pause
