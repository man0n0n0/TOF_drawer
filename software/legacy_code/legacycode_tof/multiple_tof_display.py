######
# this code is aimed to ignore unplugged TOF despite writed on the list
#####

import os
import vl53l0x
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C  
from time import sleep_ms

i2c = I2C(0, sda=Pin(5), scl=Pin(6))

'''TOF'''
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
        
display = SSD1306_I2C(70, 40, i2c)  

'''execution'''
while True :
    display.fill(0)
    display.text(f"MULTIPLE TOF",0, 0, 1)

    for index , _ in enumerate(xshut):
        display.text(f"{vl53[index].range}",23, index*10 + 10, 1)

    display.show()


