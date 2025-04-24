import network
import json
from machine import Pin, I2C, reset
from ssd1306 import SSD1306_I2C
import socket
import time

CONFIG_FILE = 'config.json'
INDEX_FILE = 'index.html'

def display_msg(display, msg):
    display.fill(0)
    display.text("bouvy_drawer", 0, 0, 1)
    y = 10
    for line in msg.split('\n'):
        display.text(line, 0, y, 1)
        y += 10
    display.show()

def main():
    # Setup network
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid='drawer-config', password='admin123', authmode=3)
    ip = ap.ifconfig()[0]
    
    # Setup display
    i2c = I2C(0, sda=Pin(5), scl=Pin(6))
    display = SSD1306_I2C(70, 40, i2c)
    display_msg(display, f"CONFIG-MODE\n{ip[:6]}\n{ip[6:]}")
    
    # Create server
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(1)
    
    # Load or create default config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.loads(f.read())
    except:
        config = {
            "d_threshold": 1000,
            "back_speed": 6000,
            "forw_speed": 1000
        }
        display_msg(display, "CONFIG-MODE\njson error")
    
    # Main server loop
    while True:
        try:
            client, _ = s.accept()
            req = client.recv(1024)
            reboot_needed = False
            
            # Handle POST request
            if req.startswith(b'POST'):
                try:
                    # Extract form data
                    data = req.split(b'\r\n\r\n')[1].decode()
                    for item in data.split('&'):
                        if '=' in item:
                            key, value = item.split('=', 1)
                            if key in config:
                                config[key] = int(value)
                    
                    # Save config
                    with open(CONFIG_FILE, 'w') as f:
                        f.write(json.dumps(config))
                    
                    message = "Settings saved! Rebooting..."
                    reboot_needed = True
                except:
                    message = "Error saving settings"
            else:
                message = ""
            
            # Get HTML template
            try:
                with open(INDEX_FILE, 'r') as f:
                    html = f.read()
                # Replace placeholders
                for key in config:
                    html = html.replace(f'{{{{{key}}}}}', str(config[key]))
                
                # Add message if needed
                if message:
                    js = f"""<script>
                    window.onload=function(){{
                        var m=document.getElementById('message');
                        if(m){{
                            m.textContent="{message}";
                            m.style.display='block';
                            setTimeout(function(){{m.style.display='none';}},3000);
                        }}
                    }};
                    </script>"""
                    html = html.replace('</body>', f'{js}</body>')
            except:
                html = f"""<html><body>
                <h1>Error: Cannot load template</h1>
                <p>Settings: {json.dumps(config)}</p>
                </body></html>"""
            
            # Send response
            client.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
            client.send(html)
            client.close()
            
            # Reboot if needed
            if reboot_needed:
                display_msg(display, "Settings saved\nRebooting...")
                time.sleep(2)  # Give time for the page to load
                reset()  # Reboot the board
                
        except Exception as e:
            try:
                client.close()
            except:
                pass

if __name__ == "__main__":
    main()