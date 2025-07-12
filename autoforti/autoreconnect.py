import subprocess
import time
import os
import pyautogui
import requests

# Configuración VPN
pyautogui.FAILSAFE = False
CONTRASENA = "Av.270461"
CAMPO_CLAVE = (1014, 629)
BOTON_CONECTAR = (1032, 692)
CLICK_FINAL = (1012, 617)

# Telegram
TELEGRAM_TOKEN = "8007324418:AAHzOR6yKFCYULo9KY3xYSp9p38j0UtgFqA"
TELEGRAM_CHAT_ID = "-1002785901192"

def enviar_mensaje_telegram(mensaje: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"[!] Error al enviar a Telegram: {response.text}")
    except Exception as e:
        print(f"[!] Excepción al enviar mensaje Telegram: {e}")

# Función para hacer ping a sigehos.gcba.gob.ar
def vpn_activa(host="sigehos.gcba.gob.ar"):
    try:
        salida = subprocess.check_output(
            ["ping", "-n", "1", host],
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=3
        )
        return "TTL=" in salida
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

# Función para reconectar VPN
def conectar_vpn():
    print("\n[~] Abriendo FortiClient y conectando VPN...")
    enviar_mensaje_telegram("🔌 <b>VPN DESCONECTADA</b> — Intentando reconectar...")

    os.system('start "" "C:\\Program Files\\Fortinet\\FortiClient\\FortiClient.exe"')
    time.sleep(5)

    pyautogui.click(CAMPO_CLAVE)
    time.sleep(0.5)
    pyautogui.typewrite(CONTRASENA, interval=0.1)

    pyautogui.click(BOTON_CONECTAR)
    time.sleep(4)

    pyautogui.click(CLICK_FINAL)
    print("[✓] Reconexión completada.")
    enviar_mensaje_telegram("✅ <b>VPN reconectada exitosamente</b>.")

# Loop principal
print("🔄 Iniciando monitoreo VPN por ping...\n")
enviar_mensaje_telegram("📡 <b>Script de monitoreo VPN iniciado</b>.")

while True:
    if vpn_activa():
        print("✅ VPN activa. Ping exitoso.")
        time.sleep(10)
    else:
        print("⚠️ VPN caída. Intentando reconectar...")
        conectar_vpn()
        time.sleep(15)
