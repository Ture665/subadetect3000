import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle
import socket
import threading
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENCODINGS_FILE = BASE_DIR / "encodings.pickle"

print("[INFO] loading encodings...")
with open(ENCODINGS_FILE, "rb") as f:
    data = pickle.loads(f.read())

known_face_encodings = data["encodings"]
known_face_names = data["names"]


clients = []
clients_lock = threading.Lock()

latest_jpeg = None
latest_frame_lock = threading.Lock()

camera_running = False
camera_status = "Starting"
latest_fps = 0
latest_detection = "None"
detections_today = 0


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("", 5000))
server.listen(5)


def accept_clients():
    while True:
        client, address = server.accept()
        print(f"Client connected: {address}")

        with clients_lock:
            clients.append(client)


def broadcast(message):
    dead_clients = []

    with clients_lock:
        for client in clients:
            try:
                client.sendall((message + "\n").encode("utf-8"))
            except Exception:
                dead_clients.append(client)

        for client in dead_clients:
            print("Removing disconnected client")
            clients.remove(client)

            try:
                client.close()
            except Exception:
                pass


threading.Thread(target=accept_clients, daemon=True).start()


cv_scaler = 4

face_locations = []
face_encodings = []
face_names = []

frame_count = 0
start_time = time.time()
fps = 0

last_sent_name = ""
last_sent_time = 0
cooldown_seconds = 5


def process_frame(frame):
    global face_locations, face_encodings, face_names
    global last_sent_name, last_sent_time, latest_detection, detections_today

    resized_frame = cv2.resize(
        frame,
        (0, 0),
        fx=(1 / cv_scaler),
        fy=(1 / cv_scaler)
    )

    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(
        rgb_resized_frame,
        face_locations,
        model="small"
    )

    face_names = []

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(
            known_face_encodings,
            face_encoding
        )

        name = "Unknown"

        face_distances = face_recognition.face_distance(
            known_face_encodings,
            face_encoding
        )

        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index]:
                name = known_face_names[best_match_index]
                latest_detection = name

                # print("Recognized:", name)

                current_time = time.time()

                if (
                    name != last_sent_name
                    or current_time - last_sent_time > cooldown_seconds
                ):
                    event = {
                        "type": "face_detected",
                        "name": name,
                        "action": "suba_detected" if name == "suba" else "none",
                        "timestamp": time.time(),
                        "distance": float(face_distances[best_match_index])
                    }

                    broadcast(json.dumps(event))
                    detections_today += 1
                    # print("Sent event:", event)

                    last_sent_name = name
                    last_sent_time = current_time

        face_names.append(name)

    return frame


def draw_results(frame):
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler

        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)

        cv2.rectangle(
            frame,
            (left - 3, top - 35),
            (right + 3, top),
            (244, 42, 3),
            cv2.FILLED
        )

        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(
            frame,
            name,
            (left + 6, top - 6),
            font,
            1.0,
            (255, 255, 255),
            1
        )

    return frame


def calculate_fps():
    global frame_count, start_time, fps, latest_fps

    frame_count += 1
    elapsed_time = time.time() - start_time

    if elapsed_time > 1:
        fps = frame_count / elapsed_time
        latest_fps = round(fps, 1)
        frame_count = 0
        start_time = time.time()

    return fps


def start_camera_service():
    global latest_jpeg, camera_running, camera_status

    if camera_running:
        return

    camera_running = True
    camera_status = "Starting"

    print("[INFO] Starting camera service...")

    picam2 = Picamera2()
    picam2.configure(
        picam2.create_preview_configuration(
            main={"format": "XRGB8888", "size": (640, 480)}
        )
    )
    picam2.start()

    camera_status = "ONLINE"

    while True:
        frame = picam2.capture_array()

        processed_frame = process_frame(frame)
        display_frame = draw_results(processed_frame)

        current_fps = calculate_fps()

        cv2.putText(
            display_frame,
            f"FPS: {current_fps:.1f}",
            (display_frame.shape[1] - 150, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        success, buffer = cv2.imencode(".jpg", display_frame)

        if success:
            with latest_frame_lock:
                latest_jpeg = buffer.tobytes()

        time.sleep(0.03)


def generate_video_frames():
    while True:
        with latest_frame_lock:
            frame = latest_jpeg

        if frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame +
                b"\r\n"
            )

        time.sleep(0.03)


def get_camera_status():
    return {
        "status": camera_status,
        "fps": latest_fps,
        "latest_detection": latest_detection,
        "connected_clients": len(clients)
        "detections_today": detections_today
    }