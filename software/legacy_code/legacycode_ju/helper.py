import ujson
import usocket as socket
import network
import usocket as socket

import var as v


#get the data from json file
def get_json_save(jsonFile):
    try:
        with open(jsonFile, 'r') as file:
        # Read the content of the file
            json_content = file.read()
    # Parse the JSON data
    except :
        print('Error Openning Json file')
    try:
        data = ujson.loads(json_content)
        return data
    except ValueError as e:
        print("Error parsing JSON:", e)
    

#Save data to json file
def update_save(newData):
    with open(v.json_file, 'r') as file:
        json_content = file.read()
    old_data = ujson.loads(json_content)
    #print("old data:", old_data)
    #print("new data :", newData)
    old_data.update(newData)
    with open(v.json_file, 'w') as file:
        ujson.dump(old_data,file)
    print("data saved to file yo !")
    
    
    
def parse_post_data(request):
    try:
        # Find the start of the POST data
        start = request.find(b'\r\n\r\n') + 4
        # Extract the POST data
        post_data = request[start:].decode('utf-8')
        # Split the POST parameters
        params = post_data.split('&')
        # Create a dictionary to store the parameters
        json_data = {}
        for param in params:
            key, value = param.split('=')
            # Decode URL-encoded values
            value = value.replace('+', ' ').replace('%21', '!').replace('%2C', ',')
            json_data[key] = value
        return json_data
    except Exception as e:
        print("Error parsing POST data:", e)
        return None

# Function to handle incoming HTTP requests

def handle_request(client):
    try:
        # Receive the request data
        request_data = client.recv(1024)
        
        # Check if the request is not empty
        if not request_data:
            print("Empty request")
            client.close()
            return None

        # Extract the requested path from the request
        request_lines = request_data.split(b'\r\n')
        first_line = request_lines[0].split(b' ')
        
        # Check if the request has at least three parts
        if len(first_line) < 3:
            print("Invalid request format")
            client.close()
            return None

        method, path, _ = first_line

        # Print the requested path for debugging
        #print("Requested path:", path.decode('utf-8'))

        if method == b'GET':
            savedata = get_json_save(v.json_file)
            html_content = ""
            try:
                with open("form.html",'r') as file:
                    html_content = file.read()
            except OSError as e:
                print("Error opening file:", e)
            print('This is a GET method')
            for key, value in savedata.items():
                #print(f"key: {key} / value: {value} ")
                placeholder = '{{' + key + '}}'
                html_content = html_content.replace(placeholder, str(value))
#                 
            client.send(html_content.encode('utf-8'))
            return None
            
        elif method == b'POST':
            # Handle POST requests
            print("Received POST request")
            # Parse the POST data to JSON
            post_data_json = parse_post_data(request_data)
            
            if post_data_json:
                #print("Parsed JSON data from POST:", post_data_json)
                update_save(post_data_json)
                
                try:
                    with open("form.html",'r') as file:
                        html_content = file.read()
                except OSError as e:
                    print("Error opening file:", e)
                    
                savedata = get_json_save(v.json_file)
                for key, value in savedata.items():
                    #print(f"key: {key} / value: {value} ")
                    placeholder = '{{' + key + '}}'
                    html_content = html_content.replace(placeholder, str(value))
                response = html_content.replace(placeholder, str(value))
                client.send(response.encode('utf-8'))
            method_type = "post"
            return method_type
                
        else:
            print("Unsupported request method:", method)
            response = "HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nUnsupported request method"
            client.send(response.encode('utf-8'))
            return none
            
    except OSError as e:
        print("Error handling request:", e)

    # Close the client connection
    client.close()


def motor_data_retriever(jsonFile):
    savedata = get_json_save(jsonFile)
    for key, value in savedata.items():
        if(key=="maxspeed"):
            max_speed_percent = int(value)
        if(key=="acctime"):
            acceleration_time_secondes = int(value)
        if(key=="runtime"):
            run_time_secondes = int(value)
        if(key=="pausetime"):
            pause_time_secondes = int(value)
    
    max_max_speed_duty_cycle = 1023 #valeur PWM entre 0 et 1023
    min_max_speed_duty_cycle = 0 #valeur PWM entre 0 et 1023
    max_speed_duty_cycle = round(((max_max_speed_duty_cycle-min_max_speed_duty_cycle)/100)*max_speed_percent)+min_max_speed_duty_cycle
    print(max_speed_duty_cycle)
    return max_speed_duty_cycle, acceleration_time_secondes, run_time_secondes, pause_time_secondes



def thread_server_function():
    global arriving_post
    
    #access point credentials
    ap_ssid = "broom-1"
    ap_password = "password789"

    #create wifi access point
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ap_ssid, password=ap_password, authmode=3) #add authmode=3 to make sure it asks password before connecting

    #print wifi access point IP address
    print("Access point IP address:", ap.ifconfig()[0]) #after connecting to wiif with smartphone, type IP address into search bar to access the page

    #create a webserver to host an html page
    server = socket.socket()
    server.bind(('0.0.0.0', 80))
    server.listen(1) #1 pour 1 connection maximum
    print("Server listening on port 80")

    #open html page (form)
    html_content = ""
    try:
        with open("form.html",'r') as file:
            html_content = file.read()
            print("Hosting HTML form")
    except OSError as e:
        print("Error opening file:", e)


    while True:
        try:
            client, addr = server.accept()
            method_type = handle_request(client)
            
            
            
            if(method_type=="post"):
                v.arriving_post = 1
                
                                        
        except KeyboardInterrupt:
            break
               
    server.close()