package com.antigravity.wakeonlan;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.TransportInfo;
import android.net.wifi.WifiInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class WolService extends Service {
    private static final String CHANNEL_ID = "AutoWakeServiceChannel";
    private ConnectivityManager connectivityManager;
    private ConnectivityManager.NetworkCallback networkCallback;
    private long lastWakeTime = 0;

    @Override
    public void onCreate() {
        super.onCreate();
        try {
            createNotificationChannel();
            Notification notification = buildNotification("Служба активна: ждём подключение к Wi-Fi");
            if (Build.VERSION.SDK_INT >= 34) {
                startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
            } else {
                startForeground(1, notification);
            }
        } catch (Throwable t) {
            t.printStackTrace();
        }

        try {
            registerNetworkCallback();
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
                handleNetworkAvailable(network);
            }
        };

        connectivityManager.registerNetworkCallback(request, networkCallback);
    }

    private void handleNetworkAvailable(final Network network) {
        long now = System.currentTimeMillis();
        if (now - lastWakeTime < 10000) {
            return;
        }
        lastWakeTime = now;

        new Thread(new Runnable() {
            @Override
            public void run() {
                PowerManager.WakeLock wl = null;
                try {
                    PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
                    if (pm != null) {
                        wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AutoWake:ServiceWakeLock");
                        wl.acquire(15000);
                    }

                    // Settle time for DHCP and routing
                    try { Thread.sleep(600); } catch (InterruptedException ignored) {}

                    SharedPreferences prefs = getSharedPreferences("wol_prefs", MODE_PRIVATE);
                    String targetSsid = prefs.getString("target_ssid", "").trim();
                    String mac = prefs.getString("mac", "").trim();
                    String ip = prefs.getString("ip", "").trim();

                    if (mac.isEmpty()) {
                        String err = "⚠️ Ошибка: укажите MAC-адрес ПК в AutoWake!";
                        updateNotification(err);
                        prefs.edit().putString("last_auto_wake", getTime() + " — " + err).apply();
                        return;
                    }

                    String currentSsid = detectSsid(network);
                    if (!targetSsid.isEmpty()) {
                        if (!currentSsid.isEmpty() && !currentSsid.equalsIgnoreCase(targetSsid)) {
                            String msg = "Чужой Wi-Fi (" + currentSsid + "): ПК не включаем";
                            updateNotification(msg);
                            prefs.edit().putString("last_auto_wake", getTime() + " — " + msg).apply();
                            return;
                        }
                    }

                    updateNotification("⚡ Wi-Fi подключен: отправка сигнала на ПК...");

                    boolean ok = WolHelper.sendPacket(WolService.this, network, mac, ip, WolHelper.WOL_PORT);

                    try { Thread.sleep(1200); } catch (InterruptedException ignored) {}
                    WolHelper.sendPacket(WolService.this, network, mac, ip, WolHelper.WOL_PORT);

                    String netLabel = currentSsid.isEmpty() ? "Wi-Fi" : currentSsid;
                    String statusText;
                    if (ok) {
                        statusText = "⚡ ПК включен (" + netLabel + ") в " + getTime();
                    } else {
                        statusText = "⚠️ Сбой отправки сигнала на " + mac;
                    }

                    updateNotification(statusText);
                    prefs.edit().putString("last_auto_wake", statusText).apply();

                } catch (Throwable t) {
                    t.printStackTrace();
                } finally {
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

    private void updateNotification(String text) {
        try {
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.notify(1, buildNotification(text));
            }
        } catch (Throwable ignored) {}
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
        }

        return builder.setContentTitle("AutoWake PC")
                .setContentText(text)
                .setSmallIcon(R.drawable.ic_stat_wol)
                .setContentIntent(pendingIntent)
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel serviceChannel = new NotificationChannel(
                    CHANNEL_ID,
                    "AutoWake Service Channel",
                    NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(serviceChannel);
            }
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
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
