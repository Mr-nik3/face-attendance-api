from flask import Flask, request, jsonify
from deepface import DeepFace
import numpy as np
import cv2
import os

# 🔕 TensorFlow logs band
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

app = Flask(__name__)

@app.route('/match', methods=['POST'])
def match():

    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image"})

    file = request.files['image']

    # image read
    file_bytes = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    try:
        result = DeepFace.find(
            img_path=frame,
            db_path="faces",   # ⚠️ quotes zaroor
            detector_backend='opencv',
            enforce_detection=False,
            silent=True
        )

        if len(result) > 0 and len(result[0]) > 0:

            user_path = result[0].iloc[0]['identity']
            user_id = user_path.split("\\")[-1].split(".")[0]

            return jsonify({
                "status": "success",
                "user_id": user_id
            })

        return jsonify({"status": "no_match"})

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


if __name__ == "__main__":
    app.run(port=5000)