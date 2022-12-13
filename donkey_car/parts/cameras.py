import os
import serial
import sys
import time

from typing import List, Tuple, Any, Dict

import logging

import time
import cv2
import threading
import numpy as np
import random

from donkeycar.parts.cv import CvCam


class Jetson_CSI_Camera(object):
    def __init__(self,
                 sensor_id: int = 0,
                 capture_width: int = 1280,
                 capture_height: int = 720,
                 framerate: int = 60,
                 gstreamer_flip: int = 2,
                 image_w: int = None,
                 image_h: int = None):
        self.sensor_id = sensor_id
        self.capture_width = capture_width
        self.capture_height = capture_height
        self.framerate = framerate
        self.gstreamer_flip = gstreamer_flip

        if image_w is None:
            self.display_width = capture_width
        else:
            self.display_width = image_w
        if image_h is None:
            self.display_height = capture_height
        else:
            self.display_height = image_h

        # The last captured image from the camera
        self.frame = None
        self.grabbed = False

        self.gstreamer_pipeline = None
        self.video_capture = None

        self.running = True
        self.__create_capture_device()


    def __construct_gstreamer_pipeline(self,
                                       sensor_id:         int = 0,
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
               f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, " \
               f"format=(string)NV12, " \
               f"framerate=(fraction){framerate}/1 ! " \
               f"nvvidconv flip-method={flip_method} ! " \
               f"nvvidconv ! " \
               f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! " \
               f"videoconvert ! appsink"

    def __create_capture_device(self):
        try:
            self.gstreamer_pipeline = self.__construct_gstreamer_pipeline(sensor_id=self.sensor_id,
                                                                          capture_width=self.capture_width,
                                                                          capture_height=self.capture_height,
                                                                          display_width=self.display_width,
                                                                          display_height=self.display_height,
                                                                          framerate=self.framerate,
                                                                          flip_method=self.gstreamer_flip)

            self.video_capture = cv2.VideoCapture(self.gstreamer_pipeline, cv2.CAP_GSTREAMER)

            # # Grab the first frame to start the video capturing
            # self.grabbed, self.frame = self.video_capture.read()
        except RuntimeError:
            self.video_capture = None
            print("Unable to open camera")
            print("Pipeline: " + self.gstreamer_pipeline)
            raise Exception(f'Please check CSI camera: [{self.sensor_id}].')

    def shutdown(self):
        self.running = False
        time.sleep(0.2)
        self.video_capture.release()

    def run(self) -> np.ndarray:
        self.read_frame_from_device()
        return self.frame

    def run_threaded(self) -> np.ndarray:
        return self.frame

    def read_frame_from_device(self):
        grabbed, frame = self.video_capture.read()
        if frame is not None:
            self.grabbed, self.frame = grabbed, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return self.grabbed, self.frame

    def update(self):
        if self.video_capture is None:
            self.__create_capture_device()

        while self.running:
            self.read_frame_from_device()


class CV_USB_Camera(CvCam):
    def __init__(self,
                 camera_path:    str = '/dev/cams/usb',
                 capture_width:  int = 640,
                 capture_height: int = 480,
                 ):
        super().__init__(iCam=camera_path,
                         image_w=capture_width,
                         image_h=capture_height,
                         image_d=3)

    def poll(self):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if frame is not None:
                self.frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


class CV_Image_Display(object):
    def __init__(self,
                 window_name: str = 'frame'):
        self.window_name = window_name

    def shutdown(self):
        cv2.destroyAllWindows()

    def run(self, frame: np.ndarray):
        if frame is not None:
            cv2.imshow(self.window_name, frame)
            cv2.waitKey(1)




if __name__=='__main__':
    import donkeycar as dk

    robot = dk.Vehicle()

    # main_cam = Jetson_CSI_Camera(sensor_id=0, framerate=30)
    main_cam = CV_USB_Camera(camera_path='/dev/cams/usb')
    # time.sleep(1)


    robot.add(main_cam, outputs=['camera/main_cam'], threaded=True)

    display = CV_Image_Display()
    robot.add(display, inputs=['camera/main_cam'])

    robot.start(rate_hz=20)