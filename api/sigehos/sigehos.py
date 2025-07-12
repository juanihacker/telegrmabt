from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

LOGIN_URL = "https://sigehos.gcba.gob.ar/accounts/login/"
RENAPER_URL = "https://sigehos.gcba.gob.ar/sigehos/padron/api/v2/persona-renaper/"
CANDIDATOS_URL = "https://sigehos.gcba.gob.ar/sigehos/padron/api/v2/pacientes/candidatos/"

USERNAME = "27273242886"
PASSWORD = "ceSac26@25"

def iniciar_sesion():
    session = requests.Session()
    response = session.get(LOGIN_URL, verify=False)
    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token = soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]

    payload = {
        "csrfmiddlewaretoken": csrf_token,
        "username": USERNAME,
        "password": PASSWORD
    }

    headers = {
        "Referer": LOGIN_URL
    }

    login_response = session.post(LOGIN_URL, data=payload, headers=headers, verify=False, allow_redirects=False)
    if login_response.status_code == 302:
        return session
    else:
        return None

@app.route('/api/renaper-candidato', methods=['GET'])
def renaper_y_candidato():
    dni = request.args.get('dni')
    sexo = request.args.get('sexo')

    if not dni or not sexo:
        return jsonify({"error": "Parámetros requeridos: dni y sexo"}), 400

    session = iniciar_sesion()
    if not session:
        return jsonify({"error": "Error al iniciar sesión"}), 500

    # Primera consulta a RENAPER
    renaper_response = session.get(f"{RENAPER_URL}?nroDocumento={dni}&sexo={sexo}", verify=False)
    if renaper_response.status_code != 200:
        return jsonify({"error": "Error en consulta RENAPER"}), 500

    try:
        renaper_data = renaper_response.json()
    except Exception as e:
        return jsonify({"error": "Error al parsear respuesta RENAPER", "detalle": str(e)}), 500

    # Datos necesarios
    try:
        apellido = renaper_data["apellido"]
        primer_nombre = renaper_data["nombres"].split()[0]
        otros_nombres = " ".join(renaper_data["nombres"].split()[1:])
        fecha_nac = renaper_data["fechaNacimiento"]
        nro_documento = renaper_data["numeroDocumento"]
    except KeyError as e:
        return jsonify({"error": f"Falta campo esperado: {e}"}), 500

    # Construir URL de candidatos
    params = {
        "acredita_identidad": "true",
        "apellido": apellido,
        "efector_id": "55",
        "fecha_nac": fecha_nac,
        "nro_documento": nro_documento,
        "otros_apellidos": "",
        "otros_nombres": otros_nombres,
        "pertenencia_documento": "PRO",
        "primer_nombre": primer_nombre,
        "sexo": sexo.upper(),
        "tipo_documento": "http://sigehos.gcba.gob.ar/sigehos/common/api/v2/tipo-documento/1/"
    }

    candidatos_response = session.get(CANDIDATOS_URL, params=params, verify=False)
    if candidatos_response.status_code != 200:
        return jsonify({"error": "Error en consulta candidatos"}), 500

    try:
        return jsonify(candidatos_response.json())
    except Exception as e:
        return jsonify({"error": "Error al parsear respuesta candidatos", "detalle": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5010, debug=True)
