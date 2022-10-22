# """ 
# My CAR CONFIG 

# This file is read by your car application's manage.py script to change the car
# performance

# If desired, all config overrides can be specified here. 
# The update operation will not touch this file.
# """

# import os
# 
# #PATHS
# CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
# DATA_PATH = os.path.join(CAR_PATH, 'data')
# MODELS_PATH = os.path.join(CAR_PATH, 'models')



WEB_CONTROL_PORT = 9001

CAMERA_TYPE = "CSIC"
# CAMERA_SENSOR_ID = 0
CAMERA_SENSOR_ID = 1

IMAGE_W, IMAGE_H = 320, 240
# IMAGE_W, IMAGE_H = 224, 224

CSIC_CAM_GSTREAMER_FLIP_PARM = 2	 # (0 => none , 4 => Flip horizontally, 6 => Flip vertically)


DRIVE_TRAIN_TYPE = "AUTOBOT"
CONTROLLER_TYPE = 'custom'            #(ps3|ps4|xbox|pigpio_rc|nimbus|wiiu|F710|rc3|MM1|custom) custom will run the my_joystick.py controller written by the `donkey createjs` command
JOYSTICK_MAX_THROTTLE = 1

# # USE_JOYSTICK_AS_DEFAULT, MODEL_TYPE, MODEL = False, None, None
# USE_JOYSTICK_AS_DEFAULT, MODEL_TYPE, MODEL = True, None, None

# tensorflow models: (linear|categorical|tflite_linear|tensorrt_linear)
USE_JOYSTICK_AS_DEFAULT, MODEL_TYPE, MODEL = False, 'tflite_linear', './models/pilot_22-10-20_0.tflite'
# USE_JOYSTICK_AS_DEFAULT, MODEL_TYPE, MODEL = False, 'tflite_inferred', './models/pilot_22-10-20_1.tflite'


# MODEL_TYPE, MODEL = True, 'tflite_linear', './trained_models/pilot_22-10-19_0.tflite'