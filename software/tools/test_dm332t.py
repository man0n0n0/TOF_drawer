"""
Example usage of the DM332T stepper motor driver library.

This example demonstrates basic movement, homing, acceleration, and millimeter positioning.
"""

from machine import Pin
from DM332T import DM332TStepper
import time

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

# Create stepper instance
stepper = DM332TStepper(
    step_pin=STEP_PIN,
    dir_pin=DIR_PIN,
    invert_dir=True,
    enable_pin=ENABLE_PIN,
    steps_per_rev=STEPS_PER_REV,
    steps_per_mm=STEPS_PER_MM
)

# Configure acceleration parameters
stepper.set_acceleration(5000)  # steps/s²
stepper.set_deceleration(5000)  # steps/s²
stepper.enable_acceleration()   # Enable acceleration/deceleration

# Print microstepping configuration info
stepper.microstepping_info()

# Basic movement test
def test_basic_movement():
    print("Testing basic movement...")
    
    # Enable motor
    stepper.enable()
    
    # Move 1/4 revolution forward
    print("Moving 1/4 revolution forward...")
    stepper.move_revolutions(0.25)
    
    time.sleep(1)
    
    # Move 1/4 revolution backward
    print("Moving 1/4 revolution backward...")
    stepper.move_revolutions(-0.25)
    
    time.sleep(1)
    
    # Move 90 degrees
    print("Moving 90 degrees...")
    stepper.move_angle(90)
    
    time.sleep(1)
    
    # Return to starting position
    print("Returning to start position...")
    stepper.move_to_position(0)
    
    print("Basic movement test complete!")

# Homing test
def test_homing():
    print("Testing homing sequence...")
    
    # Home the motor
    home_switch = Pin(HOME_SWITCH_PIN, Pin.IN, Pin.PULL_UP)
    stepper.home(home_switch, homing_speed=500, backoff_steps=100)
    
    print("Homing complete!")
    
    # Move out from home position
    print("Moving from home position...")
    stepper.move_steps(1000)
    
    time.sleep(1)
    
    # Return to home
    print("Returning to home...")
    stepper.move_to_position(0)
    
    print("Homing test complete!")

# Speed and acceleration test
def test_speed():
    print("Testing different speeds...")
    
    # Slow speed
    stepper.set_speed(1000)
    stepper.move_revolutions(1)
    
    time.sleep(1)
    
    # Medium speed
    stepper.set_speed(10000)
    stepper.move_revolutions(-1)
    stepper.set_speed(15000)
    stepper.move_revolutions(5)

    time.sleep(1)
    
    # Return to start
    stepper.move_to_position(0)
    
    print("Speed test complete!")

# Acceleration test
def test_acceleration():
    print("Testing acceleration profiles...")
    
    # Test with acceleration
    print("Moving with acceleration/deceleration...")
    stepper.enable_acceleration()
    stepper.set_speed(2000)
    stepper.move_revolutions(1)
    
    time.sleep(1)
    
    # Test without acceleration
    print("Moving without acceleration (constant speed)...")
    stepper.disable_acceleration()
    stepper.move_revolutions(-1)
    
    # Re-enable acceleration for other tests
    stepper.enable_acceleration()
    
    print("Acceleration test complete!")

# Metric movement test
def test_metric_movement():
    print("Testing millimeter positioning...")
    
    # Move 10mm forward
    print("Moving 10mm forward...")
    stepper.move_mm(100)
    
    time.sleep(1)
    
    # Move 5mm backward
    print("Moving 5mm backward...")
    stepper.move_mm(-500)
    
    time.sleep(1)
    
    # Move to absolute position 15mm
    print("Moving to absolute position 15mm...")
    stepper.move_to_mm(105)
    
    time.sleep(1)
    
    # Return to 0
    print("Returning to position 0...")
    stepper.move_to_mm(0)
    
    print("Millimeter movement test complete!")

# Metric movement test
def test_drawer():
    stepper.enable()

    stepper.move_mm(50)
    
    time.sleep(1)
    
    # Move 5mm backward
    print("Moving 5mm backward...")
    stepper.move_mm(-50)
    
    time.sleep(1)
    
    # Move to absolute position 15mm
    print("Moving to absolute position 50mm...")
    stepper.move_to_mm(50)
    
    time.sleep(1)
    
    # Return to 0
    print("Returning to position 0...")
    stepper.move_to_mm(0)
    
    print("Millimeter movement test complete!")
# Main program
try:

    # Run tests  
    #test_drawer()
    # test_speed()
    # time.sleep(1)
    # test_metric_movement()
    # time.sleep(1)

    # stepper.stop()
    # stepper.disable()
    # Uncomment to test homing (requires home switch)
    # test_homing()
    
    # Disable motor to save power
    while True :
        stepper.target_mm(10)
        stepper.start_continuous()
        print(stepper.get_position_mm())
        if stepper.is_at_target():
            stepper.stop()
        time.sleep(0.1)
    
except KeyboardInterrupt:
    # Handle Ctrl+C
    print("Program interrupted")
    stepper.stop()
    stepper.disable()
    
print("Program complete!")