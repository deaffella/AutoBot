#!/usr/bin/env python3

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

# from manage import add_drivetrain
from parts.cameras import Jetson_CSI_Camera
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
		  inputs=['cam_top/image_array', 'cam_bot/image_array', 'tub/num_records', 'user/mode', 'recording'],
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
			  # inputs=[input_image, 'user/mode', 'recording'],
			  # inputs=['cam_top/image_array', 'cam_bot/image_array', 'user/mode', 'recording'],
			  inputs=['cam_top/image_array', 'user/mode', 'recording'],
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
	# def run(self, mode, user_angle, user_throttle, pilot_angle, pilot_throttle):
	def run(self, mode, user_angle, user_throttle, pilot_angle, pilot_throttle, aruco_angle, aruco_throttle):
		if mode == 'user':
			return user_angle, user_throttle
		elif mode == 'local_angle':
			return pilot_angle if pilot_angle else 0.0, user_throttle
		elif mode == 'aruco_single':
			# return user_angle, user_throttle
			return aruco_angle, aruco_throttle

		else:
			return pilot_angle if pilot_angle else 0.0, \
				   pilot_throttle * cfg.AI_THROTTLE_MULT \
					   if pilot_throttle else 0.0


class ArucoDriveController(object):
	angle = 0
	throttle = 0

	def run(self, markerCorners: np.ndarray, markerIds: np.ndarray) -> (float, float):
		if type(markerIds) != np.ndarray or type(markerIds) != np.ndarray:
			return 0, 0
		ids = markerIds.tolist()

		if 0 in ids:
			# stop
			angle = 0
			throttle = 0
		elif 1 in ids:
			# start
			angle = 0
			throttle = 1
		elif 2 in ids:
			# cross_left
			angle = -0.8
			throttle = 1
		elif 4 in ids:
			# cross_right
			angle = 0.8
			throttle = 1
		else:
			angle = 0
			throttle = 0

		self.angle = angle
		self.throttle = throttle
		return self.angle, self.throttle

	def shutdown(self):
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
								image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH,
								capture_width=cfg.IMAGE_W, capture_height=cfg.IMAGE_H,
								framerate=cfg.CAMERA_FRAMERATE, gstreamer_flip=cfg.CSIC_CAM_GSTREAMER_FLIP_PARM)
	V.add(cam_top, inputs=[], outputs=['cam_top/image_array'], threaded=True)

	# setup bottom camera
	cam_bot = Jetson_CSI_Camera(sensor_id=1,
								image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH,
								capture_width=cfg.IMAGE_W, capture_height=cfg.IMAGE_H,
								framerate=cfg.CAMERA_FRAMERATE, gstreamer_flip=cfg.CSIC_CAM_GSTREAMER_FLIP_PARM)
	V.add(cam_bot, inputs=[],
		  # outputs=['cam_bot/image_array'],
		  outputs=['cam_bot/pure_image'],
		  threaded=True)

	# fps console counter
	if cfg.SHOW_FPS:
		from donkeycar.parts.fps import FrequencyLogger
		V.add(FrequencyLogger(cfg.FPS_DEBUG_INTERVAL), outputs=["fps/current", "fps/fps_list"])

	aruco_sign_detector = ArucoSignDetector(signs_dict=cfg.ARUCO_SIGNS_DICT)
	if cfg.ARUCO_SIGNS_SAVE_TO_DIR:
		aruco_sign_detector.save_signs_to_dir()

	V.add(aruco_sign_detector,
		  inputs=['cam_bot/pure_image'],
		  outputs=['cam_bot/image_array', 'aruco/markerCorners', 'aruco/markerIds'],
		  threaded=False)

	V.add(ArucoDriveController(),
		  inputs=['aruco/markerCorners', 'aruco/markerIds'],
		  outputs=['aruco/angle', 'aruco/throttle'],
		  threaded=False)

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
	# V.add(Lambda(lambda v: remove_collected_data(cfg.DATA_PATH)), inputs=["web/remove_data_all"],	run_condition="web/remove_data_all")

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

			# inputs = ['cam/image_array', "behavior/one_hot_state_array"]
			inputs = ['cam_top/image_array', "behavior/one_hot_state_array"]

		else:
			inputs = ['cam_top/image_array']

		# collect model inference outputs
		#
		outputs = ['pilot/angle', 'pilot/throttle']

		if cfg.TRAIN_LOCALIZER:
			outputs.append("pilot/loc")

		# Add image transformations like crop or trapezoidal mask
		#
		if hasattr(cfg, 'TRANSFORMATIONS') and cfg.TRANSFORMATIONS:
			from donkeycar.pipeline.augmentations import ImageAugmentation
			# V.add(ImageAugmentation(cfg, 'TRANSFORMATIONS'), inputs=['cam/image_array'], outputs=['cam/image_array_trans'])
			# inputs = ['cam/image_array_trans'] + inputs[1:]
			V.add(ImageAugmentation(cfg, 'TRANSFORMATIONS'), inputs=['cam_top/image_array'],
				  outputs=['cam_top/image_array_trans'])
			inputs = ['cam_top/image_array_trans'] + inputs[1:]
		V.add(kl, inputs=inputs, outputs=outputs, run_condition='run_pilot')

	# # stop at a stop sign
	# #
	# if cfg.STOP_SIGN_DETECTOR:
	# 	from donkeycar.parts.object_detector.stop_sign_detector \
	# 		import StopSignDetector
	# 	V.add(StopSignDetector(cfg.STOP_SIGN_MIN_SCORE,
	# 						   cfg.STOP_SIGN_SHOW_BOUNDING_BOX,
	# 						   cfg.STOP_SIGN_MAX_REVERSE_COUNT,
	# 						   cfg.STOP_SIGN_REVERSE_THROTTLE),
	# 		  # inputs=['cam/image_array', 'pilot/throttle'], outputs=['pilot/throttle', 'cam/image_array'])
	# 		  inputs=['cam_top/image_array', 'pilot/throttle'], outputs=['pilot/throttle', 'cam_top/image_array'])
	# 	V.add(ThrottleFilter(),
	# 		  inputs=['pilot/throttle'], outputs=['pilot/throttle'])

	# to give the car a boost when starting ai mode in a race.
	# This will also override the stop sign detector so that
	# you can start at a stop sign using launch mode, but
	# will stop when it comes to the stop sign the next time.
	#
	# NOTE: when launch throttle is in effect, pilot speed is set to None
	#
	aiLauncher = AiLaunch(cfg.AI_LAUNCH_DURATION, cfg.AI_LAUNCH_THROTTLE, cfg.AI_LAUNCH_KEEP_ENABLED)
	V.add(aiLauncher, inputs=['user/mode', 'pilot/throttle'], outputs=['pilot/throttle'])

	# Choose what inputs should change the car.
	# V.add(DriveMode(), inputs=['user/mode', 'user/angle', 'user/throttle', 'pilot/angle', 'pilot/throttle'], outputs=['angle', 'throttle'])
	V.add(DriveMode(), inputs=['user/mode', 'user/angle', 'user/throttle', 'pilot/angle', 'pilot/throttle',
							   'aruco/angle', 'aruco/throttle'], outputs=['angle', 'throttle'])

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

	# Ai Recording
	class AiRecordingCondition:
		'''
		return True when ai mode, otherwize respect user mode recording flag
		'''

		def run(self, mode, recording):
			if mode == 'user':
				return recording
			return True

	if cfg.RECORD_DURING_AI:
		V.add(AiRecordingCondition(), inputs=['user/mode', 'recording'], outputs=['recording'])

	# add_drivetrain(V, cfg)
	V.add(TwoWheelSteeringThrottle(), inputs=['throttle', 'angle'], outputs=['left/throttle', 'right/throttle'])

	# add tub to save data
	inputs = ['user/angle', 'user/throttle', 'user/mode']
	types = ['float', 'float', 'str']

	if cfg.TRAIN_BEHAVIORS:
		inputs += ['behavior/state', 'behavior/label', "behavior/one_hot_state_array"]
		types += ['int', 'str', 'vector']

	if cfg.RECORD_DURING_AI:
		inputs += ['pilot/angle', 'pilot/throttle']
		types += ['float', 'float']

	if cfg.HAVE_PERFMON:
		from donkeycar.parts.perfmon import PerfMonitor
		mon = PerfMonitor(cfg)
		perfmon_outputs = ['perf/cpu', 'perf/mem', 'perf/freq']
		inputs += perfmon_outputs
		types += ['float', 'float', 'float']
		V.add(mon, inputs=[], outputs=perfmon_outputs, threaded=True)

	if cfg.ENABLE_AUTOBOT_TELEMETRY:
		V.add(Sensor_RFID(), inputs=[], outputs=['telemetry/rfid'], threaded=False)
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

	cam_top_tub_writer = TubWriter(f'{current_tub_path}', inputs=inputs + ['cam/image_array', ],
								   types=types + ['image_array', ], metadata=meta)
	V.add(cam_top_tub_writer, inputs=inputs + ['cam_top/image_array'], outputs=["tub/num_records"],
		  run_condition='recording')

	# cam_bot_tub_writer = TubWriter(f'{current_tub_path}/cam_bot', inputs=inputs + ['cam/image_array', ], types=types + ['image_array', ], metadata=meta)
	# V.add(cam_bot_tub_writer, inputs=inputs + ['cam_bot/image_array'], outputs=["tub/num_records"], run_condition='recording')

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
	logger = logging.getLogger(__name__)
	logging.basicConfig(level=logging.INFO)

	cfg = dk.load_config(myconfig='myconfig.py', config_path='config.py')

	V = dual_cam_drive(cfg=cfg,
					   model_path=f'{cfg.MODELS_PATH}/{cfg.MODEL}' if type(cfg.MODEL) != type(None) else None,
					   model_type=cfg.DEFAULT_MODEL_TYPE)
	V.start(rate_hz=cfg.CAMERA_FRAMERATE)