"""
MicroPython library for controlling stepper motors using DM332T drivers.
Provides easy-to-use functions for precise control of stepper motors in various applications.

Created for ESP32 and similar microcontrollers.

Example usage:
    from DM332T import DM332TStepper
    from machine import Pin
    
    # Initialize with step pin, direction pin
    stepper = DM332TStepper(step_pin=0, dir_pin=2, steps_per_mm=25.6) 
    
    # Basic movements
    stepper.move_steps(1600)  # Move 1600 steps
    stepper.move_to_position(3200)  # Move to absolute position 3200
    
    # Speed control
    stepper.set_speed(1000)  # Set speed to 1000 steps/second
    stepper.set_acceleration(500)  # Set acceleration to 500 steps/second²
    
    # Metric movements
    stepper.move_mm(100)  # Move 100mm forward
    stepper.move_to_mm(50)  # Move to absolute position 50mm
"""

import time
from machine import Pin, Timer

class DM332TStepper:
    """
    Class for controlling stepper motors with DM332T drivers in MicroPython.
    
    The DM332T driver requires step and direction signals to control the motor.
    This class provides methods for configuring the driver and controlling the motor.
    """
    
    def __init__(self, step_pin, dir_pin, enable_pin=None, steps_per_rev=3200, 
                 steps_per_mm=25.6, invert_dir=False):
        """
        Initialize the stepper motor controller.
        
        Args:
            step_pin (int): GPIO pin number for step signal
            dir_pin (int): GPIO pin number for direction signal
            enable_pin (int, optional): GPIO pin number for enable signal
            steps_per_rev (int, optional): Steps per revolution (default: 3200)
            steps_per_mm (float, optional): Steps per millimeter for linear movement (default: 25.6)
            invert_dir (bool, optional): Invert direction logic (default: False)
        """
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        
        if enable_pin is not None:
            self.enable_pin = Pin(enable_pin, Pin.OUT)
            self.has_enable = True
        else:
            self.has_enable = False
            
        self.steps_per_rev = steps_per_rev
        self.steps_per_mm = steps_per_mm
        self.invert_dir = invert_dir
        
        self._current_position = 0
        self._target_position = 0
        self._current_speed = 0  # Current speed in steps per second
        self._max_speed = 1000  # Target speed in steps per second
        self._acceleration = 500  # steps per second^2 (default)
        self._deceleration = 500  # steps per second^2 (default)
        self._min_step_delay = 0.00005  # 50 microseconds minimum pulse width
        self._direction = 1  # 1 or -1
        self._is_running = False
        self._timer = None
        self._last_step_time = 0  # in microseconds
        self._step_interval = 1000000 / self._max_speed  # in microseconds
        self._use_acceleration = True  # Whether to use acceleration or not
        
        # Initialize pins
        self.step_pin.value(0)
        self.set_direction(1)
        
        if self.has_enable:
            self.enable()
    
    def _calculate_step_interval(self):
        """Calculate the step interval in microseconds based on speed."""
        if self._current_speed > 0:
            self._step_interval = 1000000 / self._current_speed
        else:
            self._step_interval = 1000000  # Default to 1 step per second
    
    def set_speed(self, speed):
        """
        Set the motor maximum speed in steps per second.
        
        Args:
            speed (float): Speed in steps per second
        """
        if speed < 0:
            speed = -speed
            self.set_direction(-1)
        else:
            self.set_direction(1)
            
        self._max_speed = speed
        if not self._use_acceleration:
            self._current_speed = speed
            self._calculate_step_interval()
        
    def set_current_speed(self, speed):
        """
        Set the motor current speed in steps per second immediately.
        
        Args:
            speed (float): Speed in steps per second
        """
        self._current_speed = abs(speed)
        self._calculate_step_interval()
        
    def set_acceleration(self, acceleration):
        """
        Set the motor acceleration in steps per second squared.
        
        Args:
            acceleration (float): Acceleration in steps/second²
        """
        self._acceleration = acceleration
        
    def set_deceleration(self, deceleration):
        """
        Set the motor deceleration in steps per second squared.
        
        Args:
            deceleration (float): Deceleration in steps/second²
        """
        self._deceleration = deceleration
        
    def disable_acceleration(self):
        """Disable acceleration/deceleration for movements."""
        self._use_acceleration = False
        self._current_speed = self._max_speed
        
    def enable_acceleration(self):
        """Enable acceleration/deceleration for movements."""
        self._use_acceleration = True
        
    def set_steps_per_mm(self, steps):
        """
        Set the steps per millimeter calibration value.
        
        Args:
            steps (float): Number of steps per millimeter of linear movement
        """
        self.steps_per_mm = steps
    
    def set_direction(self, direction):
        """
        Set the motor direction.
        
        Args:
            direction (int): 1 for forward, -1 for backward
        """
        self._direction = 1 if direction > 0 else -1
        dir_value = 1 if (direction > 0) != self.invert_dir else 0
        self.dir_pin.value(dir_value)
        
    def enable(self):
        """Enable the motor driver (if enable pin is connected)."""
        if self.has_enable:
            self.enable_pin.value(0)  # Enable is active LOW on most drivers
    
    def disable(self):
        """Disable the motor driver (if enable pin is connected)."""
        if self.has_enable:
            self.enable_pin.value(1)  # Disable with HIGH
    
    def _step(self):
        """Generate a single step pulse."""
        self.step_pin.value(1)
        time.sleep_us(int(self._min_step_delay * 1000000))  # Convert to microseconds
        self.step_pin.value(0)
        
        # Update position
        self._current_position += self._direction
    
    def _calculate_speed_for_step(self, step, total_steps):
        """
        Calculate the speed for a particular step based on acceleration profile.
        
        Args:
            step (int): Current step number
            total_steps (int): Total steps in move
            
        Returns:
            float: Speed in steps per second
        """
        if not self._use_acceleration:
            return self._max_speed
            
        # Determine acceleration/deceleration phases
        accel_steps = int(self._max_speed * self._max_speed / (2.0 * self._acceleration))
        decel_steps = int(self._max_speed * self._max_speed / (2.0 * self._deceleration))
        
        # Adjust if we don't have enough steps for full acc/decel
        if accel_steps + decel_steps > total_steps:
            accel_steps = total_steps * self._acceleration / (self._acceleration + self._deceleration)
            decel_steps = total_steps - accel_steps
        
        constant_steps = total_steps - accel_steps - decel_steps
        
        # Calculate speed for current step
        if step < accel_steps:
            # Acceleration phase: v = sqrt(2*a*d)
            return min(self._max_speed, 
                      (2.0 * self._acceleration * step) ** 0.5)
        elif step < accel_steps + constant_steps:
            # Constant speed phase
            return self._max_speed
        else:
            # Deceleration phase: v = sqrt(2*a*(total_decel_steps - steps_into_decel))
            steps_into_decel = step - accel_steps - constant_steps
            steps_remaining = decel_steps - steps_into_decel
            if steps_remaining <= 0:
                return 0
            return max(10, (2.0 * self._deceleration * steps_remaining) ** 0.5)
    
    def move_steps(self, steps):
        """
        Move the motor a specified number of steps with acceleration profile.
        
        Args:
            steps (int): Number of steps to move (positive or negative)
        """
        if steps == 0:
            return
            
        # Set direction
        if steps < 0:
            self.set_direction(-1)
            steps = -steps
        else:
            self.set_direction(1)
        
        # Set target position
        self._target_position = self._current_position + (steps * self._direction)
        
        # Initialize acceleration variables
        self._current_speed = 0 if self._use_acceleration else self._max_speed
        
        # Execute movement with acceleration profile
        for current_step in range(steps):
            # Calculate speed for this step
            if self._use_acceleration:
                self._current_speed = self._calculate_speed_for_step(current_step, steps)
                self._calculate_step_interval()
            
            # Execute step
            self._step()
            time.sleep_us(int(self._step_interval))
    
    def move_to_position(self, position):
        """
        Move to an absolute position.
        
        Args:
            position (int): Target position in steps
        """
        steps = position - self._current_position
        self.move_steps(steps)
    
    def move_angle(self, angle):
        """
        Move the motor by a specified angle in degrees.
        
        Args:
            angle (float): Angle to move in degrees
        """
        steps = int((angle / 360) * self.steps_per_rev)
        self.move_steps(steps)
    
    def move_revolutions(self, revolutions):
        """
        Move the motor a specified number of complete revolutions.
        
        Args:
            revolutions (float): Number of revolutions to move
        """
        steps = int(revolutions * self.steps_per_rev)
        self.move_steps(steps)
        
    def move_mm(self, mm):
        """
        Move a specific distance in millimeters.
        
        Args:
            mm (float): Distance to move in millimeters
        """
        steps = int(mm * self.steps_per_mm)
        self.move_steps(steps)
        
    def move_to_mm(self, mm_position):
        """
        Move to an absolute position in millimeters.
        
        Args:
            mm_position (float): Target position in millimeters
        """
        step_position = int(mm_position * self.steps_per_mm)
        self.move_to_position(step_position)
    
    def get_position(self):
        """
        Get the current position in steps.
        
        Returns:
            int: Current position
        """
        return self._current_position
    
    def set_position(self, position):
        """
        Set the current position without moving the motor.
        
        Args:
            position (int): Position value to set
        """
        self._current_position = position
    
    def is_at_target(self):
        """
        Check if the motor is at the target position.
        
        Returns:
            bool: True if at target position
        """
        return self._current_position == self._target_position

    def stop(self):
        """Stop the motor movement."""
        if self._timer:
            self._timer.deinit()
            self._is_running = False
    
    def start_continuous(self, direction=1):
        """
        Start continuous movement in the specified direction.
        
        Args:
            direction (int): 1 for forward, -1 for backward
        """
        self.set_direction(direction)
        if self._timer is None:
            self._timer = Timer(-1)
        
        # Calculate the timer period in milliseconds
        period_ms = int(self._step_interval / 1000)
        if period_ms < 1:
            period_ms = 1  # Minimum 1ms
            
        self._timer.init(period=period_ms, mode=Timer.PERIODIC, callback=lambda t: self._step())
        self._is_running = True
    
    def is_running(self):
        """
        Check if the motor is currently running.
        
        Returns:
            bool: True if running
        """
        return self._is_running
    
    def home(self, home_switch_pin, homing_speed=500, backoff_steps=100):
        """
        Home the motor using a home switch.
        
        Args:
            home_switch_pin (Pin): Pin object for the home switch
            homing_speed (int, optional): Speed for homing in steps/second
            backoff_steps (int, optional): Steps to back off after hitting switch
            
        Note:
            Assumes switch is normally open and connects to GND when triggered
            (will use internal pull-up resistor)
        """
        # Configure as input with pull-up
        if not isinstance(home_switch_pin, Pin):
            home_switch_pin = Pin(home_switch_pin, Pin.IN, Pin.PULL_UP)
        
        original_speed = self._speed
        self.set_speed(homing_speed)
        
        # Move until switch is triggered
        self.set_direction(-1)  # Assume homing direction is "backward"
        
        while home_switch_pin.value() == 1:  # While switch not triggered
            self._step()
            time.sleep_us(int(self._step_interval))
        
        # Stop and set position to 0
        self.stop()
        self.set_position(0)
        
        # Back off slightly
        if backoff_steps > 0:
            self.set_direction(1)
            self.move_steps(backoff_steps)
            self.set_position(0)  # Reset position to 0 after backoff
        
        # Restore original speed
        self.set_speed(original_speed)
        
        return True

    def microstepping_info(self):
        """
        Print information about DM332T microstepping configuration.
        """
        print("DM332T Microstepping Configuration Guide:")
        print("----------------------------------------")
        print("Set microstepping using SW1-SW4 DIP switches:")
        print("1. All OFF: 400 steps/rev (full step)")
        print("2. SW1 ON, others OFF: 800 steps/rev (half step)")
        print("3. SW2 ON, others OFF: 1600 steps/rev (1/4 step)")
        print("4. SW1+SW2 ON, others OFF: 3200 steps/rev (1/8 step)")
        print("5. SW3 ON, others OFF: 6400 steps/rev (1/16 step)")
        print("6. SW1+SW3 ON, others OFF: 12800 steps/rev (1/32 step)")
        print("7. SW2+SW3 ON, others OFF: 25600 steps/rev (1/64 step)")
        print("8. SW1+SW2+SW3 ON, others OFF: 51200 steps/rev (1/128 step)")
        print("9. SW4 ON, others OFF: 1000 steps/rev (1/2.5 step)")
        print("10. SW1+SW4 ON, others OFF: 2000 steps/rev (1/5 step)")
        print("----------------------------------------")
        print(f"Current setting: {self.steps_per_rev} steps/rev")