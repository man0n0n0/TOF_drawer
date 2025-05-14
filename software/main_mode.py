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
radar_d = 0
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
    stepper.enable()
    stepper.set_speed(speed)
    start_continuous(-1) # Move toward home switch
    
    # Wait until home switch is triggered
    while end_switch.value() == 1:
        pass
    
    stepper.stop()
    stepper.overwrite_pos(0)
    stepper.target(0)
    stepper.enable(False)
    display_msg(display, " HOMED!\n")

def radar_thread(uart, threshold):
    """Thread function to continuously read radar data"""
    global radar_d, motion_detected, thread_running
    
    # Initialize radar
    radar = LD2410()
    radar.begin(uart)
    
    while thread_running:
        # Read radar data
        radar.read()

        # Check if targets are detected
        if radar.moving_target_detected():
            radar_d = radar.moving_target_distance() * 10  # Convert to mm
            if radar_d < threshold:
                motion_detected = True

        else:
            motion_detected = False

        print(radar_d)
        sleep_ms(100)  # Small delay to prevent CPU hogging

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
    steps_per_rev=STEPS_PER_REV,
    steps_per_mm=STEPS_PER_MM
)

# End switch declaration
end_s = Pin(8, Pin.IN, Pin.PULL_UP)

# Initialize UART for radar
uart = UART(1, baudrate=256000)
uart.init(tx=Pin(10), rx=Pin(3))

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
_thread.start_new_thread(radar_thread, (uart, d_threshold))

# Configure acceleration
s.set_acceleration(1000)  # 1000 steps/second²
s.set_deceleration(1000)  # 1000 steps/second²
s.enable_acceleration()   # Make sure acceleration is enabled
s.enable()

# Home the drawer mechanism
#homing(s, end_s, display, homing_speed)
display_msg(display, "Homing...")
s.home(end_s, homing_speed=homing_speed, acceleration=1000)
display_msg(display, " HOMED!\n")
drawer_closed = True

# Main loop
while True:
    if drawer_state_change:
        drawer_state_change = False
        
        if motion_detected and not drawer_closed:
            # CLOSE DRAWER
            display_msg(display, f"Distance: {radar_d}\nClosing drawer...")
            s.enable()
            
            s.move_mm(3)
            
            sleep_ms(400)
            s.home(end_s, homing_speed=homing_speed, acceleration=1000)

            drawer_closed = True
            s.disable()  # Disable stepper
            display_msg(display, f"waiting\ninside\nfor{wait_inside/1000}sec")
            sleep_ms(wait_inside)
            
        elif not motion_detected and drawer_closed:
            # OPEN DRAWER
            display_msg(display, "Opening drawer...")

            s.enable()
            s.move_mm(d_out)

            drawer_closed = False
            sleep_ms(500)  # Wait for movement to start
            s.disable()  # Disable stepper
        
    #display_msg(display, f"d: {radar_d}\n")
    sleep_ms(200)