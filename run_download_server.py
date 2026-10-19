import http.server
import socketserver
import os
import sys
import socket
import qrcode

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PORT = 8000

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

ip = get_local_ip()
URL = f"http://{ip}:{PORT}"

os.chdir(os.path.dirname(os.path.abspath(__file__)))

qr = qrcode.QRCode()
qr.add_data(URL)
qr.make()

print("\n" + "=" * 55)
print("     СКАЧАТЬ ПРИЛОЖЕНИЕ AUTOWAKE НА ТЕЛЕФОН")
print("=" * 55)
print(f"\n1. Наведи камеру телефона на этот QR-код:\n")
qr.print_ascii(invert=True)
print(f"\nИЛИ введи в браузере телефона адрес:")
print(f"👉  {URL}  👈\n")
print("=" * 55)
print("Сервер запущен. Нажми Ctrl+C, когда скачаешь.\n")

socketserver.TCPServer.allow_reuse_address = True
Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
