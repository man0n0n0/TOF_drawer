from ld2410 import LD2410
from machine import UART, Pin
import time

# Initialize UART
uart = UART(1, baudrate=256000)
uart.init(tx=Pin(10), rx=Pin(3))

# Create radar instance
radar = LD2410()
radar.begin(uart)

# Main loop
while True:
    # Read data from sensor
    radar.read()
    print(f"Stationary target: {radar.stationary_target_distance()}cm, energy: {radar.stationary_target_energy()}")

    time.sleep(0.1)



