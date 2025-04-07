####
# BOOT FILE FOR ESP32S2Mini_wemos module
####

# Use an interrupt function count the number of times a button has been pressed
from time import sleep_ms
from machine import PWM, Pin

led = Pin(15, Pin.OUT)
b_boot = Pin(0, Pin.IN, Pin.PULL_UP)
#b_config = Pin(n, Pin.IN)

led.value(1)
sleep_ms(100)
led.value(0)
sleep_ms(100)

if b_boot.value() == 0:
    pass

# elif b_config.value() == 1 : 
#     import config

else :
    import single_tof_stepper


