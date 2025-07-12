from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def consultar_dominio(dominio):
    url_login = "https://www.workmanagement.com.ar/valida_sie.asp"
    payload_login = {
        'mail': 'busqueda.personas.policiasgo@gmail.com',  # Cambiar si hace falta
        'clave': 'BUSQUEda1923',  # Cambiar si hace falta
    }

    with requests.Session() as session:
        response_login = session.post(url_login, data=payload_login)

        if not response_login.ok:
            return {"error": f'Login fallido (código de estado: {response_login.status_code})'}

        url_patente = "https://www.workmanagement.com.ar/consulta_autos_dominio1.asp"
        payload_patente = {
            "dominio": dominio
        }
        response_patente = session.post(url_patente, data=payload_patente)

        if not response_patente.ok:
            return {"error": f'Consulta de dominio fallida (código de estado: {response_patente.status_code})'}

        soup = BeautifulSoup(response_patente.content, 'html.parser')

        individuos = {}
        contenedores = soup.find_all('div', class_='contenido')
        if not contenedores:
            return {"error": "No se encontraron resultados para la patente."}

        for i, contenedor in enumerate(contenedores, start=1):
            try:
                # Extracción segura de cada campo con fallback "-"
                p_tags = contenedor.find_all('p')
                cuit_tag = contenedor.find('p', text=lambda x: x and 'CUIT:' in x)
                cuit = cuit_tag.text.replace('CUIT:', '').strip() if cuit_tag else "-"

                nombre = p_tags[1].text.strip() if len(p_tags) > 1 else "-"
                domicilio = p_tags[2].text.replace('Domicilio:', '').strip() if len(p_tags) > 2 else "-"
                localidad = p_tags[4].text.replace('Localidad:', '').strip() if len(p_tags) > 4 else "-"
                cp = p_tags[5].text.replace('CP:', '').strip() if len(p_tags) > 5 else "-"

                individuo = {
                    "cuit": cuit,
                    "nombre": nombre,
                    "domicilio": domicilio,
                    "localidad": localidad,
                    "cp": cp,
                }
                individuos[f'Individuo {i}'] = individuo
            except Exception as e:
                individuos[f'Individuo {i}'] = {"error": f"Error al parsear datos: {str(e)}"}

        return individuos

@app.route("/api/pat", methods=["GET"])
def api_buscar_por_patente():
    patente = request.args.get("patente")
    if not patente:
        return jsonify({"error": "Falta el parámetro 'patente'"}), 400

    resultado = consultar_dominio(patente)

    if "error" in resultado:
        return jsonify(resultado), 404

    return jsonify(resultado)

if __name__ == "__main__":
    app.run(port=5004)
