@echo off
title ComplyVision Server & Live Tunnel
echo ====================================================
echo Starting ComplyVision (Smart India Hackathon 2026)
echo ====================================================
echo.

cd /d "%~dp0"

echo 1. Starting Flask Server on http://127.0.0.1:5000 ...
start "ComplyVision Backend" cmd /k python app.py

echo 2. Waiting 3 seconds for backend to initialize...
timeout /t 3 /nobreak >nul

echo 3. Starting Cloudflare Public Tunnel...
start "ComplyVision Live Public Tunnel" cmd /k "%LOCALAPPDATA%\Temp\cloudflared.exe" tunnel --url http://localhost:5000

echo.
echo ====================================================
echo ComplyVision is running!
echo - Local UI: http://127.0.0.1:5000
echo - Look at the "ComplyVision Live Public Tunnel" window for your public HTTPS link!
echo ====================================================
pause
