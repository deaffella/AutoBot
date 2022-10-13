# -*- coding: utf-8 -*-


import os
import serial
import sys
import time
import json
import datetime
import threading

from typing import List, Tuple, Any, Dict

from textwrap import wrap


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



class Threaded_Serial(Base_Serial, threading.Thread):
    """
    - Клас для взаимодействия с контроллером serial.
    - Работает в обособленном потоке.
    """

    def __init__(self,
                 device: str = os.getenv('HW_SERIAL', '/dev/ttyUSB0'),
                 baudrate: int = 115200,
                 daemon=False,
                 ):
        # BaseSerialConnection.__init__(self,
        super().__init__(device=device,
                         baudrate=baudrate)

        self.is_active = True
        threading.Thread.__init__(self, daemon=daemon)

    def parse_message(self, message: str):
        pass

    def stop(self):
        """
        Остановить чтение данных, выполняемое в отдельном потоке (смотри self.run)

        :return:
        """
        self.is_active = False

    def run(self):
        """
        Читает сообщения с self.serial,
            декодирует,
            добавляет в self.sensors,
            в отдельном потоке.

        :return:
        """
        while self.is_active:
            message = self._read()
            self.parse_message(message=message)


class RobotHardware(Threaded_Serial):
    """
    - Клас для взаимодействия с контроллером serial.
    - Работает в обособленном потоке.
    """
    def __init__(self,
                 device: str = os.getenv('HW_SERIAL', '/dev/ttyUSB0'),
                 baudrate: int = 115200,
                 autostart: bool = True,
                 daemon: bool = False,
                 ):
        init_datetime = str(datetime.datetime.now())
        self.__sensor_mask_placeholder = '@'

        self.sensors = {
                # SI  0   1   2   3   4  E
                # SI 014 012 012 013 013 E
                'IR': {
                    'message_mask': "SI",
                    'update_datetime': init_datetime,
                    'last_change_datetime': init_datetime,
                    'value': {int(ir_sensor_idx): None for ir_sensor_idx in range(5)},  # всего 5 сенсоров
                },

                # SI  0   1   2   3   4  E
                # SU 175 065 023 048 047 E
                'US': {
                    'message_mask': "SU",
                    'update_datetime': init_datetime,
                    'last_change_datetime': init_datetime,
                    'value': {int(us_sensor_idx): None for us_sensor_idx in range(5)},  # всего 5 сенсоров
                },

                'BATTERY': {
                    'message_mask': "SA",
                    'update_datetime': init_datetime,
                    'last_change_datetime': init_datetime,
                    'value': None,
                },
                'RFID': {
                    'message_mask': "SF",
                    'update_datetime': init_datetime,
                    'last_change_datetime': init_datetime,
                    'value': None,
                },
            }
        self.devices = {
                'FLASHLIGHT': {
                    'message_mask': f'ZSU{"++"}000{self.__sensor_mask_placeholder}00000E',
                    'update_datetime': init_datetime,
                    'last_change_datetime': init_datetime,
                    'value': None,
                },
                'UV_FLASHLIGHT': {
                    'message_mask': f'ZSU{"++"}{self.__sensor_mask_placeholder}00000000E',
                    'update_datetime': init_datetime,
                    'last_change_datetime': init_datetime,
                    'value': None,
                },
                # todo: Изменить команды согласно новой прошивке от Игоря
                'CAMERA_SERVO': {
                    'message_mask': f'ZSS{self.__sensor_mask_placeholder}0000000000E',
                    'update_datetime': init_datetime,
                    'last_change_datetime': init_datetime,
                    'value': None,
                },
                # todo: Изменить команды согласно новой прошивке от Игоря
                'WHEELS': {
                    # lwdir - left wheel direction ['+', '-']
                    # lwval - left wheel power 0 to 100
                    # rwdir - right wheel direction ['+', '-']
                    # rwval - right wheel power 0 to 100
                    'message_mask': f'ZST0{"lwdir"}00{"lwval"}{"rwdir"}00{"rwval"}E',
                    'update_datetime': init_datetime,
                    'last_change_datetime': init_datetime,
                    'value': {'left': None,
                              'right': None},
                },
            }

        # ThreadedSerialConnection.__init__(self, device=device, baudrate=baudrate)
        super().__init__(device=device, baudrate=baudrate, daemon=daemon)
        if autostart:
            self.start()
            time.sleep(1)

    def parse_message(self, message: str) -> None:
        """
        Распарсить принятое с serial сообщение.
        В случае совпадения сообщения с маской из self.sensors['sensor_name']['message_mask']
        обновляет значение сенсора в self.sensors.
        :param message: Декодированное сообщение с serial.
        :return:        None.
        """
        this_datetime = str(datetime.datetime.now())

        # print(message)

        # Проходимся по по каждой маске для каждого сенсора
        for _sensor_name, _sensor_data in self.sensors.items():
            message_mask = self.sensors[_sensor_name]['message_mask']
            if type(message) == str and len(message):
                if message[:2] == message_mask[:2]:
                    message = str(message)[2:].replace('E', '')
                    # парсинг многосоставных датчиков типа УЗ или ИК, данные с которых приходят в одной строке
                    if _sensor_name in ['IR', 'US']:
                        raw_values = [int(_value) for _value in wrap(message, 3)]
                        new_value = {_sensor_idx: raw_values[_sensor_idx] for _sensor_idx in range(5)}
                    elif _sensor_name in ['BATTERY', ]:
                        new_value = int(message)
                    # RFID
                    else:
                        new_value = str(message)

                    if new_value != self.sensors[_sensor_name]['value']:
                        self.sensors[_sensor_name]['last_change_datetime'] = this_datetime

                    # if _sensor_name not in ['IR', 'US']: print(self.sensors[_sensor_name])
                    self.sensors[_sensor_name]['update_datetime'] = this_datetime
                    self.sensors[_sensor_name]['value'] = new_value

        # print(self.sensors)


    def get_sensor_value(self, sensor_name: str) -> None \
                                                    or str \
                                                    or int \
                                                    or Dict[int, None or int]:
        """
        Получить значение сенсора.
        :param sensor_name: Имя-ключ сенсора из self.sensors.
        :return:            Значение сенсора.
        """
        sensor_name = sensor_name.upper()
        assert sensor_name in self.sensors.keys(), Exception(f"Bad name for `sensor_name`. Must be one of {[i for i in self.sensors.keys()]}")
        return self.sensors[sensor_name]['value']

    def get_device_value(self, device_name: str) -> int or Dict[str, None or int]:
        """
        Получить значение устройства.
        :param device_name: Имя устройства.
        :return:            Значение устройства.
        """
        device_name = device_name.upper()
        assert device_name in self.devices.keys(), Exception(f"Bad name for `device_name`. Must be one of {[i for i in self.devices.keys()]}")
        return self.devices[device_name]['value']

    def set_device_value(self, device_name: str, value: int or Tuple[int, int] or List[int]) -> int or Dict[str, int]:
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

            command_for_serial = self.devices[device_name]['message_mask'].\
                replace(self.__sensor_mask_placeholder,
                        str(1000 + value)[1:])
            new_device_value = value

        elif device_name == 'CAMERA_SERVO':
            assert type(value) is int, Exception(f"Bad type for argument `value`. Must be int from 0 to 100.")
            assert 0 <= value <= 100, Exception(f"Bad value for argument `value`. Must be int from 0 to 100.")


            if value < 2:
                value = 2   # todo: исправить после калибровки сервопривода. Сейчас команда в 0 градусов ставит камеру в 2.

            command_for_serial = self.devices[device_name]['message_mask'].\
                replace(self.__sensor_mask_placeholder,
                        # str(1000 + value)[1:])
                        # str(1000 + value - 15)[1:]) #
                        str(1000 + value)[1:])
            new_device_value = value


        elif device_name == 'WHEELS':
            assert type(value) is tuple or list, Exception(f"Bad type for argument `value`. "
                                                   f"Must be Tuple[left: int, right: int] "
                                                   f"where `left` and `right` in range form -100 to 100.\n"
                                                   f"GOT:\t{type(value)}\t{value}")
            assert -100 <= value["left"] <= 100, Exception(f"Bad type for argument `value`. "
                                                      f"Must be Tuple[left: int, right: int] "
                                                      f"where `left` and `right` in range form -100 to 100.\n"
                                                      f"GOT:\t{type(value)}\t{value}")
            assert -100 <= value["right"] <= 100, Exception(f"Bad type for argument `value`. "
                                                      f"Must be Tuple[left: int, right: int] "
                                                      f"where `left` and `right` in range form -100 to 100.\n"
                                                      f"GOT:\t{type(value)}\t{value}")
            left_wheel_value = str(1000 + abs(value["left"]))[1:]
            right_wheel_value = str(1000 + abs(value["right"]))[1:]

            command_for_serial = self.devices[device_name]['message_mask'].\
                replace("lwdir", '+' if value["left"] >= 0 else '-').\
                replace("lwval", left_wheel_value).\
                replace("rwdir", '+' if value["right"] >= 0 else '-').\
                replace("rwval", right_wheel_value)
            new_device_value = {'left': value["left"],
                                'right': value["right"]}
        else:
            raise NotImplementedError

        # print(self.write(message=command_for_serial), command_for_serial)
        self.write(message=command_for_serial)
        time.sleep(0.01)
        self.write(message=command_for_serial)
        # self.write(message=command_for_serial)

        this_datetime = str(datetime.datetime.now())
        if new_device_value != self.devices[device_name]['value']:
            self.devices[device_name]['last_change_datetime'] = this_datetime
        self.devices[device_name]['update_datetime'] = this_datetime

        self.devices[device_name]['value'] = new_device_value
        return new_device_value

    def get_sensors_and_devices(self) -> dict:
        """
        Получить объединенный словарь из self.sensors и self.devices.
        :return:
        """
        united = {}
        united.update({sensor_name: {
            'value': sensor_value['value'],
            'update_datetime': sensor_value['update_datetime'],
            'last_change_datetime': sensor_value['last_change_datetime'],
        } for (sensor_name, sensor_value) in self.sensors.items()})
        united.update({device_name: {
            'value': device_value['value'],
            'update_datetime': device_value['update_datetime'],
            'last_change_datetime': device_value['last_change_datetime'],
        } for (device_name, device_value) in self.devices.items()})
        return united


class Robot:
    def __init__(self):
        self.hardware = RobotHardware(autostart=True, daemon=True)
        self.wheels_stop()
        self.flashlight_turn_off()
        self.uv_flashlight_turn_off()
        self.camera_servo_set(angle=90)

    def get_all_telemetry(self) -> dict:
        return self.hardware.get_sensors_and_devices()

    def battery_get(self) -> int or None:
        """
        Получить состояние аккумулятора.
        :return: Состояние аккумулятора.
        """
        return self.hardware.get_sensor_value(sensor_name='BATTERY')

    def rfid_get(self) -> str:
        """
        Получить состояние RFID сенсора.
        :return: Состояние RFID сенсора.
        """
        return self.hardware.get_sensor_value('RFID')

    def ir_get(self) -> Dict[int, None or int]:
        """
        Получить состояние IR сенсора.
        :return: Состояние IR сенсора.
        """
        return self.hardware.get_sensor_value('IR')

    def us_get(self) -> Dict[int, None or int]:
        """
        :return: Состояние US сенсора.
        """
        return self.hardware.get_sensor_value('US')


    def flashlight_set(self, value: int) -> int:
        """
        Установить уровень освещенности от 0 до 100 для фонарика.
        :param value: Уровень фонарика.
        :return:      Уровень фонарика
        """
        assert 0 <= value <= 100, Exception('Уровень освещенности должен быть от 0 до 100.')
        return self.hardware.set_device_value(device_name='FLASHLIGHT', value=value)

    def flashlight_get(self) -> int:
        """
        Получить уровень освещенности фонарика.
        :return:      Уровень освещенности фонарика
        """
        return self.hardware.get_device_value(device_name='FLASHLIGHT')

    def flashlight_turn_on(self) -> int:
        """
        Включить фонарик, установив уровень освещенности на 100.
        :return: Уровень фонарика.
        """
        return self.flashlight_set(value=100)

    def flashlight_turn_off(self) -> int:
        """
        Выключить фонарик, установив уровень освещенности на 0.
        :return: Установить уровень фонарика.
        """
        return self.flashlight_set(value=0)


    def uv_flashlight_set(self, value: int) -> int:
        """
        Установить уровень освещенности от 0 до 100 для УФ фонарика.
        :param value: Уровень УФ фонарика.
        :return:      Уровень УФ фонарика
        """
        assert 0 <= value <= 100, Exception('Уровень освещенности должен быть от 0 до 100.')
        return self.hardware.set_device_value(device_name='UV_FLASHLIGHT', value=value)

    def uv_flashlight_get(self) -> int:
        """
        Получить уровень освещенности УФ фонарика.
        :return:      Уровень освещенности УФ фонарика
        """
        return self.hardware.get_device_value(device_name='UV_FLASHLIGHT')

    def uv_flashlight_turn_on(self) -> int:
        """
        Включить УФ фонарик, установив уровень освещенности на 100.
        :param value: Уровень УФ фонарика.
        """
        return self.uv_flashlight_set(value=100)

    def uv_flashlight_turn_off(self) -> int:
        """
        Выключить УФ фонарик, установив уровень освещенности на 0.
        :param value: Уровень УФ фонарика.
        """
        return self.uv_flashlight_set(value=0)


    def camera_servo_set(self, angle: int) -> int:
        """
        Установить сервопривод камеры от вертикальной оси на угол.
        Угол поворота должен быть от 45 до 140.
        :param angle: Угол поворота от вертикальной оси.
        :return:      Угол поворота от вертикальной оси
        """
        assert 0 <= angle <= 100, Exception('Угол поворота должен быть от 45 до 140.')
        return self.hardware.set_device_value(device_name='CAMERA_SERVO', value=angle)

    def camera_servo_get(self) -> int:
        """
        Получить положение сервопривода.
        :return: Угол поворота сервопривода от вертикальной оси.
        """
        return self.hardware.get_device_value(device_name='CAMERA_SERVO')


    def wheels_set(self, left: int, right: int) -> Dict[str, int]:
        """
        Установить значения мощности для левых и правых колес.
        Значения должны быть в промежутке от -100 до 100.
        :param left:  Значения мощности для левых колес.
        :param right: Значения мощности для правых колес.
        :return:      Значения мощности для левых и правых колес.
        """
        assert -100 <= left <= 100, Exception('Значение мощности для левых колес должно быть от -100 до 100.')
        assert -100 <= right <= 100, Exception('Значение мощности для правых колес должно быть от -100 до 100.')
        return self.hardware.set_device_value(device_name='WHEELS', value={"left": left, "right": right})

    def wheels_get(self)  -> Dict[str, int]:
        """
        Получить значения мощности для левых и правых колес.
        :return: Значения мощности для левых и правых колес.
        """
        return self.hardware.get_device_value(device_name='WHEELS')

    def wheels_stop(self) -> Dict[str, int]:
        """
        Остановить робота.
        :return: Значения мощности для обоих колес.
        """
        return self.wheels_set(left=0, right=0)

    def wheels_direction(self, direction: str) -> Dict[str, int]:
        """
        Управление движением робота с помощью указания направления.
        :param direction: Направление движения [`left`, `right`, `forward`, `backward`, `stop`].
        :return:          Значения мощности для обоих колес.
        """
        allowed_directions = ['left', 'right', 'forward', 'backward', 'stop']
        direction = direction.lower()
        assert direction in allowed_directions, Exception(f'Направление движения `direction` должно быть одним из: [{allowed_directions}]')
        if direction == 'left':
            left  = -100
            right = 100
        elif direction == 'right':
            left  = 100
            right = -100
        elif direction == 'forward':
            left  = 100
            right = 100
        elif direction == 'backward':
            left  = -100
            right = -100
        else:
            left  = 0
            right = 0
        return self.wheels_set(left=left, right=right)

    def wheels_direction_ir(self, direction: str) -> Dict[str, int]:
        """
        Управление движением робота с помощью указания направления
        в случае ориентирования по ИК сенсорам.
        :param direction: Направление движения [`left`, `right`, `forward`, `backward`, `stop`].
        :return:          Значения мощности для обоих колес.
        """
        allowed_directions = ['left', 'right', 'forward', 'backward', 'stop']
        direction = direction.lower()
        assert direction in allowed_directions, Exception(f'Направление движения `direction` должно быть одним из: [{allowed_directions}]')
        if direction == 'left':
            left  = -90
            right = 100
        elif direction == 'right':
            left  = 90
            right = -100
        elif direction == 'forward':
            left  = 90
            right = 90
        elif direction == 'backward':
            left  = -90
            right = -90
        else:
            left  = 0
            right = 0
        return self.wheels_set(left=left, right=right)

    def wheels_direction_us(self, direction: str) -> Dict[str, int]:
        """
        Управление движением робота с помощью указания направления
        в случае ориентирования по УЗ сенсорам.
        :param direction: Направление движения [`left`, `right`, `forward`, `backward`, `stop`].
        :return:          Значения мощности для обоих колес.
        """
        allowed_directions = ['left', 'right', 'forward', 'backward', 'stop']
        direction = direction.lower()
        assert direction in allowed_directions, Exception(f'Направление движения `direction` должно быть одним из: [{allowed_directions}]')
        if direction == 'left':
            left  = -80
            right = 90
        elif direction == 'right':
            left  = 80
            right = -90
        elif direction == 'forward':
            left  = 80
            right = 80
        elif direction == 'backward':
            left  = -80
            right = -80
        else:
            left  = 0
            right = 0
        return self.wheels_set(left=left, right=right)

    def wheels_direction_uv(self, direction: str) -> Dict[str, int]:
        """
        Управление движением робота с помощью указания направления
        в случае ориентирования по УФ сенсорам.
        :param direction: Направление движения ['left',
                                                'sharply_left',
                                                'softly_left',
                                                'right',
                                                'sharply_right',
                                                'softly_right',
                                                'forward',
                                                'backward',
                                                'stop'].
        :return:          Значения мощности для обоих колес.
        """
        allowed_directions = ['left',
                              'sharply_left',
                              'softly_left',
                              'right',
                              'sharply_right',
                              'softly_right',
                              'forward',
                              'backward',
                              'stop']
        direction = direction.lower()
        assert direction in allowed_directions, Exception(f'Направление движения `direction` должно быть одним из: [{allowed_directions}]')
        if direction == 'left':
            left  = -100
            right = 100
        elif direction == 'sharply_left':
            left  = 0
            right = 100
        elif direction == 'softly_left':
            left  = 90
            right = 100
        elif direction == 'right':
            left  = 100
            right = -100
        elif direction == 'sharply_right':
            left  = 100
            right = 0
        elif direction == 'softly_right':
            left  = 100
            right = 90
        elif direction == 'forward':
            left  = 80
            right = 80
        elif direction == 'backward':
            left  = -80
            right = -80
        else:
            left  = 0
            right = 0
        return self.wheels_set(left=left, right=right)


if __name__=='__main__':

    hardware = RobotHardware(autostart=True, daemon=True)
    value = 100
    print(hardware.get_device_value(device_name='FLASHLIGHT'))
    print(hardware.set_device_value(device_name='FLASHLIGHT', value=value))
    time.sleep(1)
    print(hardware.get_device_value(device_name='FLASHLIGHT'))

    print(hardware.get_device_value(device_name='UV_FLASHLIGHT'))
    print(hardware.set_device_value(device_name='UV_FLASHLIGHT', value=value))
    time.sleep(1)
    print(hardware.get_device_value(device_name='UV_FLASHLIGHT'))
    print(hardware.set_device_value(device_name='UV_FLASHLIGHT', value=0))


    # s = Base_Serial()
    # while True:
    #     r = s._read()
    #     print(r)