import sys
import os
import shutil
import cv2
import numpy as np
import json
import tqdm

import time
import threading



class ArucoSignDetector():
	"""
	size 6X6_250
	"""
	def __init__(self,
				 signs_dict: dict = {},
				 image_size: int = 224,
				 border_size: int = 1):
		if len(signs_dict) == 0:
			signs_dict = {0: {'name':	'stop', 'exec_time': 10}}
		self.signs = signs_dict

		self.image_size = image_size
		self.border_size = border_size
		self.dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)

		# self.detector = None
		self.detector_params = cv2.aruco.DetectorParameters_create()

	def get_sign_name_by_id(self, id: int) -> str:
		assert type(id) is int
		assert 0 <= id <= 249
		assert id in self.signs.keys()
		return self.signs[id]['name']

	def get_sign_image_by_id(self, id: int) -> np.ndarray:
		assert type(id) is int
		assert 0 <= id <= 249
		assert id in self.signs.keys()
		markerImage = np.zeros((self.image_size, self.image_size), dtype=np.uint8)
		markerImage = cv2.aruco.drawMarker(self.dictionary, id, self.image_size, markerImage, self.border_size)
		return markerImage

	def detect(self, frame: np.ndarray):
		markerCorners, markerIds, rejectedCandidates = cv2.aruco.detectMarkers(frame,
																			   self.dictionary,
																			   parameters=self.detector_params)

		if type(markerCorners) != type(None):
			markerCorners = np.asarray(markerCorners, dtype=int).reshape(-1, 4, 2)

		if type(markerIds) == np.ndarray:
			markerIds = markerIds.flatten()
		return markerCorners, markerIds, rejectedCandidates

	def save_signs_to_dir(self, dir_path: str = './signs/', ext: str = 'png'):
		if os.path.exists(dir_path):
			# shutil.rmtree(dir_path)
			return
		if not os.path.exists(dir_path):
			os.makedirs(dir_path)
		for sign_aruco_idx in tqdm.tqdm(self.signs.keys(), total=len(self.signs.keys())):
			img_path = f'{dir_path}/{sign_aruco_idx}.{ext}'
			markerImage = self.get_sign_image_by_id(id=sign_aruco_idx)
			cv2.imwrite(img_path, markerImage)

	def draw_bboxes(self, frame: np.ndarray, corners, ids):
		if len(corners) and len(ids)> 0:
			# ids = ids.flatten()

			# loop over the detected ArUCo corners
			for (markerCorner, markerID) in zip(corners, ids):
				sign_name = self.signs[markerID]['name']

				# extract the marker corners (which are always returned in
				# top-left, top-right, bottom-right, and bottom-left order)
				corners = markerCorner.reshape((4, 2))
				(topLeft, topRight, bottomRight, bottomLeft) = corners
				# convert each of the (x, y)-coordinate pairs to integers
				topRight = (int(topRight[0]), int(topRight[1]))
				bottomRight = (int(bottomRight[0]), int(bottomRight[1]))
				bottomLeft = (int(bottomLeft[0]), int(bottomLeft[1]))
				topLeft = (int(topLeft[0]), int(topLeft[1]))


				cv2.line(frame, topLeft, topRight, (0, 255, 0), 2)
				cv2.line(frame, topRight, bottomRight, (0, 255, 0), 2)
				cv2.line(frame, bottomRight, bottomLeft, (0, 255, 0), 2)
				cv2.line(frame, bottomLeft, topLeft, (0, 255, 0), 2)
				# compute and draw the center (x, y)-coordinates of the ArUco
				# marker
				cX = int((topLeft[0] + bottomRight[0]) / 2.0)
				cY = int((topLeft[1] + bottomRight[1]) / 2.0)
				cv2.circle(frame, (cX, cY), 4, (0, 0, 255), -1)
				# draw the ArUco marker ID on the image

				# cv2.putText(frame, str(markerID),
				cv2.putText(frame, str(sign_name),
							(topLeft[0], topLeft[1] - 15), cv2.FONT_HERSHEY_SIMPLEX,
							0.5, (0, 255, 0), 2)
				#print("[INFO] ArUco marker ID: {}".format(markerID))
		return frame

	def run(self, road_frame: np.ndarray, sign_frame: np.ndarray) -> (np.ndarray, np.ndarray, np.ndarray):
		if type(road_frame) == np.ndarray and type(sign_frame) == np.ndarray:
			markerCorners, markerIds, rejectedCandidates = self.detect(frame=sign_frame)
			sign_frame = self.draw_bboxes(frame=sign_frame, corners=markerCorners, ids=markerIds)
			return road_frame, sign_frame, markerCorners, markerIds

	def shutdown(self):
		pass




if __name__=='__main__':

	aruco = ArucoSignDetector(image_size=500)
	# aruco.save_signs_to_dir()