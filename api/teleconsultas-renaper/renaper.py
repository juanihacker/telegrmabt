# renaper_api.py
from flask import Flask, jsonify
import requests
import threading
import time

app = Flask(__name__)

token_data = {
    "token": None,
    "expires_at": 0  # timestamp UNIX
}

def actualizar_token():
    """Actualiza el token cada 3 horas con email y contraseña"""
    url = "https://teleconsulta.msal.gov.ar/api/getToken"
    payload = {
        "email": "pvaliente@gmail.com",
        "password": "7476Come"
    }

    while True:
        try:
            print("🔄 Actualizando token...")
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            token_data["token"] = data["token"]
            token_data["expires_at"] = time.time() + (3 * 60 * 60)
            print("✅ Token actualizado correctamente.")
        except Exception as e:
            print("❌ Error actualizando token:", e)
            if 'response' in locals():
                print("📄 Respuesta:", response.text)
        time.sleep(3 * 60 * 60)


@app.route("/renaper/3/dni/<int:dni>/sexo/<sexo>", methods=["GET"])
def consultar_renaper(dni, sexo):
    sexo = sexo.upper()
    if sexo not in ("M", "F"):
        return jsonify({"error": "Sexo inválido. Usá 'M' o 'F'."}), 400

    sexo_id = 110 if sexo == "M" else 111
    documento_id = 107  # DNI

    if not token_data["token"]:
        return jsonify({"error": "Token aún no cargado. Esperá unos segundos."}), 503

    headers = {
        "Authorization": f"Bearer {token_data['token']}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    params = {
        "documento_id": documento_id,
        "sexo_id": sexo_id,
        "nro_documento": dni
    }

    try:
        url = "https://teleconsulta.msal.gov.ar/api/pacientes/exists"
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e), "detalle": response.text if 'response' in locals() else "sin respuesta"}), 500

if __name__ == "__main__":
    # Iniciar thread que actualiza el token cada 3 horas
    threading.Thread(target=actualizar_token, daemon=True).start()
    app.run(port=5013)
