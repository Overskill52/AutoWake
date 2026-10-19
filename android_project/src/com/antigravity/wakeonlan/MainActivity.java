package com.antigravity.wakeonlan;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.CompoundButton;
import android.widget.EditText;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;
import java.util.List;

public class MainActivity extends Activity {
    private EditText etMac, etSsid, etIp;
    private TextView tvStatus, tvNetworkInfo, tvPcStatus;
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

        refreshNetworkInfo();
        checkPcOnline();

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
                Toast.makeText(MainActivity.this, "Настройки сохранены!", Toast.LENGTH_SHORT).show();
            }
        });

        swAutoWake.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
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
}
