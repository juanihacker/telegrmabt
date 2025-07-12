from flask import Flask, request, jsonify
import threading
import time
import requests
import pyotp

# === Datos de login ===
EMAIL = "ivothewall96@gmail.com"
PASSWORD = "tOvxpZcIYuyUHSEOYcReHECi+ChmtnvAGLSdLT7sI6Q="
TOTP_SECRET = "5RC7M3TVKU7QF4EOICCUDMXYYH3OFP5R"

# === Flask App y Proxy ===
app = Flask(__name__)
app.config["JWT_TOKEN"] = ""
app.config["LAST_REFRESH"] = 0

PROXIES = {
    "http": "http://9KSjzc5XYm2fKdKF:0UYdEff1TeRrIaaF_country-ar@geo.iproyal.com:12321",
    "https": "http://9KSjzc5XYm2fKdKF:0UYdEff1TeRrIaaF_country-ar@geo.iproyal.com:12321"
}

# === Refrescador automático de JWT ===
def refresh_jwt():
    while True:
        try:
            print("🔄 Actualizando token JWT...")
            session = requests.Session()

            auth = session.post(
                "https://mi.minseg.gob.ar/api/token/auth/",
                json={"username": EMAIL, "password": PASSWORD},
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                proxies=PROXIES,
                timeout=30
            )
            if auth.status_code != 200:
                print("❌ Error login:", auth.text)
                time.sleep(60)
                continue

            token = auth.json().get("token")

            code = pyotp.TOTP(TOTP_SECRET).now()

            login = session.post(
                f"https://mi.minseg.gob.ar/api/api/totp/login/{code}/",
                json={},
                headers={
                    "Authorization": f"JWT {token}",
                    "Content-Type": "application/json",
                    "Origin": "https://mi.minseg.gob.ar",
                    "Referer": "https://mi.minseg.gob.ar/",
                    "User-Agent": "Mozilla/5.0",
                    "lat": "-34.795918",
                    "lon": "-58.207253"
                },
                proxies=PROXIES,
                timeout=30
            )

            if login.status_code == 201:
                app.config["JWT_TOKEN"] = login.json()["token"]
                app.config["LAST_REFRESH"] = time.time()
                print("✅ JWT actualizado:", app.config["JWT_TOKEN"][:40], "...")
            else:
                print("❌ Error login TOTP:", login.text)

        except Exception as e:
            print("⚠️ Excepción en refresh_jwt:", str(e))

        time.sleep(3600)

threading.Thread(target=refresh_jwt, daemon=True).start()

# === Consulta por DNI ===
@app.route('/interconsulta/dni/<dni>', methods=['GET', 'POST'])
def interconsulta_dni(dni):
    if not app.config["JWT_TOKEN"]:
        return jsonify({"error": "JWT no inicializado"}), 401

    url = "https://mi.minseg.gob.ar/api/servicios/interconsultas/"
    payload = {
        "parametro": dni,
        "entidad": "Personas",
        "lat": 0,
        "lon": 0,
        "renaper": True
    }

    headers = {
        "Authorization": f"JWT {app.config['JWT_TOKEN']}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mi.minseg.gob.ar",
        "Referer": "https://mi.minseg.gob.ar/siu/Personas",
        "lat": "0",
        "lon": "0"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, proxies=PROXIES, timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === NUEVO: Consulta DNRPA por patente ===
@app.route('/dnrpa/<patente>', methods=['GET'])
def dnrpa_patente(patente):
    if not app.config["JWT_TOKEN"]:
        return jsonify({"error": "JWT no inicializado"}), 401

    url = "https://mi.minseg.gob.ar/api/servicios/interconsultas/"
    payload = {
        "parametro": patente.upper(),
        "entidad": "Vehículos",
        "lat": -34.79602113545233,
        "lon": -58.207253,
        "renaper": True
    }

    headers = {
        "Authorization": f"JWT {app.config['JWT_TOKEN']}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mi.minseg.gob.ar",
        "Referer": "https://mi.minseg.gob.ar/siu/Vehiculos",
        "lat": "-34.79602113545233",
        "lon": "-58.207253"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, proxies=PROXIES, timeout=30)
        if r.status_code != 200:
            return jsonify({"error": "Error al consultar DNRPA", "status": r.status_code}), r.status_code

        data = r.json()

        # Filtrar y limpiar: eliminar campo "img"
        for service in data.get("services", []):
            if "X-GNA" in service and "img" in service["X-GNA"]:
                del service["X-GNA"]["img"]

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": f"Excepción: {str(e)}"}), 500

# === Iniciar app ===
if __name__ == '__main__':
    app.run(port=5011)
