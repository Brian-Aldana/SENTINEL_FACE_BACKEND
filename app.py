import os
import re
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from face_logic import FaceRecognitionSystem
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

face_system = FaceRecognitionSystem()

def sanitize_string(text):
    return re.sub(r'[^a-zA-Z0-9\sáéíóúÁÉÍÓÚñÑ]', '', text).strip()

@app.route('/api/log_image/<int:log_id>', methods=['GET'])
def get_log_image(log_id):
    image_binary = face_system.get_log_image(log_id)
    if image_binary:
        return Response(image_binary, mimetype='image/jpeg')
    return jsonify({"status": "error", "message": "Imagen no encontrada"}), 404

@app.route('/api/register', methods=['POST'])
def register():
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({"success": False, "message": "Datos incompletos"}), 400
        
    file = request.files['image']
    raw_name = request.form['name']
    
    clean_name = sanitize_string(raw_name)
    if not clean_name:
         return jsonify({"success": False, "message": "El nombre contiene caracteres inválidos"}), 400
    
    success, message = face_system.register_face(file.read(), clean_name)
    return jsonify({"success": success, "message": message})

@app.route('/api/recognize', methods=['POST'])
def recognize():
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No imagen enviada"}), 400
        
    file = request.files['image']
    result = face_system.recognize_face(file.read())
    return jsonify(result)

@app.route('/api/logs', methods=['GET'])
def get_logs():
    logs = face_system.get_all_logs()
    return jsonify({"status": "success", "data": logs})

@app.route('/api/users', methods=['GET'])
def get_users():
    result = face_system.get_all_users_for_api()
    return jsonify(result)

if __name__ == '__main__':
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=is_debug, host='0.0.0.0', port=5000)