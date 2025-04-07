# This file is executed on every boot (including wake-boot from deepsleep)

import time
import machine



btn = machine.Pin(21, machine.Pin.IN)
led = machine.Pin(2 , machine.Pin.OUT)


time.sleep(0.25)
led.value(0)
time.sleep(0.25)
led.value(1)
time.sleep(0.25)
led.value(0)
time.sleep(0.25)
led.value(1)
time.sleep(0.25)
led.value(0)
time.sleep(0.25)
led.value(1)
time.sleep(0.25)
led.value(0)

if btn.value() is 1 :
    print("exit")
else :
    print("run")
    import mainprog
        
        

