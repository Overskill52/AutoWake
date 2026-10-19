package com.antigravity.wakeonlan;

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
