import machine
from time import sleep
from stepper_dm332t import Stepper

s = Stepper(33,25,26,steps_per_rev=3200,timer_id=0)

# End switch declaration
end_s = Pin(15, Pin.IN, Pin.PULL_UP)

s.enable(True)

s.speed(500) 
s.free_run(-1) #move forward

while end_s.value() == 1:
    pass

s.stop() #stop as soon as the switch is triggered
s.overwrite_pos(0) #set position as 0 point
s.track_target() #start stepper again


s.target(1000)
