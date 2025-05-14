from machine import UART, Pin, I2C
import _thread
import json
from ssd1306 import SSD1306_I2C
from time import sleep_ms
from DM332T import DM332TStepper
from ld2410 import LD2410

# Constants
CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
    "d_threshold": 1000,
    "back_speed": 8100,
    "forw_speed": 1100,
    "wait_inside": 3000,
    "steps_per_rev": 3200,
    "step_per_mm": 25.6,
    "d_out": 220,
    "homing_speed": 500
}

# Global variables for thread communication
radar_distance = 0
motion_detected = False
thread_running = True
drawer_state_change = False
drawer_closed = True

def load_config():
    """Load configuration from JSON file or use defaults"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.loads(f.read())
    except:
        # If file doesn't exist or has errors, create it with defaults
        with open(CONFIG_FILE, 'w') as f:
            f.write(json.dumps(DEFAULT_CONFIG))
        return DEFAULT_CONFIG

def display_msg(display, msg):
    """Display message on OLED screen"""
    display.fill(0)
    display.text("AB_DRAWER", 0, 0, 1)
    y = 12
    for line in msg.split('\n'):
        display.text(line, 0, y, 1)
        y += 10
    display.show()

def homing(stepper, end_switch, display, speed):
    """Home the drawer mechanism"""
    display_msg(display, "Homing...")
    stepper.enable(True)
    stepper.speed(speed)
    stepper.free_run(-1)  # Move toward home switch
    
    # Wait until home switch is triggered
    while end_switch.value() == 1:
        pass
    
    stepper.stop()
    stepper.overwrite_pos(0)
    stepper.target(0)
    display_msg(display, " HOMED!\n")

# Load configuration
config = load_config()
if not config:
    display_msg(display, "Config Error\nUsing defaults")
    config = DEFAULT_CONFIG

# Get configuration variables
d_threshold = config["d_threshold"]
back_speed = config["back_speed"]
forw_speed = config["forw_speed"]
wait_inside = config["wait_inside"]
steps_per_rev = config["steps_per_rev"]
step_per_mm = config["step_per_mm"]
d_out = config["d_out"]
homing_speed = config["homing_speed"]


# Initialize hardware
i2c = I2C(0, sda=Pin(5), scl=Pin(6))
display = SSD1306_I2C(70, 40, i2c)
s = DM332TStepper(
    step_pin=0,
    dir_pin=2,
    enable_pin=7,
    steps_per_rev=3200
)

end_s = Pin(8, Pin.IN, Pin.PULL_UP)

# Initialize UART for radar
# uart = UART(1, baudrate=256000)
# uart.init(tx=Pin(10), rx=Pin(3))

######ACTIVE PART 

# Home the drawer mechanism
#homing(s, end_s, display, homing_speed)
s.enable()

sleep_ms(10)

s.set_speed(5000)

# while True :
#     step_pin.value(0)
#     sleep_ms(1000)
#     step_pin.value(1)
#     sleep_ms(1000)