"""
Configuration mode for drawer control system
Creates a web server to allow parameter adjustment
"""
import network
import json
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import socket
import time

# Config file path
CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from JSON file or create default"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.loads(f.read())
    except:
        # Default settings
        default_config = {
            "d_threshold": 1000,
            "back_speed": 8100,
            "forw_speed": 1100
        }
        # Save defaults
        with open(CONFIG_FILE, 'w') as f:
            f.write(json.dumps(default_config))
        return default_config

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        f.write(json.dumps(config))

def setup_network():
    """Setup WiFi access point"""
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid='drawer-config', password='admin123', authmode=3)
    return ap

def parse_form_data(request_data):
    """Parse form data from HTTP POST request"""
    form_data = {}
    # Find the start of POST data (after the headers)
    try:
        data_start = request_data.find(b'\r\n\r\n') + 4
        post_data = request_data[data_start:].decode('utf-8')
        
        # Parse the form parameters
        params = post_data.split('&')
        for param in params:
            if '=' in param:
                key, value = param.split('=', 1)
                form_data[key] = value
        
        return form_data
    except:
        return {}

def handle_request(client_socket):
    """Handle HTTP request"""
    try:
        # Receive the request
        request = client_socket.recv(1024)
        
        # Get request method
        method = request.split(b' ')[0]
        
        # Handle POST request (form submission)
        if method == b'POST':
            # Parse form data
            form_data = parse_form_data(request)
            
            # Update configuration
            config = load_config()
            try:
                if 'd_threshold' in form_data:
                    config['d_threshold'] = int(form_data['d_threshold'])
                if 'back_speed' in form_data:
                    config['back_speed'] = int(form_data['back_speed'])
                if 'forw_speed' in form_data:
                    config['forw_speed'] = int(form_data['forw_speed'])
                
                # Save updated config
                save_config(config)
                message = "Settings saved successfully!"
            except:
                message = "Error saving settings"
        else:
            message = ""
        
        # Load current config for display
        config = load_config()
        
        # Generate HTML response
        html = generate_html(config, message)
        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{html}"
        
        # Send response
        client_socket.send(response.encode('utf-8'))
    except Exception as e:
        # Send error response
        error_response = f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nError: {str(e)}"
        client_socket.send(error_response.encode('utf-8'))
    finally:
        # Close connection
        client_socket.close()

def generate_html(config, message=""):
    """Generate HTML for the configuration page"""
    # Message display style
    message_style = "display: block;" if message else "display: none;"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Drawer Configuration</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f4f4f4; }}
            h1 {{ text-align: center; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .form-group {{ margin-bottom: 15px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            .slider-container {{ display: flex; align-items: center; }}
            input[type="range"] {{ flex: 1; margin-right: 10px; }}
            .value {{ min-width: 50px; text-align: right; font-weight: bold; }}
            .buttons {{ margin-top: 20px; text-align: center; }}
            button {{ background: #000; color: white; border: none; padding: 10px 20px; border-radius: 3px; cursor: pointer; margin: 0 5px; }}
            button:hover {{ background: #333; }}
            .message {{ background: #d4edda; color: #155724; padding: 10px; border-radius: 3px; margin-bottom: 15px; {message_style} }}
            .description {{ font-size: 12px; color: #666; margin-top: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Drawer Configuration</h1>
            
            <div class="message" id="message">{message}</div>
            
            <form method="post" action="/">
                <div class="form-group">
                    <label>Detection Threshold (mm):</label>
                    <div class="slider-container">
                        <input type="range" name="d_threshold" min="200" max="2000" value="{config['d_threshold']}" oninput="updateValue('d_threshold', this.value)">
                        <span class="value" id="d_threshold_value">{config['d_threshold']}</span>
                    </div>
                    <div class="description">Distance in mm. When an object is detected closer than this, the drawer will close.</div>
                </div>
                
                <div class="form-group">
                    <label>Retraction Speed:</label>
                    <div class="slider-container">
                        <input type="range" name="back_speed" min="3000" max="12000" value="{config['back_speed']}" oninput="updateValue('back_speed', this.value)">
                        <span class="value" id="back_speed_value">{config['back_speed']}</span>
                    </div>
                    <div class="description">Speed at which drawer retracts (steps/sec). Higher values = faster.</div>
                </div>
                
                <div class="form-group">
                    <label>Exit Speed:</label>
                    <div class="slider-container">
                        <input type="range" name="forw_speed" min="500" max="3000" value="{config['forw_speed']}" oninput="updateValue('forw_speed', this.value)">
                        <span class="value" id="forw_speed_value">{config['forw_speed']}</span>
                    </div>
                    <div class="description">Speed at which drawer extends (steps/sec). Lower values = smoother.</div>
                </div>
                
                <div class="buttons">
                    <button type="submit">Save Settings</button>
                    <button type="button" onclick="resetForm()">Reset</button>
                </div>
            </form>
        </div>
        
        <script>
            function updateValue(id, value) {{
                document.getElementById(id + '_value').textContent = value;
            }}
            
            function resetForm() {{
                document.querySelector('form').reset();
                // Update displayed values
                document.querySelectorAll('input[type="range"]').forEach(function(slider) {{
                    updateValue(slider.name, slider.value);
                }});
            }}
            
            // Hide message after 3 seconds
            setTimeout(function() {{
                document.getElementById('message').style.display = 'none';
            }}, 3000);
        </script>
    </body>
    </html>
    """
    
    return html

def run_server():
    """Run the configuration web server"""
    # Setup WiFi access point
    ap = setup_network()
    ip_address = ap.ifconfig()[0]
    
    # Setup display
    i2c = I2C(0, sda=Pin(5), scl=Pin(6))
    display = SSD1306_I2C(70, 40, i2c)
    
    # Show connection information
    display.fill(0)
    display.text("SETUP MODE", 0, 0, 1)
    display.text("Connect to:", 0, 10, 1)
    display.text("drawer-config", 0, 20, 1)
    display.text(f"IP: {ip_address}", 0, 30, 1)
    display.show()
    
    # Create socket server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 80))
    server_socket.listen(5)
    
    print(f"Server started at http://{ip_address}")
    
    try:
        while True:
            # Accept connection
            client, addr = server_socket.accept()
            print(f"Connection from {addr}")
            
            # Handle request in separate function
            handle_request(client)
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()

# Run the configuration server
if __name__ == "__main__":
    run_server()