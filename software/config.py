from machine import Pin, I2C
import ujson
import asyncio
import network
from microdot import os
from ssd1306 import SSD1306_I2C  
import Microdot, redirect, send_file

# '''system variable'''
# d_threshold = 1000 #distance minimal de detection en mm
# d_out = 11000 #nombre de revolution pour terroir sorti #TODO : convertir en metric
# back_speed = 6000 #vitesse de retractation du tirroir
# forw_speed = 1000 #vitesse de sortie du tirroir

'''init'''
'''--wifi'''
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='drawer', password='123456789')
while ap.active() == False:
  pass

'''---website'''
app = Microdot()

@app.route('/', methods=['GET', 'POST'])
async def index(request):
    form_cookie = None
    message_cookie = None
    
    if request.method == 'POST':   
        if 'set' in request.form:
            pull = None
            #attribute the returning value from the forms to variable
            # mode = request.form['mode']        
            # vaping_time = int(request.form['vaping_time'])
            # TODO: HERE manage ujson ? 
            
            message_cookie = "current mode is {mode} <br> timing is {vaping_time} - {chilling_time} ".format(mode=request.form['mode'], vaping_time = vaping_time  if not mode == 'random_selection' else 'random', chilling_time=chilling_time if not mode == 'random_selection' else '' )   
        
        response = redirect('/')
        
    else:
        if 'message' not in request.cookies:
            message_cookie = 'machine is load with default preset'
        response = send_file('V4P3R.html')
        
    if form_cookie:
        response.set_cookie('form', form_cookie)
        
    if message_cookie:
        response.set_cookie('message', message_cookie)
        
    return response

i2c = I2C(0, sda=Pin(5), scl=Pin(6))

'''--embeded display'''
display = SSD1306_I2C(70, 40, i2c)
display.fill(0)    
display.text(f"!NETWORK CONFIG!",0, 10, 1)
display.text(f"REBOOT",10, 28, 1)
display.text(f"WHEN DONE",2, 30, 1)
display.show()


'''execution'''
async def main():
    # start the server in a background task
    server = asyncio.create_task(app.start_server())

    # ... do other asynchronous work here ...

    # cleanup before ending the application
    await server

asyncio.run(main())

