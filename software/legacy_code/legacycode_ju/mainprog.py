#import libraries
import _thread
import time
import machine
import utime
import network
import usocket as socket



#import custom python files
import helper as h
import var as v
from motorcontrol import motorControl



mot_in1 = machine.Pin(18 , machine.Pin.OUT)
mot_in2 = machine.Pin(18 , machine.Pin.OUT)
led = machine.Pin(4 , machine.Pin.OUT)
btn = machine.Pin(21, machine.Pin.IN)

led.value(0) 

mot_in1.value(0)
mot_in2.value(1)

mot1 = motorControl(16)

max_speed = 0
ramp_time = 1
run_time = 1
off_time = 1
stp = 10

mot1.set_target_speed(speed=max_speed, time_to_ramp=ramp_time, step_increment=stp)

timer01 = 0
serv_active = False

time.sleep(1)
led.value(1)
time.sleep(0.5)
led.value(0)
time.sleep(0.5)
led.value(1)
time.sleep(0.5)
led.value(0)
if btn.value() is 1 :
    _thread.start_new_thread(h.thread_server_function, ())




max_speed, ramp_time, run_time, off_time = h.motor_data_retriever(v.json_file)
mot1.set_target_speed(speed=max_speed, time_to_ramp=ramp_time, step_increment=stp)
print("start motor")
while True:
   
    start_time = time.ticks_us()
    if v.arriving_post == 1:
        print("arriving post")
        v.arriving_post = 0
        max_speed, ramp_time, run_time, off_time = h.motor_data_retriever(v.json_file)
        mot1.set_target_speed(speed=0, time_to_ramp=0.0001, step_increment=100)
        while not mot1.update_speed():
            pass
        mot1.set_target_speed(speed=max_speed, time_to_ramp=ramp_time, step_increment=stp)
    
    
    if not mot1.update_speed():
        pass     
    
    if mot1.update_speed():
        if mot1.target_speed == max_speed:
            
            if timer01 > run_time*1000000:
                mot1.set_target_speed(speed=0, time_to_ramp=0.0001, step_increment=100)
                #print(f"RUN FOR {timer01 / 100000:.6f} seconds ")
                timer01 =0
            timer01 += time.ticks_diff(time.ticks_us(), start_time)
            
        else:
            #start_time_pause = time.ticks_us()
            if timer01 > off_time*1000000:
                mot1.set_target_speed(speed=max_speed, time_to_ramp=ramp_time, step_increment=stp)
                #print(f"STOP FOR {timer01 / 100000:.6f} seconds ")
                timer01 =0     
            timer01 += time.ticks_diff(time.ticks_us(), start_time)
        
