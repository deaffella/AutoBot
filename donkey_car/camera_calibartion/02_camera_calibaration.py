#!/usr/bin/env python3


#
# https://github.com/Asadullah-Dal17/Basic-Augmented-reality-course-opencv/blob/master/CAMERA%F0%9F%93%B7-CALIBARTION/camera_calibaration.py
#

import os
import sys
import time

import cv2
import numpy as np
import donkeycar as dk

sys.path.append('../')
from parts.cameras import CV_USB_Camera, CV_Image_Display


if __name__ == '__main__':
	# Checker board size
	CHESS_BOARD_DIM = (9, 6)

	# The size of Square in the checker board.
	SQUARE_SIZE = 19  # millimeters

	# termination criteria
	criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

	calib_data_path = "./calib_data/"
	CHECK_DIR = os.path.isdir(calib_data_path)
	if not CHECK_DIR:
		os.makedirs(calib_data_path)
		print(f'Directory is created:\t[{calib_data_path}]')
	else:
		print(f'Directory already Exists:\t[{calib_data_path}]')

	# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
	obj_3D = np.zeros((CHESS_BOARD_DIM[0] * CHESS_BOARD_DIM[1], 3), np.float32)

	obj_3D[:, :2] = np.mgrid[0: CHESS_BOARD_DIM[0], 0: CHESS_BOARD_DIM[1]].T.reshape(
		-1, 2
	)
	obj_3D *= SQUARE_SIZE
	print(obj_3D)

	# Arrays to store object points and image points from all the images.
	obj_points_3D = []  # 3d point in real world space
	img_points_2D = []  # 2d points in image plane.


	# The images directory path
	image_dir_path = "images"

	files = os.listdir(image_dir_path)
	for file in files:
		print(file)
		imagePath = os.path.join(image_dir_path, file)
		# print(imagePath)

		image = cv2.imread(imagePath)
		grayScale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		ret, corners = cv2.findChessboardCorners(image, CHESS_BOARD_DIM, None)
		if ret == True:
			obj_points_3D.append(obj_3D)
			corners2 = cv2.cornerSubPix(grayScale, corners, (3, 3), (-1, -1), criteria)
			img_points_2D.append(corners2)

			img = cv2.drawChessboardCorners(image, CHESS_BOARD_DIM, corners2, ret)

	cv2.destroyAllWindows()
	# h, w = image.shape[:2]
	ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
		obj_points_3D, img_points_2D, grayScale.shape[::-1], None, None
	)
	print("calibrated")

	print("duming the data into one files using numpy ")
	np.savez(
		f"{calib_data_path}/MultiMatrix",
		camMatrix=mtx,
		distCoef=dist,
		rVector=rvecs,
		tVector=tvecs,
	)

	print("-------------------------------------------")

	print("loading data stored using numpy savez function\n \n \n")

	data = np.load(f"{calib_data_path}/MultiMatrix.npz")

	camMatrix = data["camMatrix"]
	distCof = data["distCoef"]
	rVector = data["rVector"]
	tVector = data["tVector"]

	print("loaded calibration data successfully")
