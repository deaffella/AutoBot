#!/usr/bin/env python3

import sys
import os
import cv2
import numpy as np
import json

import time
import threading


from cameras import Jetson_CSI_Camera



class CSI_Camera:

	def __init__(self,
				 sensor_id: int = 0,
				 capture_width: int = 1280,
				 capture_height: int = 720,
				 framerate: int = 60,
				 gstreamer_flip: int = 2,
				 image_w: int = None,
				 image_h: int = None,
				 image_d: int = 3):
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
		# return f"nvarguscamerasrc sensor-id={sensor_id} ! " \
		#        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, framerate=(fraction){framerate}/1 ! " \
		#        f"nvvidconv flip-method={flip_method} ! " \
		#        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! " \
		#        f"videoconvert ! " \
		#        f"video/x-raw, format=(string)BGR ! appsink"
		return f"nvarguscamerasrc sensor-id={sensor_id} ! " \
			   f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, " \
			   f"format=(string)NV12, " \
			   f"framerate=(fraction){framerate}/1 ! " \
			   f"nvvidconv flip-method={flip_method} ! " \
			   f"nvvidconv ! " \
			   f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! " \
			   f"videoconvert ! appsink"


	def open(self):
		try:
			gstreamer_pipeline_string = self.__construct_gstreamer_pipeline(sensor_id=self.sensor_id,
																		  capture_width=self.capture_width,
																		  capture_height=self.capture_height,
																		  display_width=self.display_width,
																		  display_height=self.display_height,
																		  framerate=self.framerate,
																		  flip_method=self.gstreamer_flip)
			self.video_capture = cv2.VideoCapture(
				gstreamer_pipeline_string, cv2.CAP_GSTREAMER
			)
			# Grab the first frame to start the video capturing
			self.grabbed, self.frame = self.video_capture.read()

		except RuntimeError:
			self.video_capture = None
			print("Unable to open camera")
			print("Pipeline: " + gstreamer_pipeline_string)


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




class ArucoSigns():
	"""
	size 6X6_250
	"""
	def __init__(self,
				 image_size: int = 224,
				 border_size: int = 1):
		self.signs = {
			0: 'stop',
			1: 'start',

			2: 'cross_left',
			3: 'cross_forward',
			4: 'cross_right',

			5: 'speed_down',
			6: 'speed_up',

			7: 'rotate-90',
			8: 'rotate-180',
			9: 'rotate-270',
			10: 'rotate-360',

			11: 'rotate+90',
			12: 'rotate+180',
			13: 'rotate+270',
			14: 'rotate+360',
		}
		self.image_size = image_size
		self.border_size = border_size
		self.dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)

		# self.detector = None
		self.detector_params = cv2.aruco.DetectorParameters_create()

	def get_sign_name_by_id(self, id: int) -> str:
		assert type(id) is int
		assert 0 <= id <= 249
		assert id in self.signs.keys()
		return self.signs[id]

	def get_sign_image_by_id(self, id: int) -> np.ndarray:
		assert type(id) is int
		assert 0 <= id <= 249
		assert id in self.signs.keys()
		markerImage = np.zeros((self.image_size, self.image_size), dtype=np.uint8)
		markerImage = cv2.aruco.drawMarker(self.dictionary, id, self.image_size, markerImage, self.border_size)
		return markerImage

	def detect(self, frame: np.ndarray):
		# if self.detector is None:
		# 	self.detector = cv2.aruco.DetectorParameters_create()

		markerCorners, markerIds, rejectedCandidates = cv2.aruco.detectMarkers(frame,
																			   self.dictionary,
																			   parameters=self.detector_params)
		return markerCorners, markerIds, rejectedCandidates








if __name__=='__main__':

	aruco = ArucoSigns(image_size=500)

	# frame = aruco.get_sign_image_by_id(0)
	# cv2.imwrite('1.jpg', frame)


	main_cam = Jetson_CSI_Camera(sensor_id=0, framerate=30)
	# main_cam = CSI_Camera(sensor_id=1, framerate=30)
	# main_cam.open()
	# main_cam.start()
	# time.sleep(2)
	#
	#
	while True:
		ret, frame = main_cam.read_frame_from_device()
		# ret, frame = main_cam.read()

		if type(frame) != type(None):
			# markerCorners, markerIds, rejectedCandidates = aruco.detect(frame=frame)
			# print(markerCorners)
			# print()
			# print(markerIds)
			# print()
			# print(rejectedCandidates)
			# print()
			# print()
			# print()
			cv2.imshow('frame', frame)
			cv2.waitKeyEx(1)



	# # Загрузить предопределенный словарь
	# dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
	#
	# # Сгенерировать маркер
	# markerImage = np.zeros((600, 600), dtype=np.uint8)
	#
	# markerImage = cv2.aruco.drawMarker(dictionary, 34, 200, markerImage, 1)
	#
	# # cv2.imwrite("marker33.png", markerImage)

	# cv2.imshow('markerImage', frame)
	# cv2.waitKeyEx(0)