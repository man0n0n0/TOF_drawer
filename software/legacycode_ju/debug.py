import machine
import utime

btn = machine.Pin(21, machine.Pin.IN)


while 1 :
    print(btn.value())
    utime.sleep(0.1)