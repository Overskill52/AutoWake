package com.antigravity.wakeonlan;

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
            sb.append("Wi-Fi: Не подключен / Имя скрыто\n");
        } else {
            sb.append("Wi-Fi: \"").append(currentSsid).append("\"\n");
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
                            prefs.edit().putLong("active_timer_end", targetTime).putString("active_timer_label", label).apply();
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
                            prefs.edit().remove("active_timer_end").remove("active_timer_label").apply();
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
