import os
import vl53l0x
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C  
from time import sleep_ms
from stepper import Stepper

'''piece variable'''
steps_per_rev = 3200
step_per_mm = 25.6 #https://blog.prusa3d.com/calculator_3416/
d_threshold = 2000 #minimal distance for deteciton(mm)
d_out = 220 #distance from homing point (mm
back_speed = 11100 #vitesse de retractation du tirroir (stp/sec)
forw_speed = 1100 #vitesse de sortie du tirroir (step/sec)
homing_speed = 500
wait_inside = 3333 # waiting time after the drawer got inside (mm)

def homing(): 
    s.speed(homing_speed) 
    s.free_run(-1) #move forward

    while end_s.value() == 1:
        pass
    
    display.text(f"homed",18, 30, 1)
    display.show()
    s.stop() #stop as soon as the switch is triggered
    s.overwrite_pos(0) #set position as 0 point
    s.target(0) #set the target to the same value to avoid unwanted movement

'''init'''
i2c = I2C(0, sda=Pin(5), scl=Pin(6))

'''--TOF'''
vl1xshut = Pin(10, Pin.OUT)
vl2xshut = Pin(8, Pin.OUT)
vl3xshut = Pin(9, Pin.OUT)

xshut = [
    vl1xshut,
    vl2xshut,
    vl3xshut,
]

for power_pin in xshut:
    power_pin.value(0)

vl53 = []

for index , power_pin in enumerate(xshut):
    try : 
        print(power_pin)
        power_pin.value(1)
        vl53.insert(index , vl53l0x.VL53L0X(i2c))  
        if index < len(xshut) - 1:
            vl53[index].set_address(index + 0x30)
    except : 
        xshut.pop(index)
        print(f'cleaned list : {xshut}')
        pass
               
'''--embeded display'''
display = SSD1306_I2C(70, 40, i2c)

'''--stepper'''
dir_pin = Pin(2, Pin.OUT)
step_pin = Pin(1, Pin.OUT)
s = Stepper(step_pin,dir_pin,invert_dir=True) #stp,dir,en
end_s = Pin(3, Pin.IN, Pin.PULL_UP)

homing()

'''execution'''
while True :
    d = min(vl53[0].range, vl53[1].range, vl53[2].range) 
    
    # display.fill(0)    

    # for index , _ in enumerate(xshut):
    #     display.text(f"{vl53[index].range}",23, index*10 + 10, 1)

    # display.show()
    
    if d < d_threshold :

        for vel in range(100,back_speed,100):
            s.speed(vel) 
            s.target(10*step_per_mm) # 3mm from home
            sleep_ms(5)
        sleep_ms(500)

        homing()

        sleep_ms(wait_inside - 500)

    else :
        s.track_target() #start stepper again

        s.speed(forw_speed)
        s.target(d_out*step_per_mm)


