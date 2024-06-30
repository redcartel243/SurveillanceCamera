import cv2
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage

class CaptureIpCameraFramesWorker(QThread):
    ImageUpdated = pyqtSignal(QImage)

    def __init__(self, url) -> None:
        super(CaptureIpCameraFramesWorker, self).__init__()
        self.url = url
        self.__thread_active = True
        self.__thread_pause = False

    def run(self) -> None:
        try:
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                print(f"Failed to open IP camera at {self.url}")
                return

            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"FPS: {fps}")

            while self.__thread_active:
                if not self.__thread_pause:
                    ret, frame = cap.read()
                    if ret:
                        height, width, channels = frame.shape
                        bytes_per_line = width * channels
                        cv_rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        qt_rgb_image = QImage(cv_rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
                        qt_rgb_image_scaled = qt_rgb_image.scaled(1280, 720, Qt.KeepAspectRatio)
                        self.ImageUpdated.emit(qt_rgb_image_scaled)
                    else:
                        print("Failed to read frame from IP camera")
                        break
            cap.release()
        except Exception as e:
            print(f"Exception in CaptureIpCameraFramesWorker: {e}")
        finally:
            self.quit()

    def stop(self) -> None:
        self.__thread_active = False

    def pause(self) -> None:
        self.__thread_pause = True

    def unpause(self) -> None:
        self.__thread_pause = False
