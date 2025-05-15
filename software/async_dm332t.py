import asyncio
from machine import Pin
from DM332T import AsyncDM332TStepper

async def main():
    # Create a stepper motor instance
    motor = AsyncDM332TStepper(
        step_pin=25,
        dir_pin=26,
        enable_pin=27,
        steps_per_rev=3200,
        steps_per_mm=25.6
    )
    
    # Configure motor settings
    motor.set_speed(1000)  # 1000 steps per second
    motor.set_acceleration(500)  # 500 steps/second²
    
    # Move motor 10mm
    print("Moving 10mm...")
    await motor.move_mm(10)
    print("Reached position:", motor.get_position())
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Return to home position
    print("Returning to position 0...")
    await motor.move_to_position(0)
    print("Homing complete!")
    
    
    # Move both motors simultaneously
    print("Moving motors simultaneously...")
    motor1_task = asyncio.create_task(motor.move_steps(800))
    motor2_task = asyncio.create_task(motor2.move_steps(1600))
    
    # Wait for both movements to complete
    await asyncio.gather(motor1_task, motor2_task)
    print("Both movements complete!")

# Run on MicroPython
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Program stopped")