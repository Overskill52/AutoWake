import socket
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def listen_wol(port=9, target_mac=None):
    target_clean = target_mac.replace(":", "").replace("-", "").upper() if target_mac else None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", port))
        print(f"[*] Прослушивание Wake-on-LAN пакетов на UDP порту {port}...")
        if target_clean:
            print(f"[*] Фильтр по целевому MAC: {target_mac}")
    except Exception as e:
        print(f"[-] Не удалось занять порт {port}: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            # Проверяем структуру Magic Packet: 6 байт 0xFF + 16 повторений MAC
            if len(data) >= 102 and data[:6] == b'\xff' * 6:
                mac_bytes = data[6:12]
                mac_str = ":".join(f"{b:02X}" for b in mac_bytes)
                is_match = (target_clean is None) or (mac_str.replace(":", "") == target_clean)
                
                status = ">>> СОВПАДЕНИЕ! Magic Packet получен! <<<" if is_match else f"(для другого MAC: {mac_str})"
                print(f"[+] Получен Magic Packet от {addr[0]}:{addr[1]} для MAC {mac_str} {status}")
            else:
                print(f"[?] Неизвестный пакет от {addr[0]}:{addr[1]} ({len(data)} байт)")
        except KeyboardInterrupt:
            print("\nОстановка...")
            break
        except Exception as e:
            print(f"Ошибка приёма: {e}")

if __name__ == "__main__":
    port = 9
    target = None
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            target = sys.argv[1]
    if len(sys.argv) > 2:
        target = sys.argv[2]
    listen_wol(port, target)
