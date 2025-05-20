import machine
import time

class StepperDM332T:
    def __init__(self, step_pin, dir_pin, en_pin=None, 
                 steps_per_rev=200, speed_sps=10, 
                 invert_dir=False, timer_id=0,
                 steps_per_mm=None):
        """
        Initialize a stepper motor with DM332T driver
        
        Parameters:
        - step_pin: GPIO pin for STEP/PUL signal
        - dir_pin: GPIO pin for DIR signal
        - en_pin: GPIO pin for ENA signal (optional)
        - steps_per_rev: Steps per revolution (default: 200 for 1.8° motor)
        - speed_sps: Speed in steps per second (default: 10)
        - invert_dir: Invert direction logic (default: False)
        - timer_id: Timer ID to use (default: -1)
        - steps_per_mm: Steps per millimeter for linear motion (optional)
        """
        # Configure pins
        if not isinstance(step_pin, machine.Pin):
            step_pin = machine.Pin(step_pin, machine.Pin.OUT)
        if not isinstance(dir_pin, machine.Pin):
            dir_pin = machine.Pin(dir_pin, machine.Pin.OUT)
        if (en_pin is not None) and (not isinstance(en_pin, machine.Pin)):
            en_pin = machine.Pin(en_pin, machine.Pin.OUT)
            
        # Store pin control functions for faster access
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.en_pin = en_pin
        
        # Initialize pins to default states
        self.step_pin.value(0)
        self.dir_pin.value(0)
        if self.en_pin is not None:
            self.en_pin.value(1)  # Enable the drive by default (high for NPN control)
            
        # Configuration
        self.invert_dir = invert_dir
        self.timer = machine.Timer(timer_id)
        self.timer_is_running = False
        self.free_run_mode = 0
        self.enabled = True
        
        # Position tracking
        self.target_pos = 0
        self.pos = 0
        
        # Speed control
        self.steps_per_sec = speed_sps
        self.steps_per_rev = steps_per_rev
        
        # Linear motion support
        self.steps_per_mm = steps_per_mm
        
        # DM332T timing requirements
        self.pulse_width_us = 10  # Minimum 7.5μs according to DM332T manual
        self.direction_setup_us = 10  # Minimum 5μs according to DM332T manual

    def set_steps_per_mm(self, steps_per_mm):
        """Set steps per millimeter for linear motion"""
        self.steps_per_mm = steps_per_mm

    def speed(self, sps):
        """Set speed in steps per second"""
        self.steps_per_sec = sps
        if self.timer_is_running:
            self.track_target()
            
    def speed_rps(self, rps):
        """Set speed in revolutions per second"""
        self.speed(rps * self.steps_per_rev)
        
    def speed_mms(self, mm_per_sec):
        """Set speed in millimeters per second"""
        if self.steps_per_mm is None:
            raise ValueError("steps_per_mm not set. Use set_steps_per_mm() first.")
        self.speed(mm_per_sec * self.steps_per_mm)

    def target(self, t):
        """Set target position in steps"""
        self.target_pos = t
        self.track_target()

    def target_deg(self, deg):
        """Set target position in degrees"""
        self.target(self.steps_per_rev * deg / 360.0)

    def target_rad(self, rad):
        """Set target position in radians"""
        self.target(self.steps_per_rev * rad / (2.0 * 3.14159))
        
    def target_mm(self, mm):
        """Set target position in millimeters"""
        if self.steps_per_mm is None:
            raise ValueError("steps_per_mm not set. Use set_steps_per_mm() first.")
        self.target(mm * self.steps_per_mm)
        
    def move_mm(self, mm):
        """Move a relative distance in millimeters from current position"""
        if self.steps_per_mm is None:
            raise ValueError("steps_per_mm not set. Use set_steps_per_mm() first.")
        self.target(self.pos + (mm * self.steps_per_mm))

    def get_pos(self):
        """Get current position in steps"""
        return self.pos

    def get_pos_deg(self):
        """Get current position in degrees"""
        return self.get_pos() * 360.0 / self.steps_per_rev

    def get_pos_rad(self):
        """Get current position in radians"""
        return self.get_pos() * (2.0 * 3.14159) / self.steps_per_rev
        
    def get_pos_mm(self):
        """Get current position in millimeters"""
        if self.steps_per_mm is None:
            raise ValueError("steps_per_mm not set. Use set_steps_per_mm() first.")
        return self.get_pos() / self.steps_per_mm

    def overwrite_pos(self, p):
        """Overwrite the current position in steps"""
        self.pos = p
        
    def overwrite_pos_mm(self, mm):
        """Overwrite the current position in millimeters"""
        if self.steps_per_mm is None:
            raise ValueError("steps_per_mm not set. Use set_steps_per_mm() first.")
        self.pos = mm * self.steps_per_mm

    def step(self, d):
        """Perform a single step in the given direction"""
        if d > 0:
            if self.enabled:
                # Set direction first and wait for direction setup time
                self.dir_pin.value(1 ^ self.invert_dir)
                time.sleep_us(self.direction_setup_us)
                
                # Generate pulse with proper pulse width
                self.step_pin.value(1)
                time.sleep_us(self.pulse_width_us)
                self.step_pin.value(0)
                time.sleep_us(self.pulse_width_us)  # Ensure low level width minimum
                
                self.pos += 1
        elif d < 0:
            if self.enabled:
                # Set direction first and wait for direction setup time
                self.dir_pin.value(0 ^ self.invert_dir)
                time.sleep_us(self.direction_setup_us)
                
                # Generate pulse with proper pulse width
                self.step_pin.value(1)
                time.sleep_us(self.pulse_width_us)
                self.step_pin.value(0)
                time.sleep_us(self.pulse_width_us)  # Ensure low level width minimum
                
                self.pos -= 1

    def _timer_callback(self, t):
        """Timer callback for continuous stepping"""
        if self.free_run_mode > 0:
            self.step(1)
        elif self.free_run_mode < 0:
            self.step(-1)
        elif self.target_pos > self.pos:
            self.step(1)
        elif self.target_pos < self.pos:
            self.step(-1)

    def free_run(self, d):
        """Run motor continuously in specified direction"""
        self.free_run_mode = d
        if self.timer_is_running:
            self.timer.deinit()
            self.timer_is_running = False
            
        if d != 0:
            self.timer.init(freq=self.steps_per_sec, callback=self._timer_callback)
            self.timer_is_running = True
        else:
            self.dir_pin.value(0)

    def track_target(self):
        """Move to target position using timer"""
        self.free_run_mode = 0
        if self.timer_is_running:
            self.timer.deinit()
            self.timer_is_running = False
            
        if self.target_pos != self.pos:
            self.timer.init(freq=self.steps_per_sec, callback=self._timer_callback)
            self.timer_is_running = True

    def stop(self):
        """Stop motor movement immediately"""
        self.free_run_mode = 0
        if self.timer_is_running:
            self.timer.deinit()
            self.timer_is_running = False
        self.dir_pin.value(0)

    def enable(self, e):
        """Enable or disable the driver"""
        if self.en_pin:
            # For DM332T: High level for enabling (NPN control signal)
            self.en_pin.value(1 if e else 0)
        self.enabled = e
        if not e:
            self.dir_pin.value(0)

    def is_enabled(self):
        """Check if driver is enabled"""
        return self.enabled