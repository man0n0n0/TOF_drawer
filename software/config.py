from machine import Pin, I2C
import json_manager as j
import asyncio
import network
from microdot import Microdot, Response, redirect
from ssd1306 import SSD1306_I2C
import os

# Initialize Microdot app
app = Microdot()

# WiFi Access Point setup
def setup_wifi():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid='drawer', password='bouvy_admin')
    while ap.active() == False:
        pass
    return ap

# Initialize I2C and OLED display
def setup_display():
    i2c = I2C(0, sda=Pin(5), scl=Pin(6))
    display = SSD1306_I2C(70, 40, i2c)
    return display

# Display network information
def show_network_info(display, ap):
    display.fill(0)
    display.text("DRAWER SETUP", 0, 0, 1)
    display.text("IP Address:", 0, 10, 1)
    display.text(f'{ap.ifconfig()[0]}', 0, 20, 1)
    display.text("Port: 5000", 0, 30, 1)
    display.show()

# Routes
@app.route('/', methods=['GET', 'POST'])
async def index(request):
    if request.method == 'POST':
        # Get form data
        form_data = request.form
        
        # Update settings
        settings = j.load_settings()
        
        try:
            settings['d_threshold'] = int(form_data.get('d_threshold', settings['d_threshold']))
            settings['back_speed'] = int(form_data.get('back_speed', settings['back_speed']))
            settings['forw_speed'] = int(form_data.get('forw_speed', settings['forw_speed']))
            
            # Save updated settings
            j.save_settings(settings)
            message = "Settings updated successfully!"
        except Exception as e:
            message = f"Error updating settings: {str(e)}"
            
        # Redirect to avoid form resubmission
        return redirect('/')
    
    # GET request - show the form with current settings
    settings = j.load_settings()
    
    # Read the HTML template
    try:
        with open('index.html', 'r') as f:
            html = f.read()
    except:
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error: Template file not found</h1>
            <p>Please make sure index.html exists.</p>
        </body>
        </html>
        """
    
    # Replace placeholders with actual values
    html = html.replace('{{d_threshold}}', str(settings['d_threshold']))
    html = html.replace('{{back_speed}}', str(settings['back_speed']))
    html = html.replace('{{forw_speed}}', str(settings['forw_speed']))
    
    return Response(body=html, headers={'Content-Type': 'text/html'})

# Main function
async def main():
    # Setup WiFi
    ap = setup_wifi()
    
    # Setup display
    display = setup_display()
    show_network_info(display, ap)
    
    # Start the server
    server = asyncio.create_task(app.start_server(debug=True, port=5000))
    
    # Wait for server to complete (will run indefinitely)
    await server

# Run the application
if __name__ == "__main__":
    asyncio.run(main())