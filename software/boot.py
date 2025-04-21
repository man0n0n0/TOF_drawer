####
# BOOT FILE FOR ESP32C3OLED module
####

from time import sleep_ms
from machine import PWM, Pin

led = Pin(8, Pin.OUT)
b_boot = Pin(0, Pin.IN)
b_config = Pin(4, Pin.IN, Pin.PULL_UP)

#blink
led.value(1)
sleep_ms(100)
led.value(0)
sleep_ms(100)
#blink
led.value(1)
sleep_ms(100)
led.value(0)
sleep_ms(100)
#blink
led.value(1)
sleep_ms(100)
led.value(0)
sleep_ms(100)

if b_boot.value() == 1:
    pass

elif b_config.value() == 0 : 
     import config_mode

else :
    import ld2410c_stepper


