from machine import UART, Pin, I2C
import _thread
import json
from ssd1306 import SSD1306_I2C
from time import sleep_ms
from stepper import Stepper
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
    stepper.enable(False)
    display_msg(display, " HOMED!\n")

def radar_thread(uart, threshold):
    """Thread function to continuously read radar data"""
    global radar_distance, motion_detected, thread_running, drawer_state_change, drawer_closed
    
    # Initialize radar
    radar = LD2410()
    radar.begin(uart)
    
    while thread_running:
        # Read radar data
        if radar.read():
            if radar.moving_target_detected():
                distance = radar.moving_target_distance() * 10  # Convert to mm
                radar_distance = distance
                
                # Check if motion is detected within threshold
                if distance < threshold:
                    motion_detected = True
                    if not drawer_closed:
                        drawer_state_change = True
                else:
                    motion_detected = False
                    if drawer_closed:
                        drawer_state_change = True
            else:
                motion_detected = False
                if drawer_closed:
                    drawer_state_change = True
                    
        sleep_ms(50)  # Small delay to prevent CPU hogging

# Initialize hardware
i2c = I2C(0, sda=Pin(5), scl=Pin(6))
display = SSD1306_I2C(70, 40, i2c)
#s = Stepper(step_pin=1, dir_pin=2, en_pin=7, invert_dir=True)
dir_pin = Pin(0, Pin.OUT)
step_pin = Pin(2, Pin.OUT)
en_pin = Pin(7, Pin.OUT)
s = Stepper(step_pin,dir_pin,en_pin,invert_dir=True,timer_id=0) #stp,dir,en

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

# Start radar thread
_thread.start_new_thread(radar_thread, (uart, d_threshold))

# Home the drawer mechanism
homing(s, end_s, display, homing_speed)
drawer_closed = True

# Main loop
while True:
    if drawer_state_change:
        drawer_state_change = False
        
        if motion_detected and not drawer_closed:
            # CLOSE DRAWER
            display_msg(display, f"Distance: {radar_distance}\nClosing drawer...")
            s.enable(True)
            
            for vel in range(100, back_speed, 100):
                s.speed(vel)
                s.target(10 * step_per_mm)
                sleep_ms(5)
            
            sleep_ms(400)
            homing(s, end_s, display, homing_speed)

            drawer_closed = True
            s.enable(False)  # Disable stepper
            display_msg(display, f"waiting\ninside\nfor{wait_inside/1000}sec")
            sleep_ms(wait_inside)


            
        elif not motion_detected and drawer_closed:
            # OPEN DRAWER
            display_msg(display, "Opening drawer...")
            s.enable(True)
            s.track_target()
            s.speed(forw_speed)
            s.target(d_out * step_per_mm)
            drawer_closed = False
            sleep_ms(500)  # Wait for movement to start
            s.enable(False)  # Disable stepper
        
    display_msg(display, f"d: {radar_distance}\n")
    sleep_ms(200)
