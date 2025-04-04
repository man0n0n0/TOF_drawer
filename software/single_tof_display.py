import os
import vl53l0x
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C  
from time import sleep_ms

d_threshold = 200

i2c = I2C(0, sda=Pin(5), scl=Pin(6))

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
        
display = SSD1306_I2C(70, 40, i2c)  

'''execution'''
while True :
    d = min(vl53[0].range, 6666, 6666) #random value 
    
    display.fill(0)
    
    if d > d_threshold :
        display.fill_rect(27, 0, 16, 16, 1)         # (32/2 = 16 de large)
        display.fill_rect(28, 1, 14, 14, 0)         # (28/2 = 14 de large)
        display.vline(31, 4, 11, 1)                 # (9/2+27, 8/2, 22/2, 1)
        display.vline(35, 1, 11, 1)                 # (16/2+27, 2/2, 22/2, 1)
        display.vline(38, 4, 11, 1)                 # (23/2+27, 8/2, 22/2, 1)
        display.fill_rect(40, 12, 1, 2, 1)          # (26/2+27, 24/2, 2/2, 4/2, 1)
        
    display.text(f"{d}",23, 30, 1)
    display.show()


