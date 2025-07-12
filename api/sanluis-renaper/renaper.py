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
        "Referer": login_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    payload = {
        "user": USUARIO,
        "pwd": CLAVE,
        "ReturnUrl": ""
    }

    resp = session.post(login_url, data=payload, headers=headers)
    cookies = session.cookies.get_dict()
    if ".AspNet.ApplicationCookie" not in cookies:
        raise Exception("❌ No se pudo iniciar sesión, cookie de sesión no encontrada.")

    return session

def parsear_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    resultado = {}

    # Función auxiliar para buscar valor por texto en <label> dentro de <dt>
    def obtener_valor_por_label(texto_label):
        label = soup.find("label", string=lambda t: t and texto_label in t)
        if label:
            dt = label.find_parent("dt")
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    return dd.get_text(strip=True)
        return None

    campos = [
        ("apellido_nombre", "Apellido y Nombre"),
        ("fecha_nacimiento", "Fecha de Nacimiento"),
        ("domicilio", "Dirección"),
        ("piso", "Piso"),
        ("departamento", "Departamento"),
        ("codigo_postal", "Código postal"),
        ("barrio", "Barrio"),
        ("localidad", "Ciudad"),
        ("municipio", "Municipio"),
        ("provincia", "Provincia"),
        ("pais", "País"),
        ("observacion", "Observación"),
        ("fecha_fallecimiento", "Fecha de Fallecimiento"),
        ("id_ciudadano", "Id de Ciudadano"),
    ]

    for clave, texto in campos:
        valor = obtener_valor_por_label(texto)
        if valor:
            resultado[clave] = valor

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
    datos = parsear_html(html_text)

    return datos

@app.route("/renaper/4/dni/<int:dni>/sexo/<sexo>", methods=["GET"])
def renaper4_endpoint(dni, sexo):
    if sexo.upper() not in ["M", "F"]:
        return jsonify({"error": "Sexo inválido. Usá M o F."}), 400
    try:
        datos = consultar_renaper_sanluis(dni, sexo)
        if not datos:
            return jsonify({"error": "No se encontraron datos para ese DNI y sexo."}), 404
        return jsonify(datos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5014)
