import pyautogui
import time

print("👉 Colocá el mouse sobre una esquina del área de notificación (ej: arriba izquierda)")
print("Presioná Ctrl + C para salir\n")

try:
    while True:
        x, y = pyautogui.position()
        print(f"Coordenadas actuales: X={x} | Y={y}", end="\r")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nListo.")
