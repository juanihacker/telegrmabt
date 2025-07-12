import pyautogui
import time

print("➡️ Colocá el mouse sobre el botón 'Conectar' de FortiClient...")
time.sleep(3)

while True:
    x, y = pyautogui.position()
    print(f"Coordenadas actuales: ({x}, {y})", end="\r")
    time.sleep(0.1)
