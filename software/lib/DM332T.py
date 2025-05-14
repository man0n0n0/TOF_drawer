"""
DM332T Stepper Motor Library - Fixed Version
For ESP32 and similar microcontrollers
"""

import time
from machine import Pin, Timer

class DM332TStepper:
    """
    Class for controlling stepper motors with DM332T drivers in MicroPython.
    """
    
    def __init__(self, step_pin, dir_pin, enable_pin=None, steps_per_rev=3200, 
                 steps_per_mm=25.6, invert_dir=False, timer_id=0):
        """
        Initialize the stepper motor controller.
        
        Args:
            step_pin (int or Pin): GPIO pin number or Pin object for step signal
            dir_pin (int or Pin): GPIO pin number or Pin object for direction signal
            enable_pin (int or Pin, optional): GPIO pin number or Pin object for enable signal
            steps_per_rev (int, optional): Steps per revolution (default: 3200)
            steps_per_mm (float, optional): Steps per millimeter for linear movement (default: 25.6)
            invert_dir (bool, optional): Invert direction logic (default: False)
            timer_id (int, optional): Timer ID to use for step generation (default: 0)
        """
        # Create Pin objects if integers are provided
        if isinstance(step_pin, int):
            self.step_pin = Pin(step_pin, Pin.OUT)
        else:
            self.step_pin = step_pin
            
        if isinstance(dir_pin, int):
            self.dir_pin = Pin(dir_pin, Pin.OUT)
        else:
            self.dir_pin = dir_pin
        
        if enable_pin is not None:
            if isinstance(enable_pin, int):
                self.enable_pin = Pin(enable_pin, Pin.OUT)
            else:
                self.enable_pin = enable_pin
            self.has_enable = True
        else:
            self.has_enable = False
            
        self.steps_per_rev = steps_per_rev
        self.steps_per_mm = steps_per_mm
        self.invert_dir = invert_dir
        self._timer_id = timer_id
        
        self._current_position = 0
        self._target_position = 0
        self._speed = 1000  # steps per second
        self._acceleration = 500  # steps per second^2 (default)
        self._min_pulse_width = 10  # microseconds
        self._direction = 1  # 1 or -1
        self._is_running = False
        self._timer = None
        self._step_interval = 1000000 / self._speed  # in microseconds
        self._use_acceleration = True  # Whether to use acceleration or not
        
        # Initialize pins
        self.step_pin.value(0)
        self.set_direction(1)
        
        if self.has_enable:
            self.enable(False)  # Default to disabled
    
    def _calculate_step_interval(self):
        """Calculate the step interval in microseconds based on speed."""
        if self._speed > 0:
            self._step_interval = 1000000 / self._speed
        else:
            self._step_interval = 1000000  # Default to 1 step per second
    
    def speed(self, speed):
        """
        Set the motor speed in steps per second.
        
        Args:
            speed (float): Speed in steps per second (always positive)
        """
        self._speed = abs(speed)  # Ensure speed is positive
        self._calculate_step_interval()
    
    def set_speed(self, speed):
        """
        Set the motor speed in steps per second.
        Alias for speed() for compatibility.
        
        Args:
            speed (float): Speed in steps per second (always positive)
        """
        self.speed(speed)
        
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
        # In this simplified version, we use the same value for acceleration and deceleration
        self._acceleration = deceleration
        
    def disable_acceleration(self):
        """Disable acceleration/deceleration for movements."""
        self._use_acceleration = False
        
    def enable_acceleration(self):
        """Enable acceleration/deceleration for movements."""
        self._use_acceleration = True
        
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
            self.enable_pin.value(not state)  # Enable is active LOW on most drivers
    
    def disable(self):
        """Disable the motor driver."""
        self.enable(False)
    
    def _step(self):
        """Generate a single step pulse."""
        self.step_pin.value(1)
        time.sleep_us(self._min_pulse_width)
        self.step_pin.value(0)
        
        # Update position
        self._current_position += self._direction
    
    def move_steps(self, steps):
        """
        Move the motor a specified number of steps with acceleration profile.
        
        Args:
            steps (int): Number of steps to move (positive or negative)
        """
        if steps == 0:
            return
            
        # Set direction
        direction = 1
        if steps < 0:
            direction = -1
            steps = abs(steps)  # Make positive for calculation
            
        self.set_direction(direction)
        
        # Calculate constant speed interval
        self._calculate_step_interval()
        
        # If acceleration is disabled, use constant speed
        if not self._use_acceleration:
            for _ in range(steps):
                self._step()
                time.sleep_us(int(self._step_interval))
            return
        
        # Acceleration-based movement
        
        # Calculate acceleration parameters
        accel_steps = int((self._speed * self._speed) / (2.0 * self._acceleration))
        decel_steps = accel_steps  # Same formula for deceleration
        
        # If movement is too short for full accel + decel
        if accel_steps + decel_steps > steps:
            accel_steps = steps // 2
            decel_steps = steps - accel_steps
        
        # Calculate constant speed phase
        const_steps = steps - accel_steps - decel_steps
        
        # Execute acceleration phase
        for i in range(accel_steps):
            # v = sqrt(2*a*d) - calculate speed at this step
            current_speed = (2.0 * self._acceleration * (i + 1)) ** 0.5
            interval = 1000000 / current_speed  # microseconds
            
            self._step()
            time.sleep_us(int(interval))
        
        # Execute constant speed phase
        for _ in range(const_steps):
            self._step()
            time.sleep_us(int(self._step_interval))
        
        # Execute deceleration phase
        for i in range(decel_steps):
            # v = sqrt(2*a*d) - calculate speed for remaining steps
            steps_remaining = decel_steps - i
            current_speed = (2.0 * self._acceleration * steps_remaining) ** 0.5
            if current_speed < 50:  # Minimum speed to prevent stalling
                current_speed = 50
            interval = 1000000 / current_speed  # microseconds
            
            self._step()
            time.sleep_us(int(interval))
    
    def move_to_position(self, position):
        """
        Move to an absolute position.
        
        Args:
            position (int): Target position in steps
        """
        steps = position - self._current_position
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
    
    def set_position(self, position):
        """
        Set the current position without moving the motor.
        
        Args:
            position (int): Position value to set
        """
        self._current_position = position
        self._target_position = position
    
    # Alias for compatibility with drawer control code
    def overwrite_pos(self, position):
        """
        Alias for set_position() for compatibility with drawer control code.
        
        Args:
            position (int): Position value to set
        """
        self.set_position(position)
    
    def target(self, position):
        """
        Set the target position for the motor.
        
        Args:
            position (int): Target position in steps
        """
        self._target_position = position
        
    def track_target(self):
        """
        Start moving the motor to the target position.
        This is a blocking function that will wait until the target is reached.
        """
        steps = self._target_position - self._current_position
        self.move_steps(steps)
    
    def stop(self):
        """Stop the motor movement."""
        if self._timer:
            self._timer.deinit()
            self._timer = None
        self._is_running = False
    
    def free_run(self, direction):
        """
        Run the motor continuously in the specified direction.
        
        Args:
            direction (int): 1 for forward, -1 for backward
        """
        self.set_direction(direction)
        
        # Create a timer to generate steps
        if self._timer is None:
            self._timer = Timer(self._timer_id)
        else:
            try:
                self._timer.deinit()
            except:
                pass
        
        # Calculate the timer period in milliseconds
        # For ESP32, a reasonable minimum is 1ms
        period_ms = max(1, int(self._step_interval / 1000))
        
        # Start the timer
        self._timer.init(period=period_ms, mode=Timer.PERIODIC, 
                       callback=lambda t: self._step())
        
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
        Home the motor using a home switch with proper acceleration.
        
        Args:
            home_switch_pin (Pin): Pin object for the home switch
            homing_speed (int, optional): Speed for homing in steps/second (default: 500)
            backoff_steps (int, optional): Steps to back off after hitting switch (default: 100)
            acceleration (int, optional): Acceleration for homing in steps/second² (default: None, uses current setting)
            
        Note:
            Assumes switch is normally open and connects to GND when triggered
            (will use internal pull-up resistor)
        """
        # Configure as input with pull-up
        if not isinstance(home_switch_pin, Pin):
            home_switch_pin = Pin(home_switch_pin, Pin.IN, Pin.PULL_UP)
        
        # Store original settings
        original_speed = self._speed
        original_accel = self._acceleration
        original_use_accel = self._use_acceleration
        
        # Enable motor
        self.enable(True)
        
        # Set homing direction (backward)
        self.set_direction(-1)
        
        # Set homing speed
        self.speed(homing_speed)
        
        # Set acceleration if provided
        if acceleration is not None:
            self.set_acceleration(acceleration)
            self._use_acceleration = True
        
        # Calculate acceleration parameters
        current_speed = 50  # Start at low speed
        max_speed = homing_speed
        accel = self._acceleration
        
        # Keep track of steps for acceleration calculation
        accel_steps = 0
        
        # Home until switch is triggered
        while home_switch_pin.value() == 1:  # While switch not triggered
            # Calculate speed based on acceleration if enabled
            if self._use_acceleration and accel_steps < 1000000:  # Prevent infinite acceleration
                # v = sqrt(2*a*d) - calculate speed at this step
                current_speed = min(max_speed, (2.0 * accel * accel_steps) ** 0.5)
                if current_speed < 50:  # Minimum speed
                    current_speed = 50
                
                # Calculate step interval based on current speed
                interval = 1000000 / current_speed  # microseconds
                
                # Increment step counter for acceleration calculation
                accel_steps += 1
            else:
                # Use constant speed if acceleration is disabled
                interval = self._step_interval
            
            # Generate step pulse
            self.step_pin.value(1)
            time.sleep_us(self._min_pulse_width)
            self.step_pin.value(0)
            
            # Update position
            self._current_position += self._direction
            
            # Wait for next step
            time.sleep_us(int(interval))
        
        # Stop and set position to 0
        self.stop()
        self.set_position(0)  # Zero position when home switch hit
        
        # Back off slightly if needed
        if backoff_steps > 0:
            # Use constant speed for backoff
            backoff_speed = min(200, homing_speed)  # Limit to reasonable speed
            
            # Calculate interval for backoff
            backoff_interval = 1000000 / backoff_speed
            
            # Set direction for backoff (forward, away from switch)
            self.set_direction(1)
            
            # Execute backoff steps
            for _ in range(backoff_steps):
                # Generate step pulse
                self.step_pin.value(1)
                time.sleep_us(self._min_pulse_width)
                self.step_pin.value(0)
                
                # Update position
                self._current_position += self._direction
                
                # Wait for next step
                time.sleep_us(int(backoff_interval))
            
            # Reset position to 0 after backoff
            self.set_position(0)
        
        # Restore original settings
        self.speed(original_speed)
        self._acceleration = original_accel
        self._use_acceleration = original_use_accel
        
        return True

    def microstepping_info(self):
        """
        Print information about DM332T microstepping configuration.
        """
        print("DM332T Microstepping Guide:")
        print("---------------------------")
        print("SW1-SW4 DIP switches configuration:")
        print("1. All OFF: 400 steps/rev (full step)")
        print("2. SW1=ON: 800 steps/rev (1/2)")
        print("3. SW2=ON: 1600 steps/rev (1/4)")
        print("4. SW1+SW2=ON: 3200 steps/rev (1/8)")
        print("5. SW3=ON: 6400 steps/rev (1/16)")
        print("6. SW1+SW3=ON: 12800 steps/rev (1/32)")
        print("7. SW2+SW3=ON: 25600 steps/rev (1/64)")
        print("8. SW1+SW2+SW3=ON: 51200 steps/rev (1/128)")
        print("---------------------------")
        print(f"Current setting: {self.steps_per_rev} steps/rev")