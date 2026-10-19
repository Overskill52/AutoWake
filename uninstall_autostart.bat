@echo off
echo Removing AutoWake PC Agent from Windows Startup...
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET_VBS=%STARTUP_DIR%\AutoWake_PCAgent.vbs"

if exist "%TARGET_VBS%" (
    del /f /q "%TARGET_VBS%"
    echo [+] Startup file removed: %TARGET_VBS%
) else (
    echo [*] Startup file not found in: %STARTUP_DIR%
)

taskkill /f /im python.exe /fi "WINDOWTITLE eq AutoWake*" >nul 2>&1
echo [+] Finished.
pause
