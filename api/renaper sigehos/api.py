from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

LOGIN_URL = "https://sigehos.gcba.gob.ar/accounts/login/"
RENAPER_URL = "https://sigehos.gcba.gob.ar/sigehos/padron/api/v2/persona-renaper/"

USERNAME = "27273242886"
PASSWORD = "ceSac26@25"

def iniciar_sesion():
    session = requests.Session()

    # Obtener CSRF token
    response = session.get(LOGIN_URL, verify=False)
    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token = soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]

    # Preparar payload para login
    payload = {
        "csrfmiddlewaretoken": csrf_token,
        "username": USERNAME,
        "password": PASSWORD
    }

    # Headers con referer obligatorio para login correcto
    headers = {
        "Referer": LOGIN_URL
    }

    # Enviar POST para login
    login_response = session.post(LOGIN_URL, data=payload, headers=headers, verify=False, allow_redirects=False)

    # Verificar si login fue exitoso
    if login_response.status_code == 302:
        return session
    else:
        return None

@app.route('/api/renaper', methods=['GET'])
def consultar_renaper():
    dni = request.args.get('dni')
    sexo = request.args.get('sexo')

    if not dni or not sexo:
        return jsonify({"error": "Parámetros requeridos: dni y sexo"}), 400

    session = iniciar_sesion()

    if not session:
        return jsonify({"error": "Error al iniciar sesión"}), 500

    url = f"{RENAPER_URL}?nroDocumento={dni}&sexo={sexo}"
    response = session.get(url, verify=False)

    try:
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": "Error al parsear respuesta", "detalle": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5005, debug=True)
