from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

MESES_ES = {
    1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"
}

MESES_EN = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"
}

def formatear_fecha(fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
        dia = fecha.day
        mes = fecha.month
        año = fecha.year
        mes_es = MESES_ES.get(mes, "???")
        mes_en = MESES_EN.get(mes, "???")
        return f"{dia:02d} {mes_es}/ {mes_en} {año}"
    except Exception:
        return fecha_str

@app.route('/formatear-fechas', methods=['POST'])
def formatear_fechas():
    data = request.get_json()
    fechas = data.get("fechas", [])
    formateadas = [formatear_fecha(f) for f in fechas]
    return jsonify({"formateadas": formateadas})

if __name__ == '__main__':
    app.run(port=5018)
