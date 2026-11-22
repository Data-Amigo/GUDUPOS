@echo off
REM Gudu Bites POS - run on this laptop. Phones on the same Wi-Fi can open it too.
cd /d "%~dp0"
if not exist .venv (
  echo Creating Python environment...
  python -m venv .venv
)
call .venv\Scripts\activate
pip install -q -r requirements.txt
echo.
echo ============================================================
echo  Open on this laptop:  http://localhost:8000
echo  Open on a phone (same Wi-Fi): http://YOUR-LAPTOP-IP:8000
echo  (find YOUR-LAPTOP-IP by running "ipconfig" - IPv4 Address)
echo ============================================================
echo.
uvicorn app.main:app --host 0.0.0.0 --port 8000
