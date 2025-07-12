from flask import Flask
from routes.persona import persona_bp

app = Flask(__name__)
app.config.from_object('config.Config')

app.register_blueprint(persona_bp, url_prefix='/api/v2')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)

