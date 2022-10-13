
import cv2
import threading
import numpy as np


def construct_gstreamer_pipeline(sensor_id:         int = 0,
                                 capture_width:     int = 640,
                                 capture_height:    int = 480,
                                 display_width:     int = 640,
                                 display_height:    int = 480,
                                 framerate:         int = 30,
                                 flip_method:       int = 0,
                                 ) -> str:
    """
    construct_gstreamer_pipeline returns a GStreamer pipeline for capturing from the CSI camera
    Flip the image by setting the flip_method (most common values: 0 and 2)
    display_width and display_height determine the size of each camera pane in the window on the screen
    Default 1920x1080

    :param sensor_id:
    :param capture_width:
    :param capture_height:
    :param display_width:
    :param display_height:
    :param framerate:
    :param flip_method:
    :return:
    """
    return f"nvarguscamerasrc sensor-id={sensor_id} ! " \
           f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, framerate=(fraction){framerate}/1 ! " \
           f"nvvidconv flip-method={flip_method} ! " \
           f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! " \
           f"videoconvert ! " \
           f"video/x-raw, format=(string)BGR ! appsink"


class CSI_Camera:
    # based on https://github.com/JetsonHacksNano/CSI-Camera
    def __init__(self):
        # Initialize instance variables
        # OpenCV video capture element
        self.video_capture = None
        # The last captured image from the camera
        self.frame = None
        self.grabbed = False
        # The thread where the video capture runs
        self.read_thread = None
        self.read_lock = threading.Lock()
        self.running = False

    def open(self, gstreamer_pipeline: str):
        try:
            self.video_capture = cv2.VideoCapture(
                gstreamer_pipeline, cv2.CAP_GSTREAMER
            )
            # Grab the first frame to start the video capturing
            self.grabbed, self.frame = self.video_capture.read()

        except RuntimeError:
            self.video_capture = None
            print("Unable to open camera")
            print("Pipeline: " + gstreamer_pipeline)

    def start(self):
        if self.running:
            print('Video capturing is already running')
            return None
        # create a thread to read the camera image
        if self.video_capture != None:
            self.running = True
            self.read_thread = threading.Thread(target=self.updateCamera)
            self.read_thread.start()
        return self

    def stop(self):
        self.running = False
        # Kill the thread
        self.read_thread.join()
        self.read_thread = None

    def updateCamera(self):
        # This is the thread to read images from the camera
        while self.running:
            try:
                grabbed, frame = self.video_capture.read()
                with self.read_lock:
                    self.grabbed = grabbed
                    self.frame = frame
            except RuntimeError:
                print("Could not read image from camera")
        # FIX ME - stop and cleanup thread
        # Something bad happened

    def read(self):
        with self.read_lock:
            frame = self.frame.copy()
            grabbed = self.grabbed
        return grabbed, frame

    def release(self):
        if self.video_capture != None:
            self.video_capture.release()
            self.video_capture = None
        # Now kill the thread
        if self.read_thread != None:
            self.read_thread.join()


class Jetson_Camera(CSI_Camera):
    def __init__(self,
                 sensor_id:         int = 0,
                 capture_width:     int = 1280,
                 capture_height:    int = 720,
                 display_width:     int = 640,
                 display_height:    int = 360,
                 framerate:         int = 60,
                 flip_method:       int = 0,
                 ):
        self.sensor_id = sensor_id
        self.capture_width = capture_width
        self.capture_height = capture_height
        self.display_width = display_width
        self.display_height = display_height
        self.framerate = framerate
        self.flip_method = flip_method

        self.gstreamer_pipeline = construct_gstreamer_pipeline(sensor_id=self.sensor_id,
                                                               capture_width=self.capture_width,
                                                               capture_height=self.capture_height,
                                                               display_width=self.display_width,
                                                               display_height=self.display_height,
                                                               framerate=self.framerate,
                                                               flip_method=self.flip_method)
        # super().__init__()
        CSI_Camera.__init__(self)

        self.open()

    def open(self, gstreamer_pipeline: str = None):
        CSI_Camera.open(self,
                        gstreamer_pipeline=self.gstreamer_pipeline
                        if gstreamer_pipeline is None else gstreamer_pipeline)







if __name__ == "__main__":

    left_camera = Jetson_Camera(sensor_id=0)
    left_camera.start()

    right_camera = Jetson_Camera(sensor_id=1)
    right_camera.start()

    window_title = __file__
    if left_camera.video_capture.isOpened():

        cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)

        try:
            while True:
                _, left_image = left_camera.read()

                _, right_image = right_camera.read()
                # Use numpy to place images next to each other
                camera_images = np.hstack((left_image, right_image))

                # Check to see if the user closed the window
                # Under GTK+ (Jetson Default), WND_PROP_VISIBLE does not work correctly. Under Qt it does
                # GTK - Substitute WND_PROP_AUTOSIZE to detect if window has been closed by user
                if cv2.getWindowProperty(window_title, cv2.WND_PROP_AUTOSIZE) >= 0:
                    cv2.imshow(window_title, camera_images)
                else:
                    break

                # This also acts as
                keyCode = cv2.waitKey(30) & 0xFF
                # Stop the program on the ESC key
                if keyCode == 27:
                    break
        finally:
            left_camera.stop()
            left_camera.release()
            right_camera.stop()
            right_camera.release()
        cv2.destroyAllWindows()
    else:
        print("Error: Unable to open both cameras")
        left_camera.stop()
        left_camera.release()
        right_camera.stop()
        right_camera.release()