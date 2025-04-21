import os
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C  
from time import sleep_ms
from stepper import Stepper
import ld2410  # Import the LD2410 library
import json

# JSON file path
CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from JSON file or use defaults"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.loads(f.read())
    except:
        # Default settings
        default_config = {
            "d_threshold": 2000,
            "back_speed": 11000,
            "forw_speed": 1100
        }
        # Save defaults
        with open(CONFIG_FILE, 'w') as f:
            f.write(json.dumps(default_config))
        return default_config

def display_msg(msg : str):
    '''lines as to be seperated by /n'''
    display.fill(0)
    display.text("bouvy_drawer", 5, 0, 1)

    lines = msg.split('\n')

    for i, line in enumerate(lines):
        display.text(line, 0, (i*5)+5, 1)
        
    display.show()

def homing():
    display_msg("homing.../n")
    s.speed(homing_speed) 
    s.free_run(-1) #move forward
    while end_s.value() == 1:
        pass
    display_msg("homed !/n watching.../n")
    s.stop() #stop as soon as the switch is triggered
    s.overwrite_pos(0) #set position as 0 point
    s.target(0) #set the target to the same value to avoid unwanted movement
    
def main():
    """Main program execution"""
    # Load configuration
    config = load_config()
    d_threshold = config["d_threshold"]
    back_speed = config["back_speed"]
    forw_speed = config["forw_speed"]

    # Hardware constants
    steps_per_rev = 3200
    step_per_mm = 25.6 #https://blog.prusa3d.com/calculator_3416/
    d_out = 220 #distance from homing point (mm)
    homing_speed = 500
    wait_inside = 3333 # waiting time after the drawer got inside (mm)

    # Initialize I2C
    i2c = I2C(0, sda=Pin(5), scl=Pin(6))

    #init LD2410 radar
    radar = ld2410.LD2410(uart_num=1, tx_pin=8, rx_pin=9)

    # init embeded display
    display = SSD1306_I2C(70, 40, i2c)

    # Itinialize stepper
    s = Stepper(step_pin=2, dir_pin=1, en_pin=4, invert_dir=True) #stp,dir,en  ###to fix if problem
    end_s = Pin(3, Pin.IN, Pin.PULL_UP)
    homing()

    drawer_open = True

    while True:
        # if radar.is_presence_detected(): # do we need to have detected presence to move ?
        d = radar.get_distance() * 10  # Convert to mm from cm
        
        if d < d_threshold and drawer_open:
            s.enable(True)
            display_msg(f"detected at :{d}/nretracting at:/n{back_speed}stp/sec")
            for vel in range(100,back_speed,100):
                s.speed(vel) 
                s.target(10*step_per_mm) # 3mm from home
                sleep_ms(5)
            display_msg(f"waiting :/n{wait_inside}sec")
            sleep_ms(500) #TODO : change waiting time to actual pos https://pypi.org/project/micropython-stepper/
            homing()
            sleep_ms(wait_inside - 500)
            drawer_open = False
            s.enable(False)

        elif not drawer_open:
            s.enable(True)
            s.track_target() #start stepper again
            s.speed(forw_speed)
            s.target(d_out*step_per_mm) # go to outside pos
            drawer_open = True
            s.enable(False)