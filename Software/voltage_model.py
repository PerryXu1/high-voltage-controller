import math
from dataclasses import dataclass
from enum import Enum

class SegmentType(Enum):
    """Enum representing the different types of function segments"""
    CONSTANT = 0
    LINEAR = 1
    QUADRATIC = 2
    SINE = 3
    EXPONENTIAL = 4
    EXPONENTIAL_ASYMPTOTE = 5
    LOGARITHM = 6
    CUSTOM = 7

@dataclass
class Segment:
    """Dataclass representing a piecewise function segment
    
    :param segment_type: The type of function in the segment
    :type segment_type: SegmentType
    :param min_time: The left limit of the segment
    :type min_time: float
    :param max_time: The right limit of the segment
    :type max_time: float
    :param parameters: The function parameters
    :type parameters: list[float]
    """
    segment_type: SegmentType
    min_time: float
    max_time: float
    parameters: list[float]

class VoltageModel:
    """Model of the voltage-time signal created through the GUI
    
    :param segments: A list storing each segment of the voltage-time signal
    :type segments: list[Segments]
    """
    
    segments: list[Segment]
    def __init__(self):
        self.segments = []

    def add_segment(self, segment: Segment) -> None:
        """Adds a segment dictionary to the list and sorts by start time.
        
        :param segment: The segment to be added
        :type segment: Segment
        """
        if segment.min_time >= segment.max_time:
            return

        new_pieces = [segment]

        # Checking for segment overlap
        for old_segment in self.segments:
            next_pieces = []
            for p in new_pieces:
                # Check that segment does not overlap com
                if not (old_segment.min_time <= p.min_time and old_segment.max_time >= p.max_time):
                    # Case: no overlap
                    if p.max_time <= old_segment.min_time or p.min_time >= old_segment.max_time:
                        next_pieces.append(p)

                    # Case: piece spans overlapping; only take left section
                    elif p.min_time < old_segment.min_time and p.max_time > old_segment.max_time:
                        left_piece = Segment(
                            segment_type=p.segment_type,
                            min_time=p.min_time,
                            max_time=old_segment.min_time,
                            parameters=list(p.parameters)
                        )
                        next_pieces.append(left_piece)

                    # Case: overlaps left side of existing segment
                    elif p.min_time < old_segment.min_time < p.max_time <= old_segment.max_time:
                        p.max_time = old_segment.min_time
                        next_pieces.append(p)

                    # Case: overlaps right side of existing segment
                    elif old_segment.min_time <= p.min_time < old_segment.max_time < p.max_time:
                        p.min_time = old_segment.max_time
                        next_pieces.append(p)

            new_pieces = next_pieces

        self.segments.extend(new_pieces)
        self.segments.sort(key=lambda s: s.min_time)
        

    def get_voltage(self, t_actual: float) -> float:
        """Polls the equation for a specific time to get the voltage
        
        :param t_actual: The actual absolute time that the voltage signal is polled at
        :type t_actual: float
        
        :return: The voltage at the input time
        :rtype: float
        """
        if not self.segments:
            return 0.0

        for segment in self.segments:
            if segment.min_time <= t_actual <= segment.max_time:
                return self._calculate_voltage(segment, t_actual)
        
        last_segment = self.segments[-1]
        if t_actual > last_segment.max_time:
            return self._calculate_voltage(last_segment, last_segment.max_time)

        return 0.0

    def _calculate_voltage(self, segment: Segment, t_actual: float) -> float:
        """Routes to the correct math equation based on segment type
        
        :param segment: The segment that the voltage is calculated on
        :type segment: Segment
        :param t_actual: The actual absolute time the voltage is calculated at
        :type t_actual: float
        
        :return: The voltage at the input time
        :rtype: float
        """
        t = t_actual - segment["t_min"]
        p = segment["params"]
        s_type = segment["type"]

        try:
            if s_type == "Constant":
                return p.a
            
            elif s_type == "Linear":
                return p["a"] * t + p["b"]
                
            elif s_type == "Quadratic":
                return p["a"] * (t ** 2) + p["b"] * t + p["c"]
                
            elif s_type == "Sine":
                if p["trig_type"] == "Sine":
                    return p["a"] * math.sin(p["b"] * (t - p["c"])) + p["d"]
                else:
                    return p["a"] * math.cos(p["b"] * (t - p["c"])) + p["d"]
            
            elif s_type == "Logarithmic":
                return p["a"] * (math.log(t + p["h"]) / math.log(p["b"])) + p["k"]
                
            elif s_type == "Exponential Asymptote":
                return p["a"] * (1 - math.exp(-t / p["tau"])) + p["c"]
                
            elif s_type == "Custom":
                # Ensure custom expressions are evaluated safely
                allowed = {"t": t, "sin": math.sin, "cos": math.cos, "exp": math.exp, 
                           "log": math.log, "sqrt": math.sqrt, "pi": math.pi, "e": math.e}
                return float(eval(p["expr"], {"__builtins__": None}, allowed)) + p["offset"]
                
        except Exception as e:
            print(f"Math error in segment {s_type}: {e}")
            return 0.0
            
        return 0.0

def generate_plot_data(self, max_time: float, step_size: float = 0.5):
        """Generates arrays of T and V data points for the GUI graph or PCB based on step size
        
        :param max_time: The maximum time of the voltage signal
        :type max_time: float
        :param step_size: the time between signal pollings, in minutes
        :type step_size: float
        """
        if not self.segments or step_size <= 0:
            return [], []

        t_data = []
        v_data = []

        num_steps = int(max_time / step_size)

        for i in range(num_steps + 1):
            t = i * step_size
            t_data.append(t)
            v_data.append(self.get_voltage_at(t))

        return t_data, v_data