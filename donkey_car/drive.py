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

	cfg = dk.load_config(myconfig='myconfig.py', config_path='config.py')

	meta = []

	if not os.path.exists(cfg.JOYSTICK_DEVICE_FILE) and cfg.USE_JOYSTICK_AS_DEFAULT:
		print(f'\nGamepad not connected and does not exist at: `{cfg.JOYSTICK_DEVICE_FILE}`.\nRobot will sleep for 5s.')
		for i in range(5):
			print(f'...{4 - i}s left.')
			time.sleep(1)
		sys.exit()
	else:
		drive(cfg,
			  use_joystick=cfg.USE_JOYSTICK_AS_DEFAULT,
			  model_path=f'{cfg.MODELS_PATH}/{cfg.MODEL}' if type(cfg.MODEL) != type(None) else None,
			  model_type=cfg.DEFAULT_MODEL_TYPE,
			  camera_type='single',
			  meta=meta)