"""
MicroPython library for controlling stepper motors using DM332T drivers.
Provides easy-to-use functions for precise control of stepper motors with improved acceleration.

Created for ESP32 and similar microcontrollers.
"""

import time
from machine import Pin, Timer
import math

class DM332TStepper:
    """
    Class for controlling stepper motors with DM332T drivers in MicroPython.
    
    The DM332T driver requires step and direction signals to control the motor.
    This class provides methods for configuring the driver and controlling the motor
    with advanced acceleration management.
    """
    
    def __init__(self, step_pin, dir_pin, enable_pin=None, steps_per_rev=3200, 
                 steps_per_mm=25.6, invert_dir=False, active_low_enable=False):
        """
        Initialize the stepper motor controller.
        
        Args:
            step_pin (int): GPIO pin number for step signal
            dir_pin (int): GPIO pin number for direction signal
            enable_pin (int, optional): GPIO pin number for enable signal
            steps_per_rev (int, optional): Steps per revolution (default: 3200)
            steps_per_mm (float, optional): Steps per millimeter for linear movement (default: 25.6)
            invert_dir (bool, optional): Invert direction logic (default: False)
            active_low_enable (bool, optional): Whether enable pin is active LOW (default: False)
        """
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        
        # Handle enable pin if provided
        self.has_enable = enable_pin is not None
        if self.has_enable:
            self.enable_pin = Pin(enable_pin, Pin.OUT)
            
        # Motor configuration
        self.steps_per_rev = steps_per_rev
        self.steps_per_mm = steps_per_mm
        self.invert_dir = invert_dir
        self.active_low_enable = active_low_enable
        
        # Position tracking (both in steps and mm)
        self._current_position_steps = 0
        self._target_position_steps = 0
        self._current_position_mm = 0
        self._target_position_mm = 0
        
        # Motion parameters
        self._current_speed = 0       # Current speed in steps per second
        self._max_speed = 50000       # Maximum speed in steps per second
        self._acceleration = 500      # Steps per second^2
        self._deceleration = 500      # Steps per second^2
        self._min_step_delay = 0.00001  # 10 microseconds minimum pulse width
        self._direction = 1           # 1 or -1
        self._is_running = False
        self._timer = None
        self._step_interval = 1000000 / self._max_speed  # in microseconds
        self._use_acceleration = True
        self._is_enabled = False      # Track enabled state
        
        # New acceleration profile parameters
        self._last_step_time_us = 0    # Time of last step in microseconds
        self._c0 = 0                   # First step delay in microseconds
        self._min_step_interval = 0    # Minimum step interval (max speed) in microseconds
        self._ramp_step_count = 0      # Number of steps in acceleration ramp
        self._step_count = 0           # Current step in the current move
        self._total_steps = 0          # Total steps in the current move
        self._accel_count = 0          # Count of steps for current acceleration phase
        self._decel_start = 0          # Step at which to start deceleration
        
        # Initialize pins
        self.step_pin.value(0)
        self.set_direction(1)
        
        # Make sure motor starts in disabled state
        if self.has_enable:
            self.disable()  # Start with motor disabled
        
        # Precalculate values for acceleration profile
        self._precalculate_acceleration_values()
    
    def _precalculate_acceleration_values(self):
        """
        Precalculate values for the acceleration profile based on current settings.
        This uses a more efficient algorithm than the previous implementation.
        """
        # Calculate the minimum step interval (at max speed)
        if self._max_speed > 0:
            self._min_step_interval = 1000000 / self._max_speed  # in microseconds
        else:
            self._min_step_interval = 1000000  # Default to 1 step per second
        
        # Calculate the first step delay for acceleration
        # c0 = 1 / sqrt(2 * alpha / accel) where alpha is the angle per step in radians
        if self._acceleration > 0:
            self._c0 = 1000000 * math.sqrt(2.0 / max(0.001, self._acceleration))  # in microseconds
        else:
            self._c0 = 1000000  # Default to 1 second if no acceleration
        
        # Calculate how many steps are needed to reach max speed
        if self._acceleration > 0:
            self._ramp_step_count = int((self._max_speed * self._max_speed) / (2 * max(0.001, self._acceleration)))
        else:
            self._ramp_step_count = 0
    
    def _calculate_step_interval(self):
        """Calculate the step interval in microseconds based on current speed."""
        if self._current_speed <= 0:
            return 1000000  # Default to 1 second if speed is zero or negative
        return 1000000 / self._current_speed
    
    def set_speed(self, speed):
        """
        Set the motor maximum speed in steps per second.
        
        Args:
            speed (float): Speed in steps per second (positive value)
        """
        speed = max(1, abs(speed))  # Ensure positive non-zero value
        self._max_speed = speed
        
        if not self._use_acceleration:
            self._current_speed = speed
            self._step_interval = self._calculate_step_interval()
        
        # Recalculate acceleration profile
        self._precalculate_acceleration_values()
    
    def speed(self, speed):
        """
        Set the motor speed in steps per second.
        Alias for set_speed() for compatibility.
        
        Args:
            speed (float): Speed in steps per second
        """
        self.set_speed(speed)
    
    def set_current_speed(self, speed):
        """
        Set the motor current speed in steps per second immediately.
        
        Args:
            speed (float): Speed in steps per second
        """
        self._current_speed = max(1, abs(speed))
        self._step_interval = self._calculate_step_interval()
        
    def set_acceleration(self, acceleration):
        """
        Set the motor acceleration in steps per second squared.
        
        Args:
            acceleration (float): Acceleration in steps/second²
        """
        self._acceleration = max(1, acceleration)  # Ensure positive value
        self._precalculate_acceleration_values()
        
    def set_deceleration(self, deceleration):
        """
        Set the motor deceleration in steps per second squared.
        
        Args:
            deceleration (float): Deceleration in steps/second²
        """
        self._deceleration = max(1, deceleration)  # Ensure positive value
        
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
        
    def enable(self, state=True):
        """
        Enable or disable the motor driver.
        
        Args:
            state (bool, optional): True to enable, False to disable (default: True)
        """
        if self.has_enable:
            # Apply the appropriate logic level based on active_low_enable setting
            pin_value = not state if self.active_low_enable else state
            self.enable_pin.value(pin_value)
            self._is_enabled = state
            
            # Small delay to ensure the driver has time to respond
            time.sleep_ms(5)
            
    def disable(self):
        """Disable the motor driver."""
        if self.has_enable:
            pin_value = True if self.active_low_enable else False
            self.enable_pin.value(pin_value)
            self._is_enabled = False
            
            # Slightly longer delay for disable to ensure motor fully stops
            time.sleep_ms(10)
    
    def is_enabled(self):
        """
        Check if the motor is enabled.
        
        Returns:
            bool: True if motor is enabled
        """
        return self._is_enabled if self.has_enable else True
        
    def _steps_to_mm(self, steps):
        """Convert steps to millimeters."""
        return steps / self.steps_per_mm
        
    def _mm_to_steps(self, mm):
        """Convert millimeters to steps."""
        return int(mm * self.steps_per_mm)
    
    def _step(self):
        """Generate a single step pulse."""
        self.step_pin.value(1)
        time.sleep_us(int(self._min_step_delay * 1000000))  # Convert to microseconds
        self.step_pin.value(0)
        
        # Update position (both in steps and mm)
        self._current_position_steps += self._direction
        self._current_position_mm = self._steps_to_mm(self._current_position_steps)
        
        # Update step count for acceleration profile
        self._step_count += 1
    
    def _compute_next_step_interval(self):
        """
        Compute the next step interval based on an improved acceleration profile.
        This method implements a more efficient acceleration calculation.
        
        Returns:
            float: The next step interval in microseconds
        """
        if not self._use_acceleration:
            return self._min_step_interval
        
        if self._step_count < self._accel_count:
            # We're accelerating
            # Use square-root calculation for smooth acceleration:
            # step_interval = c0 / sqrt(step + 1)
            # This is more efficient than recalculating speed at each step
            step_count_for_calc = max(0, self._step_count)  # Ensure non-negative
            step_interval = self._c0 / math.sqrt(step_count_for_calc + 1)
            
            # Ensure we don't go faster than max speed
            if step_interval < self._min_step_interval:
                step_interval = self._min_step_interval
            
            return step_interval
            
        elif self._step_count >= self._decel_start:
            # We're decelerating
            # Use similar formula but count down from total steps
            remaining_steps = max(0, self._total_steps - self._step_count)  # Ensure non-negative
            
            # Adjust calculation to handle different acceleration vs deceleration rates
            decel_factor = max(0.001, self._acceleration / max(0.001, self._deceleration))  # Prevent division by zero
            sqrt_value = max(1, remaining_steps * decel_factor + 1)  # Ensure positive value for sqrt
            
            step_interval = self._c0 / math.sqrt(sqrt_value)
            
            # Ensure we don't go slower than reasonable
            if step_interval > 1000000:  # Cap at 1 second
                step_interval = 1000000
                
            return step_interval
        else:
            # We're at constant speed
            return self._min_step_interval
    
    def _calculate_move_profile(self, steps):
        """
        Calculate the acceleration profile for a move.
        
        Args:
            steps (int): Total number of steps to move
        """
        self._total_steps = steps
        self._step_count = 0
        
        if not self._use_acceleration or steps <= 1:
            # No acceleration, use constant speed
            self._accel_count = 0
            self._decel_start = steps
            self._current_speed = self._max_speed
            self._step_interval = self._min_step_interval
            return
        
        # Calculate how many steps we need for acceleration and deceleration
        # This is improved to handle different accel/decel rates properly
        accel_dist = int((self._max_speed * self._max_speed) / (2 * max(1, self._acceleration)))
        decel_dist = int((self._max_speed * self._max_speed) / (2 * max(1, self._deceleration)))
        
        # If we don't have enough steps for full acceleration + deceleration,
        # scale the acceleration and deceleration phases proportionately
        if accel_dist + decel_dist > steps:
            # Calculate the highest speed we can reach
            accel_ratio = float(self._acceleration) / max(0.001, self._acceleration + self._deceleration)
            accel_dist = max(0, int(steps * accel_ratio))
            decel_dist = max(0, steps - accel_dist)
            
            # Recalculate the max attainable speed for this movement
            # Ensure positive values for sqrt
            if accel_dist > 0:
                max_attainable_speed = math.sqrt(2 * self._acceleration * accel_dist)
                # Cap speed to calculated maximum
                if max_attainable_speed < self._max_speed:
                    actual_max_speed = max_attainable_speed
                    self._step_interval = 1000000 / max(1, actual_max_speed)  # Prevent division by zero
            
        self._accel_count = max(0, accel_dist)  # Ensure non-negative
        self._decel_start = max(0, steps - decel_dist)  # Ensure non-negative
        
        # Start with zero speed
        self._current_speed = 0
        self._step_interval = self._c0
    
    def move_steps(self, steps):
        """
        Move the motor a specified number of steps with acceleration profile.
        
        Args:
            steps (int): Number of steps to move (positive or negative)
        """
        if steps == 0:
            return
            
        # Ensure motor is enabled before moving
        if self.has_enable and not self._is_enabled:
            self.enable()
            
        # Set direction
        if steps < 0:
            self.set_direction(-1)
            steps = -steps
        else:
            self.set_direction(1)
        
        # Set target position (both in steps and mm)
        self._target_position_steps = self._current_position_steps + (steps * self._direction)
        self._target_position_mm = self._steps_to_mm(self._target_position_steps)
        
        # Calculate the acceleration profile for this move
        self._calculate_move_profile(steps)
        
        # Reset step count for this move
        self._step_count = 0
        self._last_step_time_us = time.ticks_us()
        
        # Execute movement with acceleration profile
        try:
            for _ in range(steps):
                # Get step interval for this step
                self._step_interval = self._compute_next_step_interval()
                
                # Execute step
                self._step()
                
                # Calculate delay based on elapsed time since last step
                # This accounts for the time taken to compute and execute the step
                current_time = time.ticks_us()
                elapsed = time.ticks_diff(current_time, self._last_step_time_us)
                delay = max(0, int(self._step_interval - elapsed))
                
                # Wait for the calculated time
                if delay > 0:
                    time.sleep_us(delay)
                    
                # Record the time of this step
                self._last_step_time_us = time.ticks_us()
        except Exception as e:
            # Catch any errors during movement and stop safely
            print(f"Error during movement: {e}")
            # Ensure we update position to wherever we ended up
            self._target_position_steps = self._current_position_steps
            self._target_position_mm = self._current_position_mm
    
    def move_to_position_steps(self, position_steps):
        """
        Move to an absolute position in steps.
        
        Args:
            position_steps (int): Target position in steps
        """
        steps = position_steps - self._current_position_steps
        self.move_steps(steps)
    
    def move_to_position_mm(self, position_mm):
        """
        Move to an absolute position in millimeters.
        
        Args:
            position_mm (float): Target position in millimeters
        """
        position_steps = self._mm_to_steps(position_mm)
        self.move_to_position_steps(position_steps)
    
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
        steps = self._mm_to_steps(mm)
        self.move_steps(steps)
    
    def get_position_mm(self):
        """
        Get the current position in millimeters.
        
        Returns:
            float: Current position in millimeters
        """
        return self._current_position_mm
    
    def get_position_steps(self):
        """
        Get the current position in steps.
        
        Returns:
            int: Current position in steps
        """
        return self._current_position_steps
    
    def get_target_position_mm(self):
        """
        Get the target position in millimeters.
        
        Returns:
            float: Target position in millimeters
        """
        return self._target_position_mm
    
    def set_position_mm(self, position_mm):
        """
        Set the current position in millimeters without moving the motor.
        
        Args:
            position_mm (float): Position value to set in millimeters
        """
        self._current_position_mm = position_mm
        self._current_position_steps = self._mm_to_steps(position_mm)
        self._target_position_mm = position_mm
        self._target_position_steps = self._current_position_steps
    
    def set_position_steps(self, position_steps):
        """
        Set the current position in steps without moving the motor.
        
        Args:
            position_steps (int): Position value to set in steps
        """
        self._current_position_steps = position_steps
        self._current_position_mm = self._steps_to_mm(position_steps)
        self._target_position_steps = position_steps
        self._target_position_mm = self._current_position_mm
    
    def target_steps(self, position_steps):
        """
        Set the target position in steps.
        
        Args:
            position_steps (int): Target position in steps
        """
        self._target_position_steps = position_steps
        self._target_position_mm = self._steps_to_mm(position_steps)
        
    def target_mm(self, position_mm):
        """
        Set the target position in millimeters.
        
        Args:
            position_mm (float): Target position in millimeters
        """
        self._target_position_mm = position_mm
        self._target_position_steps = self._mm_to_steps(position_mm)
    
    def track_target(self):
        """
        Start moving the motor to the target position.
        """
        steps = self._target_position_steps - self._current_position_steps
        self.move_steps(steps)
    
    def is_at_target(self):
        """
        Check if the motor is at the target position.
        
        Returns:
            bool: True if at target position
        """
        return self._current_position_steps >= self._target_position_steps
        
    def stop(self):
        """Stop the motor movement."""
        if self._timer:
            self._timer.deinit()
            self._timer = None
        self._is_running = False
    
    def start_continuous(self, direction=1, use_acceleration=True):
        """
        Start continuous movement in the specified direction using the improved
        acceleration profile.
        
        Args:
            direction (int): 1 for forward, -1 for backward
            use_acceleration (bool): Whether to use acceleration for smooth startup
        """
        # Ensure motor is enabled
        if self.has_enable and not self._is_enabled:
            self.enable()
            
        # Set direction
        self.set_direction(direction)
        
        # Stop any existing continuous movement
        if self._is_running:
            self.stop()
        
        # Initial values for continuous movement
        self._step_count = 0
        self._last_step_time_us = time.ticks_us()
        
        # Use improved acceleration profile for continuous movement
        if use_acceleration and self._use_acceleration:
            # Create timer if needed
            if self._timer is None:
                self._timer = Timer(-1)
            
            # Start with zero speed or minimum speed
            self._current_speed = 10  # Minimum starting speed
            self._step_interval = self._c0  # Initial step interval
            
            # Track state for continuous movement
            continuous_state = {
                'accel_count': 0,
                'next_interval': self._c0,
                'last_interval': self._c0
            }
            
            def accel_step_callback(t):
                # Execute a step
                self._step()
                
                # Update acceleration count
                continuous_state['accel_count'] += 1
                
                # Calculate next step interval
                if self._current_speed < self._max_speed:
                    try:
                        # Calculate next interval using improved acceleration formula
                        # Ensure positive value for sqrt
                        sqrt_value = max(1, continuous_state['accel_count'] + 1)
                        continuous_state['next_interval'] = self._c0 / math.sqrt(sqrt_value)
                        
                        # Ensure we don't go faster than max speed
                        if continuous_state['next_interval'] < self._min_step_interval:
                            continuous_state['next_interval'] = self._min_step_interval
                        
                        # Update current speed based on interval
                        self._current_speed = 1000000 / max(1, continuous_state['next_interval'])
                        
                        # Update the timer period, converting to milliseconds
                        # Add 1ms to avoid timer frequency limitations
                        period_ms = max(1, int(continuous_state['next_interval'] / 1000))
                        t.init(period=period_ms, mode=Timer.PERIODIC, callback=accel_step_callback)
                    except ValueError:
                        # Handle math errors by defaulting to max speed
                        continuous_state['next_interval'] = self._min_step_interval
                        self._current_speed = self._max_speed
                        period_ms = max(1, int(self._min_step_interval / 1000))
                        t.init(period=period_ms, mode=Timer.PERIODIC, callback=accel_step_callback)
            
            # Start with initial step interval
            period_ms = max(1, int(self._c0 / 1000))
            self._timer.init(period=period_ms, mode=Timer.PERIODIC, callback=accel_step_callback)
        else:
            # Simple continuous movement at max speed without acceleration
            self._current_speed = self._max_speed
            self._step_interval = self._min_step_interval
            
            # Create timer if needed
            if self._timer is None:
                self._timer = Timer(-1)
            
            # Calculate the timer period in milliseconds
            period_ms = max(1, int(self._step_interval / 1000))  # Minimum 1ms
            
            # Start timer
            self._timer.init(period=period_ms, mode=Timer.PERIODIC, callback=lambda t: self._step())
        
        self._is_running = True
    
    def is_running(self):
        """
        Check if the motor is currently running.
        
        Returns:
            bool: True if running
        """
        return self._is_running
        
    def home(self, home_switch_pin, homing_speed=500, backoff_steps=100, acceleration=None):
        """
        Home the motor using a home switch with improved acceleration management.
        
        Args:
            home_switch_pin (Pin or int): Pin object or pin number for the home switch
            homing_speed (int, optional): Speed for homing in steps/second (default: 500)
            backoff_steps (int, optional): Steps to back off after hitting switch (default: 100)
            acceleration (int, optional): Acceleration for homing in steps/second² (default: None)
            
        Note:
            Assumes switch is normally open and connects to GND when triggered
            (will use internal pull-up resistor)
        """
        # Configure as input with pull-up if pin number provided
        if not isinstance(home_switch_pin, Pin):
            home_switch_pin = Pin(home_switch_pin, Pin.IN, Pin.PULL_UP)
        
        # Store original settings
        original_settings = {
            'max_speed': self._max_speed,
            'acceleration': self._acceleration,
            'use_accel': self._use_acceleration
        }
        
        # Configure homing parameters
        self._max_speed = homing_speed
        
        # Determine whether to use acceleration for homing
        if acceleration is not None:
            self._acceleration = acceleration
            self._use_acceleration = True
            # Recalculate acceleration profile
            self._precalculate_acceleration_values()
        else:
            self._use_acceleration = False
        
        # Ensure motor is enabled
        if self.has_enable:
            self.enable(True)
        
        # Set direction for homing (backward)
        self.set_direction(-1)
        
        # Start movement toward home switch
        self.start_continuous(-1, self._use_acceleration)
        
        # Wait until switch is triggered
        while home_switch_pin.value() == 1:  # While switch not triggered
            time.sleep_ms(1)  # Small delay to prevent CPU hogging
        
        # Stop when switch is triggered
        self.stop()
        
        # Set position to 0 (both in steps and mm)
        self.set_position_steps(0)
        
        # Back off slightly if needed
        if backoff_steps > 0:
            # Use the move_steps function with acceleration
            self.set_direction(1)  # Forward (away from switch)
            self.move_steps(backoff_steps)
            
            # Reset position to 0 after backoff (both in steps and mm)
            self.set_position_steps(0)
        
        # Restore original settings
        self._max_speed = original_settings['max_speed']
        self._acceleration = original_settings['acceleration']
        self._use_acceleration = original_settings['use_accel']
        self._precalculate_acceleration_values()
        
        return True

    def microstepping_info(self):
        """
        Print information about DM332T microstepping configuration.
        """
        microstepping_table = [
            "1. All OFF: 400 steps/rev (full step)",
            "2. SW1 ON, others OFF: 800 steps/rev (half step)",
            "3. SW2 ON, others OFF: 1600 steps/rev (1/4 step)",
            "4. SW1+SW2 ON, others OFF: 3200 steps/rev (1/8 step)",
            "5. SW3 ON, others OFF: 6400 steps/rev (1/16 step)",
            "6. SW1+SW3 ON, others OFF: 12800 steps/rev (1/32 step)",
            "7. SW2+SW3 ON, others OFF: 25600 steps/rev (1/64 step)",
            "8. SW1+SW2+SW3 ON, others OFF: 51200 steps/rev (1/128 step)",
            "9. SW4 ON, others OFF: 1000 steps/rev (1/2.5 step)",
            "10. SW1+SW4 ON, others OFF: 2000 steps/rev (1/5 step)"
        ]
        
        print("DM332T Microstepping Configuration Guide:")
        print("----------------------------------------")
        print("Set microstepping using SW1-SW4 DIP switches:")
        for setting in microstepping_table:
            print(setting)
        print("----------------------------------------")
        print(f"Current setting: {self.steps_per_rev} steps/rev")


# Add these functions outside the class to create function-based aliases
def get_position(stepper):
    return stepper.get_position_steps()

def set_position(stepper, position):
    stepper.set_position_steps(position)

def overwrite_pos(stepper, position):
    stepper.set_position_steps(position)

def move_to_mm(stepper, mm_position):
    stepper.move_to_position_mm(mm_position)

def target(stepper, position):
    stepper.target_steps(position)

def free_run(stepper, direction, use_acceleration=True):
    """
    Run the motor continuously in the specified direction.
    Alias for start_continuous() for compatibility.
    
    Args:
        stepper: The DM332TStepper instance
        direction (int): 1 for forward, -1 for backward
        use_acceleration (bool): Whether to use acceleration for smooth startup
    """
    stepper.start_continuous(direction, use_acceleration)