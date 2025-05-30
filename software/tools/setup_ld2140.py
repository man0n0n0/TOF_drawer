import machine
import time

##############################################
### SENSOR VARIABLES ###
##############################################

DISTANCE_METERS = 4
TIMEOUT_SECONDS = 0  # Set to 0 to disable timeout (no delay before declaring area empty)

# Sensitivity settings (0-100): Lower = more sensitive, Higher = less sensitive
MOVING_SENSITIVITY = 20  # Sensitivity for detecting moving targets
STATIONARY_SENSITIVITY = 100  # Sensitivity for detecting stationary targets

##############################################
### CODE (NO ACTION NEEDED) ###
##############################################

class LD2410:
    def __init__(self, uart_id=2, tx_pin=17, rx_pin=16, baudrate=256000):
        """
        Initialize LD2410 sensor communication using official protocol
        
        Args:
            uart_id: UART peripheral ID (0 or 1)
            tx_pin: TX pin number
            rx_pin: RX pin number
            baudrate: Communication speed (default 256000)
        """
        self.uart = machine.UART(uart_id, baudrate=baudrate, tx=tx_pin, rx=rx_pin)
        self.uart.init(baudrate=baudrate, bits=8, parity=None, stop=1)
    
    def _low_byte(self, value):
        """Get low byte of 16-bit value"""
        return value & 0xFF
    
    def _high_byte(self, value):
        """Get high byte of 16-bit value"""
        return (value >> 8) & 0xFF
    
    def _send_command(self, cmd_bytes, value_bytes=None):
        """
        Send command using official LD2410C protocol format
        
        Args:
            cmd_bytes: 2-byte command as list [cmd1, cmd2]
            value_bytes: Optional value bytes as list
        """
        # Frame start bytes
        frame = bytes([0xFD, 0xFC, 0xFB, 0xFA])
        
        # Calculate length (command + value bytes)
        length = 2  # command bytes
        if value_bytes:
            length += len(value_bytes)
        
        # Add length bytes (little endian)
        frame += bytes([self._low_byte(length), self._high_byte(length)])
        
        # Add command bytes
        frame += bytes(cmd_bytes)
        
        # Add value bytes if present
        if value_bytes:
            frame += bytes(value_bytes)
        
        # Frame end bytes
        frame += bytes([0x04, 0x03, 0x02, 0x01])
        
        # Send frame
        self.uart.write(frame)
        time.sleep_ms(50)
    
    def _read_response(self, timeout_ms=1000):
        """Read response from sensor"""
        start_time = time.ticks_ms()
        response = b''
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            if self.uart.any():
                response += self.uart.read()
            time.sleep_ms(10)
        
        return response
    
    def _check_ack(self, response):
        """Check ACK response using official protocol logic"""
        if len(response) < 10:
            return False
        
        # Look for frame start bytes: 0xFD, 0xFC, 0xFB, 0xFA
        for i in range(len(response) - 9):
            if (response[i] == 0xFD and response[i+1] == 0xFC and 
                response[i+2] == 0xFB and response[i+3] == 0xFA):
                
                # Check if this is an ACK frame (command | 0x0100)
                if i + 7 < len(response) and response[i + 7] == 0x01:
                    # Check status bytes 8-9 (should be 0x00, 0x00 for success)
                    if (i + 9 < len(response) and 
                        response[i + 8] == 0x00 and response[i + 9] == 0x00):
                        return True
                break
        
        return False
    
    def _set_config_mode(self, enable):
        """Enable or disable configuration mode"""
        if enable:
            print("Enabling configuration mode...")
            self._send_command([0xFF, 0x00], [0x01, 0x00])
        else:
            print("Disabling configuration mode...")
            self._send_command([0xFE, 0x00])
        
        response = self._read_response()
        return self._check_ack(response)

    def _set_sensitivity(self, moving_sensitivity, stationary_sensitivity):
        """
        Set sensitivity for all distance gates using command 0x0064
        
        Args:
            moving_sensitivity: Sensitivity for moving targets (0-100)
            stationary_sensitivity: Sensitivity for stationary targets (0-100)
        """
        print(f"Setting sensitivity: Moving={moving_sensitivity}, Stationary={stationary_sensitivity}")
        
        # Command 0x0064 with 18-byte value array for setting all gates to same sensitivity
        # Using 0xFFFF as distance gate value sets all gates to the same sensitivity
        value_bytes = [
            0x00, 0x00,  # Distance gate word (parameter name)
            0xFF, 0xFF, 0x00, 0x00,  # Distance gate value (0xFFFF = all gates)
            0x01, 0x00,  # Movement sensitivity word
            moving_sensitivity, 0x00, 0x00, 0x00,  # Movement sensitivity value
            0x02, 0x00,  # Static sensitivity word
            stationary_sensitivity, 0x00, 0x00, 0x00  # Static sensitivity value
        ]
        
        self._send_command([0x64, 0x00], value_bytes)
        response = self._read_response()
        return self._check_ack(response)

    def configure(self, distance_meters, timeout_seconds, moving_sensitivity=50, stationary_sensitivity=50):
        """
        Configure distance, timeout and sensitivity using official LD2410C protocol
        
        Args:
            distance_meters: Detection distance (0.75-6.0 meters)
            timeout_seconds: Unoccupied duration in seconds (0-65535)
                           0 = immediate response (no delay)
                           >0 = seconds to wait before declaring area empty
            moving_sensitivity: Sensitivity for moving targets (0-100)
                              Lower values = more sensitive
            stationary_sensitivity: Sensitivity for stationary targets (0-100)
                                  Lower values = more sensitive
        """
        # Validate inputs
        if not (0.75 <= distance_meters <= 6.0):
            raise ValueError("Distance must be between 0.75 and 6.0 meters")
        if not (0 <= timeout_seconds <= 65535):
            raise ValueError("Timeout must be between 0 and 65535 seconds")
        if not (0 <= moving_sensitivity <= 100):
            raise ValueError("Moving sensitivity must be between 0 and 100")
        if not (0 <= stationary_sensitivity <= 100):
            raise ValueError("Stationary sensitivity must be between 0 and 100")
        
        if timeout_seconds == 0:
            print(f"Configuring LD2410: {distance_meters}m range, TIMEOUT DISABLED")
        else:
            print(f"Configuring LD2410: {distance_meters}m range, {timeout_seconds}s timeout")
        
        print(f"Sensitivity settings: Moving={moving_sensitivity}, Stationary={stationary_sensitivity}")
        
        # Convert distance to gates (each gate = 0.75m)
        max_distance_gate = int(distance_meters / 0.75)
        
        # Enable configuration mode
        if not self._set_config_mode(True):
            print("Failed to enable config mode")
            return False
        
        time.sleep_ms(100)
        
        # Step 1: Set distances and timeout using command 0x0060
        value_bytes = [
            0x00, 0x00,  # Parameter word for maximum movement distance door
            self._low_byte(max_distance_gate), self._high_byte(max_distance_gate), 0x00, 0x00,  # Moving distance gate
            0x01, 0x00,  # Parameter word for maximum resting distance door  
            self._low_byte(max_distance_gate), self._high_byte(max_distance_gate), 0x00, 0x00,  # Still distance gate
            0x02, 0x00,  # Parameter word for unoccupied duration
            self._low_byte(timeout_seconds), self._high_byte(timeout_seconds), 0x00, 0x00       # Duration in seconds
        ]
        
        self._send_command([0x60, 0x00], value_bytes)
        response = self._read_response()
        
        if not self._check_ack(response):
            print("Failed to set distance and timeout parameters")
            self._set_config_mode(False)
            return False
        
        time.sleep_ms(100)
        
        # Step 2: Set sensitivity using command 0x0064
        if not self._set_sensitivity(moving_sensitivity, stationary_sensitivity):
            print("Failed to set sensitivity parameters")
            self._set_config_mode(False)
            return False
        
        time.sleep_ms(100)
        
        # Disable configuration mode
        if not self._set_config_mode(False):
            print("Failed to disable config mode")
            return False
        
        print("✓ Configuration successful!")
        print(f"✓ GPIO OUT will trigger based on sensitivity settings")
        return True

print("Connecting to sensor...")

sensor = LD2410()

time.sleep_ms(100)

sensor.configure(DISTANCE_METERS, TIMEOUT_SECONDS, MOVING_SENSITIVITY, STATIONARY_SENSITIVITY)