import serial
import struct
import zlib
import numpy as np

def prepare_experiment(time_step: float, voltages: list[float],
                    port: str = "COM3", baud_rate: int = 115200, timeout: float = 3.0) -> bool:
    """Packages the time step, voltage data, and CRC32 checksum into binary format and sends it
    to the STM32 MCU through USB CDC serial
    
    :param time_step: The time step between consecutive samples of the defined analytical voltage signal
    :type time_step: float
    :param voltages: The list of voltage sampled from the analytical voltage signal
    :type voltages: list[float]
    :param port: The virtual port through which the data is transmitted to the MCU
    :type port: str
    :param baud_rate: Baud rate of data transfer
    :type baud_rate: int
    :param timeout: Seconds allotted for a response from the PCB
    :type timeout: float
    
    :return: If the data was recevied
    :rtype: bool
    """
    
    num_points = len(voltages)
    if num_points == 0:
        raise ValueError("Cannot send an empty waveform.")
    
    # Header
    header = struct.pack('<cIf', b'D', num_points, float(time_step))
    
    # Data
    dac_values = np.clip(
        np.round((voltages / 15000.0) * 4095).astype(int), 
        0, 
        4095
    )
    print(dac_values)
    data = struct.pack(f'<{num_points}f', *dac_values)
    
    # CRC Checksum
    data_bytes = header + data
    crc32_value = zlib.crc32(data_bytes) & 0xFFFFFFFF
    crc_bytes = struct.pack('<I', crc32_value)
    
    # Packet Assembly
    packet = data_bytes + crc_bytes
    
    try:
        with serial.Serial(port, baud_rate, timeout=timeout) as ser:
            ser.write(packet)
            ser.flush()
            
            response = ser.read(1)
            print(response)
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            return response == b'R'
    except Exception as e:
        print(f"Error sending waveform: {e}")
        return False

def start_experiment(port: str = "COM3", baud_rate: int = 115200) -> int:
    """Sends the 'S' start flag and enters a blocking read loop to print incoming MCU data.
    
    :param port: The virtual port through which the data is transmitted to the MCU
    :param baud_rate: Baud rate of data transfer
    :param total_expected_points: Optional number of telemetry packets to read before exiting
    :param process_events_fn: Optional reference to Qt's processEvents to prevent OS non-responding freeze
    """
    
    with serial.Serial(port, baud_rate, timeout=1) as ser:
        print("=====")
        print(b'\x53\x00')
        bytes_written = ser.write(b'\x53\x00')
        ser.flush()
            
    return bytes_written

def stop_experiment(port: str = "COM3", baud_rate: int = 115200) -> int:
    """Sends the 'O\x00' stop flag to the STM32 MCU.
    """
    with serial.Serial(port, baud_rate, timeout=1) as ser:
        bytes_written = ser.write(b'O\x00')
        ser.flush()
    return bytes_written

def set_control_mode(remote: bool, port: str = "COM3", baud_rate: int = 115200) -> int:
    """Sends the control mode flag. C\x01 for remote, C\x00 for local.
    """
    flag = b'C\x01' if remote else b'C\x00'
    with serial.Serial(port, baud_rate, timeout=1) as ser:
        bytes_written = ser.write(flag)
        ser.flush()
    return bytes_written