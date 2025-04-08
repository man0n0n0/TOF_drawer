import json

# JSON file path
JSON_FILE = 'data.json'

# Function to load settings from JSON file
def load_settings():
    try:
        with open(JSON_FILE, 'r') as f:
            return json.loads(f.read())
    except:
        # Default settings if file doesn't exist or is invalid
        default_settings = {
            "d_threshold": 1000,
            "back_speed": 6000,
            "forw_speed": 1000
        }
        save_settings(default_settings)
        return default_settings

# Function to save settings to JSON file
def save_settings(settings):
    with open(JSON_FILE, 'w') as f:
        f.write(json.dumps(settings))

# Function to get a specific setting
def get_setting(key, default=None):
    settings = load_settings()
    return settings.get(key, default)

# Function to update a specific setting
def update_setting(key, value):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)