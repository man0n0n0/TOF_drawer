####################
# version on the code working on the none dex : multi core operation and 3 uart avaiable
####################

from machine import UART, Pin, I2C
import _thread
import json
from ssd1306 import SSD1306_I2C
from time import sleep_ms
from stepper_dm332t import Stepper
from ld2410 import LD2410

# Constants
CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {"back_speed": 8100,
    "forw_speed": 1100,
    "wait_inside": 3,
    "steps_per_rev": 3200,
    "step_per_mm": 25.6,
    "d_out": 220,
    "homing_speed": 500
}

# Initialize hardware
i2c = I2C(0, sda=Pin(22), scl=Pin(23))
display = SSD1306_I2C(128, 64, i2c)

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

# Load configuration
config = load_config()
if not config:
    display_msg(display, "Config Error\nUsing defaults")
    config = DEFAULT_CONFIG

# Get configuration variables
back_speed = config["back_speed"]
forw_speed = config["forw_speed"]
wait_inside = config["wait_inside"]
steps_per_rev = config["steps_per_rev"]
step_per_mm = config["step_per_mm"]
d_out = config["d_out"]
homing_speed = config["homing_speed"]

# Initialize stepper motor with DM332T driver
s = Stepper(
    step_pin=33,
    dir_pin=25,
    en_pin=26,
    invert_dir=False,
    steps_per_rev=steps_per_rev,
    timer_id = 0
)

# End switch declaration
end_s = Pin(15, Pin.IN, Pin.PULL_UP)

def home(): 
    s.enable(True)
    s.speed(homing_speed) 
    s.free_run(-1) #move forward

    while end_s.value() == 1:
        pass
    
    s.stop() #stop as soon as the switch is triggered
    s.overwrite_pos(0) #set position as 0 point
    s.track_target() #start stepper again

    s.target(0) #set the target to the same value to avoid unwanted movement

    s.target(50)
    sleep_ms(500)
    
# Home the drawer mechanism
display_msg(display, "Homing...")
home()

display_msg(display, " HOMED!\nlooking\nor peace")
drawer_closed = True

# Initialize gpio detection for radar
r1 = Pin(32, Pin.IN) # use the "tx pin" placement (need a manual change on the detector)
r2 = Pin(14, Pin.IN) # use the "tx pin" placement
human = True
human_buffer = [1,1,1]

def isHuman():
    thresh = 0
    for i in range(10):
        thresh = thresh + r2.value() + r1.value() 
        sleep_ms(10)
    return thresh

# Main loop
while True:

    if isHuman() > 5 :
        human = True
    else :
        human = False
    #print(isHuman())

    #logic management
    if human and not drawer_closed:
        # CLOSE DRAWER
        s.enable(True)
        for vel in range(100,back_speed,100):
            s.speed(vel) 
            s.target(10*step_per_mm) 
            sleep_ms(5)
        sleep_ms(500)

        home()

        drawer_closed = True
        s.enable(False)  
        
        display_msg(display, f"waiting\ninside\nfor{wait_inside}sec")
        sleep_ms(wait_inside*1000)
        display_msg(display, f"waiting\nto be\nalone")

    elif not human and drawer_closed:

        # OPEN DRAWER
        drawer_closed = False
        s.enable(True)
        s.speed(forw_speed)
        s.target(d_out*step_per_mm)
        
        while s.get_pos() < d_out*step_per_mm:
            sleep_ms(500)

        sleep_ms(500) #"ensure sensor cool-down"
        s.enable(False)
    
    elif human and drawer_closed:
        while isHuman() > 1 :
            sleep_ms(200)
            #print("WAAIT")
