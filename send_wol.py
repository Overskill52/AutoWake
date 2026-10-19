import socket
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def send_wol(mac_str="AA:BB:CC:DD:EE:FF", broadcast_ip="255.255.255.255", port=9):
    mac_clean = mac_str.replace(":", "").replace("-", "")
    if len(mac_clean) != 12:
        print(f"Ошибка: Неверный MAC-адрес: {mac_str}")
        return False
    mac_bytes = bytes.fromhex(mac_clean)
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(magic_packet, (broadcast_ip, port))
    sock.close()
    print(f"[OK] Magic Packet отправлен на {broadcast_ip}:{port} для MAC {mac_str}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python send_wol.py <MAC> [Broadcast_IP] [Port]")
        print("Пример:        python send_wol.py 00:11:22:33:44:55 192.168.0.255 9")
        sys.exit(1)
    mac = sys.argv[1]
    ip = sys.argv[2] if len(sys.argv) > 2 else "255.255.255.255"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 9
    send_wol(mac, ip, port)
