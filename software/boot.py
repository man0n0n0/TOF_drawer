# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
####
# BOOT FILE FOR NONEDEX module
####

from time import sleep_ms
from machine import PWM, Pin, I2C
 
led = Pin(2, Pin.OUT)
b_boot = Pin(21, Pin.IN, Pin.PULL_UP) #
b_config = Pin(17, Pin.IN, Pin.PULL_UP)

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

if b_boot.value() == 0 :
    print("bootmode")
    pass

elif b_config.value() == 0: 
    import config_mode

else :
    import main_mode

