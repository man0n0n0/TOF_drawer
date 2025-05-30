####################
# version on the code working on the none dex : multi core operation and 3 uart avaiable
####################

from machine import UART, Pin, I2C
from time import sleep_ms

# Initialize gpio detection for radar
r1 = Pin(32, Pin.IN, Pin.PULL_UP) # use the "tx pin" placement (need a manual change on the detector)
r2 = Pin(14, Pin.IN, Pin.PULL_UP) # use the "tx pin" placement
human = True

# Main loop
while True:
    print(f"radar 1 : {r1.value()} radar 2 : {r2.value()}")
    sleep_ms(50)