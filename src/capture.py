import cv2

cap = cv2.VideoCapture()
_width = None
_height = None


def init(width: int, height: int) -> None:
    global _width, _height
    _width = width
    _height = height


def open():
    global cap
    if cap.isOpened():
        return
    cap.open(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open video capture")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, _width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, _height)


def read() -> cv2.Mat:
    global cap
    if not cap.isOpened():
        raise RuntimeError("Video capture is not opened")
    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("Failed to read frame from video capture")
    return frame


def read_rgb() -> cv2.Mat:
    frame = read()
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def release() -> None:
    global cap
    if cap.isOpened():
        cap.release()
