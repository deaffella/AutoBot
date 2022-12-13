# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import sys
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
				 marker_size_mm: int = 32,
				 calib_data_path: str = "../camera_calibartion//calib_data/MultiMatrix.npz",
				 signs_dict: dict = {},
				 image_size: int = 224,
				 border_size: int = 1):
		self.marker_size_mm  = marker_size_mm
		# self.calib_data_path = calib_data_path
		self.calib_data_path = os.path.abspath(calib_data_path)
		self.calib_data		 = self.load_calib_data()

		if len(signs_dict) == 0:
			signs_dict = {0: {'name':	'stop', 'exec_time': 10, 'distance_to_marker': 300}}
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

	# def detect(self, frame: np.ndarray):
	# 	gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	# 	markerCorners, markerIds, rejectedCandidates = cv2.aruco.detectMarkers(gray_frame,
	# 																		   self.dictionary,
	# 																		   parameters=self.detector_params)
	#
	#
	# 	distances = []
	# 	if type(markerCorners) != type(None):
	# 		markerCorners = np.asarray(markerCorners, dtype=int).reshape(-1, 4, 2)
	#
	# 		rVec, tVec, _ = cv2.aruco.estimatePoseSingleMarkers(corners=markerCorners,
	# 															markerLength=self.marker_size_mm,
	# 															cameraMatrix=self.calib_data["camMatrix"],
	# 															distCoeffs=self.calib_data["distCoef"])
	# 		if type(markerIds) == np.ndarray:
	# 			markerIds = markerIds.flatten()
	# 			distances = [np.sqrt(tVec[i][0][2] ** 2 + tVec[i][0][0] ** 2 + tVec[i][0][1] ** 2) for i in range(0, len(markerIds))]
	#
	# 	return markerCorners, markerIds, distances

	def detect(self, frame: np.ndarray):
		# gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		# markerCorners, markerIds, rejectedCandidates = cv2.aruco.detectMarkers(gray_frame,
		# 																	   self.dictionary,
		# 																	   parameters=self.detector_params)
		#
		# if type(markerCorners) != type(None):
		# 	markerCorners = np.asarray(markerCorners, dtype=int).reshape(-1, 4, 2)
		#
		# 	rVec, tVec, _ = cv2.aruco.estimatePoseSingleMarkers(corners=markerCorners,
		# 														markerLength=self.marker_size_mm,
		# 														cameraMatrix=np.array(self.calib_data["camMatrix"], dtype=np.float64),
		# 														distCoeffs=np.array(self.calib_data["distCoef"], dtype=np.float64))
		# 	if type(markerIds) == np.ndarray:
		# 		markerIds = markerIds.flatten()
		# 		distances = [np.sqrt(tVec[i][0][2] ** 2 + tVec[i][0][0] ** 2 + tVec[i][0][1] ** 2) for i in range(0, len(markerIds))]

		###
		gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		marker_corners, marker_IDs, _ = cv2.aruco.detectMarkers(gray_frame, self.dictionary, parameters=self.detector_params)

		distances = []
		if marker_corners:
			rVec, tVec, _ = cv2.aruco.estimatePoseSingleMarkers(corners=marker_corners,
																markerLength=self.marker_size_mm,
																cameraMatrix=self.calib_data["camMatrix"],
																distCoeffs=self.calib_data["distCoef"])
			total_markers = range(0, marker_IDs.size)
			if type(marker_IDs) == np.ndarray:
				marker_IDs = marker_IDs.flatten()

			for ids, corners, i in zip(marker_IDs, marker_corners, total_markers):
				sign_name = self.signs[ids]['name']

				cv2.polylines(
					frame, [corners.astype(np.int32)], True, (0, 255, 255), 4, cv2.LINE_AA
				)
				corners = corners.reshape(4, 2)
				corners = corners.astype(int)
				top_right = corners[0].ravel()
				top_left = corners[1].ravel()
				bottom_right = corners[2].ravel()
				bottom_left = corners[3].ravel()

				distance = np.sqrt(
					tVec[i][0][2] ** 2 + tVec[i][0][0] ** 2 + tVec[i][0][1] ** 2
				)
				distances.append(distance)
				cv2.putText(
					frame,
					f"{sign_name} [{round(distance, 2)}]",
					tuple(top_right),
					cv2.FONT_HERSHEY_PLAIN,
					1.3,
					(0, 0, 255),
					2,
					cv2.LINE_AA,
				)
		return marker_corners, marker_IDs, frame, distances

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

	def draw_bboxes(self, frame: np.ndarray, corners, ids, distances):
		if len(corners) and len(ids)> 0:

			# # loop over the detected ArUCo corners
			# for (markerCorner, markerID) in zip(corners, ids):
			# 	sign_name = self.signs[markerID]['name']
			#
			# 	# extract the marker corners (which are always returned in
			# 	# top-left, top-right, bottom-right, and bottom-left order)
			# 	corners = markerCorner.reshape((4, 2))
			# 	(topLeft, topRight, bottomRight, bottomLeft) = corners
			# 	# convert each of the (x, y)-coordinate pairs to integers
			# 	topRight = (int(topRight[0]), int(topRight[1]))
			# 	bottomRight = (int(bottomRight[0]), int(bottomRight[1]))
			# 	bottomLeft = (int(bottomLeft[0]), int(bottomLeft[1]))
			# 	topLeft = (int(topLeft[0]), int(topLeft[1]))
			#
			#
			# 	cv2.line(frame, topLeft, topRight, (0, 255, 0), 2)
			# 	cv2.line(frame, topRight, bottomRight, (0, 255, 0), 2)
			# 	cv2.line(frame, bottomRight, bottomLeft, (0, 255, 0), 2)
			# 	cv2.line(frame, bottomLeft, topLeft, (0, 255, 0), 2)
			# 	# compute and draw the center (x, y)-coordinates of the ArUco
			# 	# marker
			# 	cX = int((topLeft[0] + bottomRight[0]) / 2.0)
			# 	cY = int((topLeft[1] + bottomRight[1]) / 2.0)
			# 	cv2.circle(frame, (cX, cY), 4, (0, 0, 255), -1)
			# 	# draw the ArUco marker ID on the image
			#
			# 	# cv2.putText(frame, str(markerID),
			# 	cv2.putText(frame, str(sign_name),
			# 				(topLeft[0], topLeft[1] - 15), cv2.FONT_HERSHEY_SIMPLEX,
			# 				0.5, (0, 255, 0), 2)
			# 	#print("[INFO] ArUco marker ID: {}".format(markerID))

			total_markers = range(0, ids.size)
			for single_id, corners, distance, i in zip(ids, corners, distances, total_markers):
				sign_name = self.signs[single_id]['name']

				cv2.polylines(
					frame, [corners.astype(np.int32)], True, (0, 255, 255), 4, cv2.LINE_AA
				)
				corners = corners.reshape(4, 2)
				corners = corners.astype(int)
				top_right = corners[0].ravel()
				top_left = corners[1].ravel()
				bottom_right = corners[2].ravel()
				bottom_left = corners[3].ravel()

				cv2.putText(
					frame,
					f"{sign_name} [{round(distance, 2)}]",
					tuple(top_right),
					cv2.FONT_HERSHEY_PLAIN,
					1.3,
					(0, 0, 255),
					2,
					cv2.LINE_AA,
				)
		return frame

	def run(self, road_frame: np.ndarray, sign_frame: np.ndarray) -> (np.ndarray, np.ndarray, np.ndarray):
		if type(road_frame) == np.ndarray and type(sign_frame) == np.ndarray:
			# markerCorners, markerIds, distances = self.detect(frame=sign_frame)
			# sign_frame = self.draw_bboxes(frame=sign_frame, corners=markerCorners, ids=markerIds, distances=distances)

			markerCorners, markerIds, sign_frame, distances = self.detect(frame=sign_frame)
			return road_frame, sign_frame, markerCorners, markerIds, distances

	def shutdown(self):
		pass

	def load_calib_data(self):
		assert os.path.exists(self.calib_data_path), Exception(f'The camera is not calibrated. The file does not exist:\t{os.path.abspath(self.calib_data_path)}')
		calib_data = np.load(self.calib_data_path)

		return calib_data



if __name__=='__main__':

	aruco = ArucoSignDetector(image_size=500)
	# aruco.save_signs_to_dir()