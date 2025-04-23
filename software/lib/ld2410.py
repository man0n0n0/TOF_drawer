"""
LD2410 MicroPython Library

A library for interfacing with LD2410 24GHz mmWave radar sensors using MicroPython.
This driver communicates with the sensor via UART and aims to replicate the functionality
of the C++ LD2410 library.

Basic usage:
    from ld2410 import LD2410
    from machine import UART, Pin
    
    # Initialize the sensor with a UART instance
    uart = UART(1, 256000)
    uart.init(tx=Pin(16), rx=Pin(17))
    radar = LD2410()
    radar.begin(uart)
    
    # Read sensor data
    radar.read()
    
    # Get data
    if radar.presence_detected():
        print("Target detected!")
        
        if radar.moving_target_detected():
            print(f"Moving target: {radar.moving_target_distance()}cm, energy: {radar.moving_target_energy()}")
            
        if radar.stationary_target_detected():
            print(f"Stationary target: {radar.stationary_target_distance()}cm, energy: {radar.stationary_target_energy()}")
"""

from machine import UART, Pin
import time

# Constants
LD2410_MAX_FRAME_LENGTH = 40
LD2410_BUFFER_SIZE = 128

class LD2410:
    """Driver for LD2410 24GHz mmWave radar sensor."""
    
    def __init__(self, io_timeout_ms=1000):
        """
        Initialize the LD2410 radar sensor.
        
        Args:
            io_timeout_ms: Read timeout in milliseconds (default: 1000)
        """
        # UART connection
        self.radar_uart = None
        self.debug_uart = None
        
        # Timeouts
        self.radar_uart_timeout = 2000  # ms
        self.radar_uart_command_timeout_ = 1000  # ms
        self.io_timeout_ms = io_timeout_ms
        
        # Buffer and frame handling
        self.radar_data_frame_ = bytearray(LD2410_MAX_FRAME_LENGTH)
        self.radar_data_frame_position_ = 0
        self.frame_started_ = False
        self.ack_frame_ = False
        
        # Status and data
        self.radar_uart_last_packet_ = 0
        self.radar_uart_last_command_ = 0
        
        self.target_type_ = 0
        self.moving_target_distance_ = 0
        self.moving_target_energy_ = 0
        self.stationary_target_distance_ = 0
        self.stationary_target_energy_ = 0
        
        # Command response data
        self.latest_ack_ = 0
        self.latest_command_success_ = False
        
        # Circular buffer for data reception
        self.circular_buffer = bytearray(LD2410_BUFFER_SIZE)
        self.buffer_head = 0
        self.buffer_tail = 0
        
        # Firmware version
        self.firmware_major_version = 0
        self.firmware_minor_version = 0
        self.firmware_bugfix_version = 0
        
        # Configuration values
        self.max_gate = 0
        self.max_moving_gate = 0
        self.max_stationary_gate = 0
        self.motion_sensitivity = [0] * 9
        self.stationary_sensitivity = [0] * 9
        self.sensor_idle_time = 0
        
        # Last valid frame length for reference
        self.last_valid_frame_length = 0
    
    def begin(self, radar_uart, wait_for_radar=True):
        """
        Begin communication with the radar module.
        
        Args:
            radar_uart: UART stream connected to the radar
            wait_for_radar: If True, wait for radar to respond (default: True)
            
        Returns:
            bool: True if connected successfully, False otherwise
        """
        self.radar_uart = radar_uart
        
        if self.debug_uart:
            self.debug_uart.println("ld2410 started")
        
        if not wait_for_radar:
            return True
        
        if self.debug_uart:
            self.debug_uart.print("\nLD2410 firmware: ")
        
        start_time = time.ticks_ms()
        firmware_received = False
        
        while time.ticks_diff(time.ticks_ms(), start_time) < 1000:
            if self.requestFirmwareVersion():
                firmware_received = True
                break
        
        if firmware_received:
            if self.debug_uart:
                self.debug_uart.print(f" v{self.firmware_major_version}.")
                self.debug_uart.print(f"{self.firmware_minor_version}.")
                self.debug_uart.print(f"{self.firmware_bugfix_version}")
            return True
        
        if self.debug_uart:
            self.debug_uart.print("no response")
        return False
    
    def setGateSensitivityThreshold(self, gate, moving, stationary):
        """
        Set sensitivity thresholds for a specific gate.
        
        Args:
            gate: Gate number (0-8)
            moving: Moving sensitivity threshold (0-100)
            stationary: Stationary sensitivity threshold (0-100)
            
        Returns:
            bool: True if setting was successful, False otherwise
        """
        if self.enter_configuration_mode_():
            time.sleep_ms(50)
            
            self.send_command_preamble_()
            
            # Command payload
            payload = bytearray([
                0x14, 0x00,  # Command length (20 bytes)
                0x64, 0x00,  # Set sensitivity values command
                
                # Gate command
                0x00, 0x00,
                gate, 0x00,
                0x00, 0x00,
                
                # Motion sensitivity command
                0x01, 0x00,
                moving, 0x00,
                0x00, 0x00,
                
                # Stationary sensitivity command
                0x02, 0x00,
                stationary, 0x00,
                0x00, 0x00,
            ])
            
            self.radar_uart.write(payload)
            
            self.send_command_postamble_()
            self.radar_uart_last_command_ = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), self.radar_uart_last_command_) < self.radar_uart_command_timeout_:
                if self.read_frame_():
                    if self.latest_ack_ == 0x64 and self.latest_command_success_:
                        time.sleep_ms(50)
                        self.leave_configuration_mode_()
                        return True
            
            time.sleep_ms(50)
            self.leave_configuration_mode_()
        
        return False
    
    # Target information methods
    
    def presence_detected(self):
        """
        Check if any target is detected.
        
        Returns:
            bool: True if a target is detected, False otherwise
        """
        return self.target_type_ != 0
    
    def stationary_target_detected(self):
        """
        Check if a stationary target is detected.
        
        Returns:
            bool: True if a stationary target is detected, False otherwise
        """
        return ((self.target_type_ & 0x02) and 
                self.stationary_target_distance_ > 0 and 
                self.stationary_target_energy_ > 0)
    
    def stationary_target_distance(self):
        """
        Get the distance to the stationary target in centimeters.
        
        Returns:
            int: Distance in centimeters
        """
        return self.stationary_target_distance_
    
    def stationary_target_energy(self):
        """
        Get the energy level of the stationary target.
        
        Returns:
            int: Energy level (0-100)
        """
        return self.stationary_target_energy_
    
    def moving_target_detected(self):
        """
        Check if a moving target is detected.
        
        Returns:
            bool: True if a moving target is detected, False otherwise
        """
        return ((self.target_type_ & 0x01) and 
                self.moving_target_distance_ > 0 and 
                self.moving_target_energy_ > 0)
    
    def moving_target_distance(self):
        """
        Get the distance to the moving target in centimeters.
        
        Returns:
            int: Distance in centimeters
        """
        return self.moving_target_distance_
    
    def moving_target_energy(self):
        """
        Get the energy level of the moving target.
        
        Returns:
            int: Energy level (0-100)
        """
        # Limit energy value to 100 if it's higher
        if self.moving_target_energy_ > 100:
            return 100
        
        return self.moving_target_energy_
    
    def debug(self, terminal_uart):
        """
        Set a debug UART for printing diagnostic information.
        
        Args:
            terminal_uart: UART stream for debug output
        """
        self.debug_uart = terminal_uart
    
    def isConnected(self):
        """
        Check if the radar is connected and responding.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if time.ticks_diff(time.ticks_ms(), self.radar_uart_last_packet_) < self.radar_uart_timeout:
            return True
        
        if self.read_frame_():
            return True
        
        return False
    
    def add_to_buffer(self, byte):
        """
        Add a byte to the circular buffer.
        
        Args:
            byte: Single byte to add to the buffer
        """
        self.circular_buffer[self.buffer_head] = byte
        self.buffer_head = (self.buffer_head + 1) % LD2410_BUFFER_SIZE
        
        # Handle buffer overflow by overwriting oldest data
        if self.buffer_head == self.buffer_tail:
            self.buffer_tail = (self.buffer_tail + 1) % LD2410_BUFFER_SIZE
    
    def read_from_buffer(self):
        """
        Read a byte from the circular buffer.
        
        Returns:
            tuple: (success, byte) where success is a boolean indicating if read was successful
        """
        if self.buffer_head == self.buffer_tail:
            return False, 0  # Buffer empty
        
        byte = self.circular_buffer[self.buffer_tail]
        self.buffer_tail = (self.buffer_tail + 1) % LD2410_BUFFER_SIZE
        return True, byte
    
    def read(self):
        """
        Read data from the radar sensor.
        
        Returns:
            bool: True if new data was read, False otherwise
        """
        new_data = False
        
        # Read all available data from UART into buffer
        while self.radar_uart.any():
            self.add_to_buffer(self.radar_uart.read(1)[0])
            new_data = True
        
        # Try to process a frame
        frame_processed = self.read_frame_()
        
        return new_data or frame_processed
    
    def read_frame_(self):
        """
        Process the buffer to find and parse a complete frame.
        
        Returns:
            bool: True if a complete frame was found and processed, False otherwise
        """
        while True:
            success, byte_read = self.read_from_buffer()
            if not success:
                break  # No more data in buffer
            
            # If frame hasn't started, check for frame start markers
            if not self.frame_started_:
                if byte_read == 0xF4 or byte_read == 0xFD:
                    self.radar_data_frame_[0] = byte_read
                    self.radar_data_frame_position_ = 1
                    self.frame_started_ = True
                    self.ack_frame_ = (byte_read == 0xFD)  # Determine frame type
            else:
                # Continue building the frame
                self.radar_data_frame_[self.radar_data_frame_position_] = byte_read
                self.radar_data_frame_position_ += 1
                
                # After reading at least 8 bytes, verify frame length
                if self.radar_data_frame_position_ == 8:
                    intra_frame_data_length = self.radar_data_frame_[4] | (self.radar_data_frame_[5] << 8)
                    
                    # Check if frame length exceeds maximum allowed
                    if intra_frame_data_length + 10 > LD2410_MAX_FRAME_LENGTH:
                        self.frame_started_ = False
                        self.radar_data_frame_position_ = 0
                        continue
                
                # Check if the frame is complete
                if self.radar_data_frame_position_ >= 8 and self.check_frame_end_():
                    self.frame_started_ = False  # Reset for next frame
                    
                    # Process the frame
                    if self.ack_frame_:
                        return self.parse_command_frame_()
                    else:
                        return self.parse_data_frame_()
        
        return False
    
    def check_frame_end_(self):
        """
        Check if the current frame data includes a valid end marker.
        
        Returns:
            bool: True if end marker is found, False otherwise
        """
        if self.ack_frame_:
            return (self.radar_data_frame_[0] == 0xFD and
                    self.radar_data_frame_[1] == 0xFC and
                    self.radar_data_frame_[2] == 0xFB and
                    self.radar_data_frame_[3] == 0xFA and
                    self.radar_data_frame_[self.radar_data_frame_position_ - 4] == 0x04 and
                    self.radar_data_frame_[self.radar_data_frame_position_ - 3] == 0x03 and
                    self.radar_data_frame_[self.radar_data_frame_position_ - 2] == 0x02 and
                    self.radar_data_frame_[self.radar_data_frame_position_ - 1] == 0x01)
        else:
            return (self.radar_data_frame_[0] == 0xF4 and
                    self.radar_data_frame_[1] == 0xF3 and
                    self.radar_data_frame_[2] == 0xF2 and
                    self.radar_data_frame_[3] == 0xF1 and
                    self.radar_data_frame_[self.radar_data_frame_position_ - 4] == 0xF8 and
                    self.radar_data_frame_[self.radar_data_frame_position_ - 3] == 0xF7 and
                    self.radar_data_frame_[self.radar_data_frame_position_ - 2] == 0xF6 and
                    self.radar_data_frame_[self.radar_data_frame_position_ - 1] == 0xF5)
    
    def parse_data_frame_(self):
        """
        Parse a data frame from the radar sensor.
        
        Returns:
            bool: True if parsing was successful, False otherwise
        """
        intra_frame_data_length = self.radar_data_frame_[4] | (self.radar_data_frame_[5] << 8)
        
        # Check if frame length is correct
        if self.radar_data_frame_position_ != intra_frame_data_length + 10:
            return False
        
        # Check specific bytes to validate the frame
        if (self.radar_data_frame_[6] == 0x02 and 
            self.radar_data_frame_[7] == 0xAA and
            self.radar_data_frame_[17] == 0x55 and 
            self.radar_data_frame_[18] == 0x00):
            
            self.target_type_ = self.radar_data_frame_[8]
            
            # Extract distances and energies
            # Using little-endian for converting 2 bytes to uint16
            self.stationary_target_distance_ = self.radar_data_frame_[9] | (self.radar_data_frame_[10] << 8)
            self.moving_target_distance_ = self.radar_data_frame_[15] | (self.radar_data_frame_[16] << 8)
            self.stationary_target_energy_ = self.radar_data_frame_[14]
            self.moving_target_energy_ = self.radar_data_frame_[11]
            
            self.last_valid_frame_length = self.radar_data_frame_position_
            self.radar_uart_last_packet_ = time.ticks_ms()
            return True
        
        return False
    
    def parse_command_frame_(self):
        """
        Parse a command acknowledgement frame.
        
        Returns:
            bool: True if command was successful, False otherwise
        """
        intra_frame_data_length = self.radar_data_frame_[4] | (self.radar_data_frame_[5] << 8)
        
        self.latest_ack_ = self.radar_data_frame_[6]
        self.latest_command_success_ = (self.radar_data_frame_[8] == 0x00 and self.radar_data_frame_[9] == 0x00)
        
        # Handle different command acknowledgements
        if intra_frame_data_length == 8 and self.latest_ack_ == 0xFF:
            # ACK for entering configuration mode
            if self.latest_command_success_:
                self.radar_uart_last_packet_ = time.ticks_ms()
                return True
            return False
        
        elif intra_frame_data_length == 4 and self.latest_ack_ == 0xFE:
            # ACK for leaving configuration mode
            if self.latest_command_success_:
                self.radar_uart_last_packet_ = time.ticks_ms()
                return True
            return False
        
        elif intra_frame_data_length == 4 and self.latest_ack_ == 0x60:
            # ACK for setting max values
            if self.latest_command_success_:
                self.radar_uart_last_packet_ = time.ticks_ms()
                return True
            return False
        
        elif intra_frame_data_length == 28 and self.latest_ack_ == 0x61:
            # ACK for current configuration
            if self.latest_command_success_:
                self.radar_uart_last_packet_ = time.ticks_ms()
                
                # Extract configuration values
                self.max_gate = self.radar_data_frame_[11]
                self.max_moving_gate = self.radar_data_frame_[12]
                self.max_stationary_gate = self.radar_data_frame_[13]
                
                # Motion sensitivity for each gate
                for i in range(9):
                    self.motion_sensitivity[i] = self.radar_data_frame_[14 + i]
                
                # Stationary sensitivity for each gate
                for i in range(9):
                    self.stationary_sensitivity[i] = self.radar_data_frame_[23 + i]
                
                # Sensor idle time
                self.sensor_idle_time = self.radar_data_frame_[32] | (self.radar_data_frame_[33] << 8)
                
                return True
            return False
        
        elif intra_frame_data_length == 4 and self.latest_ack_ == 0x64:
            # ACK for setting sensitivity values
            if self.latest_command_success_:
                self.radar_uart_last_packet_ = time.ticks_ms()
                return True
            return False
        
        elif intra_frame_data_length == 12 and self.latest_ack_ == 0xA0:
            # ACK for firmware version
            if self.latest_command_success_:
                self.firmware_major_version = self.radar_data_frame_[13]
                self.firmware_minor_version = self.radar_data_frame_[12]
                
                # 32-bit value from 4 bytes
                self.firmware_bugfix_version = (
                    self.radar_data_frame_[14] |
                    (self.radar_data_frame_[15] << 8) |
                    (self.radar_data_frame_[16] << 16) |
                    (self.radar_data_frame_[17] << 24)
                )
                
                self.radar_uart_last_packet_ = time.ticks_ms()
                return True
            return False
        
        elif intra_frame_data_length == 4 and self.latest_ack_ == 0xA2:
            # ACK for factory reset
            if self.latest_command_success_:
                self.radar_uart_last_packet_ = time.ticks_ms()
                return True
            return False
        
        elif intra_frame_data_length == 4 and self.latest_ack_ == 0xA3:
            # ACK for restart
            if self.latest_command_success_:
                self.radar_uart_last_packet_ = time.ticks_ms()
                return True
            return False
        
        # For any successful command
        if self.latest_command_success_:
            self.last_valid_frame_length = self.radar_data_frame_position_
            self.radar_uart_last_packet_ = time.ticks_ms()
            return True
            
        return False
    
    def read_frame_no_buffer_(self):
        """
        Read a frame directly from UART without using buffer.
        Used mainly for command responses.
        
        Returns:
            bool: True if a complete frame was read and processed, False otherwise
        """
        if not self.radar_uart.any():
            return False
            
        if not self.frame_started_:
            byte_read = self.radar_uart.read(1)[0]
            if byte_read == 0xF4:
                self.radar_data_frame_[0] = byte_read
                self.radar_data_frame_position_ = 1
                self.frame_started_ = True
                self.ack_frame_ = False
            elif byte_read == 0xFD:
                self.radar_data_frame_[0] = byte_read
                self.radar_data_frame_position_ = 1
                self.frame_started_ = True
                self.ack_frame_ = True
        else:
            if self.radar_data_frame_position_ < LD2410_MAX_FRAME_LENGTH:
                self.radar_data_frame_[self.radar_data_frame_position_] = self.radar_uart.read(1)[0]
                self.radar_data_frame_position_ += 1
                
                if self.radar_data_frame_position_ > 7:
                    # Check for data frame end
                    if (self.radar_data_frame_[0] == 0xF4 and
                        self.radar_data_frame_[1] == 0xF3 and
                        self.radar_data_frame_[2] == 0xF2 and
                        self.radar_data_frame_[3] == 0xF1 and
                        self.radar_data_frame_[self.radar_data_frame_position_ - 4] == 0xF8 and
                        self.radar_data_frame_[self.radar_data_frame_position_ - 3] == 0xF7 and
                        self.radar_data_frame_[self.radar_data_frame_position_ - 2] == 0xF6 and
                        self.radar_data_frame_[self.radar_data_frame_position_ - 1] == 0xF5):
                        
                        if self.parse_data_frame_():
                            self.frame_started_ = False
                            self.radar_data_frame_position_ = 0
                            return True
                        else:
                            self.frame_started_ = False
                            self.radar_data_frame_position_ = 0
                    
                    # Check for command frame end
                    elif (self.radar_data_frame_[0] == 0xFD and
                          self.radar_data_frame_[1] == 0xFC and
                          self.radar_data_frame_[2] == 0xFB and
                          self.radar_data_frame_[3] == 0xFA and
                          self.radar_data_frame_[self.radar_data_frame_position_ - 4] == 0x04 and
                          self.radar_data_frame_[self.radar_data_frame_position_ - 3] == 0x03 and
                          self.radar_data_frame_[self.radar_data_frame_position_ - 2] == 0x02 and
                          self.radar_data_frame_[self.radar_data_frame_position_ - 1] == 0x01):
                        
                        if self.parse_command_frame_():
                            self.frame_started_ = False
                            self.radar_data_frame_position_ = 0
                            return True
                        else:
                            self.frame_started_ = False
                            self.radar_data_frame_position_ = 0
            else:
                self.frame_started_ = False
                self.radar_data_frame_position_ = 0
                
        return False
    
    def send_command_preamble_(self):
        """Send the command preamble sequence."""
        # Command preamble
        self.radar_uart.write(bytes([0xFD, 0xFC, 0xFB, 0xFA]))
    
    def send_command_postamble_(self):
        """Send the command postamble sequence."""
        # Command end
        self.radar_uart.write(bytes([0x04, 0x03, 0x02, 0x01]))
    
    def enter_configuration_mode_(self):
        """
        Enter configuration mode for sending commands.
        
        Returns:
            bool: True if entered successfully, False otherwise
        """
        self.send_command_preamble_()
        
        # Request enter command mode
        self.radar_uart.write(bytes([
            0x04, 0x00,  # Command length (4 bytes)
            0xFF, 0x00,  # Enter configuration mode command
            0x01, 0x00   # Command parameters
        ]))
        
        self.send_command_postamble_()
        self.radar_uart_last_command_ = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), self.radar_uart_last_command_) < self.radar_uart_command_timeout_:
            if self.read_frame_no_buffer_():
                if self.latest_ack_ == 0xFF and self.latest_command_success_:
                    return True
        
        return False
    
    def leave_configuration_mode_(self):
        """
        Leave configuration mode.
        
        Returns:
            bool: True if exited successfully, False otherwise
        """
        self.send_command_preamble_()
        
        # Request leave command mode
        self.radar_uart.write(bytes([
            0x02, 0x00,  # Command length (2 bytes)
            0xFE, 0x00   # Leave configuration mode command
        ]))
        
        self.send_command_postamble_()
        self.radar_uart_last_command_ = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), self.radar_uart_last_command_) < self.radar_uart_command_timeout_:
            if self.read_frame_no_buffer_():
                if self.latest_ack_ == 0xFE and self.latest_command_success_:
                    return True
        
        return False
    
    def requestFirmwareVersion(self):
        """
        Request the firmware version from the sensor.
        
        Returns:
            bool: True if request was successful, False otherwise
        """
        if self.enter_configuration_mode_():
            time.sleep_ms(50)
            
            self.send_command_preamble_()
            
            # Request firmware version
            self.radar_uart.write(bytes([
                0x02, 0x00,  # Command length (2 bytes)
                0xA0, 0x00   # Request firmware version command
            ]))
            
            self.send_command_postamble_()
            self.radar_uart_last_command_ = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), self.radar_uart_last_command_) < self.radar_uart_command_timeout_:
                if self.read_frame_no_buffer_():
                    if self.latest_ack_ == 0xA0 and self.latest_command_success_:
                        time.sleep_ms(50)
                        self.leave_configuration_mode_()
                        return True
            
            time.sleep_ms(50)
            self.leave_configuration_mode_()
        
        return False
    
    def requestCurrentConfiguration(self):
        """
        Request the current configuration from the sensor.
        
        Returns:
            bool: True if request was successful, False otherwise
        """
        if self.enter_configuration_mode_():
            time.sleep_ms(50)
            
            self.send_command_preamble_()
            
            # Request current configuration
            self.radar_uart.write(bytes([
                0x02, 0x00,  # Command length (2 bytes)
                0x61, 0x00   # Request current configuration command
            ]))
            
            self.send_command_postamble_()
            self.radar_uart_last_command_ = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), self.radar_uart_last_command_) < self.radar_uart_command_timeout_:
                if self.read_frame_no_buffer_():
                    if self.latest_ack_ == 0x61 and self.latest_command_success_:
                        time.sleep_ms(50)
                        self.leave_configuration_mode_()
                        return True
            
            time.sleep_ms(50)
            self.leave_configuration_mode_()
        
        return False
    
    def requestFactoryReset(self):
        """
        Reset the sensor to factory defaults.
        
        Returns:
            bool: True if reset was successful, False otherwise
        """
        if self.enter_configuration_mode_():
            time.sleep_ms(50)
            
            self.send_command_preamble_()
            
            # Request factory reset
            self.radar_uart.write(bytes([
                0x02, 0x00,  # Command length (2 bytes)
                0xA2, 0x00   # Factory reset command
            ]))
            
            self.send_command_postamble_()
            self.radar_uart_last_command_ = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), self.radar_uart_last_command_) < self.radar_uart_command_timeout_:
                if self.read_frame_():
                    if self.latest_ack_ == 0xA2 and self.latest_command_success_:
                        time.sleep_ms(50)
                        self.leave_configuration_mode_()
                        return True
            
            time.sleep_ms(50)
            self.leave_configuration_mode_()
        
        return False
    
    def requestRestart(self):
        """
        Restart the sensor.
        
        Returns:
            bool: True if restart command was successful, False otherwise
        """
        if self.enter_configuration_mode_():
            time.sleep_ms(50)
            
            self.send_command_preamble_()
            
            # Request restart
            self.radar_uart.write(bytes([
                0x02, 0x00,  # Command length (2 bytes)
                0xA3, 0x00   # Restart command
            ]))
            
            self.send_command_postamble_()
            self.radar_uart_last_command_ = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), self.radar_uart_last_command_) < self.radar_uart_command_timeout_:
                if self.read_frame_():
                    if self.latest_ack_ == 0xA3 and self.latest_command_success_:
                        time.sleep_ms(50)
                        self.leave_configuration_mode_()
                        return True
            
            time.sleep_ms(50)
            self.leave_configuration_mode_()
        
        return False
    
    def setMaxValues(self, moving, stationary, inactivity_timer):
        """
        Set maximum detection values for the sensor.
        
        Args:
            moving: Maximum moving gate value
            stationary: Maximum stationary gate value
            inactivity_timer: Inactivity timer in seconds
            
        Returns:
            bool: True if setting was successful, False otherwise
        """
        if self.enter_configuration_mode_():
            time.sleep_ms(50)
            
            self.send_command_preamble_()
            
            # Command payload
            payload = bytearray([
                0x14, 0x00,  # Command length (20 bytes)
                0x60, 0x00,  # Set max values command
                
                # Moving gate command
                0x00, 0x00,
                moving & 0xFF, (moving >> 8) & 0xFF,
                0x00, 0x00,
                
                # Stationary gate command
                0x01, 0x00,
                stationary & 0xFF, (stationary >> 8) & 0xFF,
                0x00, 0x00,
                
                # Inactivity timer command
                0x02, 0x00,
                inactivity_timer & 0xFF, (inactivity_timer >> 8) & 0xFF,
                0x00, 0x00
            ])
            
            self.radar_uart.write(payload)
            
            self.send_command_postamble_()
            self.radar_uart_last_command_ = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), self.radar_uart_last_command_) < self.radar_uart_command_timeout_:
                if self.read_frame_():
                    if self.latest_ack_ == 0x60 and self.latest_command_success_:
                        time.sleep_ms(50)
                        self.leave_configuration_mode_()
                        return True
            
            time.sleep_ms(50)
            self.leave_configuration_mode_()
        
        return False