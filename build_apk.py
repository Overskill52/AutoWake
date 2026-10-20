import os
import subprocess
import shutil
import struct
import zlib

SDK_DIR = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
if not SDK_DIR:
    user_home = os.path.expanduser("~")
    for candidate in [
        os.path.join(user_home, "AppData", "Local", "Android", "Sdk"),
        r"C:\Android\Sdk",
        r"C:\Program Files (x86)\Android\android-sdk"
    ]:
        if os.path.exists(candidate):
            SDK_DIR = candidate
            break

build_tools_root = os.path.join(SDK_DIR, "build-tools") if SDK_DIR else ""
if os.path.exists(build_tools_root):
    versions = sorted(os.listdir(build_tools_root))
    BUILD_TOOLS_DIR = os.path.join(build_tools_root, versions[-1]) if versions else ""
else:
    BUILD_TOOLS_DIR = ""

platforms_root = os.path.join(SDK_DIR, "platforms") if SDK_DIR else ""
if os.path.exists(platforms_root):
    platforms = sorted(os.listdir(platforms_root))
    PLATFORM_DIR = os.path.join(platforms_root, platforms[-1]) if platforms else ""
else:
    PLATFORM_DIR = ""

ANDROID_JAR = os.path.join(PLATFORM_DIR, "android.jar") if PLATFORM_DIR else ""

AAPT2 = os.path.join(BUILD_TOOLS_DIR, "aapt2.exe") if BUILD_TOOLS_DIR else "aapt2"
D8 = os.path.join(BUILD_TOOLS_DIR, "d8.bat") if BUILD_TOOLS_DIR else "d8"
ZIPALIGN = os.path.join(BUILD_TOOLS_DIR, "zipalign.exe") if BUILD_TOOLS_DIR else "zipalign"
APKSIGNER = os.path.join(BUILD_TOOLS_DIR, "apksigner.bat") if BUILD_TOOLS_DIR else "apksigner"

JDK_DIR = os.environ.get("JAVA_HOME")
if not JDK_DIR:
    for candidate in [
        r"C:\Program Files\Microsoft\jdk-17.0.10.7-hotspot",
        r"C:\Program Files\Java\jdk-17",
        r"C:\Program Files\Eclipse Adoptium\jdk-17",
        r"C:\Program Files\Android\Android Studio\jbr"
    ]:
        if os.path.exists(candidate):
            JDK_DIR = candidate
            break

if JDK_DIR:
    os.environ["JAVA_HOME"] = JDK_DIR
    os.environ["PATH"] = os.path.join(JDK_DIR, "bin") + os.pathsep + os.environ["PATH"]

PROJ_DIR = os.path.abspath("android_project")
SRC_DIR = os.path.join(PROJ_DIR, "src", "com", "antigravity", "wakeonlan")
RES_DIR = os.path.join(PROJ_DIR, "res")
BIN_DIR = os.path.join(PROJ_DIR, "bin")
GEN_DIR = os.path.join(PROJ_DIR, "gen")

def run(cmd, shell=False):
    print(f"RUN: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    res = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"STDOUT: {res.stdout}")
        print(f"STDERR: {res.stderr}")
        raise RuntimeError(f"Command failed with code {res.returncode}")
    return res.stdout

def make_png(w, h, color):
    raw = b''.join([b'\x00' + color * w for _ in range(h)])
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw))
    png += chunk(b'IEND', b'')
    return png

def create_project_files():
    os.makedirs(SRC_DIR, exist_ok=True)
    os.makedirs(os.path.join(RES_DIR, "values"), exist_ok=True)
    os.makedirs(os.path.join(RES_DIR, "layout"), exist_ok=True)
    os.makedirs(os.path.join(RES_DIR, "drawable"), exist_ok=True)
    os.makedirs(BIN_DIR, exist_ok=True)
    os.makedirs(GEN_DIR, exist_ok=True)

    # 1. AndroidManifest.xml
    manifest = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.antigravity.wakeonlan"
    android:versionCode="11"
    android:versionName="2.0">

    <uses-sdk
        android:minSdkVersion="26"
        android:targetSdkVersion="34" />

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
    <uses-permission android:name="android.permission.CHANGE_NETWORK_STATE" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.CHANGE_WIFI_MULTICAST_STATE" />
    <uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />

    <application
        android:label="@string/app_name"
        android:icon="@drawable/ic_launcher"
        android:roundIcon="@drawable/ic_launcher"
        android:theme="@android:style/Theme.DeviceDefault.NoActionBar">
        
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".WolService"
            android:enabled="true"
            android:exported="false"
            android:stopWithTask="false"
            android:foregroundServiceType="connectedDevice" />

        <receiver
            android:name=".BootReceiver"
            android:enabled="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
            </intent-filter>
        </receiver>

    </application>
</manifest>"""
    with open(os.path.join(PROJ_DIR, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest)

    # 2. strings.xml
    strings = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">AutoWake</string>
</resources>"""
    with open(os.path.join(RES_DIR, "values", "strings.xml"), "w", encoding="utf-8") as f:
        f.write(strings)

    # 3. colors.xml
    colors = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="bg_dark">#0F111A</color>
    <color name="card_dark">#1A1D2B</color>
    <color name="cyan_glow">#00E5FF</color>
    <color name="purple_accent">#7C4DFF</color>
    <color name="text_white">#FFFFFF</color>
    <color name="text_gray">#8F9CAE</color>
</resources>"""
    with open(os.path.join(RES_DIR, "values", "colors.xml"), "w", encoding="utf-8") as f:
        f.write(colors)

    # 4. Adaptive and Themed Icon Drawables
    ic_launcher = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
    <monochrome android:drawable="@drawable/ic_launcher_monochrome" />
</adaptive-icon>"""
    with open(os.path.join(RES_DIR, "drawable", "ic_launcher.xml"), "w", encoding="utf-8") as f:
        f.write(ic_launcher)

    ic_launcher_bg = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <gradient
        android:angle="135"
        android:startColor="#1E2333"
        android:endColor="#0B0D14"
        android:type="linear" />
</shape>"""
    with open(os.path.join(RES_DIR, "drawable", "ic_launcher_background.xml"), "w", encoding="utf-8") as f:
        f.write(ic_launcher_bg)

    ic_launcher_fg = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:pathData="M 68.14,37.15 A 22,22 0 1,1 39.86,37.15"
        android:strokeColor="#00E5FF"
        android:strokeWidth="6.5"
        android:strokeLineCap="round"
        android:strokeLineJoin="round" />
    <path
        android:pathData="M 54,20 L 54,52"
        android:strokeColor="#00E5FF"
        android:strokeWidth="6.5"
        android:strokeLineCap="round" />
</vector>"""
    with open(os.path.join(RES_DIR, "drawable", "ic_launcher_foreground.xml"), "w", encoding="utf-8") as f:
        f.write(ic_launcher_fg)

    ic_launcher_mono = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:pathData="M 68.14,37.15 A 22,22 0 1,1 39.86,37.15"
        android:strokeColor="#FFFFFF"
        android:strokeWidth="6.5"
        android:strokeLineCap="round"
        android:strokeLineJoin="round" />
    <path
        android:pathData="M 54,20 L 54,52"
        android:strokeColor="#FFFFFF"
        android:strokeWidth="6.5"
        android:strokeLineCap="round" />
</vector>"""
    with open(os.path.join(RES_DIR, "drawable", "ic_launcher_monochrome.xml"), "w", encoding="utf-8") as f:
        f.write(ic_launcher_mono)

    with open(os.path.join(RES_DIR, "drawable", "ic_stat_wol.png"), "wb") as f:
        f.write(make_png(48, 48, b'\xff\xff\xff'))

    btn_wake_bg = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <gradient
        android:angle="45"
        android:startColor="#0072FF"
        android:endColor="#00E5FF"
        android:type="linear" />
    <corners android:radius="14dp" />
</shape>"""
    with open(os.path.join(RES_DIR, "drawable", "btn_wake_bg.xml"), "w", encoding="utf-8") as f:
        f.write(btn_wake_bg)

    btn_shutdown_bg = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <gradient
        android:angle="45"
        android:startColor="#B71C1C"
        android:endColor="#FF3D00"
        android:type="linear" />
    <corners android:radius="14dp" />
</shape>"""
    with open(os.path.join(RES_DIR, "drawable", "btn_shutdown_bg.xml"), "w", encoding="utf-8") as f:
        f.write(btn_shutdown_bg)

    btn_sleep_bg = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <gradient
        android:angle="45"
        android:startColor="#4A148C"
        android:endColor="#7C4DFF"
        android:type="linear" />
    <corners android:radius="14dp" />
</shape>"""
    with open(os.path.join(RES_DIR, "drawable", "btn_sleep_bg.xml"), "w", encoding="utf-8") as f:
        f.write(btn_sleep_bg)

    btn_timer_bg = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <gradient
        android:angle="45"
        android:startColor="#E65100"
        android:endColor="#FF9100"
        android:type="linear" />
    <corners android:radius="14dp" />
</shape>"""
    with open(os.path.join(RES_DIR, "drawable", "btn_timer_bg.xml"), "w", encoding="utf-8") as f:
        f.write(btn_timer_bg)

    card_bg = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="#1A1D2B" />
    <corners android:radius="16dp" />
    <stroke android:width="1dp" android:color="#2A2F45" />
</shape>"""
    with open(os.path.join(RES_DIR, "drawable", "card_bg.xml"), "w", encoding="utf-8") as f:
        f.write(card_bg)

    btn_small_bg = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="#262B3F" />
    <corners android:radius="8dp" />
    <stroke android:width="1dp" android:color="#3A425F" />
</shape>"""
    with open(os.path.join(RES_DIR, "drawable", "btn_small_bg.xml"), "w", encoding="utf-8") as f:
        f.write(btn_small_bg)

    # 5. activity_main.xml
    layout = """<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#0F111A"
    android:fillViewport="true">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:gravity="center_horizontal"
        android:padding="20dp">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="AutoWake &amp; Power PC"
            android:textSize="24sp"
            android:textStyle="bold"
            android:textColor="#FFFFFF"
            android:layout_marginTop="10dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Управление питанием компьютера"
            android:textSize="13sp"
            android:textColor="#8F9CAE"
            android:layout_marginTop="3dp" />

        <!-- PC Status Banner -->
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:gravity="center_vertical"
            android:background="@drawable/card_bg"
            android:padding="14dp"
            android:layout_marginTop="18dp">

            <TextView
                android:id="@+id/tvPcStatus"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="🔄 Проверка статуса ПК..."
                android:textSize="15sp"
                android:textStyle="bold"
                android:textColor="#00E5FF" />

            <Button
                android:id="@+id/btnCheckStatus"
                android:layout_width="wrap_content"
                android:layout_height="36dp"
                android:text="🔄 Проверить"
                android:textSize="11sp"
                android:textColor="#FFFFFF"
                android:background="@drawable/btn_small_bg"
                android:paddingLeft="10dp"
                android:paddingRight="10dp" />
        </LinearLayout>

        <!-- Main Power Buttons -->
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:background="@drawable/card_bg"
            android:padding="16dp"
            android:layout_marginTop="14dp">

            <Button
                android:id="@+id/btnWake"
                android:layout_width="match_parent"
                android:layout_height="56dp"
                android:background="@drawable/btn_wake_bg"
                android:text="⚡ ВКЛЮЧИТЬ ПК"
                android:textSize="17sp"
                android:textStyle="bold"
                android:textColor="#FFFFFF" />

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="horizontal"
                android:layout_marginTop="12dp">

                <Button
                    android:id="@+id/btnShutdown"
                    android:layout_width="0dp"
                    android:layout_height="52dp"
                    android:layout_weight="1"
                    android:background="@drawable/btn_shutdown_bg"
                    android:text="🛑 ВЫКЛЮЧИТЬ"
                    android:textSize="15sp"
                    android:textStyle="bold"
                    android:textColor="#FFFFFF" />

                <View
                    android:layout_width="10dp"
                    android:layout_height="match_parent" />

                <Button
                    android:id="@+id/btnSleep"
                    android:layout_width="0dp"
                    android:layout_height="52dp"
                    android:layout_weight="1"
                    android:background="@drawable/btn_sleep_bg"
                    android:text="💤 В СОН"
                    android:textSize="15sp"
                    android:textStyle="bold"
                    android:textColor="#FFFFFF" />
            </LinearLayout>

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="horizontal"
                android:layout_marginTop="10dp">

                <Button
                    android:id="@+id/btnTimer"
                    android:layout_width="0dp"
                    android:layout_height="50dp"
                    android:layout_weight="1"
                    android:background="@drawable/btn_timer_bg"
                    android:text="⏱️ ВЫКЛЮЧИТЬ ЧЕРЕЗ..."
                    android:textSize="14sp"
                    android:textStyle="bold"
                    android:textColor="#FFFFFF" />

                <Button
                    android:id="@+id/btnCancelTimer"
                    android:layout_width="wrap_content"
                    android:layout_height="50dp"
                    android:background="@drawable/btn_small_bg"
                    android:text="❌ Отмена"
                    android:textSize="12sp"
                    android:textStyle="bold"
                    android:textColor="#FF5252"
                    android:visibility="gone"
                    android:layout_marginLeft="8dp" />
            </LinearLayout>

            <TextView
                android:id="@+id/tvStatus"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:layout_gravity="center_horizontal"
                android:text="Готов к отправке команд"
                android:textSize="13sp"
                android:textColor="#8F9CAE"
                android:layout_marginTop="12dp" />
        </LinearLayout>

        <!-- Network Info Card -->
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:background="@drawable/card_bg"
            android:padding="14dp"
            android:layout_marginTop="14dp">

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="📡 Текущая сеть:"
                android:textSize="12sp"
                android:textStyle="bold"
                android:textColor="#00E5FF" />

            <TextView
                android:id="@+id/tvNetworkInfo"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="Определение сети..."
                android:textSize="13sp"
                android:textColor="#FFFFFF"
                android:layout_marginTop="3dp" />
        </LinearLayout>

        <!-- Auto-wake Switch Card -->
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:background="@drawable/card_bg"
            android:padding="14dp"
            android:layout_marginTop="12dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="horizontal"
                android:gravity="center_vertical">

                <LinearLayout
                    android:layout_width="0dp"
                    android:layout_height="wrap_content"
                    android:layout_weight="1"
                    android:orientation="vertical">

                    <TextView
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="Авто-включение при Wi-Fi"
                        android:textSize="15sp"
                        android:textStyle="bold"
                        android:textColor="#FFFFFF" />

                    <TextView
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="Будить ПК при подключении к домашней сети"
                        android:textSize="12sp"
                        android:textColor="#8F9CAE"
                        android:layout_marginTop="2dp" />
                </LinearLayout>

                <Switch
                    android:id="@+id/swAutoWake"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content" />
            </LinearLayout>

            <TextView
                android:id="@+id/tvLastAutoWake"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:text="Последний сигнал: не зафиксирован"
                android:textSize="12sp"
                android:textColor="#00E5FF"
                android:layout_marginTop="8dp" />

            <Button
                android:id="@+id/btnBatteryOpt"
                android:layout_width="match_parent"
                android:layout_height="38dp"
                android:background="@drawable/btn_small_bg"
                android:text="🔋 Разрешить работу в фоне (без засыпания)"
                android:textSize="11sp"
                android:textColor="#FFFFFF"
                android:visibility="gone"
                android:layout_marginTop="8dp" />

            <Button
                android:id="@+id/btnHideNotification"
                android:layout_width="match_parent"
                android:layout_height="38dp"
                android:background="@drawable/btn_small_bg"
                android:text="🔕 Скрыть уведомление службы из шторки"
                android:textSize="11sp"
                android:textColor="#8F9CAE"
                android:layout_marginTop="6dp" />
        </LinearLayout>

        <!-- Settings Card -->
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:background="@drawable/card_bg"
            android:padding="16dp"
            android:layout_marginTop="12dp">

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="Параметры и фильтрация"
                android:textSize="15sp"
                android:textStyle="bold"
                android:textColor="#FFFFFF"
                android:layout_marginBottom="10dp" />

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="MAC-адрес ПК"
                android:textSize="12sp"
                android:textColor="#8F9CAE" />

            <EditText
                android:id="@+id/etMac"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:hint="AA:BB:CC:DD:EE:FF"
                android:textColorHint="#5A6578"
                android:textColor="#FFFFFF"
                android:textSize="14sp"
                android:background="#12141E"
                android:padding="10dp"
                android:layout_marginTop="4dp" />

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="Домашний Wi-Fi (SSID)"
                android:textSize="12sp"
                android:textColor="#8F9CAE"
                android:layout_marginTop="10dp" />

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="horizontal"
                android:gravity="center_vertical"
                android:layout_marginTop="4dp">

                <EditText
                    android:id="@+id/etSsid"
                    android:layout_width="0dp"
                    android:layout_height="wrap_content"
                    android:layout_weight="1"
                    android:hint="Имя сети (или пусто для всех)"
                    android:textColorHint="#5A6578"
                    android:textColor="#FFFFFF"
                    android:textSize="14sp"
                    android:background="#12141E"
                    android:padding="10dp" />

                <Button
                    android:id="@+id/btnDetectWifi"
                    android:layout_width="wrap_content"
                    android:layout_height="40dp"
                    android:text="🔍 Текущий"
                    android:textSize="11sp"
                    android:textColor="#00E5FF"
                    android:background="@drawable/btn_small_bg"
                    android:paddingLeft="10dp"
                    android:paddingRight="10dp"
                    android:layout_marginLeft="8dp" />
            </LinearLayout>

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="IP адрес ПК (для команд и Broadcast)"
                android:textSize="12sp"
                android:textColor="#8F9CAE"
                android:layout_marginTop="10dp" />

            <EditText
                android:id="@+id/etIp"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:hint="IP ПК (например: 192.168.0.100)"
                android:textColorHint="#5A6578"
                android:textColor="#FFFFFF"
                android:textSize="14sp"
                android:background="#12141E"
                android:padding="10dp"
                android:layout_marginTop="4dp" />

            <Button
                android:id="@+id/btnSave"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:text="Сохранить настройки"
                android:textColor="#FFFFFF"
                android:background="#262B3F"
                android:layout_marginTop="16dp" />
        </LinearLayout>

    </LinearLayout>
</ScrollView>"""
    with open(os.path.join(RES_DIR, "layout", "activity_main.xml"), "w", encoding="utf-8") as f:
        f.write(layout)

    # 6. Java source files
    wol_helper = """package com.antigravity.wakeonlan;

import android.content.Context;
import android.net.Network;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class WolHelper {
    public static final String DEFAULT_MAC = "";
    public static final String DEFAULT_IP = "";
    public static final int WOL_PORT = 9;
    public static final int AGENT_PORT = 9876;

    public static String getSubnetBroadcast(String ipStr) {
        try {
            if (ipStr == null || ipStr.trim().isEmpty()) return null;
            String[] parts = ipStr.trim().split("\\\\.");
            if (parts.length == 4) {
                return parts[0] + "." + parts[1] + "." + parts[2] + ".255";
            }
        } catch (Exception ignored) {}
        return null;
    }

    public static boolean isSameSubnet(String ip1, String ip2) {
        try {
            if (ip1 == null || ip2 == null) return false;
            String[] p1 = ip1.trim().split("\\\\.");
            String[] p2 = ip2.trim().split("\\\\.");
            if (p1.length == 4 && p2.length == 4) {
                return p1[0].equals(p2[0]) && p1[1].equals(p2[1]) && p1[2].equals(p2[2]);
            }
        } catch (Exception ignored) {}
        return false;
    }

    public static List<String> getDeviceIpv4Addresses() {
        List<String> list = new ArrayList<>();
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces != null && interfaces.hasMoreElements()) {
                NetworkInterface ni = interfaces.nextElement();
                if (ni.isLoopback() || !ni.isUp()) continue;
                Enumeration<InetAddress> addrs = ni.getInetAddresses();
                while (addrs.hasMoreElements()) {
                    InetAddress addr = addrs.nextElement();
                    if (addr instanceof Inet4Address && !addr.isLoopbackAddress()) {
                        String host = addr.getHostAddress();
                        if (host != null && !host.isEmpty()) {
                            list.add(host);
                        }
                    }
                }
            }
        } catch (Exception ignored) {}
        return list;
    }

    public static List<String> getDynamicBroadcastAddresses() {
        Set<String> addresses = new LinkedHashSet<>();
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces != null && interfaces.hasMoreElements()) {
                NetworkInterface networkInterface = interfaces.nextElement();
                if (networkInterface.isLoopback() || !networkInterface.isUp()) {
                    continue;
                }
                for (InterfaceAddress interfaceAddress : networkInterface.getInterfaceAddresses()) {
                    InetAddress broadcast = interfaceAddress.getBroadcast();
                    if (broadcast != null && broadcast instanceof Inet4Address) {
                        String host = broadcast.getHostAddress();
                        if (host != null && !host.isEmpty()) {
                            addresses.add(host);
                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return new ArrayList<>(addresses);
    }

    public static String cleanSsid(String ssid) {
        if (ssid == null) return "";
        if (ssid.startsWith("\\\"") && ssid.endsWith("\\\"") && ssid.length() >= 2) {
            ssid = ssid.substring(1, ssid.length() - 1);
        }
        if (ssid.equals("<unknown ssid>")) {
            return "";
        }
        return ssid.trim();
    }

    public static String getCurrentWifiSsid(Context context) {
        try {
            WifiManager wifiManager = (WifiManager) context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wifiManager != null) {
                WifiInfo info = wifiManager.getConnectionInfo();
                if (info != null && info.getSSID() != null) {
                    return cleanSsid(info.getSSID());
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return "";
    }

    public static boolean sendPacket(Context context, Network network, String macStr, String manualIp, int port) {
        try {
            String cleanMac = macStr.replaceAll("[:\\\\-]", "").trim();
            if (cleanMac.length() != 12) {
                return false;
            }
            byte[] macBytes = new byte[6];
            for (int i = 0; i < 6; i++) {
                macBytes[i] = (byte) Integer.parseInt(cleanMac.substring(i * 2, i * 2 + 2), 16);
            }

            byte[] bytes = new byte[6 + 16 * 6];
            for (int i = 0; i < 6; i++) {
                bytes[i] = (byte) 0xff;
            }
            for (int i = 6; i < bytes.length; i += 6) {
                System.arraycopy(macBytes, 0, bytes, i, 6);
            }

            Set<String> targets = new LinkedHashSet<>();
            String calcBroadcast = getSubnetBroadcast(manualIp);
            if (calcBroadcast != null) {
                targets.add(calcBroadcast);
            }
            for (String devIp : getDeviceIpv4Addresses()) {
                String devBc = getSubnetBroadcast(devIp);
                if (devBc != null) {
                    targets.add(devBc);
                }
            }
            targets.addAll(getDynamicBroadcastAddresses());
            targets.add("255.255.255.255");
            if (manualIp != null && !manualIp.trim().isEmpty()) {
                targets.add(manualIp.trim());
            }

            WifiManager.MulticastLock multicastLock = null;
            try {
                WifiManager wifi = (WifiManager) context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if (wifi != null) {
                    multicastLock = wifi.createMulticastLock("AutoWakeMulticast");
                    multicastLock.acquire();
                }
            } catch (Throwable ignored) {}

            int[] ports = (port == 9) ? new int[]{9, 7} : new int[]{port};
            boolean anySuccess = false;

            try {
                for (int p : ports) {
                    for (String ip : targets) {
                        try {
                            InetAddress address = InetAddress.getByName(ip);
                            DatagramPacket packet = new DatagramPacket(bytes, bytes.length, address, p);
                            
                            if (network != null) {
                                try {
                                    DatagramSocket netSock = new DatagramSocket();
                                    network.bindSocket(netSock);
                                    netSock.setBroadcast(true);
                                    netSock.send(packet);
                                    netSock.close();
                                    anySuccess = true;
                                } catch (Throwable ignored) {}
                            }

                            DatagramSocket socket = new DatagramSocket();
                            socket.setBroadcast(true);
                            socket.send(packet);
                            socket.close();
                            anySuccess = true;
                        } catch (Exception ignored) {}
                    }
                }
            } finally {
                if (multicastLock != null && multicastLock.isHeld()) {
                    try { multicastLock.release(); } catch (Throwable ignored) {}
                }
            }

            return anySuccess;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    public static boolean sendPacket(Context context, String macStr, String manualIp, int port) {
        return sendPacket(context, null, macStr, manualIp, port);
    }

    public static boolean sendAgentCommand(String command, String manualIp) {
        Set<String> targets = new LinkedHashSet<>();
        if (manualIp != null && !manualIp.trim().isEmpty()) {
            targets.add(manualIp.trim());
        }
        targets.addAll(getDynamicBroadcastAddresses());
        targets.add("255.255.255.255");

        boolean anySuccess = false;
        for (String ip : targets) {
            try {
                byte[] data = command.getBytes("UTF-8");
                InetAddress address = InetAddress.getByName(ip);
                DatagramPacket packet = new DatagramPacket(data, data.length, address, AGENT_PORT);
                DatagramSocket socket = new DatagramSocket();
                socket.setBroadcast(true);
                socket.send(packet);
                socket.close();
                anySuccess = true;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return anySuccess;
    }

    public static boolean checkPcStatus(String manualIp) {
        Set<String> targets = new LinkedHashSet<>();
        if (manualIp != null && !manualIp.trim().isEmpty() && !manualIp.endsWith(".255")) {
            targets.add(manualIp.trim());
        }
        targets.addAll(getDynamicBroadcastAddresses());

        for (String ip : targets) {
            try {
                DatagramSocket socket = new DatagramSocket();
                socket.setSoTimeout(1200);
                byte[] data = "PING".getBytes("UTF-8");
                InetAddress address = InetAddress.getByName(ip);
                DatagramPacket packet = new DatagramPacket(data, data.length, address, AGENT_PORT);
                socket.send(packet);

                byte[] buf = new byte[128];
                DatagramPacket recv = new DatagramPacket(buf, buf.length);
                socket.receive(recv);
                String resp = new String(recv.getData(), 0, recv.getLength()).trim();
                socket.close();
                if ("PONG".equals(resp)) {
                    return true;
                }
            } catch (Exception ignored) {}
        }
        return false;
    }
}
"""
    with open(os.path.join(SRC_DIR, "WolHelper.java"), "w", encoding="utf-8") as f:
        f.write(wol_helper)

    wol_service = """package com.antigravity.wakeonlan;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.TransportInfo;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.SystemClock;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class WolService extends Service {
    private static final String CHANNEL_ID = "AutoWakeServiceChannel";
    private ConnectivityManager connectivityManager;
    private ConnectivityManager.NetworkCallback networkCallback;
    private boolean isWifiConnected = false;
    private long lastWakeWorkerTime = 0;

    @Override
    public void onCreate() {
        super.onCreate();
        ensureForeground("Авто-включение ПК активно");
        registerNetworkCallback();
    }

    private void ensureForeground(String text) {
        try {
            createNotificationChannel();
            Notification notification = buildNotification(text);
            if (Build.VERSION.SDK_INT >= 34) {
                startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
            } else {
                startForeground(1, notification);
            }
        } catch (Throwable t) {
            t.printStackTrace();
        }
    }

    private void registerNetworkCallback() {
        connectivityManager = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (connectivityManager == null) return;

        NetworkRequest request = new NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .build();

        networkCallback = new ConnectivityManager.NetworkCallback() {
            @Override
            public void onAvailable(final Network network) {
                synchronized (WolService.this) {
                    if (isWifiConnected) {
                        return;
                    }
                    isWifiConnected = true;
                }
                triggerAutoWake(network);
            }

            @Override
            public void onLost(final Network network) {
                synchronized (WolService.this) {
                    isWifiConnected = false;
                }
            }
        };

        try {
            connectivityManager.registerNetworkCallback(request, networkCallback);
        } catch (Throwable t) {
            t.printStackTrace();
        }
    }

    private synchronized void triggerAutoWake(final Network network) {
        long now = System.currentTimeMillis();
        // Cooldown between auto-wakes: minimum 15 minutes!
        if (now - lastWakeWorkerTime < 15 * 60 * 1000) {
            return;
        }

        SharedPreferences prefs = getSharedPreferences("wol_prefs", MODE_PRIVATE);
        if (!prefs.getBoolean("auto_wake", false)) {
            return;
        }

        // Check if user recently shut down the PC (within last 30 minutes)
        long userShutdownTime = prefs.getLong("user_shutdown_time", 0);
        if (now - userShutdownTime < 30 * 60 * 1000) {
            prefs.edit().putString("last_auto_wake", getTime() + " — ПК недавно выключен, авто-включение на паузе").apply();
            return;
        }

        lastWakeWorkerTime = now;

        new Thread(new Runnable() {
            @Override
            public void run() {
                PowerManager.WakeLock wl = null;
                WifiManager.WifiLock wifiLock = null;
                try {
                    PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
                    if (pm != null) {
                        wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AutoWake:ServiceWakeLock");
                        wl.acquire(15000);
                    }

                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    if (wm != null) {
                        wifiLock = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "AutoWake:ServiceWifiLock");
                        wifiLock.acquire();
                    }

                    SharedPreferences prefs = getSharedPreferences("wol_prefs", MODE_PRIVATE);
                    String targetSsid = prefs.getString("target_ssid", "").trim();
                    String mac = prefs.getString("mac", "").trim();
                    String ip = prefs.getString("ip", "").trim();

                    if (mac.isEmpty()) {
                        prefs.edit().putString("last_auto_wake", getTime() + " — ⚠️ Укажите MAC-адрес ПК!").apply();
                        return;
                    }

                    int[] delays = new int[]{1500, 2500, 3000};
                    boolean anySent = false;
                    String finalMatchedLabel = "Wi-Fi";

                    for (int step = 0; step < delays.length; step++) {
                        try { Thread.sleep(delays[step]); } catch (InterruptedException ignored) {}

                        String currentSsid = detectSsid(network);
                        if (!targetSsid.isEmpty()) {
                            if (!currentSsid.isEmpty()) {
                                boolean matchesSsid = currentSsid.equalsIgnoreCase(targetSsid)
                                        || currentSsid.equalsIgnoreCase(targetSsid + "_5G")
                                        || currentSsid.equalsIgnoreCase(targetSsid + "_2.4G")
                                        || currentSsid.contains(targetSsid);
                                if (!matchesSsid) {
                                    prefs.edit().putString("last_auto_wake", getTime() + " — Чужой Wi-Fi (" + currentSsid + ")").apply();
                                    return;
                                }
                                finalMatchedLabel = currentSsid;
                            } else {
                                List<String> devIps = WolHelper.getDeviceIpv4Addresses();
                                boolean sameSubnet = false;
                                for (String dIp : devIps) {
                                    if (WolHelper.isSameSubnet(dIp, ip)) {
                                        sameSubnet = true;
                                        break;
                                    }
                                }
                                if (!sameSubnet && !ip.isEmpty() && step < delays.length - 1) {
                                    continue;
                                }
                                finalMatchedLabel = "Домашняя сеть";
                            }
                        } else {
                            if (!currentSsid.isEmpty()) finalMatchedLabel = currentSsid;
                        }

                        boolean ok = WolHelper.sendPacket(WolService.this, network, mac, ip, WolHelper.WOL_PORT);
                        if (ok) anySent = true;
                    }

                    String statusText;
                    if (anySent) {
                        statusText = "⚡ ПК включен (" + finalMatchedLabel + ") в " + getTime();
                    } else {
                        statusText = "⚠️ Сбой отправки на " + mac;
                    }
                    prefs.edit().putString("last_auto_wake", statusText).apply();

                } catch (Throwable t) {
                    t.printStackTrace();
                } finally {
                    if (wifiLock != null && wifiLock.isHeld()) {
                        try { wifiLock.release(); } catch (Throwable ignored) {}
                    }
                    if (wl != null && wl.isHeld()) {
                        try { wl.release(); } catch (Throwable ignored) {}
                    }
                }
            }
        }).start();
    }

    private String detectSsid(Network network) {
        if (Build.VERSION.SDK_INT >= 29 && connectivityManager != null && network != null) {
            try {
                NetworkCapabilities caps = connectivityManager.getNetworkCapabilities(network);
                if (caps != null) {
                    TransportInfo ti = caps.getTransportInfo();
                    if (ti instanceof WifiInfo) {
                        String s = ((WifiInfo) ti).getSSID();
                        String clean = WolHelper.cleanSsid(s);
                        if (!clean.isEmpty()) return clean;
                    }
                }
            } catch (Throwable ignored) {}
        }
        return WolHelper.getCurrentWifiSsid(this);
    }

    private String getTime() {
        return new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date());
    }

    private Notification buildNotification(String text) {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, notificationIntent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
            builder.setPriority(Notification.PRIORITY_MIN);
        }

        return builder.setContentTitle("AutoWake")
                .setContentText(text)
                .setSmallIcon(R.drawable.ic_stat_wol)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel serviceChannel = new NotificationChannel(
                    CHANNEL_ID,
                    "Фоновая служба",
                    NotificationManager.IMPORTANCE_MIN
            );
            serviceChannel.setDescription("Служба авто-включения ПК в фоне");
            serviceChannel.setShowBadge(false);
            serviceChannel.enableLights(false);
            serviceChannel.enableVibration(false);
            serviceChannel.setSound(null, null);
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(serviceChannel);
            }
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        ensureForeground("Авто-включение ПК активно");
        return START_STICKY;
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        super.onTaskRemoved(rootIntent);
        SharedPreferences prefs = getSharedPreferences("wol_prefs", MODE_PRIVATE);
        if (prefs.getBoolean("auto_wake", false)) {
            Intent restartIntent = new Intent(getApplicationContext(), WolService.class);
            PendingIntent restartPendingIntent = PendingIntent.getService(
                    getApplicationContext(), 1, restartIntent,
                    PendingIntent.FLAG_ONE_SHOT | PendingIntent.FLAG_IMMUTABLE
            );
            AlarmManager alarmService = (AlarmManager) getApplicationContext().getSystemService(Context.ALARM_SERVICE);
            if (alarmService != null) {
                alarmService.set(
                        AlarmManager.ELAPSED_REALTIME,
                        SystemClock.elapsedRealtime() + 1000,
                        restartPendingIntent
                );
            }
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (connectivityManager != null && networkCallback != null) {
            try {
                connectivityManager.unregisterNetworkCallback(networkCallback);
            } catch (Throwable ignored) {}
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
"""
    with open(os.path.join(SRC_DIR, "WolService.java"), "w", encoding="utf-8") as f:
        f.write(wol_service)

    boot_receiver = """package com.antigravity.wakeonlan;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            SharedPreferences prefs = context.getSharedPreferences("wol_prefs", Context.MODE_PRIVATE);
            boolean autoWake = prefs.getBoolean("auto_wake", false);
            if (autoWake) {
                try {
                    Intent serviceIntent = new Intent(context, WolService.class);
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        context.startForegroundService(serviceIntent);
                    } else {
                        context.startService(serviceIntent);
                    }
                } catch (Throwable ignored) {}
            }
        }
    }
}
"""
    with open(os.path.join(SRC_DIR, "BootReceiver.java"), "w", encoding="utf-8") as f:
        f.write(boot_receiver)

    main_activity = """package com.antigravity.wakeonlan;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.view.View;
import android.widget.Button;
import android.widget.CompoundButton;
import android.widget.EditText;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class MainActivity extends Activity {
    private EditText etMac, etSsid, etIp;
    private TextView tvStatus, tvNetworkInfo, tvPcStatus, tvLastAutoWake;
    private Button btnBatteryOpt, btnTimer, btnCancelTimer;
    private Switch swAutoWake;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        if (Build.VERSION.SDK_INT >= 33) {
            if (checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 101);
            }
        }

        prefs = getSharedPreferences("wol_prefs", MODE_PRIVATE);

        etMac = findViewById(R.id.etMac);
        etSsid = findViewById(R.id.etSsid);
        etIp = findViewById(R.id.etIp);
        tvStatus = findViewById(R.id.tvStatus);
        tvNetworkInfo = findViewById(R.id.tvNetworkInfo);
        tvPcStatus = findViewById(R.id.tvPcStatus);
        tvLastAutoWake = findViewById(R.id.tvLastAutoWake);
        btnBatteryOpt = findViewById(R.id.btnBatteryOpt);
        btnTimer = findViewById(R.id.btnTimer);
        btnCancelTimer = findViewById(R.id.btnCancelTimer);
        swAutoWake = findViewById(R.id.swAutoWake);

        Button btnWake = findViewById(R.id.btnWake);
        Button btnShutdown = findViewById(R.id.btnShutdown);
        Button btnSleep = findViewById(R.id.btnSleep);
        Button btnCheckStatus = findViewById(R.id.btnCheckStatus);
        Button btnSave = findViewById(R.id.btnSave);
        Button btnDetectWifi = findViewById(R.id.btnDetectWifi);
        Button btnHideNotification = findViewById(R.id.btnHideNotification);

        btnHideNotification.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                try {
                    Intent intent = new Intent(android.provider.Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS);
                    intent.putExtra(android.provider.Settings.EXTRA_APP_PACKAGE, getPackageName());
                    intent.putExtra(android.provider.Settings.EXTRA_CHANNEL_ID, "AutoWakeServiceChannel");
                    startActivity(intent);
                } catch (Throwable t) {
                    try {
                        Intent intent = new Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS);
                        intent.putExtra(android.provider.Settings.EXTRA_APP_PACKAGE, getPackageName());
                        startActivity(intent);
                    } catch (Throwable ignored) {}
                }
            }
        });

        etMac.setText(prefs.getString("mac", WolHelper.DEFAULT_MAC));
        etSsid.setText(prefs.getString("target_ssid", ""));
        etIp.setText(prefs.getString("ip", WolHelper.DEFAULT_IP));

        boolean autoWake = prefs.getBoolean("auto_wake", false);
        swAutoWake.setChecked(autoWake);
        startAutoWakeServiceIfNeeded();

        refreshNetworkInfo();
        checkPcOnline();
        updateTimerUi();

        btnWake.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                doWake();
            }
        });

        btnShutdown.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                confirmShutdown();
            }
        });

        btnSleep.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                confirmSleep();
            }
        });

        btnTimer.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showTimerDialog();
            }
        });

        btnCancelTimer.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                cancelShutdownTimer();
            }
        });

        btnCheckStatus.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                checkPcOnline();
            }
        });

        btnDetectWifi.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                detectCurrentWifi();
            }
        });

        btnSave.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                saveSettings();
                refreshNetworkInfo();
                checkPcOnline();
                if (swAutoWake.isChecked()) {
                    Intent serviceIntent = new Intent(MainActivity.this, WolService.class);
                    stopService(serviceIntent);
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startForegroundService(serviceIntent);
                    } else {
                        startService(serviceIntent);
                    }
                }
                Toast.makeText(MainActivity.this, "Настройки сохранены!", Toast.LENGTH_SHORT).show();
            }
        });

        swAutoWake.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                if (isChecked) {
                    String mac = prefs.getString("mac", "").trim();
                    if (mac.replace(":", "").replace("-", "").length() != 12) {
                        swAutoWake.setChecked(false);
                        Toast.makeText(MainActivity.this, "⚠️ Сначала укажите MAC-адрес ПК и сохраните!", Toast.LENGTH_LONG).show();
                        etMac.requestFocus();
                        return;
                    }
                }

                prefs.edit().putBoolean("auto_wake", isChecked).apply();
                Intent serviceIntent = new Intent(MainActivity.this, WolService.class);
                try {
                    if (isChecked) {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            startForegroundService(serviceIntent);
                        } else {
                            startService(serviceIntent);
                        }
                        tvStatus.setText("Авто-режим включен (при Wi-Fi)");
                    } else {
                        stopService(serviceIntent);
                        tvStatus.setText("Авто-режим выключен");
                    }
                } catch (Throwable t) {
                    t.printStackTrace();
                    Toast.makeText(MainActivity.this, "Ошибка службы: " + t.getMessage(), Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshNetworkInfo();
        checkPcOnline();
        startAutoWakeServiceIfNeeded();

        String lastWake = prefs.getString("last_auto_wake", "Пока не зафиксировано");
        tvLastAutoWake.setText("Последний сигнал: " + lastWake);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                btnBatteryOpt.setVisibility(View.VISIBLE);
                btnBatteryOpt.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        try {
                            Intent intent = new Intent(android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                            intent.setData(android.net.Uri.parse("package:" + getPackageName()));
                            startActivity(intent);
                        } catch (Throwable t) {
                            Toast.makeText(MainActivity.this, "Отключите экономию батареи в настройках приложения", Toast.LENGTH_LONG).show();
                        }
                    }
                });
            } else {
                btnBatteryOpt.setVisibility(View.GONE);
            }
        }
    }

    private void startAutoWakeServiceIfNeeded() {
        if (prefs != null && prefs.getBoolean("auto_wake", false)) {
            String mac = prefs.getString("mac", "").trim();
            if (mac.replace(":", "").replace("-", "").length() == 12) {
                try {
                    Intent serviceIntent = new Intent(this, WolService.class);
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startForegroundService(serviceIntent);
                    } else {
                        startService(serviceIntent);
                    }
                } catch (Throwable t) {
                    t.printStackTrace();
                }
            }
        }
    }

    private void checkPcOnline() {
        tvPcStatus.setText("🔄 Проверка статуса ПК...");
        final String ip = etIp.getText().toString().trim();
        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean online = WolHelper.checkPcStatus(ip);
                new Handler(Looper.getMainLooper()).post(new Runnable() {
                    @Override
                    public void run() {
                        if (online) {
                            tvPcStatus.setText("🟢 ПК включен (в сети)");
                            tvPcStatus.setTextColor(0xFF00E676);
                        } else {
                            tvPcStatus.setText("⚪ ПК выключен (не в сети)");
                            tvPcStatus.setTextColor(0xFF8F9CAE);
                        }
                    }
                });
            }
        }).start();
    }

    private void refreshNetworkInfo() {
        String currentSsid = WolHelper.getCurrentWifiSsid(this);
        List<String> broadcasts = WolHelper.getDynamicBroadcastAddresses();

        StringBuilder sb = new StringBuilder();
        if (currentSsid.isEmpty()) {
            sb.append("Wi-Fi: Не подключен / Имя скрыто\\n");
        } else {
            sb.append("Wi-Fi: \\"").append(currentSsid).append("\\"\\n");
        }

        if (broadcasts.isEmpty()) {
            sb.append("Broadcast: 255.255.255.255 (общий)");
        } else {
            sb.append("Broadcast: ");
            for (int i = 0; i < broadcasts.size(); i++) {
                if (i > 0) sb.append(", ");
                sb.append(broadcasts.get(i));
            }
            sb.append(" (авто)");
        }

        tvNetworkInfo.setText(sb.toString());
    }

    private void detectCurrentWifi() {
        if (checkSelfPermission("android.permission.ACCESS_FINE_LOCATION") != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{"android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION"}, 102);
            return;
        }

        String ssid = WolHelper.getCurrentWifiSsid(this);
        if (!ssid.isEmpty()) {
            etSsid.setText(ssid);
            refreshNetworkInfo();
            Toast.makeText(this, "Определена сеть: " + ssid, Toast.LENGTH_SHORT).show();
        } else {
            Toast.makeText(this, "Включите геолокацию в шторке или введите имя сети вручную", Toast.LENGTH_LONG).show();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 102) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                detectCurrentWifi();
            }
        }
    }

    private void saveSettings() {
        String mac = etMac.getText().toString().trim();
        String ssid = etSsid.getText().toString().trim();
        String ip = etIp.getText().toString().trim();
        prefs.edit().putString("mac", mac).putString("target_ssid", ssid).putString("ip", ip).apply();
    }

    private void doWake() {
        final String mac = etMac.getText().toString().trim();
        final String ip = etIp.getText().toString().trim();
        saveSettings();
        prefs.edit().remove("user_shutdown_time").apply();

        if (mac.isEmpty()) {
            tvStatus.setText("⚠️ Введите MAC-адрес ПК в настройках");
            Toast.makeText(MainActivity.this, "Введите MAC-адрес ПК в настройках!", Toast.LENGTH_SHORT).show();
            return;
        }

        tvStatus.setText("Отправка сигнала включения...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean success = WolHelper.sendPacket(MainActivity.this, mac, ip, WolHelper.WOL_PORT);
                new Handler(Looper.getMainLooper()).post(new Runnable() {
                    @Override
                    public void run() {
                        if (success) {
                            tvStatus.setText("⚡ Сигнал включения отправлен!");
                            Toast.makeText(MainActivity.this, "Сигнал отправлен на ПК!", Toast.LENGTH_SHORT).show();
                            new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                                @Override
                                public void run() {
                                    checkPcOnline();
                                }
                            }, 5000);
                        } else {
                            tvStatus.setText("❌ Ошибка отправки пакета");
                            Toast.makeText(MainActivity.this, "Ошибка! Проверь MAC-адрес", Toast.LENGTH_SHORT).show();
                        }
                    }
                });
            }
        }).start();
    }

    private void confirmShutdown() {
        new AlertDialog.Builder(this)
                .setTitle("Выключение ПК")
                .setMessage("Вы уверены, что хотите завершить работу компьютера?")
                .setPositiveButton("Да, выключить", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        doShutdown();
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }

    private void doShutdown() {
        final String ip = etIp.getText().toString().trim();
        prefs.edit().putLong("user_shutdown_time", System.currentTimeMillis()).apply();
        tvStatus.setText("🛑 Отправка команды выключения...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean ok = WolHelper.sendAgentCommand("SHUTDOWN", ip);
                new Handler(Looper.getMainLooper()).post(new Runnable() {
                    @Override
                    public void run() {
                        if (ok) {
                            tvStatus.setText("🛑 Команда выключения отправлена!");
                            Toast.makeText(MainActivity.this, "Компьютер выключается...", Toast.LENGTH_LONG).show();
                            new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                                @Override
                                public void run() {
                                    checkPcOnline();
                                }
                            }, 3000);
                        } else {
                            tvStatus.setText("❌ Ошибка отправки команды");
                        }
                    }
                });
            }
        }).start();
    }

    private void confirmSleep() {
        new AlertDialog.Builder(this)
                .setTitle("Спящий режим")
                .setMessage("Перевести компьютер в спящий режим?")
                .setPositiveButton("В сон", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        doSleep();
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }

    private void doSleep() {
        final String ip = etIp.getText().toString().trim();
        prefs.edit().putLong("user_shutdown_time", System.currentTimeMillis()).apply();
        tvStatus.setText("💤 Отправка команды сна...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean ok = WolHelper.sendAgentCommand("SLEEP", ip);
                new Handler(Looper.getMainLooper()).post(new Runnable() {
                    @Override
                    public void run() {
                        if (ok) {
                            tvStatus.setText("💤 ПК отправлен в спящий режим!");
                            Toast.makeText(MainActivity.this, "ПК переходит в спящий режим...", Toast.LENGTH_SHORT).show();
                            new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                                @Override
                                public void run() {
                                    checkPcOnline();
                                }
                            }, 3000);
                        } else {
                            tvStatus.setText("❌ Ошибка отправки команды");
                        }
                    }
                });
            }
        }).start();
    }

    private void showTimerDialog() {
        final String[] options = new String[]{
            "30 минут",
            "1 час (60 мин)",
            "1.5 часа (90 мин)",
            "2 часа (120 мин)",
            "3 часа (180 мин)",
            "4 часа (240 мин)",
            "✏️ Своё время в минутах..."
        };
        final int[] seconds = new int[]{
            1800,
            3600,
            5400,
            7200,
            10800,
            14400,
            -1
        };

        new AlertDialog.Builder(this)
            .setTitle("⏱️ Выключить ПК по таймеру")
            .setItems(options, new DialogInterface.OnClickListener() {
                @Override
                public void onClick(DialogInterface dialog, int which) {
                    if (seconds[which] == -1) {
                        showCustomTimerDialog();
                    } else {
                        setShutdownTimer(seconds[which], options[which]);
                    }
                }
            })
            .setNegativeButton("Отмена", null)
            .show();
    }

    private void showCustomTimerDialog() {
        final EditText input = new EditText(this);
        input.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        input.setHint("Количество минут (например, 45)");
        input.setTextColor(0xFFFFFFFF);
        input.setHintTextColor(0xFF5A6578);
        input.setPadding(40, 30, 40, 30);

        new AlertDialog.Builder(this)
            .setTitle("⏱️ Укажите время (в минутах)")
            .setView(input)
            .setPositiveButton("Запустить таймер", new DialogInterface.OnClickListener() {
                @Override
                public void onClick(DialogInterface dialog, int which) {
                    String val = input.getText().toString().trim();
                    try {
                        int mins = Integer.parseInt(val);
                        if (mins > 0) {
                            setShutdownTimer(mins * 60, mins + " мин");
                        } else {
                            Toast.makeText(MainActivity.this, "Введите число больше 0", Toast.LENGTH_SHORT).show();
                        }
                    } catch (Exception e) {
                        Toast.makeText(MainActivity.this, "Неверный формат числа", Toast.LENGTH_SHORT).show();
                    }
                }
            })
            .setNegativeButton("Отмена", null)
            .show();
    }

    private void setShutdownTimer(final int sec, final String label) {
        final String ip = etIp.getText().toString().trim();
        tvStatus.setText("⏱️ Отправка таймера на ПК...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean ok = WolHelper.sendAgentCommand("SHUTDOWN_TIMER:" + sec, ip);
                new Handler(Looper.getMainLooper()).post(new Runnable() {
                    @Override
                    public void run() {
                        if (ok) {
                            long targetTime = System.currentTimeMillis() + (long) sec * 1000;
                            SimpleDateFormat sdf = new SimpleDateFormat("HH:mm", Locale.getDefault());
                            String timeStr = sdf.format(new Date(targetTime));
                            prefs.edit().putLong("active_timer_end", targetTime)
                                    .putString("active_timer_label", label)
                                    .putLong("user_shutdown_time", targetTime)
                                    .apply();
                            updateTimerUi();
                            Toast.makeText(MainActivity.this, "⏱️ Таймер запущен: выключение в " + timeStr + " (" + label + ")", Toast.LENGTH_LONG).show();
                        } else {
                            tvStatus.setText("❌ Ошибка отправки команды таймера");
                            Toast.makeText(MainActivity.this, "Не удалось связаться с ПК", Toast.LENGTH_SHORT).show();
                        }
                    }
                });
            }
        }).start();
    }

    private void cancelShutdownTimer() {
        final String ip = etIp.getText().toString().trim();
        tvStatus.setText("❌ Отмена таймера на ПК...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean ok = WolHelper.sendAgentCommand("CANCEL_SHUTDOWN", ip);
                new Handler(Looper.getMainLooper()).post(new Runnable() {
                    @Override
                    public void run() {
                        if (ok) {
                            prefs.edit().remove("active_timer_end")
                                    .remove("active_timer_label")
                                    .remove("user_shutdown_time")
                                    .apply();
                            updateTimerUi();
                            tvStatus.setText("✅ Таймер выключения отменен!");
                            Toast.makeText(MainActivity.this, "Таймер выключения отменен", Toast.LENGTH_SHORT).show();
                        } else {
                            tvStatus.setText("❌ Не удалось отменить таймер");
                        }
                    }
                });
            }
        }).start();
    }

    private void updateTimerUi() {
        long timerEnd = prefs.getLong("active_timer_end", 0);
        if (timerEnd > System.currentTimeMillis()) {
            SimpleDateFormat sdf = new SimpleDateFormat("HH:mm", Locale.getDefault());
            String timeStr = sdf.format(new Date(timerEnd));
            String label = prefs.getString("active_timer_label", "");
            tvStatus.setText("⏳ Таймер: выключение в " + timeStr + " (" + label + ")");
            btnCancelTimer.setVisibility(View.VISIBLE);
        } else {
            prefs.edit().remove("active_timer_end").remove("active_timer_label").apply();
            btnCancelTimer.setVisibility(View.GONE);
        }
    }
}
"""
    with open(os.path.join(SRC_DIR, "MainActivity.java"), "w", encoding="utf-8") as f:
        f.write(main_activity)

def build_apk():
    create_project_files()

    compiled_res = os.path.join(PROJ_DIR, "compiled_res.zip")
    unaligned_apk = os.path.join(PROJ_DIR, "unaligned.apk")
    aligned_apk = os.path.join(PROJ_DIR, "aligned.apk")
    final_apk = os.path.abspath("AutoWakePC.apk")

    print("[1] Compiling resources with aapt2...")
    run([AAPT2, "compile", "--dir", RES_DIR, "-o", compiled_res])

    print("[2] Linking resources with aapt2...")
    run([
        AAPT2, "link",
        "-I", ANDROID_JAR,
        compiled_res,
        "--manifest", os.path.join(PROJ_DIR, "AndroidManifest.xml"),
        "-o", unaligned_apk,
        "--java", GEN_DIR,
        "--auto-add-overlay"
    ])

    print("[3] Compiling Java code with javac...")
    java_files = []
    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(root, f))
    for root, _, files in os.walk(GEN_DIR):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(root, f))

    javac = r"C:\Program Files\Microsoft\jdk-17.0.10.7-hotspot\bin\javac.exe"
    run([javac, "-encoding", "UTF-8", "-cp", f"{ANDROID_JAR};{GEN_DIR};{SRC_DIR}", "-d", BIN_DIR] + java_files)

    print("[4] Dexing classes with d8...")
    class_files = []
    for root, _, files in os.walk(BIN_DIR):
        for f in files:
            if f.endswith(".class"):
                class_files.append(os.path.join(root, f))
    
    run([D8, "--release", "--min-api", "26", "--output", PROJ_DIR] + class_files, shell=True)

    print("[5] Packaging classes.dex into unaligned.apk...")
    import zipfile
    with zipfile.ZipFile(unaligned_apk, 'a') as zf:
        zf.write(os.path.join(PROJ_DIR, "classes.dex"), "classes.dex")

    print("[6] Aligning apk with zipalign...")
    if os.path.exists(aligned_apk):
        os.remove(aligned_apk)
    run([ZIPALIGN, "-v", "-p", "4", unaligned_apk, aligned_apk])

    print("[7] Creating debug keystore if not exists...")
    keystore = os.path.join(PROJ_DIR, "debug.keystore")
    if not os.path.exists(keystore):
        keytool = r"C:\Program Files\Microsoft\jdk-17.0.10.7-hotspot\bin\keytool.exe"
        run([
            keytool, "-genkeypair", "-v",
            "-keystore", keystore,
            "-storepass", "android",
            "-alias", "androiddebugkey",
            "-keypass", "android",
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-dname", "CN=Debug,O=Android,C=US"
        ])

    print("[8] Signing apk with apksigner...")
    if os.path.exists(final_apk):
        os.remove(final_apk)
    shutil.copyfile(aligned_apk, final_apk)
    run([
        APKSIGNER, "sign",
        "--ks", keystore,
        "--ks-pass", "pass:android",
        "--ks-key-alias", "androiddebugkey",
        "--key-pass", "pass:android",
        final_apk
    ], shell=True)

    print(f"\n[УСПЕХ!] APK готов: {final_apk} (Размер: {os.path.getsize(final_apk)} байт)")

if __name__ == "__main__":
    build_apk()
