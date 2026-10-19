@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ====================================================
echo   Fixing Windows Firewall and Network Profile...
echo ====================================================
echo.

echo [1/3] Setting active network to Private profile...
powershell -NoProfile -Command "Get-NetConnectionProfile | Where-Object { $_.IPv4Connectivity -eq 'Internet' } | Set-NetConnectionProfile -NetworkCategory Private"

echo [2/3] Removing old BLOCK rules for python...
netsh advfirewall firewall delete rule name="python.exe" >nul 2>&1

echo [3/3] Allowing Python and UDP Port 9876...
netsh advfirewall firewall delete rule name="AutoWake_Python" >nul 2>&1
netsh advfirewall firewall delete rule name="AutoWake_Agent" >nul 2>&1

for /f "delims=" %%i in ('where python 2^>nul') do (
    netsh advfirewall firewall add rule name="AutoWake_Python" dir=in program="%%i" action=allow profile=any
)
netsh advfirewall firewall add rule name="AutoWake_Agent" dir=in action=allow protocol=UDP localport=9876 profile=any

echo.
echo ====================================================
echo   [SUCCESS] Firewall configured successfully!
echo   Port 9876 is open and Python traffic is allowed.
echo ====================================================
echo.
pause
