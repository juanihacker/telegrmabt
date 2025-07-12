from flask import Blueprint
from services.efecty_service import consultar_persona
from utils.responses import success_response, error_response

persona_bp = Blueprint('persona', __name__)

@persona_bp.route('/persona/<cedula>', methods=['GET'])
def obtener_persona(cedula):
    try:
        data = consultar_persona(cedula)
        return success_response(data)
    except Exception as e:
        return error_response(str(e), 500)
