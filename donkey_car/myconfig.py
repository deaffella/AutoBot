# """
# My CAR CONFIG

# This file is read by your car application's manage.py script to change the car
# performance

# If desired, all config overrides can be specified here.
# The update operation will not touch this file.
# """

import os


AUTO_CREATE_NEW_TUB = False
# AUTO_CREATE_NEW_TUB = True

### PATHS --------------------------------------------------------------------------------------------------------------
# AutoBot/donkey_car/
# DONKEY_CAR_DIR_PATH = CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__ + '/../'))
DONKEY_CAR_DIR_PATH = CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DYNAMIC_DATA_DIR_PATH = os.path.join(CAR_PATH, 'DYNAMIC_DATA')
DATA_PATH = os.path.join(DYNAMIC_DATA_DIR_PATH, 'data')
MODELS_PATH = os.path.join(DYNAMIC_DATA_DIR_PATH, 'models')


DRIVE_LOOP_HZ = 20


### CAMERAS ------------------------------------------------------------------------------------------------------------
CAMERA_TYPE = "JETSON_CSIC"			# (MOCK | JETSON_CSIC | CSIC | PICAM | WEBCAM | CVCAM | V4L | D435 | IMAGE_LIST)
CAMERA_SENSOR_ID = 1				# [0 - stable] \\ [1 -
CSIC_CAM_GSTREAMER_FLIP_PARM = 2	# (0 => none , 4 => Flip horizontally, 6 => Flip vertically)
# IMAGE_W, IMAGE_H = 224, 224		# default
IMAGE_W, IMAGE_H = 320, 240			# custom


### HW AND CONTROLS ----------------------------------------------------------------------------------------------------
# DRIVE_TRAIN_TYPE = "MOCK"			# No drive train.  This can be used to test other features in a test rig.
DRIVE_TRAIN_TYPE = "AUTOBOT"		# MegaBot platform compatible steering-throttle drive control type

CONTROLLER_TYPE = 'custom'          # (ps3|ps4|xbox|pigpio_rc|nimbus|wiiu|F710|rc3|MM1|custom) custom will run the my_joystick.py controller written by the `donkey createjs` command
JOYSTICK_MAX_THROTTLE = 1


### GAMEPAD ------------------------------------------------------------------------------------------------------------
USE_JOYSTICK_AS_DEFAULT = False
# USE_JOYSTICK_AS_DEFAULT = True


### FPS COUNTER ------------------------------------------------------------------------------------------------------------
# SHOW_FPS = False
SHOW_FPS = True
FPS_DEBUG_INTERVAL = 10    # the interval in seconds for printing the frequency info into the shell

HAVE_PERFMON=False
# HAVE_PERFMON=True

### AUTOPILOT MODELS ---------------------------------------------------------------------------------------------------
# tensorflow models: (linear | categorical | tflite_linear | tensorrt_linear)
# pytorch models: (resnet18)
DEFAULT_MODEL_TYPE, MODEL = None, None	# Don't use autopilot
# DEFAULT_MODEL_TYPE, MODEL = 'tflite_linear', 'pilot_22-10-20_0.tflite'


### TRAIN MODELS -------------------------------------------------------------------------------------------------------
SEND_BEST_MODEL_TO_PI = False   #change to true to automatically send best model during training
CREATE_TF_LITE 	 	  = True    # automatically create tflite model in training
CREATE_TENSOR_RT 	  = False   # automatically create tensorrt model in training
MAX_EPOCHS 		 	  = 10
# MAX_EPOCHS 		 	  = 2

# TRANSFORMATIONS to be set
ROI_TRAPEZE_LL 		= 0 						# bottom-left  dot
ROI_TRAPEZE_LR 		= IMAGE_W 					# bottom-right dot
ROI_TRAPEZE_UL 		= int(IMAGE_W / 4) 			# top-left     dot
ROI_TRAPEZE_UR 		= IMAGE_W - ROI_TRAPEZE_UL 	# top-right    dot
ROI_TRAPEZE_MIN_Y 	= 0
ROI_TRAPEZE_MAX_Y 	= IMAGE_H