from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import re

app = Flask(__name__)

@app.route("/api/tel", methods=["GET"])
def buscar_por_telefono():
    telefono = request.args.get("telefono")
    if not telefono:
        return jsonify({"error": "Falta el parámetro 'telefono'"}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Cambiar a True para headless
            context = browser.new_context()
            page = context.new_page()

            # LOGIN
            page.goto("https://workmanagement.com.ar/inicio.html")
            page.fill('#mail', 'busqueda.personas.policiasgo@gmail.com')
            page.fill('#clave', 'BUSQUEda1923')
            page.click('button[type="submit"]')
            page.wait_for_timeout(3000)

            # CONSULTA
            page.goto("https://workmanagement.com.ar/consulta_celular_linea.asp")
            page.fill('input[name="linea"]', telefono)
            page.click('button[type="submit"]')

            # Esperamos que se redirija a la página final de resultados
            page.wait_for_url("**/Consulta_celulares_linea1.asp", timeout=7000)
            contenido = page.locator('div.contenido').inner_text()
            lineas = [line.strip() for line in contenido.split("\n") if line.strip()]

            resultado = {
                "documento": "-",
                "nombre": "-",
                "direccion": "-",
                "localidad": "-",
                "cp": "-"
            }

            for line in lineas:
                if line.startswith("Documento:"):
                    resultado["documento"] = line.replace("Documento:", "").strip()
                elif "Localidad:" in line:
                    resultado["localidad"] = line.replace("Localidad:", "").strip()
                elif "CP:" in line:
                    resultado["cp"] = line.replace("CP:", "").strip()
                elif resultado["direccion"] == "-" and any(x in line.lower() for x in ["av", "calle", "figueroa", "kr", "mz", "acuña"]):
                    resultado["direccion"] = line
                elif resultado["nombre"] == "-" and not any(x in line for x in ["Documento:", "Localidad:", "CP:"]):
                    resultado["nombre"] = line

            browser.close()
            return jsonify(resultado if resultado["documento"] != "-" else {"error": "No se encontraron resultados"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5003)
