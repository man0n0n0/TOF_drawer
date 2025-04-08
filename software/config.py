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
ap.config(essid='drawer', password='bouvy_admin')
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
                    
        response = redirect('/')
        
    return response

i2c = I2C(0, sda=Pin(5), scl=Pin(6))

'''--embeded display'''
display = SSD1306_I2C(70, 40, i2c)
display.fill(0)    
display.text(f"!NETWORK CONFIG!",0, 10, 1)
display.text(f"REBOOT",10, 28, 1)
display.text(f"WHEN DONE",2, 30, 1)
display.text(f'{ap.ifconfig()[0]}:5000', 0, 28, 1)
display.show()


'''execution'''
async def main():
    # start the server in a background task
    server = asyncio.create_task(app.start_server())

    # ... do other asynchronous work here ...

    # cleanup before ending the application
    await server

asyncio.run(main())

