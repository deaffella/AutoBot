#!/usr/bin/env python3

import os
import sys
import time
import logging


import donkeycar as dk
from donkeycar.parts.camera import MockCamera
from donkeycar.parts.fps import FrequencyLogger

from manage import get_camera, add_user_controller




def add_camera(V: dk.Vehicle, cfg):
	"""
	Add the configured camera to the vehicle pipeline.

	:param V: the vehicle pipeline.
			  On output this will be modified.
	:param cfg: the configuration (from myconfig.py)
	"""
	logger.info("cfg.CAMERA_TYPE %s" % cfg.CAMERA_TYPE)
	cam = get_camera(cfg)
	if cam:
		V.add(cam,
			  inputs=[],
			  outputs=['cam/image_array'],
			  threaded=True)

def add_controller(V: dk.Vehicle, cfg, use_joystick: bool = False):
	"""
	add the user input controller(s)
    - this will add the web controller
    - it will optionally add any configured 'joystick' controller

	:return:
	"""






if __name__ == '__main__':
	logger = logging.getLogger(__name__)
	logging.basicConfig(level=logging.INFO)

	cfg = dk.load_config(myconfig='myconfig.py', config_path='config.py')


	V = dk.Vehicle()

	add_camera(V=V, cfg=cfg)

	V.add(FrequencyLogger(cfg.FPS_DEBUG_INTERVAL), outputs=["fps/current", "fps/fps_list"])

	has_input_controller = hasattr(cfg, "CONTROLLER_TYPE") and cfg.CONTROLLER_TYPE != "mock"
	ctr = add_user_controller(V, cfg, cfg.USE_JOYSTICK_AS_DEFAULT)

	V.start()