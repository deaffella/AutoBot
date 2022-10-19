#!/usr/bin/python3

import os
import sys
import time
import donkeycar as dk

from car_manage.manage import drive







if __name__ == '__main__':
	cfg = dk.load_config(myconfig='myconfig.py', config_path='./configs/config.py')

	use_gamepad = cfg.USE_GAMEPAD
	model = cfg.MODEL
	model_type = cfg.MODEL_TYPE

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
			  meta=[])