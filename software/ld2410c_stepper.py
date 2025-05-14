import os
from machine import UART,Pin, I2C
from ssd1306 import SSD1306_I2C  
from time import sleep_ms
from stepper import Stepper
from ld2410 import LD2410

'''piece variable'''
steps_per_rev = 3200
step_per_mm = 25.6 #https://blog.prusa3d.com/calculator_3416/
d_threshold = 2000 #minimal distance for detection(mm)
d_out = 220 #distance from homing point (mm)
back_speed = 11100 #retraction speed of drawer (stp/sec)
forw_speed = 1100 #exit speed of drawer (step/sec)
homing_speed = 500
wait_inside = 3333 # waiting time after the drawer got inside (mm)


def display_msg(msg : str):
    '''lines as to be seperated by /n'''
    display.fill(0)
    display.text("bouvy_drawer", 5, 0, 1)

    lines = msg.split('\n')

    for i, line in enumerate(lines):
        display.text(line, 0, (i*10)+10, 1)
        
    display.show()

def homing():
    display_msg("homing.../n")
    s.speed(homing_speed) 
    s.free_run(-1) #move forward
    while end_s.value() == 1:
        pass
    display_msg("homed !/n watching.../n")
    s.stop() #stop as soon as the switch is triggered
    s.overwrite_pos(0) #set position as 0 point
    s.target(0) #set the target to the same value to avoid unwanted movement
    

'''-----init------'''
i2c = I2C(0, sda=Pin(5), scl=Pin(6))

'''LD2410 radar'''
# Initialize UART
uart = UART(1, baudrate=256000)
uart.init(tx=Pin(10), rx=Pin(3))

# Create radar instance
radar = LD2410()
radar.begin(uart)


'''embeded display'''
display = SSD1306_I2C(70, 40, i2c)

'''stepper'''
s = Stepper(step_pin=2, dir_pin=1, en_pin=7, invert_dir=True) #stp,dir,en  ###to fix if problem
end_s = Pin(3, Pin.IN, Pin.PULL_UP)


'''------execution------'''
# homing()
drawer_open = False

while True:
    # Read data from sensor
    radar.read()
    
    # Check if targets are detected
    if radar.moving_target_detected():
       display_msg(f"radar :\n {radar.moving_target_distance()*10}")
    else :
        display_msg("NOT MOVING")

    # if d < d_threshold and drawer_open:
    #     s.enable(True)
    #     for vel in range(100,back_speed,100):
    #         s.speed(vel) 
    #         s.target(10*step_per_mm) # 3mm from home
    #         sleep_ms(5)
    #     sleep_ms(500) #TODO : change waiting time to actual pos https://pypi.org/project/micropython-stepper/
    #     homing()
    #     sleep_ms(wait_inside - 500)
    #     drawer_open = False
    #     s.enable(False)

    # elif not drawer_open:
    #     s.enable(True)
    #     s.track_target() #start stepper again
    #     s.speed(forw_speed)
    #     s.target(d_out*step_per_mm) # go to outside pos
    #     drawer_open = True
    #     s.enable(False)