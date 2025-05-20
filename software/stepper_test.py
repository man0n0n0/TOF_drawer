import machine
from time import sleep
from stepper import Stepper

s1 = Stepper(33,25,26,steps_per_rev=3200,timer_id=0)
#create an input pin for the end switch (switch connects pin to GND)
endswitch = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)

s1.speed(200) #use low speed for the calibration
s1.free_run(-1) #move backwards
while endswitch.value(): #wait till the switch is triggered
    pass
s1.stop() #stop as soon as the switch is triggered
s1.overwrite_pos(0) #set position as 0 point
s1.target(0) #set the target to the same value to avoid unwanted movement
s1.speed(1000) #return to default speed
s1.track_target() #start stepper again

#calibration finished. Do something else below.
s1.target_deg(45)
time.sleep(5.0)