#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import sys
import time
import logging
import numpy as np

import donkeycar as dk
from donkeycar.parts.camera import MockCamera

from donkeycar.parts.explode import ExplodeDict
from donkeycar.parts.transform import Lambda
from donkeycar.parts.throttle_filter import ThrottleFilter
from donkeycar.parts.controller import JoystickController
from donkeycar.parts.behavior import BehaviorPart
from donkeycar.parts.file_watcher import FileWatcher
from donkeycar.parts.transform import TriggeredCallback, DelayedTrigger
from donkeycar.parts.launch import AiLaunch
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.tub_v2 import TubWriter

from donkeycar.parts.actuator import TwoWheelSteeringThrottle

# from donkeycar.parts.cv import CvCam

# from manage import add_drivetrain
from parts.cameras import Jetson_CSI_Camera, CV_USB_Camera
from parts.web_controller.web import LocalWebController

from parts.actuators import autobot_platform
from parts.actuators import AutoBot_Actuator, AutoBot_Flashlight, AutoBot_UV_Flashlight, AutoBot_Camera_Servo
from parts.actuators import Sensor_RFID, Sensor_Battery, Sensor_US, Sensor_IR

from parts.aruco import ArucoSignDetector


def remove_collected_data(dir_path: str):
	if os.path.exists(dir_path):
		shutil.rmtree(dir_path)
	print(f'REMOVED:\t{dir_path}')



def add_controller(V, cfg):
	ctr = LocalWebController(port=cfg.WEB_CONTROL_PORT, mode=cfg.WEB_INIT_MODE)
	V.add(ctr,
		  inputs=[f'cam_top/image_array', f'cam_bot/image_array', 'tub/num_records', 'user/mode', 'recording'],
		  outputs=['user/angle', 'user/throttle', 'user/mode', 'recording', 'web/buttons'],
		  threaded=True)

	if cfg.USE_JOYSTICK_AS_DEFAULT and os.path.exists(cfg.JOYSTICK_DEVICE_FILE):
		# custom game controller mapping created with
		# `donkey createjs` command
		#
		if cfg.CONTROLLER_TYPE == "custom":  # custom controller created with `donkey createjs` command
			from joystics.ds4_blue import DS4_BlueController
			ctr = DS4_BlueController(
				throttle_dir=cfg.JOYSTICK_THROTTLE_DIR,
				throttle_scale=cfg.JOYSTICK_MAX_THROTTLE,
				steering_scale=cfg.JOYSTICK_STEERING_SCALE,
				auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)
			ctr.set_deadzone(cfg.JOYSTICK_DEADZONE)
		elif cfg.CONTROLLER_TYPE == "mock":
			from donkeycar.parts.controller import MockController
			ctr = MockController(steering=cfg.MOCK_JOYSTICK_STEERING,
								 throttle=cfg.MOCK_JOYSTICK_THROTTLE)
		else:
			# game controller
			#
			from donkeycar.parts.controller import get_js_controller
			ctr = get_js_controller(cfg)
			if cfg.USE_NETWORKED_JS:
				from donkeycar.parts.controller import JoyStickSub
				netwkJs = JoyStickSub(cfg.NETWORK_JS_SERVER_IP)
				V.add(netwkJs, threaded=True)
				ctr.js = netwkJs
		V.add(ctr,
			  inputs=[f'{cfg.ROAD_CAM}/image_array', 'user/mode', 'recording'],
			  outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
			  threaded=True)
	return ctr


class PilotCondition:
	def run(self, mode):
		if mode == 'user':
			return False
		else:
			return True


class DriveMode:
	def run(self,
			mode,
			user_angle, user_throttle, pilot_angle,
			pilot_throttle,
			aruco_angle, aruco_throttle,
			):
		if mode == 'user':
			return user_angle, user_throttle

		elif mode == 'local_angle':
			return pilot_angle if pilot_angle else 0.0, user_throttle
		elif mode == 'local':
			return pilot_angle if pilot_angle else 0.0, \
				   pilot_throttle * cfg.AI_THROTTLE_MULT \
					   if pilot_throttle else 0.0

		elif mode == 'aruco_single':
			if aruco_angle is None or aruco_throttle is None:
				return 0.0, 0.0
			return aruco_angle, aruco_throttle

		elif mode == 'local+aruco':
			if aruco_angle is None or aruco_throttle is None:
				return pilot_angle if pilot_angle else 0.0, \
					   pilot_throttle * cfg.AI_THROTTLE_MULT \
						   if pilot_throttle else 0.0
			return aruco_angle, aruco_throttle

		else:
			return 0.0, 0.0


class ArucoDriveController(object):

	def __init__(self, signs_dict: dict):
		if len(signs_dict) == 0:
			signs_dict = {0: {'name':	'stop', 'exec_time': 10, 'distance_to_marker': 300}}
		self.signs = signs_dict

		self.last_detected_sign_id = None

		self.angle: float = None
		self.throttle: float = None

		self.maneuver_execution_time_sec: float = 0  # время выполнения маневра
		self.last_sign_detect_time: float = 0
		self.running: bool = True

		self.logger = logging.getLogger(self.__class__.__name__)

	def update(self):
		while self.running:
			this_time = time.time()
			time_delta = this_time - self.last_sign_detect_time
			if time_delta >= self.maneuver_execution_time_sec:
				if self.angle is not None and self.throttle is not None:
					self.logger.info(f'[done]: {time_delta}')
				self.angle = None
				self.throttle = None
			time.sleep(0.01)

	def run_threaded(self,
					 markerCorners: np.ndarray,
					 markerIds: np.ndarray,
					 distances: list) -> (float, float):
		if type(markerIds) == np.ndarray and type(markerIds) == np.ndarray and type(distances) == list:
			# ids = markerIds.tolist()

			this_time = time.time()
			if this_time - self.last_sign_detect_time > self.maneuver_execution_time_sec:
				self.last_sign_detect_time = this_time

				if len(markerIds):
					selected_id = markerIds[0]
					# if selected_id != self.last_detected_sign_id:
						# self.last_detected_sign_id = selected_id
					current_dist_to_marker = distances[0]
					min_dist_to_marker = self.signs[selected_id]['distance_to_marker']
					if current_dist_to_marker <= min_dist_to_marker:
						if selected_id == 0:
							# stop
							self.angle = 0
							self.throttle = 0
						elif selected_id == 1:
							# start
							self.angle = 0
							self.throttle = 1
						elif selected_id == 2:
							# cross_left
							self.angle = -0.8
							self.throttle = 1
						elif selected_id == 3:
							# cross_forward
							self.angle = 0
							self.throttle = 1
						elif selected_id == 4:
							# cross_right
							self.angle = 0.8
							self.throttle = 1

						self.maneuver_execution_time_sec = self.signs[selected_id]['exec_time']
						self.logger.info(f'[selected_id]: [{selected_id} - {self.signs[selected_id]["name"]}]')

		return self.angle, self.throttle

	def shutdown(self):
		self.running = False
		return 0, 0


def dual_cam_drive(cfg,
				   model_path=None,
				   model_type=None,
				   meta=[]):
	"""
	Construct a working robotic vehicle from many parts. Each part runs as a
	job in the Vehicle loop, calling either it's run or run_threaded method
	depending on the constructor flag `threaded`. All parts are updated one
	after another at the framerate given in cfg.DRIVE_LOOP_HZ assuming each
	part finishes processing in a timely manner. Parts may have named outputs
	and inputs. The framework handles passing named outputs to parts
	requesting the same named input.
	"""
	logger.info(f'PID: {os.getpid()}')

	if model_type is None:
		if cfg.TRAIN_LOCALIZER:
			model_type = "localizer"
		elif cfg.TRAIN_BEHAVIORS:
			model_type = "behavior"
		else:
			model_type = cfg.DEFAULT_MODEL_TYPE

	# Initialize car
	V = dk.Vehicle()

	# Initialize logging before anything else to allow console logging
	if cfg.HAVE_CONSOLE_LOGGING:
		logger.setLevel(logging.getLevelName(cfg.LOGGING_LEVEL))
		ch = logging.StreamHandler()
		ch.setFormatter(logging.Formatter(cfg.LOGGING_FORMAT))
		logger.addHandler(ch)

	V.add(AutoBot_Actuator(), inputs=['left/throttle', 'right/throttle'])

	control_flashlight = AutoBot_Flashlight()
	control_uv_flashlight = AutoBot_UV_Flashlight()
	control_camera_servo = AutoBot_Camera_Servo()

	# setup top camera
	cam_top = Jetson_CSI_Camera(sensor_id=0,
								image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H,
								capture_width=cfg.IMAGE_W, capture_height=cfg.IMAGE_H,
								framerate=cfg.CAMERA_FRAMERATE, gstreamer_flip=cfg.CSIC_CAM_GSTREAMER_FLIP_PARM)
	V.add(cam_top, inputs=[], outputs=[f'cam_top/pure_image'], threaded=True)

	# setup bottom camera
	cam_bot = CV_USB_Camera(camera_path='/dev/cams/usb', capture_width=cfg.IMAGE_W, capture_height=cfg.IMAGE_H)
	V.add(cam_bot, inputs=[], outputs=[f'cam_bot/pure_image'], threaded=True)

	time.sleep(0.4)

	# fps console counter
	if cfg.SHOW_FPS:
		from donkeycar.parts.fps import FrequencyLogger
		V.add(FrequencyLogger(cfg.FPS_DEBUG_INTERVAL), outputs=["fps/current", "fps/fps_list"])

	aruco_sign_detector = ArucoSignDetector(signs_dict=cfg.ARUCO_SIGNS_DICT,
											calib_data_path=cfg.ARUCO_CAMERA_CALIB_DATA_PATH,
											marker_size_mm=cfg.ARUCO_SIGN_SIZE_MM)
											# marker_size_mm=38/2)
	if cfg.ARUCO_SIGNS_SAVE_TO_DIR:
		aruco_sign_detector.save_signs_to_dir()

	# ARUCO SIGNS BOTTOM DETECTION
	V.add(aruco_sign_detector,
		  inputs=[f'{cfg.ROAD_CAM}/pure_image', f'{cfg.SIGNS_CAM}/pure_image'],
		  outputs=[f'cam_top/image_array', 'cam_bot/image_array', 'aruco/markerCorners', 'aruco/markerIds', 'aruco/distances'],
		  threaded=False)

	V.add(ArucoDriveController(signs_dict=cfg.ARUCO_SIGNS_DICT),
		  inputs=['aruco/markerCorners', 'aruco/markerIds', 'aruco/distances'],
		  outputs=['aruco/angle', 'aruco/throttle'],
		  threaded=True)

	# ARUCO SIGNS TOP DETECTION
	# V.add(aruco_sign_detector,
	# 	  inputs=[f'{cfg.ROAD_CAM}/pure_image', f'{cfg.ROAD_CAM}/pure_image'],
	# 	  outputs=[f'cam_top/image_array', 'cam_bot/image_array', 'aruco/markerCorners', 'aruco/markerIds', 'aruco/distances'],
	# 	  threaded=False)


	# V.add(aruco_sign_detector,
	# 	  inputs=[f'{cfg.ROAD_CAM}/pure_image', f'{cfg.SIGNS_CAM}/pure_image'],
	# 	  outputs=[f'{cfg.ROAD_CAM}/image_array', f'{cfg.SIGNS_CAM}/image_array', 'aruco/markerCorners', 'aruco/markerIds', 'aruco/distances'],
	# 	  threaded=False)
	#
	# V.add(ArucoDriveController(signs_dict=cfg.ARUCO_SIGNS_DICT),
	# 	  inputs=['aruco/markerCorners', 'aruco/markerIds', 'aruco/distances'],
	# 	  outputs=['aruco/angle', 'aruco/throttle'],
	# 	  threaded=True)


	# add the user input controller(s)
	# - this will add the web controller
	# - it will optionally add any configured 'joystick' controller
	#
	ctr = add_controller(V, cfg)

	# explode the buttons into their own key/values in memory
	V.add(ExplodeDict(V.mem, "web/"), inputs=['web/buttons'])

	# adding a button handler is just adding a part with a run_condition
	# set to the button's name, so it runs when button is pressed.
	V.add(Lambda(lambda v: print('`Delete` not implemented yet')), inputs=["web/remove_data_last_100"],
		  run_condition="web/remove_data_last_100")
	V.add(Lambda(lambda v: print('`Delete all` not implemented yet')), inputs=["web/remove_data_all"],
		  run_condition="web/remove_data_all")

	V.add(Lambda(lambda v: control_flashlight.run(0)), inputs=["web/fl_off"], run_condition="web/fl_off")
	V.add(Lambda(lambda v: control_flashlight.run(100)), inputs=["web/fl_on"], run_condition="web/fl_on")
	V.add(Lambda(lambda v: control_uv_flashlight.run(100)), inputs=["web/uvfl_on"], run_condition="web/uvfl_on")

	V.add(Lambda(lambda v: control_camera_servo.run(15)), inputs=["web/cam_servo_15"], run_condition="web/cam_servo_15")
	V.add(Lambda(lambda v: control_camera_servo.run(30)), inputs=["web/cam_servo_30"], run_condition="web/cam_servo_30")
	V.add(Lambda(lambda v: control_camera_servo.run(45)), inputs=["web/cam_servo_45"], run_condition="web/cam_servo_45")
	V.add(Lambda(lambda v: control_camera_servo.run(60)), inputs=["web/cam_servo_60"], run_condition="web/cam_servo_60")
	V.add(Lambda(lambda v: control_camera_servo.run(75)), inputs=["web/cam_servo_75"], run_condition="web/cam_servo_75")
	V.add(Lambda(lambda v: control_camera_servo.run(90)), inputs=["web/cam_servo_90"], run_condition="web/cam_servo_90")
	V.add(Lambda(lambda v: control_camera_servo.run(105)), inputs=["web/cam_servo_105"], run_condition="web/cam_servo_105")

	# this throttle filter will allow one tap back for esc reverse
	th_filter = ThrottleFilter()
	V.add(th_filter, inputs=['user/throttle'], outputs=['user/throttle'])

	# See if we should even run the pilot module.
	# This is only needed because the part run_condition only accepts boolean
	V.add(PilotCondition(), inputs=['user/mode'], outputs=['run_pilot'])

	def get_record_alert_color(num_records):
		col = (0, 0, 0)
		for count, color in cfg.RECORD_ALERT_COLOR_ARR:
			if num_records >= count:
				col = color
		return col

	class RecordTracker:
		def __init__(self):
			self.last_num_rec_print = 0
			self.dur_alert = 0
			self.force_alert = 0

		def run(self, num_records):
			if num_records is None:
				return 0
			if self.last_num_rec_print != num_records or self.force_alert:
				self.last_num_rec_print = num_records
				if num_records % 10 == 0:
					print("recorded", num_records, "records")
				if num_records % cfg.REC_COUNT_ALERT == 0 or self.force_alert:
					self.dur_alert = num_records // cfg.REC_COUNT_ALERT * cfg.REC_COUNT_ALERT_CYC
					self.force_alert = 0
			if self.dur_alert > 0:
				self.dur_alert -= 1
			if self.dur_alert != 0:
				return get_record_alert_color(num_records)
			return 0

	rec_tracker_part = RecordTracker()
	V.add(rec_tracker_part, inputs=["tub/num_records"], outputs=['records/alert'])

	if cfg.AUTO_RECORD_ON_THROTTLE:
		def show_record_count_status():
			rec_tracker_part.last_num_rec_print = 0
			rec_tracker_part.force_alert = 1

		if isinstance(ctr, JoystickController):
			ctr.set_button_down_trigger('circle',
										show_record_count_status)  # then we are not using the circle button. hijack that to force a record count indication

	def load_model(kl, model_path):
		start = time.time()
		print(f'\nloading model:{model_path}\n')
		kl.load(model_path)
		print('finished loading in %s sec.' % (str(time.time() - start)))

	def load_weights(kl, weights_path):
		start = time.time()
		try:
			print('loading model weights', weights_path)
			kl.model.load_weights(weights_path)
			print('finished loading in %s sec.' % (str(time.time() - start)))
		except Exception as e:
			print(e)
			print('ERR>> problems loading weights', weights_path)

	def load_model_json(kl, json_fnm):
		start = time.time()
		print('loading model json', json_fnm)
		from tensorflow.python import keras
		try:
			with open(json_fnm, 'r') as handle:
				contents = handle.read()
				kl.model = keras.models.model_from_json(contents)
			print('finished loading json in %s sec.' % (str(time.time() - start)))
		except Exception as e:
			print(e)
			print("ERR>> problems loading model json", json_fnm)

	# load and configure model for inference
	#
	if model_path:
		# If we have a model, create an appropriate Keras part
		kl = dk.utils.get_model_by_type(model_type, cfg)

		# get callback function to reload the model
		# for the configured model format
		#
		model_reload_cb = None

		if '.h5' in model_path or '.trt' in model_path or '.tflite' in \
				model_path or '.savedmodel' in model_path or '.pth':
			# load the whole model with weigths, etc
			load_model(kl, model_path)

			def reload_model(filename):
				load_model(kl, filename)

			model_reload_cb = reload_model

		elif '.json' in model_path:
			# when we have a .json extension
			# load the model from there and look for a matching
			# .wts file with just weights
			load_model_json(kl, model_path)
			weights_path = model_path.replace('.json', '.weights')
			load_weights(kl, weights_path)

			def reload_weights(filename):
				weights_path = filename.replace('.json', '.weights')
				load_weights(kl, weights_path)

			model_reload_cb = reload_weights

		else:
			print("ERR>> Unknown extension type on model file!!")
			return

		# this part will signal visual LED, if connected
		V.add(FileWatcher(model_path, verbose=True),
			  outputs=['modelfile/modified'])

		# these parts will reload the model file, but only when ai is running
		# so we don't interrupt user driving
		V.add(FileWatcher(model_path), outputs=['modelfile/dirty'],
			  run_condition="ai_running")
		V.add(DelayedTrigger(100), inputs=['modelfile/dirty'],
			  outputs=['modelfile/reload'], run_condition="ai_running")
		V.add(TriggeredCallback(model_path, model_reload_cb),
			  inputs=["modelfile/reload"], run_condition="ai_running")

		# collect inputs to model for inference
		#
		if cfg.TRAIN_BEHAVIORS:
			bh = BehaviorPart(cfg.BEHAVIOR_LIST)
			V.add(bh, outputs=['behavior/state', 'behavior/label', "behavior/one_hot_state_array"])
			try:
				ctr.set_button_down_trigger('L1', bh.increment_state)
			except:
				pass
			inputs = [f'{cfg.ROAD_CAM}/image_array', "behavior/one_hot_state_array"]
		else:
			inputs = [f'{cfg.ROAD_CAM}/image_array']

		# collect model inference outputs
		outputs = ['pilot/angle', 'pilot/throttle']


		# Add image transformations like crop or trapezoidal mask
		if hasattr(cfg, 'TRANSFORMATIONS') and cfg.TRANSFORMATIONS:
			from donkeycar.pipeline.augmentations import ImageAugmentation
			# V.add(ImageAugmentation(cfg, 'TRANSFORMATIONS'), inputs=['cam/image_array'], outputs=['cam/image_array_trans'])
			# inputs = ['cam/image_array_trans'] + inputs[1:]
			V.add(ImageAugmentation(cfg, 'TRANSFORMATIONS'),
				  inputs=[f'{cfg.ROAD_CAM}/image_array'],
				  outputs=[f'{cfg.ROAD_CAM}/image_array_trans'])
			inputs = [f'{cfg.ROAD_CAM}/image_array_trans'] + inputs[1:]
		V.add(kl, inputs=inputs, outputs=outputs, run_condition='run_pilot')

	# NOTE: when launch throttle is in effect, pilot speed is set to None
	#
	aiLauncher = AiLaunch(cfg.AI_LAUNCH_DURATION, cfg.AI_LAUNCH_THROTTLE, cfg.AI_LAUNCH_KEEP_ENABLED)
	V.add(aiLauncher, inputs=['user/mode', 'pilot/throttle'], outputs=['pilot/throttle'])

	# Choose what inputs should change the car.
	# V.add(DriveMode(), inputs=['user/mode', 'user/angle', 'user/throttle', 'pilot/angle', 'pilot/throttle'], outputs=['angle', 'throttle'])
	V.add(DriveMode(), inputs=['user/mode', 'user/angle', 'user/throttle',
							   'pilot/angle', 'pilot/throttle',
							   'aruco/angle', 'aruco/throttle',
							   ], outputs=['angle', 'throttle'])

	if isinstance(ctr, JoystickController):
		ctr.set_button_down_trigger(cfg.AI_LAUNCH_ENABLE_BUTTON, aiLauncher.enable_ai_launch)

	class AiRunCondition:
		'''
		A bool part to let us know when ai is running.
		'''

		def run(self, mode):
			if mode == "user":
				return False
			return True

	V.add(AiRunCondition(), inputs=['user/mode'], outputs=['ai_running'])

	# add_drivetrain(V, cfg)
	V.add(TwoWheelSteeringThrottle(), inputs=['throttle', 'angle'], outputs=['left/throttle', 'right/throttle'])

	# add tub to save data
	inputs = ['user/angle', 'user/throttle', 'user/mode']
	types = ['float', 'float', 'str']

	if cfg.TRAIN_BEHAVIORS:
		inputs += ['behavior/state', 'behavior/label', "behavior/one_hot_state_array"]
		types += ['int', 'str', 'vector']

	if cfg.ENABLE_AUTOBOT_TELEMETRY:
		#V.add(Sensor_RFID(), inputs=[], outputs=['telemetry/rfid'], threaded=False)
		# inputs += ['telemetry/rfid']
		# types += ['str']

		V.add(Sensor_Battery(), inputs=[], outputs=['telemetry/battery'], threaded=False)
		inputs += ['telemetry/battery']
		types += ['int']

		V.add(Sensor_US(),
			  inputs=[],
			  outputs=['telemetry/us1', 'telemetry/us2', 'telemetry/us3', 'telemetry/us4', 'telemetry/us5'],
			  threaded=False)
		inputs += ['telemetry/us1', 'telemetry/us2', 'telemetry/us3', 'telemetry/us4', 'telemetry/us5']
		types += ['int', 'int', 'int', 'int', 'int']

		V.add(Sensor_IR(),
			  inputs=[],
			  outputs=['telemetry/ir1', 'telemetry/ir2', 'telemetry/ir3', 'telemetry/ir4', 'telemetry/ir5'],
			  threaded=False)
		inputs += ['telemetry/ir1', 'telemetry/ir2', 'telemetry/ir3', 'telemetry/ir4', 'telemetry/ir5']
		types += ['int', 'int', 'int', 'int', 'int']

	current_tub_path = cfg.DATA_PATH
	if cfg.AUTO_CREATE_NEW_TUB:
		current_tub_path = TubHandler(path=cfg.DATA_PATH).create_tub_path()
	meta += getattr(cfg, 'METADATA', [])

	cam_top_tub_writer = TubWriter(f'{current_tub_path}',
								   inputs=inputs + ['cam/image_array', ],
								   types=types + ['image_array', ], metadata=meta)
	V.add(cam_top_tub_writer, inputs=inputs + [f'{cfg.ROAD_CAM}/image_array'], outputs=["tub/num_records"],
		  run_condition='recording')

	print(f"{'-' * 20}\n{'-' * 20}\n{'-' * 20}\n")
	print(f"You can now go to:\n\n<your hostname.local>:{cfg.WEB_CONTROL_PORT}\nto drive your car.\n")
	has_input_controller = hasattr(cfg, "CONTROLLER_TYPE") and cfg.CONTROLLER_TYPE != "mock"
	if has_input_controller:
		print("\nYou can now move your controller to drive your car.\n")
		if isinstance(ctr, JoystickController):
			# ctr.set_tub(tub_writer.tub)
			ctr.set_tub(cam_top_tub_writer.tub)
			ctr.print_controls()

	return V


if __name__ == '__main__':
	logger = logging.getLogger(__file__)
	logging.basicConfig(level=logging.INFO)

	cfg = dk.load_config(myconfig='myconfig.py', config_path='config.py')

	V = dual_cam_drive(cfg=cfg,
					   model_path=f'{cfg.MODELS_PATH}/{cfg.MODEL}' if type(cfg.MODEL) != type(None) else None,
					   model_type=cfg.DEFAULT_MODEL_TYPE)
	V.start(rate_hz=cfg.CAMERA_FRAMERATE)