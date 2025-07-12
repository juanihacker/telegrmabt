from flask import Flask, request, jsonify
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import requests
import asyncio

app = Flask(__name__)

EMAIL = "cedubi764@gmail.com"
PASSWORD = "AkaEnfasis2023@"
BASE_URL = "https://pagosenlinea.pagofacil.com.ar/"


async def obtener_token_movistar():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        token_container = {"token": None}

        async def handle_request(request):
            if "/api/billers" in request.url:
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token_container["token"] = auth_header.split(" ")[1]
                    await browser.close()

        context.on("request", handle_request)

        try:
            await page.goto(BASE_URL, timeout=60000)
            await page.wait_for_selector('input[type="email"]', timeout=15000)
            await page.fill('input[type="email"]', EMAIL)
            await page.fill('input[type="password"]', PASSWORD)
            await page.click('button:has-text("Ingresar")')

            for _ in range(20):
                await asyncio.sleep(1)
                if token_container["token"]:
                    return token_container["token"]

        except PlaywrightTimeoutError:
            return None
        finally:
            await browser.close()

    return None


def consultar_movistar(token: str, numero: str):
    payload = {
        "recaptchaToken": "1234",
        "idBiller": 2168,
        "descripcionProducto": "Movistar",
        "origen": "PORTAL_WEB",
        "datosAdicionales": [
            {
                "ordinal": 1,
                "valor": numero,
                "descripcion": "Nro. de Celular"
            }
        ]
    }

    headers = {
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://pagosenlinea.pagofacil.com.ar",
        "user-agent": "Mozilla/5.0"
    }

    response = requests.post("https://pagosenlinea.pagofacil.com.ar/api/carrito/productos", headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Error {response.status_code}: No se pudo obtener la información."}


@app.route("/movistar", methods=["GET"])
def movistar_endpoint():
    numero = request.args.get("numero")
    if not numero:
        return jsonify({"error": "Número de celular requerido."}), 400

    try:
        token = asyncio.run(obtener_token_movistar())
        if not token:
            return jsonify({"error": "No se pudo obtener el token."}), 500

        resultado = consultar_movistar(token, numero)

        # Limpieza y formato de respuesta
        transacciones = resultado.get("transacciones") if isinstance(resultado, dict) else resultado[0].get("transacciones", [])
        if not transacciones:
            return jsonify({"error": "No se encontraron resultados para este número."}), 404

        opciones = transacciones[0].get("opciones", [])
        detalle = opciones[0].split(";")[-1] if opciones else "No disponible"

        return jsonify({
            "numero": numero,
            "producto": "Movistar",
            "detalle": detalle
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
