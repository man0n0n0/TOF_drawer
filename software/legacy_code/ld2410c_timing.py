from ld2410 import LD2410
from machine import UART, Pin
import _thread
import time

def timer_func(func):
    # This function shows the execution time of 
    # the function object passed
    def wrap_func(*args, **kwargs):
        t1 = time.time_ns()
        result = func(*args, **kwargs)
        t2 = time.time_ns()
        print(f'Function {func.__name__!r} executed in {(t2-t1):.4f}ns')
        return result
    return wrap_func

"""Thread function to continuously read radar data"""
global r1_d
# Initialize UART
uart1 = UART(1, baudrate=256000)
uart1.init(tx=Pin(12), rx=Pin(32))

#r objects
r1 = LD2410()
r1.begin(uart1)

@timer_func
def r_thread(r, n):
    for i in range(n):
        r.read()
        r_d = r1.moving_target_distance()

@timer_func
def r2_thread():
    """Thread function to continuously read radar data"""
    global r2_d
    # Initialize UART
    uart2 = UART(2, baudrate=256000)
    uart2.init(tx=Pin(27), rx=Pin(14))
    
    #r objects
    r2 = LD2410()
    r2.begin(uart2)

    # Read radar data
    r2.read()
    r2_d = r2.moving_target_distance()
    print(r2_d)

while True :
    r_thread(r1, 1)

