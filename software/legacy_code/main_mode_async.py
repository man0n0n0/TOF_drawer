from machine import UART, Pin, I2C
import json
import asyncio
from ssd1306 import SSD1306_I2C
from time import sleep_ms
from DM332T_async import DM332TStepper  # Import the async version
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
drawer_moving = False  # Flag to track if drawer is currently moving

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

async def move_drawer_open(stepper, display, d_out, forw_speed):
    """Async function to open the drawer"""
    global drawer_moving
    
    drawer_moving = True
    display_msg(display, "Opening drawer...")
    
    stepper.enable()
    stepper.set_speed(forw_speed)
    # Run at maximum speed to fully utilize the optimized code
    await stepper.move_to_mm_async(d_out)
    
    display_msg(display, f"Open & watching\nDistance: {r_d}mm")
    stepper.disable()  # Disable stepper to save power
    
    drawer_moving = False
    return True  # Drawer is now open

async def move_drawer_close(stepper, display, end_switch, back_speed, homing_speed):
    """Async function to close the drawer"""
    global drawer_moving, r_d
    
    drawer_moving = True
    display_msg(display, f"Closing drawer\nDistance: {r_d}mm")
    
    stepper.enable()
    
    # First move away from end position (non-blocking) at higher speed
    stepper.set_speed(back_speed)
    await stepper.move_mm_async(-200)  # Move closer to home position first
    
    # Then home the drawer (non-blocking) at higher speed
    # The homing speed parameter is important for fast closing
    await stepper.home_async(end_switch, homing_speed=homing_speed*1.5)  # Increase homing speed
    
    stepper.disable()  # Disable stepper to save power
    drawer_moving = False
    return True  # Drawer is now closed

async def drawer_controller():
    """Non-blocking drawer control coroutine"""
    global human, r_d, drawer_moving
    
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
    
    # Configure stepper acceleration - increase for faster movement
    s.set_acceleration(80000)  # steps/second² (increased from 60000)
    s.set_deceleration(40000)  # steps/second² (increased from 30000)
    s.enable_acceleration()
    
    # For very fast movements, sometimes disabling acceleration helps
    # Uncomment the next line if you prefer constant speed over smooth acceleration
    # s.disable_acceleration()
    
    s.enable()
    
    # Extract configuration parameters
    d_threshold = config["d_threshold"]
    back_speed = config["back_speed"] * 1.5  # Increase speed by 50%
    forw_speed = config["forw_speed"] * 1.5  # Increase speed by 50%
    wait_inside = config["wait_inside"]
    d_out = config["d_out"]
    homing_speed = config["homing_speed"] * 1.5  # Increase speed by 50%
    
    # Home the drawer mechanism (using async version)
    display_msg(display, "Homing...")
    drawer_moving = True
    await s.home_async(end_s, homing_speed=homing_speed)
    drawer_moving = False
    display_msg(display, "HOMED!\nStarting...")
    
    # Track drawer state
    drawer_closed = True
    
    # Task variables to track drawer movement operations
    drawer_open_task = None
    drawer_close_task = None
    
    # Counter for reducing display updates
    update_counter = 0
    
    while True:      
        # Only take action if drawer is not currently moving
        if not drawer_moving:
            # Handle human detection and drawer state
            if human and not drawer_closed:
                # Start task to close drawer
                drawer_close_task = asyncio.create_task(
                    move_drawer_close(s, display, end_s, back_speed, homing_speed)
                )
                drawer_closed = True
                
            elif not human and drawer_closed:
                # Start task to open drawer
                drawer_open_task = asyncio.create_task(
                    move_drawer_open(s, display, d_out, forw_speed)
                )
                drawer_closed = False
        
        # Update display less frequently to reduce overhead
        update_counter += 1
        if update_counter >= 5:  # Update every 5 iterations (500ms at 100ms sleep)
            # Display current state
            state = "Closed" if drawer_closed else "Open"
            moving_status = "Moving" if drawer_moving else "Idle"
            display_msg(display, f"State: {state}\nStatus: {moving_status}\nDistance: {r_d}mm\nHuman: {'Yes' if human else 'No'}")
            update_counter = 0

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