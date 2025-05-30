from ld2410 import LD2410
from machine import UART, Pin
import time

# Initialize UART
uart1 = UART(1, baudrate=256000)
uart1.init(tx=Pin(12), rx=Pin(32))

uart2 = UART(2, baudrate=256000)
uart2.init(tx=Pin(27), rx=Pin(14))

# Create radar instance
radar1 = LD2410()
radar1.begin(uart1)
# Create radar instance
radar2 = LD2410()
radar2.begin(uart2)

# Main loop
while True:
    # Read data from sensor
    radar1.read()
    radar2.read()

    print(f"Stationary target: {radar1.moving_target_distance()}cm, energy: {radar1.stationary_target_energy()}")
    print(f"Stationary target: {radar2.moving_target_distance()}cm, energy: {radar2.stationary_target_energy()}")



