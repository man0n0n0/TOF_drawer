from machine import UART, Pin, I2C
import json
import asyncio
from ssd1306 import SSD1306_I2C
from time import sleep_ms, ticks_ms, ticks_diff
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

# This class will handle low-level movement for the stepper
class NonBlockingStepper:
    def __init__(self, stepper):
        self.stepper = stepper
        self.is_moving = False
        self.is_homing = False
        self.target_mm = 0
        self.current_mm = 0
        self.step_delay_ms = 1
        self.last_step_time = 0
        self.homing_switch = None
        self.homing_speed = 500
        
    async def move_to_mm_non_blocking(self, mm_position, speed):
        """Start moving stepper to position in mm without blocking"""
        self.stepper.enable()
        self.stepper.set_speed(speed)
        self.target_mm = mm_position
        self.is_moving = True
        self.is_homing = False
        # Return immediately, movement will be handled in update()
    
    async def home_non_blocking(self, end_switch, speed):
        """Start homing stepper without blocking"""
        self.stepper.enable()
        self.stepper.set_speed(speed)
        self.homing_switch = end_switch
        self.is_homing = True
        self.is_moving = True
        # Return immediately, homing will be handled in update()
    
    async def update(self):
        """Update stepper position - call this frequently"""
        if not self.is_moving:
            return
            
        current_time = ticks_ms()
        
        # Only move if enough time has passed since last step
        if ticks_diff(current_time, self.last_step_time) < self.step_delay_ms:
            return
            
        self.last_step_time = current_time
        
        # Handle homing
        if self.is_homing:
            # If home switch is pressed, homing is complete
            if not self.homing_switch.value():
                self.is_homing = False
                self.is_moving = False
                self.current_mm = 0
                self.stepper.position = 0  # Reset position counter
                print("Homing complete")
                return
                
            # Step toward home
            self.stepper.set_dir(False)  # Direction toward home switch
            self.stepper.step()  # Take one step
            return
            
        # Handle regular movement
        # Calculate current position in mm
        self.current_mm = self.stepper.position / self.stepper.steps_per_mm
        
        # Determine direction based on target
        if abs(self.current_mm - self.target_mm) < 0.1:
            # Target reached
            self.is_moving = False
            print(f"Target reached: {self.current_mm}mm")
            return
            
        # Determine direction and step
        if self.current_mm < self.target_mm:
            # Move away from home
            self.stepper.move_mm(0.1)  # Move a tiny bit forward
        else:
            # Move toward home
            self.stepper.move_mm(-0.1)  # Move a tiny bit backward

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
            print(f"Radar: {r_d}mm, Human: {'Yes' if human else 'No'}")
        else:
            # No target detected
            human = False
            
        # Small delay to yield to other tasks
        await asyncio.sleep_ms(50)

async def drawer_controller():
    """Non-blocking drawer control coroutine"""
    global human, r_d, last_display_update
    
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
    
    # Create our non-blocking wrapper
    nb_stepper = NonBlockingStepper(s)
    
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
    await nb_stepper.home_non_blocking(end_s, homing_speed)
    
    # Wait for homing to complete, while still calling update
    while nb_stepper.is_homing:
        await nb_stepper.update()
        await asyncio.sleep_ms(1)  # Yield to other tasks
    
    display_msg(display, "HOMED!\nStarting...")
    
    # Track drawer state
    drawer_closed = True
    drawer_target_state = True  # True = closed, False = open
    last_state_change = ticks_ms()
    movement_start_time = ticks_ms()
    last_display_update = ticks_ms()
    
    while True:
        current_time = ticks_ms()
        
        # Update the stepper position
        await nb_stepper.update()
        
        # Check if movement just finished
        if nb_stepper.is_moving == False and drawer_target_state != drawer_closed:
            drawer_closed = drawer_target_state
            s.disable()  # Disable motor to save power
            print(f"Movement complete. Now {'closed' if drawer_closed else 'open'}")
        
        # State machine for drawer operation
        cooldown_expired = ticks_diff(current_time, last_state_change) > 500
        
        if human and not drawer_closed and not nb_stepper.is_moving and cooldown_expired:
            # CLOSE DRAWER
            display_msg(display, f"Closing drawer\nDistance: {r_d}mm")
            s.enable()
            await nb_stepper.home_non_blocking(end_s, homing_speed)
            drawer_target_state = True
            last_state_change = current_time
            
        elif not human and drawer_closed and not nb_stepper.is_moving and cooldown_expired:
            # OPEN DRAWER
            display_msg(display, f"Opening drawer\nDistance: {r_d}mm")
            s.enable()
            await nb_stepper.move_to_mm_non_blocking(d_out, forw_speed)
            drawer_target_state = False
            last_state_change = current_time
            
        # Update display periodically
        if ticks_diff(current_time, last_display_update) > 200:  # Update every 200ms
            state = "Closed" if drawer_closed else "Open"
            moving = " (moving)" if nb_stepper.is_moving else ""
            target = " -> " + ("Close" if drawer_target_state else "Open") if drawer_target_state != drawer_closed else ""
            display_msg(display, f"State: {state}{moving}{target}\nDistance: {r_d}mm\nHuman: {'Yes' if human else 'No'}")
            last_display_update = current_time
        
        # Small delay to yield to other tasks
        await asyncio.sleep_ms(5)

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