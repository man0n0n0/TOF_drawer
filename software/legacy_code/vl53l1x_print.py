from machine import I2C, Pin
from vl53l1x import VL53L1X
import time
i2c = I2C(0, sda=Pin(10), scl=Pin(3))
distance = VL53L1X(i2c)
while True:
    print("range: mm ", distance.read())
    time.sleep_ms(50)


