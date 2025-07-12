from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ----------------------------- DNRPA ----------------------------- #

def consultar_dnrpa(motor):
    login_url = "https://gap.seguridadciudad.gob.ar/Gap/index.php"
    consulta_url = "https://gap.seguridadciudad.gob.ar/Gap/index.php?modulo=Objetos\\Search&accion=CargarImpedimento&ajax=true"

    login_payload = {
        "modulo": "login\\Search",
        "accion": "login",
        "ajax": "true",
        "txtUsuario": "12958",
        "txtPassword": "Isaias54",
        "boton_enviar": "",
        "email": ""
    }

    session = requests.Session()
    login_response = session.get(login_url, params=login_payload)
    if login_response.status_code != 200:
        return {
            "Error": {"Success": False, "Text": "Error al iniciar sesión"},
            "Respuesta": {},
            "ok": "no"
        }

    consulta_payload = {
        "modulo": "Objetos\\Search",
        "accion": "CargarImpedimento",
        "ajax": "true",
        "tipo": "DNRPA",
        "parte": "1",
        "valor": motor,           # Cambio aquí: ahora uso chasis
        "servicio": "DNRPA"
    }

    consulta_response = session.post(consulta_url, data=consulta_payload)
    if consulta_response.status_code != 200:
        return {
            "Error": {"Success": False, "Text": "Error al consultar el chasis"},
            "Respuesta": {},
            "ok": "no"
        }

    try:
        data = consulta_response.json()
    except Exception:
        return {
            "Error": {"Success": False, "Text": "Respuesta inválida del servidor"},
            "Respuesta": {},
            "ok": "no"
        }

    try:
        respuesta = data.get("Respuesta", {})
        return {
            "Error": {
                "Success": True,
                "Text": ""
            },
            "Respuesta": respuesta,
            "ok": "si"
        }
    except Exception as e:
        return {
            "Error": {"Success": False, "Text": f"Error al extraer datos: {str(e)}"},
            "Respuesta": {},
            "ok": "no"
        }


@app.route("/api/dnrpa")
def api_dnrpa():
    chasis = request.args.get("chasis", "").upper()  # Cambio aquí: parámetro chasis
    if not chasis:
        return jsonify({
            "Error": {"Success": False, "Text": "Parámetro faltante: chasis"},
            "Respuesta": {},
            "ok": "no"
        }), 400

    resultado = consultar_dnrpa(chasis)
    return jsonify(resultado)

# ----------------------------- MAIN ----------------------------- #

if __name__ == "__main__":
    app.run(debug=True, port=5019)  # Cambio aquí: puerto 5019
