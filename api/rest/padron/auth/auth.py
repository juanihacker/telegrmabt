import uuid
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APIKEYS_FILE = os.path.join(BASE_DIR, "apikeys.json")

def cargar_apikeys():
    if not os.path.exists(APIKEYS_FILE):
        return {}
    with open(APIKEYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_apikeys(data):
    with open(APIKEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def generar_apikey():
    return uuid.uuid4().hex

def main():
    nombre = input("¿Qué nombre quieres asignar al cliente? ").strip()
    apikey = generar_apikey()
    data = cargar_apikeys()
    data[apikey] = nombre
    guardar_apikeys(data)
    print(f"Cliente '{nombre}' creado exitosamente.")
    print(f"API Key: {apikey}")

if __name__ == "__main__":
    main()
