import cv2

cap = cv2.VideoCapture(0)  # Change '0' to the correct camera index

if not cap.isOpened():
    print("Camera failed to open.")
else:
    print("Camera opened successfully.")
    while True:
        ret, frame = cap.read()
        if ret:
            cv2.imshow('Camera Feed', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Failed to capture frame.")

cap.release()
cv2.destroyAllWindows()
