package com.antigravity.wakeonlan;

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
            String[] parts = ipStr.trim().split("\\.");
            if (parts.length == 4) {
                return parts[0] + "." + parts[1] + "." + parts[2] + ".255";
            }
        } catch (Exception ignored) {}
        return null;
    }

    public static boolean isSameSubnet(String ip1, String ip2) {
        try {
            if (ip1 == null || ip2 == null) return false;
            String[] p1 = ip1.trim().split("\\.");
            String[] p2 = ip2.trim().split("\\.");
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
        if (ssid.startsWith("\"") && ssid.endsWith("\"") && ssid.length() >= 2) {
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
            String cleanMac = macStr.replaceAll("[:\\-]", "").trim();
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
