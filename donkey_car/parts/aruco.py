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

    def detect(self, frame: np.ndarray):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        marker_corners, marker_IDs, _ = cv2.aruco.detectMarkers(gray_frame, self.dictionary, parameters=self.detector_params)
        if type(marker_IDs) == np.ndarray:
            marker_IDs = marker_IDs.flatten()
        if type(marker_corners) == np.ndarray:
            marker_corners = marker_corners.reshape(-1, 4, 2)
        return marker_corners, marker_IDs

    def estimate_pose(self, marker_corners: np.ndarray, markerIds: np.ndarray):
        sign_names = []
        distances = []

        if type(marker_corners) == list and type(markerIds) == np.ndarray:
            rVec, tVec, _ = cv2.aruco.estimatePoseSingleMarkers(corners=marker_corners,
                                                                markerLength=self.marker_size_mm,
                                                                cameraMatrix=self.calib_data["camMatrix"],
                                                                distCoeffs=self.calib_data["distCoef"])
            total_markers = range(len(markerIds))
            for marker_id, corners, i in zip(markerIds, marker_corners, total_markers):
                sign_name = self.signs[marker_id]['name']
                distance = np.sqrt(tVec[i][0][2] ** 2 + tVec[i][0][0] ** 2 + tVec[i][0][1] ** 2)
                sign_names.append(sign_name)
                distances.append(distance)
        return sign_names, marker_corners, distances

    def draw(self,
             frame: np.ndarray,
             sign_names: list,
             bboxes: list,
             distances: list,
             ):
        if type(frame) == np.ndarray:
            for sign_name, bbox, distance in zip(sign_names, bboxes, distances):
                bbox = bbox.reshape(-1, 2).astype(np.int32)

                top_right = bbox[0].ravel()
                top_left = bbox[1].ravel()
                bottom_left = bbox[2].ravel()
                bottom_right = bbox[3].ravel()

                cv2.line(frame, tuple(top_left), tuple(top_right), (0, 255, 0), 2)
                cv2.line(frame, tuple(top_right), tuple(bottom_right), (0, 255, 0), 2)
                cv2.line(frame, tuple(bottom_right), tuple(bottom_left), (0, 255, 0), 2)
                cv2.line(frame, tuple(bottom_left), tuple(top_left), (0, 255, 0), 2)

                cv2.putText(frame,
                            f"{sign_name} [{round(distance, 2)}]",
                            tuple(bbox[0]),
                            cv2.FONT_HERSHEY_PLAIN,
                            1.3,
                            (0, 255, 0),
                            1,
                            cv2.LINE_AA)
        return frame


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

    def run(self, road_frame: np.ndarray, sign_frame: np.ndarray) -> (np.ndarray, np.ndarray, np.ndarray):
        if type(road_frame) == np.ndarray and type(sign_frame) == np.ndarray:
            marker_corners, markerIds = self.detect(frame=sign_frame)
            sign_names, bboxes, distances = self.estimate_pose(marker_corners=marker_corners, markerIds=markerIds)
            sign_frame = self.draw(frame=sign_frame, sign_names=sign_names, bboxes=marker_corners, distances=distances)
            return road_frame, sign_frame, marker_corners, markerIds, distances

    def shutdown(self):
        pass

    def load_calib_data(self):
        assert os.path.exists(self.calib_data_path), Exception(f'The camera is not calibrated. The file does not exist:\t{os.path.abspath(self.calib_data_path)}')
        calib_data = np.load(self.calib_data_path)

        return calib_data



if __name__=='__main__':

    aruco = ArucoSignDetector(image_size=500)
    # aruco.save_signs_to_dir()