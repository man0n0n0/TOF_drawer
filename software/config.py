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
        
        # Read HTML template from file
        try:
            with open('index.html', 'r') as file:
                html_template = file.read()
                
            # Replace placeholders with actual values
            html = html_template.replace('{{d_threshold}}', str(config['d_threshold']))
            html = html.replace('{{back_speed}}', str(config['back_speed']))
            html = html.replace('{{forw_speed}}', str(config['forw_speed']))
            
            # Add message script if there's a message
            if message:
                message_script = f"""
                <script>
                    window.onload = function() {{
                        var messageElement = document.getElementById('message');
                        if (messageElement) {{
                            messageElement.textContent = "{message}";
                            messageElement.style.display = 'block';
                            setTimeout(function() {{
                                messageElement.style.display = 'none';
                            }}, 3000);
                        }}
                    }};
                </script>
                """
                # Insert the script before the closing </body> tag
                html = html.replace('</body>', f'{message_script}</body>')
                
        except Exception as e:
            # Fallback if index.html is not found
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
            </head>
            <body>
                <h1>Error: Cannot load template</h1>
                <p>The index.html file could not be loaded: {str(e)}</p>
                <p>Current settings:</p>
                <ul>
                    <li>Detection threshold: {config['d_threshold']}</li>
                    <li>Retraction speed: {config['back_speed']}</li>
                    <li>Exit speed: {config['forw_speed']}</li>
                </ul>
            </body>
            </html>
            """
        
        # Send HTTP response
        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{html}"
        client_socket.send(response.encode('utf-8'))
        
    except Exception as e:
        # Send error response
        error_response = f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nError: {str(e)}"
        client_socket.send(error_response.encode('utf-8'))
    finally:
        # Close connection
        client_socket.close()

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