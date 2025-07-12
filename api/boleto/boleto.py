import os
import json
import datetime
import shutil
import requests
from flask import Flask, request, jsonify
from pdf417gen import encode, render_image
from PIL import Image
from bs4 import BeautifulSoup
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import base64

CARPETA_DESTINO = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(CARPETA_DESTINO, exist_ok=True)

app = Flask(__name__)


logging.basicConfig(filename='consultas.log', level=logging.INFO, format='%(asctime)s - %(message)s')

@app.route('/backend/api/2/consultar', methods=['GET'])
def consultar():
    dni = request.args.get('dni', '')
    cuil = request.args.get('cuil', '')
    tipo_documento = request.args.get('tipo_documento', 'F')
    fecha_nacimiento = request.args.get('fecha_nacimiento', '')

    if not dni or not cuil or not fecha_nacimiento:
        return jsonify({"error": "Faltan parámetros"}), 400

    url = "https://boleto.gba.gob.ar/modulos/boleto/publico.php"
    payload = {
        "xjxfun": "validarAlumno",
        "xjxr": "1746817885036",
        "xjxargs[]": [
            "S1",
            f"S{dni}",
            f"S{cuil}",
            f"S{tipo_documento}",
            f"S<![CDATA[{fecha_nacimiento}]]>"
        ]
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(url, data=payload, headers=headers)

    match = re.search(r'publico_credencial\.php\?tra=[A-Z0-9]+', response.text)
    if not match:
        # ERROR: no encontró link al PDF, entonces no hay boleto para ese DNI
        return jsonify({"error": "No se encontró el boleto para ese DNI"}), 404

    enlace_pdf = f"https://boleto.gba.gob.ar/modulos/boleto/{match.group(0)}"

    pdf_response = requests.get(enlace_pdf)
    if pdf_response.status_code != 200:
        # ERROR: no pudo descargar el PDF
        return jsonify({"error": "Error al descargar el PDF"}), 500

    pdf_path = os.path.join(CARPETA_DESTINO, f"{dni}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_response.content)

    doc = fitz.open(pdf_path)
    page = doc[0]

    matriz = fitz.Matrix(3, 3)  
    pix = page.get_pixmap(matrix=matriz)

    img_path_temp = os.path.join(CARPETA_DESTINO, f"{dni}_temp.png")
    pix.save(img_path_temp)

    image = Image.open(img_path_temp)
    crop_box = (540, 165, 737, 402)  
    foto = image.crop(crop_box)

    buffered = BytesIO()
    foto.save(buffered, format="PNG")
    foto_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    doc.close()
    os.remove(img_path_temp)
    os.remove(pdf_path)

    log_data = {
        'ip': request.remote_addr,
        'hora': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dni': dni,
        'cuil': cuil,
        'tipo_documento': tipo_documento,
        'fecha_nacimiento': fecha_nacimiento,
        'response': foto_base64[:50]  
    }
    logging.info(f"Consulta realizada: {log_data}")

    return jsonify({
        "foto": foto_base64
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5020)
