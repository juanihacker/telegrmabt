from flask import jsonify

def success_response(data, code=200):
    return jsonify({"status": "success", "data": data}), code

def error_response(message, code=400):
    return jsonify({"status": "error", "message": message}), code
