#!/usr/bin/python3

import os
import sys
import time
import donkeycar as dk

from car_manage.manage import drive







if __name__ == '__main__':
	cfg = dk.load_config(myconfig='./configs/myconfig.py', config_path='./configs/config.py')

	if not os.path.exists(cfg.JOYSTICK_DEVICE_FILE):
		print(f'\nGamepad not connected and does not exist at: `{cfg.JOYSTICK_DEVICE_FILE}`.\nRobot will sleep for 5s.')
		for i in range(5):
			print(f'...{4 - i}s left.')
			time.sleep(1)
		sys.exit()
	else:
		use_gamepad = True
		model = None
		model_type = None

		drive(cfg,
			  use_joystick=use_gamepad,
			  model_path=model,
			  model_type=model_type,
			  camera_type='single',
			  meta=[])