from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
import sqlite3
import os
import json
from datetime import datetime
from typing import Optional

app = FastAPI()

DB_FOLDER = r"C:\Users\cedu\Desktop\api\personas\database"
LOG_FILE = r"C:\Users\cedu\Desktop\api\personas\logs\access.log"
APIKEYS_FILE = r"C:\Users\cedu\Desktop\api\personas\auth\apikeys.json"

# -------------------- Utilidades --------------------

def extraer_primer_apellido(nombre_completo):
    return nombre_completo.split()[0].upper() if nombre_completo else ""

def registrar_log(ip: str, dni: str, cliente: str, apikey: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{now}] | IP: {ip} | Cliente: {cliente} | APIKEY: {apikey} | DNI: {dni}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linea)

def validar_apikey_query(apikey: Optional[str]) -> str:
    if not apikey:
        raise HTTPException(status_code=401, detail="API Key requerida en el parámetro 'apikey'.")

    if not os.path.exists(APIKEYS_FILE):
        raise HTTPException(status_code=500, detail="Base de claves no encontrada.")

    with open(APIKEYS_FILE, "r", encoding="utf-8") as f:
        apikeys = json.load(f)

    if apikey not in apikeys:
        raise HTTPException(status_code=403, detail="API Key inválida.")

    return apikeys[apikey]

# -------------------- Endpoint principal --------------------

@app.get("/back/api/v2/informe/dni/{dni}")
async def buscar_por_dni(dni: str, request: Request, apikey: str = Query(...)):
    cliente = validar_apikey_query(apikey)
    ip = request.client.host

    registrar_log(ip, dni, cliente, apikey)

    persona_encontrada = []
    posibles_familiares = []

    # Buscar persona original
    for archivo in os.listdir(DB_FOLDER):
        if archivo.lower().endswith(".db"):
            ruta = os.path.join(DB_FOLDER, archivo)
            try:
                conn = sqlite3.connect(ruta)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM personas WHERE dni = ?", (dni,))
                filas = cursor.fetchall()

                for fila in filas:
                    persona_encontrada.append(dict(fila))

                conn.close()
            except Exception as e:
                print(f"Error en la DB {archivo}: {e}")

    if not persona_encontrada:
        raise HTTPException(status_code=404, detail="DNI no encontrado")

    # Buscar familiares
    persona = persona_encontrada[0]
    apellido = extraer_primer_apellido(persona.get("nombre_completo", ""))
    domicilio = persona.get("domicilio", "").strip().upper()

    for archivo in os.listdir(DB_FOLDER):
        if archivo.lower().endswith(".db"):
            ruta = os.path.join(DB_FOLDER, archivo)
            try:
                conn = sqlite3.connect(ruta)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM personas WHERE domicilio = ?", (domicilio,))
                filas = cursor.fetchall()

                for fila in filas:
                    fila_dict = dict(fila)
                    if extraer_primer_apellido(fila_dict.get("nombre_completo", "")) == apellido and fila_dict["dni"] != dni:
                        posibles_familiares.append(fila_dict)

                conn.close()
            except Exception as e:
                print(f"Error buscando familiares en {archivo}: {e}")

    persona["familiares"] = posibles_familiares
    return JSONResponse(content=persona)
