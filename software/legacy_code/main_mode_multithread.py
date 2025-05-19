from machine import UART, Pin, I2C
import json
import asyncio
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

# Global variables for state
r_d = 0
human = True
radar_running = True
last_display_update = 0

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


async def read_radar():
    """Non-blocking radar reading coroutine"""
    global r_d, human
    
    # Initialize radar and UART
    uart = UART(1, baudrate=256000)
    uart.init(tx=Pin(10), rx=Pin(3))
    r = LD2410()
    
    # Load configuration to get threshold
    config = load_config()
    threshold = config["d_threshold"]
    
    while True:
        # Read radar data
        r.begin(uart)
        r.read()

        # Check if targets are detected
        if r.stationary_target_detected():
            r_d = r.stationary_target_distance() * 10
            if r_d < threshold:
                human = True
            else:
                human = False
            print(r_d)
        # Small delay to yield to other tasks
        await asyncio.sleep_ms(100)

async def drawer_controller():
    """Non-blocking drawer control coroutine"""
    global human, r_d
    
    # Initialize hardware
    i2c = I2C(0, sda=Pin(5), scl=Pin(6))
    display = SSD1306_I2C(70, 40, i2c)
    
    # Load configuration
    config = load_config()
    
    # Initialize stepper motor with DM332T driver
    STEP_PIN = 0     # GPIO pin connected to STEP input on DM332T
    DIR_PIN = 2      # GPIO pin connected to DIR input on DM332T  
    ENABLE_PIN = 7   # GPIO pin connected to ENA input on DM332T
    HOME_SWITCH_PIN = 8  # GPIO pin connected to home switch
    
    # Create stepper object
    s = DM332TStepper(
        step_pin=STEP_PIN,
        dir_pin=DIR_PIN,
        enable_pin=ENABLE_PIN,
        invert_dir=True,
        steps_per_rev=config["steps_per_rev"],
        steps_per_mm=config["step_per_mm"]
    )
    
    # End switch declaration
    end_s = Pin(HOME_SWITCH_PIN, Pin.IN, Pin.PULL_UP)
    
    # Configure stepper acceleration
    s.set_acceleration(60000)  # steps/second²
    s.set_deceleration(30000)  # steps/second²
    s.enable_acceleration()
    s.enable()
    
    # Extract configuration parameters
    d_threshold = config["d_threshold"]
    back_speed = config["back_speed"]
    forw_speed = config["forw_speed"]
    wait_inside = config["wait_inside"]
    d_out = config["d_out"]
    homing_speed = config["homing_speed"]
    
    # Home the drawer mechanism
    display_msg(display, "Homing...")
    s.home(end_s, homing_speed=homing_speed)
    display_msg(display, "HOMED!\nStarting...")
    
    # Track drawer state
    drawer_closed = True
    waiting_start_time = 0
    waiting_inside = False
    
    while True:      
        # Handle human detection and drawer state
        if human and not drawer_closed:
            # CLOSE DRAWER
            display_msg(display, f"Closing drawer\nDistance: {r_d}mm")
            s.enable()
            
            # First move away from end position
            s.set_speed(back_speed)
            s.move_mm(-200)  # Move closer to home position first
            
            # Then home the drawer
            s.home(end_s, homing_speed=homing_speed)
            
            drawer_closed = True
            s.disable()  # Disable stepper to save power
            
        elif not human and drawer_closed :
            # OPEN DRAWER
            display_msg(display, "Opening drawer...")
            
            s.enable()
            s.set_speed(forw_speed)
            s.move_to_mm(d_out)

            display_msg(display, f"Open & watching\nDistance: {r_d}mm")
            s.disable()  # Disable stepper to save power
            
            drawer_closed = False
            
            
            
        state = "Closed" if drawer_closed else "Open"
        display_msg(display, f"State: {state}\nDistance: {r_d}mm\nHuman: {'Yes' if human else 'No'}")

        # Small delay to yield to other tasks
        await asyncio.sleep_ms(100)

async def main():
    """Main entry point for the application"""
    # Create the two main tasks
    radar_task = asyncio.create_task(read_radar())
    drawer_task = asyncio.create_task(drawer_controller())
    
    # Run both tasks concurrently, without one waiting for the other
    await asyncio.gather(radar_task, drawer_task)

# Run the main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user")
    finally:
        radar_running = False  # Stop radar task