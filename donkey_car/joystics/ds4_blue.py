
from donkeycar.parts.controller import Joystick, JoystickController


class DS4_Blue(Joystick):
    #An interface to a physical joystick available at /dev/input/js0
    def __init__(self, *args, **kwargs):
        super(DS4_Blue, self).__init__(*args, **kwargs)

            
        self.button_names = {
            0x133 : 'triangle',
            0x132 : 'round',
            0x131 : 'cross',
            0x130 : 'square',
            0x135 : 'R1',
            0x137 : 'R2',
            0x134 : 'L1',
            0x136 : 'L2',
            0x138 : 'share',
            0x139 : 'options',
            0x13d : 'touch-pannel',
            0x13c : 'PS-logo',
            0x13a : 'LS',
            0x13b : 'RS',
        }


        self.axis_names = {
            0x0 : 'LS-hor',
            0x1 : 'LS-ver',
            0x2 : 'RS-hor',
            0x5 : 'RS-ver',
            0x10 : 'pad-hor',
            0x11 : 'pad-ver',
        }



class DS4_BlueController(JoystickController):
    #A Controller object that maps inputs to actions
    def __init__(self, *args, **kwargs):
        super(DS4_BlueController, self).__init__(*args, **kwargs)


    def init_js(self):
        #attempt to init joystick
        try:
            self.js = DS4_Blue(self.dev_fn)
            self.js.init()
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def init_trigger_maps(self):
        #init set of mapping from buttons to function calls
            
        self.button_down_trigger_map = {
            'options' : self.toggle_mode,
            'cross' : self.toggle_manual_recording,
            'round' : self.erase_last_N_records,
            'R1' : self.emergency_stop,
            'L1' : self.toggle_constant_throttle,
            'R2' : self.increase_max_throttle,
            'L2' : self.decrease_max_throttle,
        }


        self.axis_trigger_map = {
            'RS-hor' : self.set_steering,
            'LS-ver' : self.set_throttle,
        }


