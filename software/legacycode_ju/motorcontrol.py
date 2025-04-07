import utime
import machine


class motorControl :
    def __init__(self,pin):
        self.pwm = machine.PWM(machine.Pin(pin))
        self.target_speed = 0
        self.current_speed = 0
        self.step_increment = 1
        self.ramp_time = 0
        self.direction = 1
        self.delta = 0 
        self.pwm.duty(self.current_speed)
        self.last_call_time = utime.ticks_us()
        
        
    def set_target_speed(self, speed, time_to_ramp=None, step_increment=1):
        self.target_speed = speed
        self.current_speed = self.pwm.duty()
        self.delta = self.current_speed  - speed
        self.direction = 1 if self.delta < 0  else -1
        self.step_increment = step_increment
        self.time_to_ramp = time_to_ramp*1000000 or 0
        self.steps_qty = abs(self.delta / self.step_increment)
        if self.steps_qty < 1:
            self.steps_qty = 1
        self.steps_timming = self.time_to_ramp / self.steps_qty

    
    def update_speed(self):
        current_time = utime.ticks_us()
        self.current_speed  = self.pwm.duty()
        time_elapsed = utime.ticks_diff(current_time, self.last_call_time)
        steps = int((time_elapsed / self.time_to_ramp) / self.step_increment) + 1
        #print(".")

        if  steps > 0 and time_elapsed > self.steps_timming:
            self.current_speed += self.direction * self.step_increment * steps
            self.current_speed = max(0, min(1023, self.current_speed))

            
            if self.direction == 1 and self.current_speed >= self.target_speed:
                self.pwm.duty(self.target_speed)
                return True
            elif self.direction == -1 and self.current_speed <= self.target_speed:
                self.pwm.duty(self.target_speed)
                return True
            
            self.pwm.duty(self.current_speed)
#             print(self.pwm.duty())
            self.last_call_time = current_time

        return False