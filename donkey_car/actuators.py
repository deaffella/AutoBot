import os
import serial
import sys
import time

from typing import List, Tuple, Any, Dict

import logging

import donkeycar as dk
from donkeycar.utils import clamp




logger = logging.getLogger(__name__)



class Base_Serial():
	"""
	- Базовый клас для взаимодействия с контроллером serial.
	"""

	def __init__(self,
				 device: str = os.getenv('HW_SERIAL', '/dev/ttyUSB0'),
				 baudrate: int = 115200,
				 ):
		self.device = device
		self.baudrate = baudrate

		self.serial = serial.Serial(self.device)
		self.serial.baudrate = self.baudrate

	def __encode_message(self,
						 message: str) -> bytes:
		"""
		Кодировать сообщение.

		:param msg: str
		:return:
		"""
		encoded_message = message.encode('utf-8')
		return encoded_message

	def __decode_message(self,
						 bytes_message: bytes) -> str:
		"""
		Декодировать сообщение.

		:param bytes_message: bytes
		:return:
		"""
		# decoded = bytes_message.decode(encoding='utf-8')
		decoded = bytes_message.decode(encoding='utf-8', errors='ignore')
		if len(decoded):
			decoded = decoded.replace('\r', '').replace('\n', '')
		return decoded

	def __write_bytes_to_serial(self,
								encoded_message: bytes) -> bool:
		"""
		Отправить кодированное сообщение на контроллер self.serial.

		:param encoded_message: bytes
		:return:
		"""
		# try:
		# self.serial.write(encoded_message)
		# return True
		return self.serial.write(encoded_message)

		# except:
		#     return False

	def __read_bytes_from_serial(self) -> bytes or None:
		"""
		Считать с контроллера self.serial кодированное сообщение .

		:return:
		"""
		# try:
		data_from_serial = self.serial.readline()
		# except serial.serialutil.SerialException:
		#     data_from_serial = None
		return data_from_serial

	def _read(self) -> str:
		"""
		Считать с контроллера self.serial сообщение и декодировать.

		:return:
		"""
		encoded_message = self.__read_bytes_from_serial()
		if type(encoded_message) == type(None):
			# return None
			return ""
		return self.__decode_message(bytes_message=encoded_message)

	def write(self, message: str) -> bool:
		"""
		Кодировать и отправить сообщение на контроллер self.serial.

		:param message:
		:return:
		"""
		# try:
		encoded_message = self.__encode_message(message=message)
		return self.__write_bytes_to_serial(encoded_message=encoded_message)
		# except:
		#     return False


class AutoBot_Serial(Base_Serial):
	def __init__(self,
				 device: str = os.getenv('HW_SERIAL', '/dev/ttyUSB0'),
				 baudrate: int = 115200,
				 ):
		self.__sensor_mask_placeholder = '@'
		self.devices = {
			'FLASHLIGHT': 		f'ZSU{"++"}000{self.__sensor_mask_placeholder}00000E',
			'UV_FLASHLIGHT': 	f'ZSU{"++"}{self.__sensor_mask_placeholder}00000000E',
			'CAMERA_SERVO': 	f'ZSS{self.__sensor_mask_placeholder}0000000000E',
			'WHEELS': 			f'ZST0{"lwdir"}00{"lwval"}{"rwdir"}00{"rwval"}E',
		}
		Base_Serial.__init__(self, device=device, baudrate=baudrate)

	def set_device_value(self,
						 device_name: str,
						 value: int or Dict[str, int]) -> None:
		"""
		Установить значение для устройства.
		:param device_name: Имя устройства.
		:param value:       Значение устройства.
		:return:            Новое значение устройства.
		"""
		device_name = device_name.upper()
		assert device_name in self.devices.keys(), \
			Exception(f"Bad name for argument `device_name`. Must be one of [{[i for i in self.devices.keys()]}]")

		if device_name in ['FLASHLIGHT', 'UV_FLASHLIGHT']:
			assert type(value) is int, Exception(f"Bad type for argument `value`. Must be int from 0 to 100.\n"
												 f"GOT:\t{type(value)}\t{value}")
			assert 0 <= value <= 100, Exception(f"Bad value for argument `value`. Must be int from 0 to 100.\n"
												f"GOT:\t{type(value)}\t{value}")

			command_for_serial = self.devices[device_name].replace(self.__sensor_mask_placeholder,
																   str(1000 + value)[1:])

		elif device_name == 'CAMERA_SERVO':
			assert type(value) is int, Exception(f"Bad type for argument `value`. Must be int from 0 to 100.")
			assert 0 <= value <= 100, Exception(f"Bad value for argument `value`. Must be int from 0 to 100.")

			if value < 2:
				value = 2  # todo: исправить после калибровки сервопривода. Сейчас команда в 0 градусов ставит камеру в 2.

			command_for_serial = self.devices[device_name].replace(self.__sensor_mask_placeholder,
																   # str(1000 + value)[1:])
																   # str(1000 + value - 15)[1:])
																   str(1000 + value)[1:])

		elif device_name == 'WHEELS':
			assert type(value) == dict, Exception(f"Bad type for argument `value`. "
												  f"Must be Tuple[left: int, right: int] "
												  f"where `left` and `right` in range form -100 to 100.\n"
												  f"GOT:\t{type(value)}\t{value}")
			assert -100 <= value["left"] <= 100, Exception(f"Bad type for argument `value`. "
														   f"Must be Dict[str, int] "
														   f"where `left` and `right` in range form -100 to 100.\n"
														   f"GOT:\t{type(value)}\t{value}")
			assert -100 <= value["right"] <= 100, Exception(f"Bad type for argument `value`. "
															f"Must be Dict[str, int] "
															f"where `left` and `right` in range form -100 to 100.\n"
															f"GOT:\t{type(value)}\t{value}")
			left_wheel_value = str(1000 + abs(value["left"]))[1:]
			right_wheel_value = str(1000 + abs(value["right"]))[1:]

			command_for_serial = self.devices[device_name]. \
				replace("lwdir", '+' if value["left"] >= 0 else '-'). \
				replace("lwval", left_wheel_value). \
				replace("rwdir", '+' if value["right"] >= 0 else '-'). \
				replace("rwval", right_wheel_value)
		else:
			raise NotImplementedError

		# print(self.write(message=command_for_serial), command_for_serial)
		self.write(message=command_for_serial)




class AutoBot_Actuator(object):
	def __init__(self,
				 device: str = os.getenv('HW_SERIAL', '/dev/ttyUSB0'),
				 baudrate: int = 115200,
				 zero_throttle: float = 0,
				 max_duty: float = 1):
		"""
		zero_throttle: values at or below zero_throttle are treated as zero.
		max_duty: the maximum duty cycle that will be send to the motors
		NOTE: if pin_forward and pin_backward are both at duty_cycle == 0,
			then the motor is 'detached' and will glide to a stop.
			if pin_forward and pin_backward are both at duty_cycle == 1,
			then the motor will be forcibly stopped (can be used for braking)
		max_duty is from 0 to 1 (fully off to fully on). I've read 0.9 is a good max.
		"""
		self.device = device
		self.baudrate = baudrate
		self.serial_port = None
		self.connect_to_serial()

		self.running = True

		self.zero_throttle = zero_throttle
		self.max_duty = max_duty

		self.left_throttle = 0
		self.right_throttle = 0

		self.serial_port.set_device_value(device_name='FLASHLIGHT', value=100)	# turn on flashlight

		# self.serial_port.set_device_value(device_name='CAMERA_SERVO', value=50) # set camera servo to initial pose
		# self.serial_port.set_device_value(device_name='CAMERA_SERVO', value=70) # set camera servo to initial pose
		self.serial_port.set_device_value(device_name='CAMERA_SERVO', value=80) # set camera servo to initial pose


	def connect_to_serial(self):
		self.serial_port = AutoBot_Serial(device=self.device, baudrate=self.baudrate)

	def run(self,
			left_throttle: float,
			right_throttle: float,
			) -> None:
		if left_throttle is None:
			logger.warn("`left_throttle` is None")
			return
		if right_throttle is None:
			logger.warn("`right_throttle` is None")
			return

		if left_throttle > 1 or left_throttle < -1:
			logger.warn(f"`left_throttle is {left_throttle}, but it must be between 1(forward) and -1(reverse)")

		if right_throttle > 1 or right_throttle < -1:
			logger.warn(f"`right_throttle is {right_throttle}, but it must be between 1(forward) and -1(reverse)")

		self.left_throttle = dk.utils.map_range_float(left_throttle, -1, 1, -self.max_duty, self.max_duty)
		self.right_throttle = dk.utils.map_range_float(right_throttle, -1, 1, -self.max_duty, self.max_duty)

		left_wheel = int(self.left_throttle * 100)
		right_wheel = int(self.right_throttle * 100)

		self.serial_port.set_device_value(device_name='WHEELS', value={'left': left_wheel, 'right': right_wheel})

	def shutdown(self):
		self.serial_port.set_device_value(device_name='WHEELS', value={'left': 0, 'right': 0})
		time.sleep(0.1)
		self.serial_port.set_device_value(device_name='FLASHLIGHT', value=0)	# turn off flashlight
		time.sleep(0.1)
		self.serial_port.set_device_value(device_name='CAMERA_SERVO', value=50)


