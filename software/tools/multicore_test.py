from ld2410 import LD2410
from machine import UART, Pin
import _thread
import time

def r_thread():
        # Read radar data
    while thread_running:
        # Initialize UART
        uart1 = UART(1, baudrate=256000)
        uart1.init(tx=Pin(12), rx=Pin(32))

        uart2 = UART(2, baudrate=256000)
        uart2.init(tx=Pin(27), rx=Pin(14))

        # Create r instance
        r1 = LD2410()
        r1.begin(uart1)
        # Create r instance
        r2 = LD2410()
        r2.begin(uart2)

        # Main loop
        while True:
            # Read data from sensor
            r1.read()
            r2.read()

        print(f"Stationary target: {r1.moving_target_distance()}cm, energy: {r1.stationary_target_energy()}")
        print(f"Stationary target: {r2.moving_target_distance()}cm, energy: {r2.stationary_target_energy()}")

        time.sleep(0.1)

thread_id = r_thread.start_new_thread(r_thread)


