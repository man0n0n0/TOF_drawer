"""
@claude generated

LD2410 mmWave Radar Sensor Library for MicroPython
This library interfaces with the LD2410 mmWave presence detection sensor,
providing functions for configuration, data reading, and parameter adjustment.

The LD2410 is a 24GHz mmWave radar module that can detect human presence
and provide distance measurements.

Example usage:
    from machine import UART
    import ld2410
    
    # Initialize with UART 1, default pins
    radar = ld2410.LD2410(1)
    
    # Check for presence detection
    if radar.is_presence_detected():
        distance = radar.get_distance()
        print(f"Person detected at {distance} cm")
        
    # Configure sensor parameters
    radar.set_detection_range(moving=120, stationary=100)  # in cm
    
    # Enable engineering mode (for configuration)
    radar.enter_config_mode()
    
    # Set sensitivity for each distance gate
    radar.set_sensitivity(gate=3, moving=25, stationary=30)
    
    # Save configuration
    radar.save_config()
    
    # Exit engineering mode
    radar.exit_config_mode()
"""

from machine import UART
import time
import struct

# Command frame headers and endings
CMD_HEADER = b'\xFD\xFC\xFB\xFA'
CMD_ENDING = b'\x04\x03\x02\x01'
REPORT_HEADER = b'\xF4\xF3\xF2\xF1'
REPORT_ENDING = b'\xF8\xF7\xF6\xF5'

# Command types
CMD_ENABLE_CONFIG = 0x00FF
CMD_DISABLE_CONFIG = 0x00FE
CMD_SET_MAX_DISTANCE = 0x0060
CMD_SET_SENSITIVITY = 0x0061
CMD_RESTART_MODULE = 0x00A0
CMD_FACTORY_RESET = 0x00A1
CMD_SAVE_SETTINGS = 0x00A2
CMD_READ_FIRMWARE = 0x00A3

class LD2410:
    """
    Driver for LD2410 mmWave Radar Sensor
    """
    
    def __init__(self, uart_num=1, tx_pin=None, rx_pin=None, baudrate=256000, timeout=1000):
        """
        Initialize the LD2410 sensor
        
        Args:
            uart_num: UART bus number (0, 1, etc)
            tx_pin: Optional TX pin if not using default
            rx_pin: Optional RX pin if not using default
            baudrate: Communication baudrate (default 256000)
            timeout: UART timeout in milliseconds
        """
        # Initialize UART
        if tx_pin is not None and rx_pin is not None:
            self.uart = UART(uart_num, baudrate=baudrate, tx=tx_pin, rx=rx_pin, timeout=timeout)
        else:
            self.uart = UART(uart_num, baudrate=baudrate, timeout=timeout)
            
        # Set buffer for holding data
        self._buffer = bytearray(64)
        
        # Initialize state variables
        self._detection_state = 0  # 0: No detection, 1: Moving, 2: Stationary, 3: Both
        self._moving_distance = 0
        self._stationary_distance = 0
        self._moving_energy = 0
        self._stationary_energy = 0
        self._config_mode = False
        
        # Clear buffer
        self._flush_uart()
        
    def _flush_uart(self):
        """Clear all data in the UART buffer"""
        while self.uart.any():
            self.uart.read()
    
    def _send_command(self, cmd_type, data=None):
        """
        Send a command to the LD2410 sensor
        
        Args:
            cmd_type: Command type code
            data: Optional data bytes
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        # Prepare data length (command + data)
        data_len = 2  # Command type (2 bytes)
        
        if data:
            data_len += len(data)
        
        # Create command frame
        cmd = bytearray()
        cmd.extend(CMD_HEADER)  # Header
        cmd.extend(struct.pack("<H", data_len))  # Data length
        cmd.extend(struct.pack("<H", cmd_type))  # Command
        
        if data:
            cmd.extend(data)  # Additional data if present
            
        cmd.extend(CMD_ENDING)  # Ending
        
        # Send command
        self.uart.write(cmd)
        
        # Small delay to ensure command is processed
        time.sleep_ms(50)
        
        return True
    
    def _read_response(self, timeout_ms=1000):
        """
        Read and parse response from the sensor
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Tuple of (status, data) or (False, None) on error
        """
        start_time = time.ticks_ms()
        
        # Wait for data with timeout
        while not self.uart.any() and time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            time.sleep_ms(10)
        
        if not self.uart.any():
            return False, None  # Timeout
            
        # Read available data
        data = self.uart.read()
        
        # Check if data contains a valid response
        header_pos = data.find(REPORT_HEADER)
        if header_pos == -1:
            return False, None  # No valid header found
            
        # Find ending
        ending_pos = data.find(REPORT_ENDING, header_pos)
        if ending_pos == -1:
            return False, None  # No valid ending found
            
        # Extract response data
        response_data = data[header_pos+4:ending_pos]
        
        return True, response_data
    
    def _parse_data_frame(self, data):
        """
        Parse a standard data frame from the sensor
        
        Args:
            data: Raw data bytes
            
        Returns:
            True if parsed successfully, False otherwise
        """
        if len(data) < 10:  # Minimum length for basic data
            return False
            
        try:
            # Get target state (bit 0: moving, bit 1: stationary)
            self._detection_state = data[4]
            
            # Get distance values
            if self._detection_state & 0x01:  # Moving target
                self._moving_distance = (data[6] << 8) | data[5]
                self._moving_energy = data[7]
                
            if self._detection_state & 0x02:  # Stationary target
                self._stationary_distance = (data[9] << 8) | data[8]
                self._stationary_energy = data[10] if len(data) > 10 else 0
                
            return True
        except:
            return False
    
    def read_data(self):
        """
        Read and parse the latest data from the sensor
        
        Returns:
            True if new data was successfully read and parsed, False otherwise
        """
        if not self.uart.any():
            return False
            
        # Read data bytes
        data = self.uart.read()
        
        # Look for a data frame
        header_pos = data.find(REPORT_HEADER)
        if header_pos == -1:
            return False
        
        # Find the end of the frame
        ending_pos = data.find(REPORT_ENDING, header_pos)
        if ending_pos == -1:
            return False
            
        # Extract and parse the data frame
        frame_data = data[header_pos+4:ending_pos]
        return self._parse_data_frame(frame_data)
    
    def is_presence_detected(self):
        """
        Check if presence is currently detected
        
        Returns:
            True if presence is detected, False otherwise
        """
        self.read_data()
        return self._detection_state > 0
    
    def is_moving_detected(self):
        """
        Check if moving target is detected
        
        Returns:
            True if moving target is detected, False otherwise
        """
        self.read_data()
        return (self._detection_state & 0x01) > 0
    
    def is_stationary_detected(self):
        """
        Check if stationary target is detected
        
        Returns:
            True if stationary target is detected, False otherwise
        """
        self.read_data()
        return (self._detection_state & 0x02) > 0
    
    def get_moving_distance(self):
        """
        Get the distance of moving target in cm
        
        Returns:
            Distance in cm, or 0 if no moving target
        """
        self.read_data()
        return self._moving_distance
    
    def get_stationary_distance(self):
        """
        Get the distance of stationary target in cm
        
        Returns:
            Distance in cm, or 0 if no stationary target
        """
        self.read_data()
        return self._stationary_distance
    
    def get_distance(self):
        """
        Get the minimum distance of any detected target in cm
        
        Returns:
            Minimum distance in cm, or 0 if no target
        """
        self.read_data()
        
        moving_dist = self._moving_distance if (self._detection_state & 0x01) else 0
        stationary_dist = self._stationary_distance if (self._detection_state & 0x02) else 0
        
        if moving_dist > 0 and stationary_dist > 0:
            return min(moving_dist, stationary_dist)
        elif moving_dist > 0:
            return moving_dist
        else:
            return stationary_dist
    
    def get_moving_energy(self):
        """
        Get the energy value of moving target detection
        
        Returns:
            Energy value (0-100)
        """
        self.read_data()
        return self._moving_energy
    
    def get_stationary_energy(self):
        """
        Get the energy value of stationary target detection
        
        Returns:
            Energy value (0-100)
        """
        self.read_data()
        return self._stationary_energy
    
    # Configuration commands
    def enter_config_mode(self):
        """
        Enter configuration mode (engineering mode)
        
        Returns:
            True if successful, False otherwise
        """
        result = self._send_command(CMD_ENABLE_CONFIG)
        if result:
            self._config_mode = True
        return result
    
    def exit_config_mode(self):
        """
        Exit configuration mode (engineering mode)
        
        Returns:
            True if successful, False otherwise
        """
        result = self._send_command(CMD_DISABLE_CONFIG)
        if result:
            self._config_mode = False
        return result
    
    def set_detection_range(self, moving=0, stationary=0):
        """
        Set maximum detection distance for moving and stationary targets
        
        Args:
            moving: Max distance for moving targets (0-600 cm)
            stationary: Max distance for stationary targets (0-600 cm)
            
        Returns:
            True if successful, False otherwise
            
        Note:
            Requires configuration mode to be active
        """
        if not self._config_mode:
            return False
            
        # Validate ranges
        moving = max(0, min(600, moving))
        stationary = max(0, min(600, stationary))
        
        # Prepare data
        data = bytearray()
        data.extend(struct.pack("<H", moving))
        data.extend(struct.pack("<H", stationary))
        
        return self._send_command(CMD_SET_MAX_DISTANCE, data)
    
    def set_sensitivity(self, gate, moving=0, stationary=0):
        """
        Set sensitivity for a specific distance gate
        
        Args:
            gate: Distance gate number (0-8)
            moving: Sensitivity for moving detection (0-100)
            stationary: Sensitivity for stationary detection (0-100)
            
        Returns:
            True if successful, False otherwise
            
        Note:
            Requires configuration mode to be active
        """
        if not self._config_mode:
            return False
            
        # Validate parameters
        gate = max(0, min(8, gate))
        moving = max(0, min(100, moving))
        stationary = max(0, min(100, stationary))
        
        # Prepare data
        data = bytearray()
        data.append(gate)
        data.append(moving)
        data.append(stationary)
        
        return self._send_command(CMD_SET_SENSITIVITY, data)
    
    def restart_module(self):
        """
        Restart the LD2410 module
        
        Returns:
            True if successful, False otherwise
        """
        return self._send_command(CMD_RESTART_MODULE)
    
    def factory_reset(self):
        """
        Reset the module to factory settings
        
        Returns:
            True if successful, False otherwise
            
        Note:
            Requires configuration mode to be active
        """
        if not self._config_mode:
            return False
            
        return self._send_command(CMD_FACTORY_RESET)
    
    def save_config(self):
        """
        Save current configuration to module flash
        
        Returns:
            True if successful, False otherwise
            
        Note:
            Requires configuration mode to be active
        """
        if not self._config_mode:
            return False
            
        return self._send_command(CMD_SAVE_SETTINGS)
    
    def read_firmware_version(self):
        """
        Read the firmware version of the module
        
        Returns:
            Tuple of (major, minor) version numbers or None if failed
            
        Note:
            Requires configuration mode to be active
        """
        if not self._config_mode:
            return None
            
        if not self._send_command(CMD_READ_FIRMWARE):
            return None
            
        # Read response
        status, data = self._read_response()
        if not status or len(data) < 4:
            return None
            
        # Extract version
        try:
            major = data[2]
            minor = data[3]
            return (major, minor)
        except:
            return None