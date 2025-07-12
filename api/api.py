from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ----------------------------- RENAPER ----------------------------- #

def consultar_renaper_gap(dni, sexo):
    login_url = "https://gap.seguridadciudad.gob.ar/Gap/index.php"
    consulta_url = f"https://gap.seguridadciudad.gob.ar/Gap/index.php?modulo=Personas\\Search&accion=buscarPersCivil1&ajax=true&dni={dni}&sexo={sexo}"

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
    login_response = session.post(login_url, data=login_payload)
    if login_response.status_code != 200:
        return {"error": "Error al iniciar sesión"}

    consulta_response = session.get(consulta_url)
    if consulta_response.status_code != 200:
        return {"error": "Error al consultar el DNI"}

    try:
        data = consulta_response.json()
        if not isinstance(data, dict):
            return {"error": "Respuesta no estructurada"}

        if 'IdTramitePrincipal' in data:
            try:
                id_tramite = int(data['IdTramitePrincipal'])
                data['IdTramitePrincipal'] = f"{id_tramite:011d}"
            except:
                pass

        return data

    except Exception as e:
        return {"error": f"Error procesando la respuesta: {str(e)}"}


@app.route("/api/renaper")
def api_renaper():
    dni = request.args.get("dni")
    sexo = request.args.get("sexo", "").upper()

    if not dni or sexo not in ["M", "F"]:
        return jsonify({"error": "Parámetros inválidos. Usa ?dni=12345678&sexo=M"}), 400

    resultado = consultar_renaper_gap(dni, sexo)
    return jsonify(resultado)

# ----------------------------- DNRPA ----------------------------- #

def consultar_dnrpa(patente):
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
        "valor": patente,
        "servicio": "DNRPA"
    }

    consulta_response = session.post(consulta_url, data=consulta_payload)
    if consulta_response.status_code != 200:
        return {
            "Error": {"Success": False, "Text": "Error al consultar la patente"},
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
    dominio = request.args.get("dominio", "").upper()
    if not dominio:
        return jsonify({
            "Error": {"Success": False, "Text": "Parámetro faltante: dominio"},
            "Respuesta": {},
            "ok": "no"
        }), 400

    resultado = consultar_dnrpa(dominio)
    return jsonify(resultado)
# ----------------------------- MAIN ----------------------------- #

if __name__ == "__main__":
    app.run(debug=True)
