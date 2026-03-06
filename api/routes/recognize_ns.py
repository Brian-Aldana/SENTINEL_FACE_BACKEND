from flask_restx import Namespace, Resource, fields
from flask import request
from api.controllers.log_controller import recognize

ns = Namespace("recognize", description="Reconocimiento facial con liveness activo")

result_model = ns.model("RecognitionResult", {
    "status":     fields.String,
    "access":     fields.String,
    "person":     fields.String,
    "user_id":    fields.Integer,
    "confidence": fields.Float,
    "liveness":   fields.String,
    "message":    fields.String,
})


@ns.route("")
class Recognize(Resource):
    @ns.response(200, "Resultado del reconocimiento", result_model)
    @ns.response(400, "No se recibieron frames")
    def post(self):
        frame_bytes_list = []
        for key in sorted(request.files.keys()):
            if key.startswith("frame_"):
                frame_bytes_list.append(request.files[key].read())

        if not frame_bytes_list:
            ns.abort(400, "No se recibieron frames")

        try:
            result = recognize(frame_bytes_list)
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            ns.abort(500, str(e))