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

# Initialize hardware
i2c = I2C(0, sda=Pin(5), scl=Pin(6))
display = SSD1306_I2C(70, 40, i2c)

# Initialize stepper motor with DM332T driver
# Configuration
STEP_PIN = 0     # GPIO pin connected to STEP input on DM332T
DIR_PIN = 2      # GPIO pin connected to DIR input on DM332T  
ENABLE_PIN = 7   # GPIO pin connected to ENA input on DM332T (optional)
HOME_SWITCH_PIN = 3  # GPIO pin connected to home switch

# Set steps per revolution based on DM332T microstepping setting
# Common values: 
# - 200 (full step, no microstepping)
# - 400 (half step)
# - 1600 (1/8 step)
# - 3200 (1/16 step)
STEPS_PER_REV = 3200

# For linear movements - steps per millimeter
# This value needs to be calibrated for your specific setup
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
end_s = Pin(8, Pin.IN, Pin.PULL_UP)

# Initialize UART
uart = UART(1, baudrate=256000)
uart.init(tx=Pin(10), rx=Pin(3))
#r object
r = LD2410()
#state variable
r_d = 0
human = True
# Create a list to store the last readings
distance_history = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # Initialize with zeros
history_index = 0  # Index to track position in the circular buffer

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
#thread_id = _thread.start_new_thread(r_thread, (uart, d_threshold))

# Configure acceleration
s.set_acceleration(33333)  # 1000 steps/second²
s.set_deceleration(11111)  # 1000 steps/second²
s.enable_acceleration()   # Make sure acceleration is enabled
s.enable()

# Home the drawer mechanism
#homing(s, end_s, display, homing_speed)
display_msg(display, "Homing...")
s.home(end_s)
display_msg(display, " HOMED!\nlooking\nor peace")

drawer_closed = True
drawer_fully_opened = False

# Main loop
while True:  
    r.begin(uart)
    r.read()

    current_distance = r.stationary_target_distance() * 10
    distance_history[history_index] = current_distance
    
    #Update index for circular buffer
    history_index = (history_index + 1) % 10
    
    #Calculate the average of the last 10 readings
    r_d = sum(distance_history) / 10

    human = True if r_d < d_threshold else False


    #print(f"{r_d} :: {d_threshold} mm ")

    if human and not drawer_closed:
        # CLOSE DRAWER
        print("close drawer")
        
        # thread_running = False
        
        s.enable()
        s.set_speed(back_speed)

        s.move_to_position_mm(20)

        if end_s.value() == 1 :
            print("homign")
            s.home(end_s)

        drawer_closed = True
        drawer_fully_opened = False
        s.disable()  # Disable stepper
        
        display_msg(display, f"waiting\ninside\nfor{wait_inside/1000}sec")
        sleep_ms(wait_inside)
        display_msg(display, f"waiting\nto be\nalone")

    elif not human and drawer_closed:
        # OPEN DRAWER
        print("open_drawer")
        display_msg(display, f"opening...")
        drawer_closed = False
        s.set_speed(forw_speed)
        s.enable()
        s.move_to_position_mm(d_out)
        display_msg(display, "OPENED! \n WATCHING...")
        s.disable()  # Disable stepper
        # Create a list to store the last readings
        distance_history = [d_threshold,d_threshold,d_threshold,d_threshold,d_threshold,d_threshold,d_threshold,d_threshold,d_threshold,d_threshold]  # Initialize with zeros
        history_index = 0  # Index to track position in the circular buffer

    sleep_ms(100)