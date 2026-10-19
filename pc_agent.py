import socket
import os
import sys
import subprocess
import datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pc_agent.log")

def log(text):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{now}] {text}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass
    try:
        print(msg, end="", flush=True)
    except Exception:
        pass

PORT = 9876

def run_agent():
    log("==========================================")
    log(f"PC Agent запускается на UDP порту {PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", PORT))
        log(f"УСПЕШНО: сокет слушает 0.0.0.0:{PORT}")
    except Exception as e:
        log(f"ОШИБКА: Не удалось занять порт {PORT}: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            cmd = data.decode('utf-8', errors='ignore').strip()
            log(f"ПОЛУЧЕН ПАКЕТ: '{cmd}' от {addr[0]}:{addr[1]}")

            if cmd == "PING":
                sock.sendto(b"PONG", addr)
                log(f"ОТВЕТИЛИ: 'PONG' на {addr[0]}:{addr[1]}")

            elif cmd == "SHUTDOWN":
                sock.sendto(b"OK_SHUTDOWN", addr)
                log("КОМАНДА: Завершение работы Windows через 2 сек...")
                subprocess.run(["shutdown", "/s", "/t", "2"], shell=True)

            elif cmd == "RESTART":
                sock.sendto(b"OK_RESTART", addr)
                log("КОМАНДА: Перезагрузка Windows через 2 сек...")
                subprocess.run(["shutdown", "/r", "/t", "2"], shell=True)

            elif cmd == "SLEEP":
                sock.sendto(b"OK_SLEEP", addr)
                log("КОМАНДА: Переход в спящий режим...")
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)

        except Exception as e:
            log(f"Ошибка в цикле: {e}")

if __name__ == "__main__":
    run_agent()
