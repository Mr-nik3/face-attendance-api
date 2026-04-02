from flask import Flask, request, jsonify
from flask_cors import CORS
from deepface import DeepFace
import cv2
import numpy as np
import base64
import os
import requests
import tempfile

app = Flask(__name__)
CORS(app)

# ✅ Haar Cascade for liveness
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# ✅ Faces folder path (same directory mein faces/ folder hona chahiye)
# FACES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faces")
#FACES_DIR = "http://localhost/attendance_system/application/libraries/uploads/customer_photo/"
# FACES_DIR = "C:/wamp645/www/attendance_system/application/libraries/uploads/customer_photo/"BASE_URL
FACES_DIR = "BASE_URL"


# =============================================================
# 🔥 HELPER — base64 string to OpenCV image
# =============================================================
def decode_base64_image(base64_string):
    # Handle both with and without data:image/jpeg;base64, prefix
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    img_bytes = base64.b64decode(base64_string)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


# =============================================================
# 🔥 ROUTE 1 — /liveness (port 5000 pe)
# Frontend se 5 frames aate hain base64 mein
# Movement detect karke live/spoof decide karta hai
# =============================================================
@app.route('/liveness', methods=['POST'])
def liveness():
    try:
        data = request.json

        if not data or 'frames' not in data:
            return jsonify({"status": "error", "message": "No frames received"})

        frames = data['frames']

        if len(frames) < 2:
            return jsonify({"status": "error", "message": "At least 2 frames required"})

        positions = []
        sizes = []

        for f in frames:
            img = decode_base64_image(f)
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=6)

            if len(faces) == 0:
                return jsonify({"status": "no_face", "message": "No face detected in frame"})

            (x, y, w, h) = faces[0]
            cx = x + w // 2
            cy = y + h // 2

            positions.append((cx, cy))
            sizes.append(w * h)

        if len(positions) < 2:
            return jsonify({"status": "no_face", "message": "Face not detected consistently"})

        # 🔥 Movement + size change calculate
        movements = []
        size_changes = []

        for i in range(1, len(positions)):
            dx = abs(positions[i][0] - positions[i-1][0])
            dy = abs(positions[i][1] - positions[i-1][1])
            movements.append(dx + dy)
            size_changes.append(abs(sizes[i] - sizes[i-1]))

        total_movement = sum(movements)
        max_single_movement = max(movements) if movements else 0
        total_size_change = sum(size_changes)

        print(f"[LIVENESS] Total Movement: {total_movement} | Max Single: {max_single_movement} | Size Change: {total_size_change}")

        # 🔥 Strict threshold:
        # Real face = consistent movement across frames (max_single > 15)
        # Photo = near-zero movement (artifacts < 5 per frame)
        # Size change > 800 = person moved closer/farther (real)
        if max_single_movement > 15 or total_size_change > 800:
            return jsonify({"status": "live"})
        else:
            return jsonify({"status": "spoof", "message": "No real movement detected — photo spoofing suspected"})

    except Exception as e:
        print(f"[LIVENESS ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)})


# =============================================================
# 🔥 ROUTE 2 — /match
# CI3 PHP se image file aati hai (multipart/form-data)
# DeepFace se faces/ folder mein match karta hai
# filename = student_id (e.g. 1.jpg -> user_id = "1")
# =============================================================
# @app.route('/match', methods=['POST'])
# def match():
#     try:
#         if 'image' not in request.files:
#             return jsonify({"status": "error", "message": "No image file received"})

#         file = request.files['image']
#         file_bytes = np.frombuffer(file.read(), np.uint8)
#         frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

#         if frame is None:
#             return jsonify({"status": "error", "message": "Invalid image"})

#         if not os.path.exists(FACES_DIR):
#             return jsonify({"status": "error", "message": f"Faces folder not found: {FACES_DIR}"})

#         # 🔥 DeepFace match
#         result = DeepFace.find(
#             img_path=frame,
#             db_path=FACES_DIR,
#             enforce_detection=False,
#             silent=True
#         )

#         if len(result) > 0 and len(result[0]) > 0:
#             user_path = result[0].iloc[0]['identity']

#             # ✅ Cross-platform path fix (Windows \ aur Linux / dono handle)
#             filename = os.path.basename(user_path)        # "1.jpg"
#             user_id = os.path.splitext(filename)[0]       # "1"

#             print(f"[MATCH] Matched user_id: {user_id}")

#             return jsonify({
#                 "status": "success",
#                 "user_id": user_id
#             })

#         return jsonify({"status": "no_match", "message": "Face not matched"})

#     except Exception as e:
#         print(f"[MATCH ERROR] {e}")
#         return jsonify({"status": "error", "message": str(e)})






@app.route('/match', methods=['POST'])
def match():
    try:
        if 'image' not in request.files:
            return jsonify({"status": "error", "message": "No image file received"})

        file = request.files['image']
        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"status": "error", "message": "Invalid image"})

        # 🔥 temp input image
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        cv2.imwrite(temp_input.name, frame)

        # 🔥 API se users list lo
        API_URL = "https://technoearthinnovations.com/attendance_system/index.php/api/get_faces"
        BASE_URL = "https://technoearthinnovations.com/attendance_system/application/libraries/uploads/customer_photo/"

        res = requests.get(API_URL)
        users = res.json()

        for user in users:
            image_url = BASE_URL + user

            try:
                response = requests.get(image_url, timeout=3)
                if response.status_code != 200:
                    continue

                temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                temp_db.write(response.content)
                temp_db.close()

                result = DeepFace.verify(
                    img1_path=temp_input.name,
                    img2_path=temp_db.name,
                    enforce_detection=False
                )

                # cleanup db image
                os.remove(temp_db.name)

                if result["verified"]:
                    user_id = user.split(".")[0]

                    os.remove(temp_input.name)

                    return jsonify({
                        "status": "success",
                        "user_id": user_id
                    })

            except:
                continue

        os.remove(temp_input.name)

        return jsonify({"status": "no_match"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
# =============================================================
# 🔥 ROUTE 3 — /health (test karne ke liye)
# Browser mein http://127.0.0.1:5000/health kholo
# =============================================================


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "api_url": "https://technoearthinnovations.com/attendance_system/index.php/api/get_faces"
    })


if __name__ == "__main__":
    API_URL = "https://technoearthinnovations.com/attendance_system/index.php/api/get_faces"
    BASE_URL = "https://technoearthinnovations.com/attendance_system/application/libraries/uploads/customer_photo/"

    print(f"[INFO] Faces API: {API_URL}")
    print(f"[INFO] Base Image URL: {BASE_URL}")

    try:
        res = requests.get(API_URL, timeout=3)
        if res.status_code == 200:
            print("[INFO] API working ✅")
            print(f"[INFO] Total faces: {len(res.json())}")
        else:
            print("[ERROR] API not responding ❌")
    except Exception as e:
        print(f"[ERROR] API connection failed: {e}")

    app.run(host="0.0.0.0", port=5000, debug=True)
