#!/usr/bin/env python3

import cv2
import os

import sys
sys.path.append('../')

from parts.cameras import Jetson_CSI_Camera

def detect_checker_board(image, grayImage, criteria, boardDimension):
	ret, corners = cv2.findChessboardCorners(grayImage, boardDimension)
	if ret == True:
		corners1 = cv2.cornerSubPix(grayImage, corners, (3, 3), (-1, -1), criteria)
		image = cv2.drawChessboardCorners(image, boardDimension, corners1, ret)

	return image, ret


if __name__ == '__main__':

	CHESS_BOARD_DIM = (9, 6)

	n = 0  # image_counter

	# checking if  images dir is exist not, if not then create images directory
	image_dir_path = "images"

	CHECK_DIR = os.path.isdir(image_dir_path)
	# if directory does not exist create
	if CHECK_DIR:
		print(f'"{image_dir_path}" Directory already Exists. Removing.')
		os.rmdir(image_dir_path)

	os.makedirs(image_dir_path)
	print(f'"{image_dir_path}" Directory is created')

	criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

	#cap = cv2.VideoCapture('/dev/cams/usb')
	cap = Jetson_CSI_Camera(sensor_id=0, image_w=640, image_h=480, capture_width=640, capture_height=480, framerate=20, gstreamer_flip=2)
	while True:
		# _, frame = cap.read()
		_, frame = cap.read_frame_from_device()

		copyFrame = frame.copy()
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

		image, board_detected = detect_checker_board(frame, gray, criteria, CHESS_BOARD_DIM)
		# print(ret)
		cv2.putText(
			frame,
			f"saved_img : {n}",
			(30, 40),
			cv2.FONT_HERSHEY_PLAIN,
			1.4,
			(0, 255, 0),
			2,
			cv2.LINE_AA,
		)

		cv2.imshow("frame", frame)
		cv2.imshow("copyFrame", copyFrame)

		key = cv2.waitKey(1)

		if key == ord("q"):
			break
		if key == ord("s") and board_detected == True:
			# storing the checker board image
			cv2.imwrite(f"{image_dir_path}/image{n}.png", copyFrame)

			print(f"saved image number {n}")
			n += 1  # incrementing the image counter
	cap.release()
	cv2.destroyAllWindows()

	print("Total saved Images:", n)