import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "access.log")

def ver_logs_de_cliente(nombre_cliente):
    if not os.path.exists(LOG_FILE):
        print("No hay logs aún.")
        return

    encontrados = False
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for linea in f:
            if f"Cliente: {nombre_cliente}" in linea:
                print(linea.strip())
                encontrados = True

    if not encontrados:
        print(f"No se encontraron logs para el cliente: {nombre_cliente}")

if __name__ == "__main__":
    nombre = input("Nombre del cliente a consultar logs: ").strip()
    ver_logs_de_cliente(nombre)
