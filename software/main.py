from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
from time import sleep_ms
from stepper import Stepper
import ld2410
import json

# Constants
CONFIG_FILE = 'config.json'

# Hardware definition
i2c = I2C(0, sda=Pin(5), scl=Pin(6))
display = SSD1306_I2C(70, 40, i2c)
s = Stepper(step_pin=2, dir_pin=1, en_pin=7, invert_dir=True)
end_s = Pin(3, Pin.IN, Pin.PULL_UP)
radar = ld2410.LD2410(baudrate= 256000,uart_num=1, tx_pin=9, rx_pin=8)

def load_config():
    """Load configuration from JSON file or use defaults"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.loads(f.read())
    except:
        display_msg("problem with json\n")
        return None

def display_msg(msg):
    display.fill(0)
    display.text("bouvy_drawer", 5, 0, 1)
    y = 10
    for line in msg.split('\n'):
        display.text(line, 0, y, 1)
        y += 10
    display.show()

def homing(homing_speed):
    display_msg("homing...")
    s.speed(homing_speed)
    s.free_run(-1)
    while end_s.value() == 1:
        pass
    s.stop()
    s.overwrite_pos(0)
    s.target(0)
    display_msg("homed!\nwatching...")

def main():
    # Load configuration
    config = load_config()
    if not config:
        display_msg("No JSON/ncheck files/n")

    # Get all variables from config
    d_threshold = config["d_threshold"]
    back_speed = config["back_speed"]
    forw_speed = config["forw_speed"]
    wait_inside = config["wait_inside"]
    steps_per_rev = config["steps_per_rev"]
    step_per_mm = config["step_per_mm"]
    d_out = config["d_out"]
    homing_speed = config["homing_speed"]
    
    drawer_open = False
    homing(homing_speed)
    s.enable(False)  
    
    while True:
        d = radar.get_distance() * 10  # Convert to mm from cm
        print(".")
        if d < d_threshold and not drawer_open:
            s.enable(True)
            display_msg(f"detected: {d}mm\nopening drawer")
            s.track_target()
            s.speed(forw_speed)
            s.target(d_out * step_per_mm)
            drawer_open = True
            s.enable(False)

        elif d > d_threshold and drawer_open:
            s.enable(True)
            display_msg(f"no detection\nclosing drawer")
            
            for vel in range(100, back_speed, 100):
                s.speed(vel)
                s.target(10 * step_per_mm)
                sleep_ms(5)
                
            homing(homing_speed)
            sleep_ms(wait_inside)
            drawer_open = False
            s.enable(False)  # Disable motor to save power

if __name__ == "__main__":
    main()