import os
import vl53l0x
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C  
from time import sleep_ms
from stepper import Stepper

'''piece variable'''
d_threshold = 1000 #distance minimal de detection en mm
d_out = 11000 #nombre de revolution pour terroir sorti #TODO : convertir en metric
back_speed = 6000 #vitesse de retractation du tirroir
forw_speed = 1000 #vitesse de sortie du tirroir

def homing():
        s.speed(back_speed) 
        s.free_run(1) #move forward
        
        while end_s.value() == 1:
            pass
        
        display.text(f"homed",18, 30, 1)
        s.stop() #stop as soon as the switch is triggered
        s.overwrite_pos(0) #set position as 0 point
        s.target(0) #set the target to the same value to avoid unwanted movement

'''init'''
i2c = I2C(0, sda=Pin(5), scl=Pin(6))

'''--tof'''
vl1xshut = Pin(10, Pin.OUT)#2
# vl2xshut = Pin(15, Pin.OUT)
# vl3xshut = Pin(16, Pin.OUT)
xshut = [
    vl1xshut,
#     vl2xshut,
#     vl3xshut,
]
vl53 = []
for index , power_pin in enumerate(xshut):
    power_pin.value(1)
    vl53.insert(index , vl53l0x.VL53L0X(i2c))  
    if index < len(xshut) - 1:
        vl53[index].set_address(index + 0x30)
        
'''--embeded display'''
display = SSD1306_I2C(70, 40, i2c)

'''--stepper'''
s = Stepper(0,2,1,steps_per_rev=3200) #stp,dir,en
#create an input pin for the end switch (switch connects pin to GND)
end_s = Pin(3, Pin.IN, Pin.PULL_UP)

homing()

'''execution'''
while True :
    d = min(vl53[0].range, 6666, 6666) 
    display.fill(0)    
    display.text(f"{d}",23, 23, 1)
    
    if d < d_threshold :
        homing()
        display.show()
        
    else :
#         display.fill_rect(27, 0, 16, 16, 1)        
#         display.fill_rect(28, 1, 14, 14, 0)        
#         display.vline(31, 4, 11, 1)                
#         display.vline(35, 1, 11, 1)                 
#         display.vline(38, 4, 11, 1)                
#         display.fill_rect(40, 12, 1, 2, 1)          
#         display.show()
        s.track_target() #start stepper again
        s.speed(forw_speed)
        s.target(-d_out)
        #TODO : manage this part to be more fluid
