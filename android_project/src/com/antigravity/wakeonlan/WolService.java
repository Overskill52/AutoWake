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
import android.os.Build;
import android.os.IBinder;

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
            public void onAvailable(Network network) {
                long now = System.currentTimeMillis();
                if (now - lastWakeTime > 30000) {
                    SharedPreferences prefs = getSharedPreferences("wol_prefs", MODE_PRIVATE);
                    String targetSsid = prefs.getString("target_ssid", "").trim();

                    if (!targetSsid.isEmpty()) {
                        String currentSsid = WolHelper.getCurrentWifiSsid(WolService.this);
                        if (!currentSsid.isEmpty() && !currentSsid.equalsIgnoreCase(targetSsid)) {
                            updateNotification("Чужой Wi-Fi (" + currentSsid + "): ПК не включаем");
                            return;
                        }
                    }

                    lastWakeTime = now;
                    triggerWake();
                }
            }
        };

        connectivityManager.registerNetworkCallback(request, networkCallback);
    }

    private void triggerWake() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    SharedPreferences prefs = getSharedPreferences("wol_prefs", MODE_PRIVATE);
                    String mac = prefs.getString("mac", WolHelper.DEFAULT_MAC);
                    String ip = prefs.getString("ip", "");
                    
                    boolean ok = WolHelper.sendPacket(WolService.this, mac, ip, WolHelper.WOL_PORT);
                    if (ok) {
                        String currentSsid = WolHelper.getCurrentWifiSsid(WolService.this);
                        String text = currentSsid.isEmpty() ? 
                                "Wi-Fi подключен: Сигнал на ПК отправлен!" :
                                "Домашний Wi-Fi (" + currentSsid + "): ПК включен!";
                        updateNotification(text);
                    }
                } catch (Throwable ignored) {}
            }
        }).start();
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
