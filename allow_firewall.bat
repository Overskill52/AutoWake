@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ====================================================
echo   Opening UDP Port 9876 in Windows Firewall...
echo ====================================================
echo.

netsh advfirewall firewall delete rule name="AutoWake_Agent" >nul 2>&1
netsh advfirewall firewall add rule name="AutoWake_Agent" dir=in action=allow protocol=UDP localport=9876 profile=any

echo.
echo ====================================================
echo   [SUCCESS] Port 9876 is now OPEN!
echo   Vse gotovo! Teper telefon uvidit PC.
echo ====================================================
echo.
pause
