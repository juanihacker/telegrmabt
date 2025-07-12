from flask import Flask, request, jsonify
import asyncio
import httpx
from urllib.parse import urljoin
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

async def ant_phpsessid():
    base_url = 'http://10.74.50.115/prueba/index.php'

    async with httpx.AsyncClient(follow_redirects=False) as client:
        # Paso 1: visitar página base para cookies
        response_get = await client.get(base_url)
        cookies = response_get.cookies

        headers = {
            'Host': '10.74.50.115',
            'Origin': 'http://10.74.50.115',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
            'Referer': base_url,
            'Connection': 'close'
        }

        # ⚠️ Payload correcto del login (según capturaste)
        login_payload = {
            "modulo": "login",
            "accion": "login",
            "componente": "true",
            "txtUsuario": "12958",
            "txtPassword": "Isaias54",
            "boton_enviar": "",
            "email": ""
        }

        # Paso 2: POST al login
        response_post = await client.post(base_url, headers=headers, data=login_payload, cookies=cookies)
        cookies.update(response_post.cookies)

        # Paso 3: Si redirecciona, seguir y capturar el PHPSESSID
        if response_post.status_code == 302:
            redirect_url = response_post.headers.get("location")
            if not redirect_url:
                return None

            from urllib.parse import urljoin
            full_redirect_url = urljoin(base_url, redirect_url)
            response_redirect = await client.get(full_redirect_url, headers=headers, cookies=cookies)
            cookies.update(response_redirect.cookies)

            phpsessid = cookies.get('PHPSESSID')
            return phpsessid
        else:
            return None


# Función para obtener antecedentes
async def obtener_antecedentes(dni: str):
    phpsessid = await ant_phpsessid()
    if not phpsessid:
        return {"error": "No se pudo iniciar sesión para obtener PHPSESSID"}

    query_url = (
        f"http://10.74.50.115/prueba/index.php?"
        f"modulo=Personas%5CSearch&accion=buscarInformeGAP&ajax=true"
        f"&sexo=M&documento={dni}&nacimiento=&apellido=&observacion=Tareas+de+Investigaci%C3%B3n+-+"
    )

    headers = {
        'Host': '10.74.50.115',
        'Cookie': f'PHPSESSID={phpsessid}',
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(query_url, headers=headers)
        if "No se encontraron coincidencias" in response.text:
            return {"error": "No se encontraron antecedentes"}

        try:
            return response.json()
        except Exception:
            return {"error": "Error al procesar la respuesta"}

# Ruta Flask
@app.route("/antecedentes", methods=["GET"])
def antecedentes():
    dni = request.args.get("dni")
    if not dni or not dni.isdigit():
        return jsonify({"error": "Parámetro 'dni' inválido o faltante"}), 400

    try:
        result = asyncio.run(obtener_antecedentes(dni))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

# Ejecutar servidor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5012)
