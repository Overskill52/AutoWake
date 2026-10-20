package com.antigravity.wakeonlan;

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
    private BroadcastReceiver wifiReceiver;
    private long lastWakeWorkerTime = 0;

    @Override
    public void onCreate() {
        super.onCreate();
        ensureForeground("Авто-включение ПК активно");
        registerNetworkCallback();
        registerWifiReceiver();
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
                triggerAutoWake(network, "onAvailable");
            }

            @Override
            public void onLinkPropertiesChanged(final Network network, final android.net.LinkProperties lp) {
                triggerAutoWake(network, "onLinkPropertiesChanged");
            }

            @Override
            public void onCapabilitiesChanged(final Network network, final NetworkCapabilities nc) {
                triggerAutoWake(network, "onCapabilitiesChanged");
            }
        };

        try {
            connectivityManager.registerNetworkCallback(request, networkCallback);
        } catch (Throwable t) {
            t.printStackTrace();
        }
    }

    private void registerWifiReceiver() {
        try {
            wifiReceiver = new BroadcastReceiver() {
                @Override
                public void onReceive(Context context, Intent intent) {
                    triggerAutoWake(null, "BroadcastReceiver");
                }
            };
            IntentFilter filter = new IntentFilter();
            filter.addAction("android.net.wifi.STATE_CHANGE");
            filter.addAction("android.net.conn.CONNECTIVITY_CHANGE");
            registerReceiver(wifiReceiver, filter);
        } catch (Throwable t) {
            t.printStackTrace();
        }
    }

    private synchronized void triggerAutoWake(final Network network, final String source) {
        long now = System.currentTimeMillis();
        // Debounce: don't start multiple parallel workers within 8 seconds
        if (now - lastWakeWorkerTime < 8000) {
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
                        wl.acquire(25000);
                    }

                    WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    if (wm != null) {
                        wifiLock = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "AutoWake:ServiceWifiLock");
                        wifiLock.acquire();
                    }

                    SharedPreferences prefs = getSharedPreferences("wol_prefs", MODE_PRIVATE);
                    if (!prefs.getBoolean("auto_wake", false)) {
                        return;
                    }

                    String targetSsid = prefs.getString("target_ssid", "").trim();
                    String mac = prefs.getString("mac", "").trim();
                    String ip = prefs.getString("ip", "").trim();

                    if (mac.isEmpty()) {
                        String err = "⚠️ Ошибка: укажите MAC-адрес ПК в AutoWake!";
                        prefs.edit().putString("last_auto_wake", getTime() + " — " + err).apply();
                        return;
                    }

                    // Multi-wave transmission over 10 seconds to allow DHCP to settle
                    int[] delays = new int[]{800, 1500, 2000, 2500, 3000};
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
                                    String msg = "Чужой Wi-Fi (" + currentSsid + "): ПК не включаем";
                                    prefs.edit().putString("last_auto_wake", getTime() + " — " + msg).apply();
                                    return;
                                }
                                finalMatchedLabel = currentSsid;
                            } else {
                                // Background location blocked SSID reading: check subnet IP
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
                                finalMatchedLabel = "Домашний Wi-Fi";
                            }
                        } else {
                            if (!currentSsid.isEmpty()) finalMatchedLabel = currentSsid;
                        }

                        boolean ok = WolHelper.sendPacket(WolService.this, network, mac, ip, WolHelper.WOL_PORT);
                        if (ok) {
                            anySent = true;
                        }
                    }

                    String statusText;
                    if (anySent) {
                        statusText = "⚡ ПК включен (" + finalMatchedLabel + ") в " + getTime();
                    } else {
                        statusText = "⚠️ Сбой отправки сигнала на " + mac;
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
        if (wifiReceiver != null) {
            try {
                unregisterReceiver(wifiReceiver);
            } catch (Throwable ignored) {}
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
