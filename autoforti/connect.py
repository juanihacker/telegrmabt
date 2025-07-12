import pyautogui
import time
import os

# Coordenadas y valores
CAMPO_CLAVE = (1014, 629)
BOTON_CONECTAR = (1032, 692)
CLICK_FINAL = (1012, 617)
CONTRASENA = "Aramis0921?"

# 1. Abrir FortiClient
print("[~] Abriendo FortiClient...")
os.system('start "" "C:\\Program Files\\Fortinet\\FortiClient\\FortiClient.exe"')

# 2. Esperar que cargue
time.sleep(6)  # Ajustar si tarda más en abrir

# 3. Click en el campo de contraseña y escribirla
print("[~] Escribiendo contraseña...")
pyautogui.click(CAMPO_CLAVE)
time.sleep(0.5)
pyautogui.typewrite(CONTRASENA, interval=0.1)

# 4. Click en el botón de conectar
print("[~] Haciendo clic en 'Conectar'...")
pyautogui.click(BOTON_CONECTAR)

# 5. Esperar conexión
time.sleep(4)

# 6. Click final (confirmación o cerrar)
print("[~] Haciendo clic final...")
pyautogui.click(CLICK_FINAL)

print("[✓] Proceso de conexión VPN completado.")
