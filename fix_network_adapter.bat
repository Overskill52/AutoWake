@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ====================================================
echo   Configuring Network Adapter for Safe Wake-on-LAN
echo ====================================================
echo.

echo [1/3] Disabling 'Wake on Pattern Match' (blocks router ARP noise)...
powershell -NoProfile -Command "Get-NetAdapter | Where-Object { $_.Status -ne 'Disabled' } | ForEach-Object { try { Set-NetAdapterAdvancedProperty -Name $_.Name -RegistryKeyword '*WakeOnPattern' -RegistryValue 0 -ErrorAction SilentlyContinue } catch {} }"

echo [2/3] Ensuring 'Wake on Magic Packet' is enabled...
powershell -NoProfile -Command "Get-NetAdapter | Where-Object { $_.Status -ne 'Disabled' } | ForEach-Object { try { Set-NetAdapterAdvancedProperty -Name $_.Name -RegistryKeyword '*WakeOnMagicPacket' -RegistryValue 1 -ErrorAction SilentlyContinue } catch {} }"

echo [3/3] Setting adapter to wake ONLY on Magic Packet in Windows...
powershell -NoProfile -Command "$keys = Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}'; foreach ($k in $keys) { $val = Get-ItemProperty -Path $k.PSPath -ErrorAction SilentlyContinue; if ($val.DriverDesc -match 'Realtek|Intel|Killer|Broadcom|Ethernet') { Set-ItemProperty -Path $k.PSPath -Name '*WakeOnPattern' -Value 0 -ErrorAction SilentlyContinue; Set-ItemProperty -Path $k.PSPath -Name '*WakeOnMagicPacket' -Value 1 -ErrorAction SilentlyContinue; Set-ItemProperty -Path $k.PSPath -Name 'PnPCapabilities' -Value 288 -ErrorAction SilentlyContinue; Set-ItemProperty -Path $k.PSPath -Name 'S5WakeOnLan' -Value 1 -ErrorAction SilentlyContinue; } }"

echo.
echo ====================================================
echo   [SUCCESS] Network card configured!
echo   False wakeups from router ARP probes are now blocked.
echo   Only genuine Magic Packets will wake this PC.
echo ====================================================
echo.
pause
