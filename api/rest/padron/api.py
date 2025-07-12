from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Optional
from collections import deque
import asyncio

app = FastAPI()

DB_FOLDER = r"C:\Users\benja\Desktop\telegram-bot\main\api\rest\padron\database"
LOG_FILE = r"C:\Users\benja\Desktop\telegram-bot\main\api\rest\padron\logs\access.log"
APIKEYS_FILE = r"C:\Users\benja\Desktop\telegram-bot\main\api\rest\padron\auth\apikeys.json"
BLACKLIST_FILE = r"C:\Users\benja\Desktop\telegram-bot\main\api\rest\padron\blacklist\blacklist.json"

rate_limit_tracker = {}
MAX_REQUESTS = 30
INTERVAL_SECONDS = 60
COOLDOWN_SECONDS = 180
MAX_STRIKES = 5
PERMANENT_BLOCK = timedelta(hours=24)

def check_rate_limit(ip: str):
    now = datetime.now()
    tracker = rate_limit_tracker.setdefault(ip, {
        "requests": deque(),
        "blocked_until": None,
        "strike_count": 0
    })

    if tracker["blocked_until"]:
        if now < tracker["blocked_until"]:
            remaining = int((tracker["blocked_until"] - now).total_seconds())
            raise HTTPException(status_code=429, detail=f"Rate limit excedido. Intente nuevamente en {remaining} segundos.")
        else:
            tracker["blocked_until"] = None
            tracker["requests"].clear()

    while tracker["requests"] and (now - tracker["requests"][0]).total_seconds() > INTERVAL_SECONDS:
        tracker["requests"].popleft()

    tracker["requests"].append(now)

    if len(tracker["requests"]) > MAX_REQUESTS:
        tracker["strike_count"] += 1
        if tracker["strike_count"] >= MAX_STRIKES:
            tracker["blocked_until"] = now + PERMANENT_BLOCK
            raise HTTPException(status_code=429, detail="Demasiados abusos. Su IP fue bloqueada por 24 horas.")
        tracker["blocked_until"] = now + timedelta(seconds=COOLDOWN_SECONDS)
        raise HTTPException(status_code=429, detail="Rate limit excedido. Bloqueado temporalmente por 3 minutos.")

def extraer_primer_apellido(nombre_completo):
    return nombre_completo.split()[0].upper() if nombre_completo else ""

def registrar_log(ip: str, dato: str, cliente: str, apikey: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{now}] | IP: {ip} | Cliente: {cliente} | APIKEY: {apikey} | DATO: {dato}\n"
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

def esta_en_blacklist(dni: str) -> bool:
    if not os.path.exists(BLACKLIST_FILE):
        return False
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            blacklist = json.load(f)
        return dni in blacklist
    except:
        return False

def consulta_sqlite(ruta, query, params=()):
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    filas = cursor.fetchall()
    conn.close()
    return [dict(fila) for fila in filas]

# -------------------- Endpoint principal --------------------

@app.get("/back/api/v2/informe/dni/{dni}")
async def buscar_por_dni(dni: str, request: Request, apikey: str = Query(...)):
    ip = request.client.host

    # Check blacklist
    if esta_en_blacklist(dni):
        raise HTTPException(status_code=403, detail="Acceso denegado: DNI en blacklist.")

    check_rate_limit(ip)
    cliente = validar_apikey_query(apikey)
    registrar_log(ip, dni, cliente, apikey)

    persona_encontrada = []
    posibles_familiares = []

    # Consultar persona original
    for archivo in os.listdir(DB_FOLDER):
        if archivo.lower().endswith(".db"):
            ruta = os.path.join(DB_FOLDER, archivo)
            try:
                filas = await asyncio.get_event_loop().run_in_executor(
                    None,
                    consulta_sqlite,
                    ruta,
                    "SELECT * FROM personas WHERE dni = ?",
                    (dni,)
                )
                persona_encontrada.extend(filas)
            except Exception as e:
                print(f"Error en la DB {archivo}: {e}")

    if not persona_encontrada:
        raise HTTPException(status_code=404, detail="DNI no encontrado")

    persona = persona_encontrada[0]
    apellido = extraer_primer_apellido(persona.get("nombre_completo", ""))
    domicilio = persona.get("domicilio", "").strip().upper()

    # Consultar familiares
    for archivo in os.listdir(DB_FOLDER):
        if archivo.lower().endswith(".db"):
            ruta = os.path.join(DB_FOLDER, archivo)
            try:
                filas = await asyncio.get_event_loop().run_in_executor(
                    None,
                    consulta_sqlite,
                    ruta,
                    "SELECT * FROM personas WHERE domicilio = ?",
                    (domicilio,)
                )
                for fila_dict in filas:
                    if extraer_primer_apellido(fila_dict.get("nombre_completo", "")) == apellido and fila_dict["dni"] != dni:
                        posibles_familiares.append(fila_dict)
            except Exception as e:
                print(f"Error buscando familiares en {archivo}: {e}")

    persona["familiares"] = posibles_familiares

    return JSONResponse(content=persona)

@app.get("/back/api/v2/informe/tel/{telefono}")
async def buscar_por_telefono(telefono: str, request: Request, apikey: str = Query(...)):
    ip = request.client.host

    check_rate_limit(ip)
    cliente = validar_apikey_query(apikey)
    registrar_log(ip, f"TEL:{telefono}", cliente, apikey)

    persona_encontrada = []

    for archivo in os.listdir(DB_FOLDER):
        if archivo.lower().endswith(".db"):
            ruta = os.path.join(DB_FOLDER, archivo)
            try:
                filas = await asyncio.get_event_loop().run_in_executor(
                    None,
                    consulta_sqlite,
                    ruta,
                    "SELECT * FROM personas WHERE telefono = ? AND telefono IS NOT NULL",
                    (telefono,)
                )
                persona_encontrada.extend(filas)
            except Exception as e:
                print(f"Error en la DB {archivo}: {e}")

    if not persona_encontrada:
        raise HTTPException(status_code=404, detail="Teléfono no encontrado")

    # Devolvemos el primer resultado (igual que /dni)
    persona = persona_encontrada[0]
    return JSONResponse(content=persona)

@app.get("/back/api/v2/informe/domicilio/")
async def buscar_por_domicilio(domicilio: str = Query(...), request: Request = None, apikey: str = Query(...)):
    ip = request.client.host
    check_rate_limit(ip)
    cliente = validar_apikey_query(apikey)
    registrar_log(ip, f"DOM:{domicilio}", cliente, apikey)

    domicilio = domicilio.strip().upper().replace(" ", "")
    personas = []

    for archivo in os.listdir(DB_FOLDER):
        if archivo.endswith(".db"):
            ruta = os.path.join(DB_FOLDER, archivo)
            try:
                filas = await asyncio.get_event_loop().run_in_executor(
                    None, consulta_sqlite, ruta,
                    "SELECT * FROM personas WHERE REPLACE(REPLACE(domicilio, ' ', ''), '.', '') = ?",
                    (domicilio,)
                )
                personas.extend(filas)
            except Exception as e:
                print(f"Error en {archivo}: {e}")

    if not personas:
        raise HTTPException(status_code=404, detail="No se encontraron personas en ese domicilio")

    return JSONResponse(content={"domicilio": domicilio, "personas": personas})

@app.get("/back/api/v2/informe/nombre/{nombre_completo}")
async def buscar_por_nombre_exacto(nombre_completo: str, request: Request, apikey: str = Query(...)):
    ip = request.client.host

    check_rate_limit(ip)
    cliente = validar_apikey_query(apikey)
    registrar_log(ip, f"NOMBRE:{nombre_completo}", cliente, apikey)

    base_files = [f for f in os.listdir(DB_FOLDER) if f.lower().endswith(".db")]

    async def consultar_base(archivo):
        ruta = os.path.join(DB_FOLDER, archivo)
        try:
            filas = await asyncio.get_event_loop().run_in_executor(
                None,
                consulta_sqlite,
                ruta,
                "SELECT * FROM personas WHERE UPPER(nombre_completo) = ? LIMIT 10",
                (nombre_completo.upper(),)
            )
            return filas
        except Exception as e:
            print(f"Error en la DB {archivo}: {e}")
            return []

    resultados_por_base = await asyncio.gather(*(consultar_base(archivo) for archivo in base_files))

    personas = []
    for res in resultados_por_base:
        personas.extend(res)

    if not personas:
        raise HTTPException(status_code=404, detail="Nombre no encontrado")

    # Solo devolvemos la primer coincidencia para que sea rápido y consistente con /dni
    persona = personas[0]

    return JSONResponse(content=persona)

