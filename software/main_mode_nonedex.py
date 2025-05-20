####################
# version on the code working on the none dex : multi core operation and 3 uart avaiable
####################

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
    "d_threshold": 500,
    "back_speed": 8100,
    "forw_speed": 1100,
    "wait_inside": 3000,
    "steps_per_rev": 3200,
    "step_per_mm": 25.6,
    "d_out": 220,
    "homing_speed": 500
}

# Thread state variables
r_d = 0
thread_running = True
human = True

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

def r_thread(threshold):
    """Thread function to continuously read radar data"""
    global r_d, human, thread_running
    # Initialize UART
    uart1 = UART(1, baudrate=256000)
    uart1.init(tx=Pin(12), rx=Pin(32))

    uart2 = UART(2, baudrate=256000)
    uart2.init(tx=Pin(27), rx=Pin(14))
    
    #r objects
    r1 = LD2410()
    r1.begin(uart1)

    r2 = LD2410()
    r2.begin(uart2)

    # Create a list to store the last readings
    # distance_history = [0, 0, 0]  # Initialize with zeros
    # history_index = 0  # Index to track position in the circular buffer

    while thread_running:
        # Read radar data
        r1.read()
        r2.read()

        # #### avenraging value 
        # # Store the current reading in the history
        # current_distance = max(r1.moving_target_distance(),r2.moving_target_distance()) * 10
        # distance_history[history_index] = current_distance
        
        # #Update index for circular buffer
        # history_index = (history_index + 1) % 3
        
        # #Calculate the average of the last 3 readings
        # r_d = sum(distance_history) / 3

        r_d = min(r1.moving_target_distance(),r2.moving_target_distance()) * 10 
        human = True if r_d < threshold else False
        sleep_ms(20)  # Small delay to prevent CPU hogging

# Initialize hardware
i2c = I2C(0, sda=Pin(22), scl=Pin(23))
display = SSD1306_I2C(128, 64, i2c)

# Initialize stepper motor with DM332T driver
STEP_PIN = 33    # GPIO pin connected to STEP input on DM332T
DIR_PIN = 25    # GPIO pin connected to DIR input on DM332T  
ENABLE_PIN = 26  # GPIO pin connected to ENA input on DM332T (optional)
HOME_SWITCH_PIN = 15  # GPIO pin connected to home switch

STEPS_PER_REV = 3200

# For linear movements - steps per millimeter
# For a belt drive with 20 teeth pulley, 2mm pitch, and 1/16 microstepping:
# (200 steps/rev × 16 microsteps) ÷ (20 teeth × 2mm) = 80 steps/mm
STEPS_PER_MM = 25.6

s = DM332TStepper(
    step_pin=STEP_PIN,
    dir_pin=DIR_PIN,
    enable_pin=ENABLE_PIN,
    invert_dir=True,
    steps_per_rev=STEPS_PER_REV,
    steps_per_mm=STEPS_PER_MM
)

# End switch declaration
end_s = Pin(HOME_SWITCH_PIN, Pin.IN, Pin.PULL_UP)

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

# Set steps per mm in the stepper driver
s.steps_per_mm = step_per_mm

# Start radar thread
thread_id = _thread.start_new_thread(r_thread, [d_threshold])

# Configure acceleration
s.set_acceleration(333333)  # stp*sec⁻2
s.set_deceleration(99999)  
s.enable_acceleration()   
s.enable()

# Home the drawer mechanism
display_msg(display, "Homing...")
s.home(end_s)
display_msg(display, " HOMED!\nlooking\nor peace")
drawer_closed = True

# Main loop
while True: 
    if human and not drawer_closed:
        # CLOSE DRAWER
        s.enable()
        s.move_to_position_mm(20)

        if end_s.value() == 1 :
            display_msg(display, "Homing...")
            s.home(end_s)
            display_msg(display, " HOMED!\nlooking\nor peace")

        drawer_closed = True
        s.disable()  
        
        display_msg(display, f"waiting\ninside\nfor{wait_inside/1000}sec")
        sleep_ms(wait_inside)
        display_msg(display, f"waiting\nto be\nalone")

    elif not human and drawer_closed:
        # OPEN DRAWER
        display_msg(display, f"opening...")
        drawer_closed = False
        s.set_speed(forw_speed)
        s.enable()

        s.move_to_position_mm(d_out)
        
        display_msg(display, "OPENED! \n WATCHING...")
        s.set_speed(back_speed) # preprare speed for next operation
        s.disable() 

    # else :
    #     if not r_d == 0 :
    #         display_msg(display, f"radar distance : \n {r_d}mm")
    #     else : 
    #         # if a r value is 0 radar is missing OR something is blocking in front of it (unactive state :: 0 mm value)
    #         display_msg(display, f"\n!!RADAR ERROR!! \ncheck ld2410")

    sleep_ms(20)