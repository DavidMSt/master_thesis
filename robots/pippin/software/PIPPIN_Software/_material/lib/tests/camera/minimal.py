import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    exit()

ret, frame = cap.read()
if not ret:
    print("Can't receive frame (stream end?). Exiting...")
    exit()

cv2.imwrite("test.jpg", frame)
cap.release()
