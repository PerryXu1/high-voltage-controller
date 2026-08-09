import numpy as np
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
    :param parameters: Dictionary of equation parameters (e.g., {"a": 1.0, "b": 2.0})
    :type parameters: dict[str, float]
    """
    segment_type: SegmentType
    min_time: float
    max_time: float
    parameters: dict[str, float]

class VoltageModel:
    """Model of the voltage-time signal created through the GUI"""
    
    def __init__(self):
        self.segments: list[Segment] = []

    def add_segment(self, segment: Segment) -> None:
        """Adds a segment to the list, handling overlap and sorting."""
        if segment.min_time >= segment.max_time:
            return

        new_pieces = [segment]

        for old_segment in self.segments:
            next_pieces = []
            for p in new_pieces:
                if not (old_segment.min_time <= p.min_time and old_segment.max_time >= p.max_time):
                    # No overlap
                    if p.max_time <= old_segment.min_time or p.min_time >= old_segment.max_time:
                        next_pieces.append(p)
                    # Spans overlapping; take left section
                    elif p.min_time < old_segment.min_time and p.max_time > old_segment.max_time:
                        left_piece = Segment(
                            segment_type=p.segment_type,
                            min_time=p.min_time,
                            max_time=old_segment.min_time,
                            parameters=dict(p.parameters)
                        )
                        if hasattr(p, 'expression'):
                            left_piece.expression = p.expression
                        next_pieces.append(left_piece)
                    # Overlaps left side of existing segment
                    elif p.min_time < old_segment.min_time < p.max_time <= old_segment.max_time:
                        p.max_time = old_segment.min_time
                        next_pieces.append(p)
                    # Overlaps right side of existing segment
                    elif old_segment.min_time <= p.min_time < old_segment.max_time < p.max_time:
                        p.min_time = old_segment.max_time
                        next_pieces.append(p)
            new_pieces = next_pieces

        self.segments.extend(new_pieces)
        self.segments.sort(key=lambda s: s.min_time)
        
    def get_voltage(self, t_actual: float) -> float:
        """Polls the equation for a specific time to get the voltage."""
        if not self.segments:
            return np.nan

        for segment in self.segments:
            if segment.min_time <= t_actual <= segment.max_time:
                return self._calculate_voltage(segment, t_actual)

        return np.nan

    def _calculate_voltage(self, segment: Segment, t_actual: float) -> float:
        """Routes to the correct math equation based on segment type using dictionary keys."""
        t = t_actual - segment.min_time
        p = segment.parameters
        s_type = segment.segment_type

        try:
            if s_type == SegmentType.CONSTANT:
                return p["a"]
            
            elif s_type == SegmentType.LINEAR:
                return p["a"] * t + p["b"]
                
            elif s_type == SegmentType.QUADRATIC:
                return p["a"] * (t ** 2) + p["b"] * t + p["c"]
                
            elif s_type == SegmentType.SINE:
                is_cos = p.get("is_cos", 0.0)
                if is_cos == 0.0:
                    return p["a"] * np.sin(p["b"] * (t - p["c"])) + p["d"]
                else:
                    return p["a"] * np.cos(p["b"] * (t - p["c"])) + p["d"]
            
            elif s_type == SegmentType.EXPONENTIAL:
                return p["a"] * np.exp(p["k"] * t) + p["c"]

            elif s_type == SegmentType.EXPONENTIAL_ASYMPTOTE:
                return p["a"] * (1 - np.exp(-t / p["tau"])) + p["c"]

            elif s_type == SegmentType.LOGARITHM:
                return p["a"] * (np.log(t + p["h"]) / np.log(p["b"])) + p["k"]
                
            elif s_type == SegmentType.CUSTOM:
                allowed = {"t": t, "sin": np.sin, "cos": np.cos, "exp": np.exp, 
                           "log": np.log, "sqrt": np.sqrt, "pi": np.pi, "e": np.e}
                expr = getattr(segment, 'expression', '0')
                return float(eval(expr, {"__builtins__": None}, allowed)) + p.get("offset", 0.0)
                
        except Exception as e:
            print(f"Math error in segment {s_type.name}: {e}")
            return 0.0
            
        return 0.0

    def generate_plot_data(self, max_time: float, step_size: float = 0.5) -> list[float]:
        """Generates an array of voltage signal data points for the GUI graph.
        
        :param max_time: The maximum time that the voltage signal goes to
        :type max_time: float
        :param step_size: The time between consecutive samples of the analytical signal
        :type step_size: float
        
        :return: The list of voltages
        :rtype: list[float]
        """
        if not self.segments or step_size <= 0:
            return []

        v_data = []
        num_steps = int(max_time / step_size)

        for i in range(num_steps + 1):
            t = i * step_size
            v_data.append(self.get_voltage(t))

        return v_data