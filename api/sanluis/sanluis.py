from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

USUARIO = "gabriel.dorato52@gmail.com"
CLAVE = "36580030"

def iniciar_sesion():
    session = requests.Session()
    login_url = "https://va.sanluis.gob.ar/Pages/Login"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://va.sanluis.gob.ar",
        "Referer": login_url
    }
    payload = {
        "user": USUARIO,
        "pwd": CLAVE,
        "ReturnUrl": ""
    }

    resp = session.post(login_url, data=payload, headers=headers)
    cookies = session.cookies.get_dict()
    if ".AspNet.ApplicationCookie" not in cookies:
        raise Exception("❌ No se pudo iniciar sesión.")

    return session

def parsear_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    resultado = {}

    def buscar_valor(texto):
        label = soup.find("label", string=lambda t: t and texto in t)
        if label:
            dt = label.find_parent("dt")
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    return dd.get_text(strip=True)
        return None

    # Datos personales y RENAPER
    resultado["apellido_nombre"] = buscar_valor("Apellido y Nombre")
    resultado["fecha_nacimiento"] = buscar_valor("Fecha de Nacimiento")
    resultado["domicilio"] = buscar_valor("Dirección")
    resultado["piso"] = buscar_valor("Piso")
    resultado["departamento"] = buscar_valor("Departamento")
    resultado["codigo_postal"] = buscar_valor("Código postal")
    resultado["barrio"] = buscar_valor("Barrio")
    resultado["localidad"] = buscar_valor("Ciudad")
    resultado["municipio"] = buscar_valor("Municipio")
    resultado["provincia"] = buscar_valor("Provincia")
    resultado["pais"] = buscar_valor("País")
    resultado["observacion"] = buscar_valor("Observación")
    resultado["fecha_fallecimiento"] = buscar_valor("Fecha de Fallecimiento")
    resultado["id_ciudadano"] = buscar_valor("Id de Ciudadano")

    # Fotos
    fotos = soup.select('#cipe img.img-thumbnail')
    if fotos and len(fotos) >= 2:
        resultado["foto_perfil"] = "https://va.sanluis.gob.ar" + fotos[0]["src"]
        resultado["foto_frente"] = "https://va.sanluis.gob.ar" + fotos[1]["src"]

    # Datos físicos
    fisicos = {
        "genero": "Genero",
        "nacionalidad": "Nacionalidad",
        "provincia_origen": "Provincia de origen",
        "localidad_origen": "Localidad de origen",
        "localidad_actual": "Localidad Actual",
        "cutiscolor": "Cutiscolor",
        "cabellocolor": "Cabellocolor",
        "barbacolor": "Barbacolor",
        "ojoscolor": "Ojoscolor",
        "frente": "Frente",
        "cejas": "Cejas",
        "parpados": "Parpados",
        "narizdorso": "Narizdorso",
        "narizbase": "Narizbase",
        "boca": "Boca",
        "labios": "Labios",
        "orejas": "Orejas",
    }

    for clave, etiqueta in fisicos.items():
        resultado[clave] = buscar_valor(etiqueta)

    # REBELDÍAS Y CAUSAS
    rebeldias = soup.find("div", {"id": "boddyREBELDIA"})
    if rebeldias:
        texto = rebeldias.get_text(strip=True)
        resultado["rebeldias_y_causas"] = texto if texto else "Sin información"

    # SIGGE
    sigge = soup.find("div", {"id": "boddyLEGAUTO"})
    if sigge:
        texto = sigge.get_text(strip=True)
        resultado["sigge"] = texto if texto else "Sin información"

    return resultado

def consultar_renaper_sanluis(dni, sexo):
    session = iniciar_sesion()
    consulta_url = "https://va.sanluis.gob.ar/BusquedaInteligente/Busqueda"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://va.sanluis.gob.ar",
        "Referer": "https://va.sanluis.gob.ar/Pages/Inicio",
        "X-Requested-With": "XMLHttpRequest"
    }
    payload = {
        "filtro": 1,
        "genero": sexo.upper(),
        "dni": dni,
        "texto": "",
        "X-Requested-With": "XMLHttpRequest"
    }

    resp = session.post(consulta_url, data=payload, headers=headers)
    resp.raise_for_status()
    html_text = resp.text

    return parsear_html(html_text)

@app.route("/sanluis/dni/<int:dni>/sexo/<sexo>", methods=["GET"])
def sanluis_endpoint(dni, sexo):
    if sexo.upper() not in ["M", "F"]:
        return jsonify({"error": "Sexo inválido. Usá M o F."}), 400
    try:
        datos = consultar_renaper_sanluis(dni, sexo)
        provincia = (datos.get("provincia") or "").lower()
        provincia_origen = (datos.get("provincia_origen") or "").lower()
        localidad = (datos.get("localidad_actual") or datos.get("localidad_origen") or "").lower()

        if (
            "san luis" not in provincia and
            "san luis" not in provincia_origen and
            "san luis" not in localidad
        ):
            return jsonify({"error": "No se encontraron datos para ese DNI y sexo."}), 404

        return jsonify(datos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5015)
