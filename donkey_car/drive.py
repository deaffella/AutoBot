#!/usr/bin/python3

import os
import sys
import time

import logging

import donkeycar as dk
from manage import drive







if __name__ == '__main__':
	logger = logging.getLogger(__name__)
	logging.basicConfig(level=logging.INFO)

	cfg = dk.load_config(config_path='./config.py')


	use_gamepad = cfg.USE_JOYSTICK_AS_DEFAULT
	model = cfg.MODEL
	model_type = cfg.DEFAULT_MODEL_TYPE
	meta = cfg.DEFAULT_META

	if not os.path.exists(cfg.JOYSTICK_DEVICE_FILE) and use_gamepad:
		print(f'\nGamepad not connected and does not exist at: `{cfg.JOYSTICK_DEVICE_FILE}`.\nRobot will sleep for 5s.')
		for i in range(5):
			print(f'...{4 - i}s left.')
			time.sleep(1)
		sys.exit()
	else:
		drive(cfg,
			  use_joystick=use_gamepad,
			  model_path=model,
			  model_type=model_type,
			  camera_type='single',
			  meta=meta)