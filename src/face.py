import json
import logging

import cv2
import face_recognition
import numpy as np

logger = logging.getLogger(__name__)

known_encodings = []
known_names = []


def init(face_features_path: str) -> None:
    global known_encodings
    global known_names
    with open(face_features_path, "r") as f:
        known_faces = json.load(f)
    known_encodings = [face["encoding"] for face in known_faces]
    known_names = [face["name"] for face in known_faces]
    logger.info(
        f"Loaded {len(known_encodings)} known face encodings from {face_features_path}"
    )


def recognize_face_names(frame: cv2.Mat, threshold: float = 0.6):
    """
    frameに含まれる顔を識別する
    """
    global known_encodings
    global known_names

    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    recognized_names = []
    for encoding in face_encodings:
        distances = face_recognition.face_distance(known_encodings, encoding)
        best_match_index = np.argmin(distances)
        if distances[best_match_index] <= threshold:
            recognized_names.append(known_names[best_match_index])

    return recognized_names


if __name__ == "__main__":
    """動作テスト"""
    import sys
    import time

    import cv2

    logging.basicConfig(level=logging.INFO)

    cap = cv2.VideoCapture(sys.argv[1] if len(sys.argv) > 1 else 0)
    if not cap.isOpened():
        logger.error("Could not open video capture")
        exit(1)

    init(sys.argv[2] if len(sys.argv) > 2 else "assets/face_features.json")

    while True:
        start_time = time.time()

        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to read frame from video capture")
            break
        frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
        logger.info(frame.shape)

        names = recognize_face_names(frame, threshold=0.6)
        for name in names:
            logger.info(f"Recognized name: {name}")

        cv2.imshow("Face Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        elapsed_time = time.time() - start_time
        logger.info(f"Frame processed in {elapsed_time:.2f} seconds")
        time.sleep(0.1)

    cap.release()
    cv2.destroyAllWindows()
