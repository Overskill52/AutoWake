@echo off
setlocal
set "CURR_DIR=%~dp0"
set "CURR_DIR=%CURR_DIR:~0,-1%"
set "TARGET_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AutoWake_PCAgent.vbs"

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%CURR_DIR%"
echo WshShell.Run "python.exe """ ^& "%CURR_DIR%\pc_agent.py""" , 0, False
) > "%TARGET_VBS%"

echo [+] Added to Windows Startup: %TARGET_VBS%
cscript //nologo "%TARGET_VBS%"
echo [+] PC Agent running in background on UDP port 9876.
echo.
pause
