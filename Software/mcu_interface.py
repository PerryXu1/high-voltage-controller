import serial
import struct
import zlib

def transmit_signal(time_step: float, voltages: list[float], port: str = "COM3", baud_rate: int = 115200) -> int:
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
    
    :return: Total number of bytes sent
    :rtype: int
    """
    
    num_points = len(voltages)
    if num_points == 0:
        raise ValueError("Cannot send an empty waveform.")
    
    # Header
    header = struct.pack('<cIf', b'W', num_points, float(time_step))
    
    # Data
    data = struct.pack(f'<{num_points}f', *voltages)
    
    # CRC Checksum
    data_bytes = header + data
    crc32_value = zlib.crc32(data_bytes) & 0xFFFFFFFF
    crc_bytes = struct.pack('<I', crc32_value)
    
    # Packet Assembly
    packet = data_bytes + crc_bytes
    
    with serial.Serial(port, baud_rate, timeout=2) as ser:
        ser.write(packet)
        
    return len(packet)