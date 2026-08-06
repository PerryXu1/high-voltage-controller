from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QDoubleSpinBox, QFormLayout, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt
import math

class SegmentDialog(QDialog):
    """
    Base class for all waveform segment pop-ups. 
    Handles the standard layout: Equation, Limits, 2-Column Parameters, and Buttons.
    
    :param function_name: Name of the function
    :type function_name: str
    :param equation_html: The defining equation of the function, in html format
    :type equation_html: str
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    def __init__(self, function_name: str, equation_html: str, previous_v_end: float = 0.0,
                 max_time: float = 60.0, parent = None):
        super().__init__(parent)
        self.setWindowTitle(f"Add {function_name} Segment")
        self.setMinimumWidth(500)
        
        self.previous_v_end = previous_v_end
        self.max_time = max_time
        
        self._is_updating = False

        # === Layout ===
        main_layout = QVBoxLayout(self)

        # Equation
        self.eq_label = QLabel(f"<b>Equation:</b> {equation_html}")
        self.eq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eq_label.setStyleSheet("font-size: 14px; padding: 10px;")
        main_layout.addWidget(self.eq_label)
        
        # note on relative time
        note = QLabel("<i>Note: t is relative to Start Time (t = t_actual - t_min)</i>")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(note)

        # Limits
        limits_group = QGroupBox("Time Limits")
        limits_layout = QHBoxLayout()
        self.t_min_input = self.create_spinbox(0, self.max_time, 0.0) # Default to 0, ideally passed from main GUI
        self.t_max_input = self.create_spinbox(0, self.max_time, self.max_time)
        limits_layout.addWidget(QLabel("Start Time (t_min):"))
        limits_layout.addWidget(self.t_min_input)
        limits_layout.addWidget(QLabel("End Time (t_max):"))
        limits_layout.addWidget(self.t_max_input)
        limits_group.setLayout(limits_layout)
        main_layout.addWidget(limits_group)

        # Parameters
        params_layout = QHBoxLayout()
        
        self.derived_group = QGroupBox("Derived Parameters")
        self.derived_layout = QFormLayout()
        self.derived_group.setLayout(self.derived_layout)
        
        self.eq_group = QGroupBox("Equation Parameters")
        self.eq_layout = QFormLayout()
        self.eq_group.setLayout(self.eq_layout)
        
        params_layout.addWidget(self.derived_group)
        params_layout.addWidget(self.eq_group)
        main_layout.addLayout(params_layout)

        self.build_parameters()

        # Buttons
        btn_layout = QHBoxLayout()
        self.match_btn = QPushButton("Match with Previous Segment")
        self.match_btn.clicked.connect(self.match_previous)
        
        self.add_btn = QPushButton("Add Segment")
        self.add_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        self.add_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.match_btn)
        btn_layout.addWidget(self.add_btn)
        main_layout.addLayout(btn_layout)
        
        self.t_max_input.valueChanged.connect(self.trigger_eq_update)
        self.t_min_input.valueChanged.connect(self.trigger_eq_update)

    def create_spinbox(self, min_val: str = -1e6, max_val: str = 1e6, default: str = 0.0):
        sb = QDoubleSpinBox()
        sb.setRange(min_val, max_val)
        sb.setDecimals(4)
        sb.setValue(default)
        return sb

    def build_parameters(self):
        """Override in subclasses to populate self.eq_layout and self.derived_layout"""
        pass

    def match_previous(self):
        """Override in subclasses to shift the starting V to self.previous_v_end"""
        pass

    def trigger_eq_update(self, *args):
        """Called when Equation parameters change. Updates Derived."""
        if self._is_updating: return
        self._is_updating = True
        self.update_derived_from_eq()
        self._is_updating = False

    def trigger_derived_update(self, *args):
        """Called when Derived parameters change. Updates Equation."""
        if self._is_updating: return
        self._is_updating = True
        self.update_eq_from_derived()
        self._is_updating = False

    def update_derived_from_eq(self):
        pass

    def update_eq_from_derived(self):
        pass

#=== Specific Function Implementations ===

class ConstantDialog(SegmentDialog):
    """Dialog for a constant function V = a
    
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    def __init__(self, previous_v_end: float = 0.0, max_time: float = 60.0, parent = None):
        equation_html = "V = a"
        super().__init__("Constant", equation_html, previous_v_end, max_time, parent)

    def build_parameters(self):
        # Equation Parameter
        self.param_a = self.create_spinbox(default=self.previous_v_end)
        self.eq_layout.addRow("Voltage Level (a):", self.param_a)

        # Derived Parameters
        self.param_first = self.create_spinbox(default=self.previous_v_end)
        self.param_last = self.create_spinbox(default=self.previous_v_end)

        self.derived_layout.addRow("First Value:", self.param_first)
        self.derived_layout.addRow("Last Value:", self.param_last)

        # Connections
        self.param_a.valueChanged.connect(self.trigger_eq_update)
        self.param_first.valueChanged.connect(lambda: self.trigger_derived_update('first'))
        self.param_last.valueChanged.connect(lambda: self.trigger_derived_update('last'))

    def update_derived_from_eq(self):
        a = self.param_a.value()
        self.param_first.setValue(a)
        self.param_last.setValue(a)

    def trigger_derived_update(self, source):
        if self._is_updating:
            return
        self._is_updating = True

        if source == 'first':
            val = self.param_first.value()
        else:
            val = self.param_last.value()

        self.param_a.setValue(val)
        self.param_first.setValue(val)
        self.param_last.setValue(val)

        self._is_updating = False

    def match_previous(self):
        """Sets the constant voltage level to match the ending voltage of the previous segment."""
        self.param_a.setValue(self.previous_v_end)
        self.trigger_eq_update()

class LinearDialog(SegmentDialog):
    """Dialog for a linear function V = ax + b
    
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    def __init__(self, previous_v_end: float = 0.0, max_time: float = 60.0, parent = None):
        super().__init__("Linear", "V = a*t + b", previous_v_end, max_time, parent)

    def build_parameters(self):
        # Equation Parameters
        self.param_a = self.create_spinbox()
        self.param_b = self.create_spinbox()
        self.eq_layout.addRow("Slope (a):", self.param_a)
        self.eq_layout.addRow("Y-Int (b):", self.param_b)

        # Derived Parameters
        self.param_first = self.create_spinbox()
        self.param_last = self.create_spinbox()
        self.derived_layout.addRow("First Value:", self.param_first)
        self.derived_layout.addRow("Last Value:", self.param_last)

        # Connections
        self.param_a.valueChanged.connect(self.trigger_eq_update)
        self.param_b.valueChanged.connect(self.trigger_eq_update)
        self.param_first.valueChanged.connect(self.trigger_derived_update)
        self.param_last.valueChanged.connect(self.trigger_derived_update)

    def update_derived_from_eq(self):
        t_len = self.t_max_input.value() - self.t_min_input.value()
        a = self.param_a.value()
        b = self.param_b.value()
        
        self.param_first.setValue(b)
        self.param_last.setValue(a * t_len + b)

    def update_eq_from_derived(self):
        t_len = self.t_max_input.value() - self.t_min_input.value()
        first = self.param_first.value()
        last = self.param_last.value()
        
        self.param_b.setValue(first)
        if t_len > 0:
            self.param_a.setValue((last - first) / t_len)

    def match_previous(self):
        """Updates the first value of this segment to equal the final value of the previous segment"""
        self.param_first.setValue(self.previous_v_end)
        self.trigger_derived_update()


class SineDialog(SegmentDialog):
    """Dialog for a sine/cosine function V = a sin(b(t - c)) + d | V = a cos(b(t - c)) + d
    
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    def __init__(self, previous_v_end: float = 0.0, max_time: float = 60.0, parent = None):
        super().__init__("Sine", "V = a*sin(b(t - c)) + d", previous_v_end, max_time, parent)

    def build_parameters(self):
        # Base Function (Sine or Cosine)
        self.trig_choice = QComboBox()
        self.trig_choice.addItems(["Sine", "Cosine"])
        self.eq_layout.addRow("Function:", self.trig_choice)
        
        # Equation Parameters
        self.param_a = self.create_spinbox()
        self.param_b = self.create_spinbox(min_val=0.0001, default=1.0)
        self.param_c = self.create_spinbox()
        self.param_d = self.create_spinbox()
        
        self.eq_layout.addRow("Multiplier (a):", self.param_a)
        self.eq_layout.addRow("Multiplier (b):", self.param_b)
        self.eq_layout.addRow("Phase Shift (c):", self.param_c)
        self.eq_layout.addRow("Vertical Shift (d):", self.param_d)

        # Derived Parameters
        self.param_period = self.create_spinbox(min_val=0.0001, default=2 * math.pi)
        self.param_freq = self.create_spinbox(min_val=0.0001, default=1 / (2 * math.pi))
        self.param_num_periods = self.create_spinbox(min_val=0.1)
        
        self.derived_layout.addRow("Period (min):", self.param_period)
        self.derived_layout.addRow("Frequency (Hz):", self.param_freq)
        self.derived_layout.addRow("Num Periods to Max Time:", self.param_num_periods)

        # Connections
        self.param_b.valueChanged.connect(self.trigger_eq_update)
        self.param_period.valueChanged.connect(lambda: self.trigger_derived_update('period'))
        self.param_freq.valueChanged.connect(lambda: self.trigger_derived_update('freq'))
        self.param_num_periods.valueChanged.connect(self.update_max_time_from_periods)

    def update_derived_from_eq(self):
        b = self.param_b.value()
        period = (2 * math.pi) / b
        self.param_period.setValue(period)
        self.param_freq.setValue(1.0 / period)
        
        t_len = self.t_max_input.value() - self.t_min_input.value()
        self.param_num_periods.setValue(t_len / period)

    def trigger_derived_update(self, source):
        if self._is_updating: return
        self._is_updating = True
        
        if source == 'period':
            period = self.param_period.value()
            self.param_b.setValue((2 * math.pi) / period)
            self.param_freq.setValue(1.0 / period)
        elif source == 'freq':
            freq = self.param_freq.value()
            self.param_b.setValue(2 * math.pi * freq)
            self.param_period.setValue(1.0 / freq)
            
        self._is_updating = False

    def update_max_time_from_periods(self):
        """Adjusts the max time limit to fit a user-selected number of periods. Keeps the min time limit
        the same.
        """
        if self._is_updating: return
        periods = self.param_num_periods.value()
        period_time = self.param_period.value()
        self.t_max_input.setValue(self.t_min_input.value() + (periods * period_time))

    def match_previous(self):
        """Adjusts the first value of this segment to equal the last value of the previous segment"""
        a = self.param_a.value()
        b = self.param_b.value()
        c = self.param_c.value()
        
        if self.trig_choice.currentText() == "Sine":
            current_start_v = a * math.sin(b * (0 - c))
        else:
            current_start_v = a * math.cos(b * (0 - c))
            
        required_d = self.previous_v_end - current_start_v
        self.param_d.setValue(required_d)

class QuadraticDialog(SegmentDialog):
    """Dialog for a quadratic function V = at^2 + bt + c
    
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    
    def __init__(self, previous_v_end: float = 0.0, max_time: float = 60.0, parent = None):
        super().__init__("Quadratic", "V = a*t<sup>2</sup> + b*t + c", previous_v_end, max_time, parent)

    def build_parameters(self):
        self.param_a = self.create_spinbox()
        self.param_b = self.create_spinbox()
        self.param_c = self.create_spinbox()
        self.eq_layout.addRow("a:", self.param_a)
        self.eq_layout.addRow("b:", self.param_b)
        self.eq_layout.addRow("c:", self.param_c)

        self.param_first = self.create_spinbox()
        self.param_last = self.create_spinbox()
        self.param_vx = self.create_spinbox()
        self.param_vy = self.create_spinbox()
        self.derived_layout.addRow("First Value:", self.param_first)
        self.derived_layout.addRow("Last Value:", self.param_last)
        self.derived_layout.addRow("Vertex X (relative):", self.param_vx)
        self.derived_layout.addRow("Vertex Y:", self.param_vy)

    def match_previous(self):
        self.param_c.setValue(self.previous_v_end)
        self.trigger_eq_update()

class ExponentialDialog(SegmentDialog):
    """Dialog for an exponential function V = a e^(kt) + c
    
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    def __init__(self, previous_v_end: float = 0.0, max_time: float = 60.0, parent = None):
        super().__init__("Exponential", "V = a * e<sup>k*t</sup> + c", previous_v_end, max_time, parent)

    def build_parameters(self):
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Growth (k > 0)", "Decay (k < 0)"])
        self.eq_layout.addRow("Type:", self.type_combo)

        self.param_a = self.create_spinbox()
        self.param_k = self.create_spinbox()
        self.param_c = self.create_spinbox()
        self.eq_layout.addRow("Multiplier (a):", self.param_a)
        self.eq_layout.addRow("Rate (k):", self.param_k)
        self.eq_layout.addRow("Shift (c):", self.param_c)

        self.param_first = self.create_spinbox()
        self.param_last = self.create_spinbox()
        self.derived_layout.addRow("First Value:", self.param_first)
        self.derived_layout.addRow("Last Value:", self.param_last)
        
    def match_previous(self):
        self.param_c.setValue(self.previous_v_end - self.param_a.value())
        
class ExponentialAsymptoteDialog(SegmentDialog):
    """Dialog for an exponential asymptote function (e.g. RC circuit voltage equation)
    
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    def __init__(self, previous_v_end: float = 0.0, max_time: float = 60.0, parent = None):
        equation_html = "V = a*(1 - e<sup>-t / &tau;</sup>) + c"
        super().__init__("Exponential Asymptote", equation_html, previous_v_end, max_time, parent)

    def build_parameters(self):
        # Equation Params
        self.param_a = self.create_spinbox()
        self.param_tau = self.create_spinbox(min_val=0.0001, default=1.0)
        self.param_c = self.create_spinbox()
        
        self.eq_layout.addRow("Scale (a):", self.param_a)
        self.eq_layout.addRow("Time Const (τ):", self.param_tau)
        self.eq_layout.addRow("Shift (c):", self.param_c)

        # Derived Params
        self.param_first = self.create_spinbox()
        self.param_last = self.create_spinbox()
        self.param_asymp = self.create_spinbox()
        
        self.derived_layout.addRow("First Value:", self.param_first)
        self.derived_layout.addRow("Last Value:", self.param_last)
        self.derived_layout.addRow("Asymptote:", self.param_asymp)

        # Connections
        self.param_a.valueChanged.connect(self.trigger_eq_update)
        self.param_tau.valueChanged.connect(self.trigger_eq_update)
        self.param_c.valueChanged.connect(self.trigger_eq_update)
        
        self.param_first.valueChanged.connect(self.trigger_derived_update)
        self.param_last.valueChanged.connect(self.trigger_derived_update)
        self.param_asymp.valueChanged.connect(self.trigger_derived_update)

    def update_derived_from_eq(self):
        a = self.param_a.value()
        tau = self.param_tau.value()
        c = self.param_c.value()
        t_len = self.t_max_input.value() - self.t_min_input.value()
        
        self.param_first.setValue(c)
        self.param_asymp.setValue(a + c)
        
        if tau > 0:
            last_val = a * (1 - math.exp(-t_len / tau)) + c
            self.param_last.setValue(last_val)

    def update_eq_from_derived(self):
        first = self.param_first.value()
        asymp = self.param_asymp.value()
        last = self.param_last.value()
        t_len = self.t_max_input.value() - self.t_min_input.value()
        
        c = first
        self.param_c.setValue(c)
        
        a = asymp - c
        self.param_a.setValue(a)

        if a != 0 and t_len > 0:
            ratio = 1 - ((last - c) / a)
            if ratio > 0:
                tau = -t_len / math.log(ratio)
                self.param_tau.setValue(tau)

    def match_previous(self):
        """Adjusts first value of current segment to equal the last value of the previous segment"""
        self.param_first.setValue(self.previous_v_end)
        self.trigger_derived_update()
        
class LogarithmicDialog(SegmentDialog):
    """Dialog for a logarithmic function V = a log_b(t + h) + k
    
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    def __init__(self, previous_v_end: float = 0.0, max_time: float = 60.0, parent: float = None):
        equation_html = "V = a * log<sub>b</sub>(t + h) + k"
        super().__init__("Logarithmic", equation_html, previous_v_end, max_time, parent)

    def build_parameters(self):
        self.base_combo = QComboBox()
        self.base_combo.addItems(["Natural Log (ln)", "Base 10", "Custom Base"])
        self.eq_layout.addRow("Log Type:", self.base_combo)

        # Equation Parameters
        self.param_a = self.create_spinbox(default=1.0)
        self.param_b = self.create_spinbox(min_val=0.0001, default=math.e)
        self.param_h = self.create_spinbox(min_val=0.0001, default=1.0)
        self.param_k = self.create_spinbox()

        self.eq_layout.addRow("Scale (a):", self.param_a)
        self.eq_layout.addRow("Base (b):", self.param_b)
        self.eq_layout.addRow("Time Shift (h):", self.param_h)
        self.eq_layout.addRow("Vertical Shift (k):", self.param_k)

        self.param_b.setEnabled(False)

        # Derived Parameters
        self.param_first = self.create_spinbox()
        self.param_last = self.create_spinbox()

        self.derived_layout.addRow("First Value:", self.param_first)
        self.derived_layout.addRow("Last Value:", self.param_last)

        # Connections
        self.base_combo.currentIndexChanged.connect(self.on_base_type_changed)

        self.param_a.valueChanged.connect(self.trigger_eq_update)
        self.param_b.valueChanged.connect(self.trigger_eq_update)
        self.param_h.valueChanged.connect(self.trigger_eq_update)
        self.param_k.valueChanged.connect(self.trigger_eq_update)

        self.param_first.valueChanged.connect(self.trigger_derived_update)
        self.param_last.valueChanged.connect(self.trigger_derived_update)

    def get_effective_base(self):
        """Returns the actual numerical base based on dropdown selection"""
        idx = self.base_combo.currentIndex()
        if idx == 0:
            return math.e
        elif idx == 1:
            return 10.0
        else:
            base = self.param_b.value()
            return base if base != 1.0 else 1.0001

    def on_base_type_changed(self, index):
        if index == 0:
            self.param_b.setValue(math.e)
            self.param_b.setEnabled(False)
        elif index == 1:
            self.param_b.setValue(10.0)
            self.param_b.setEnabled(False)
        else:
            self.param_b.setEnabled(True)

        self.trigger_eq_update()

    def update_derived_from_eq(self):
        a = self.param_a.value()
        b = self.get_effective_base()
        h = self.param_h.value()
        k = self.param_k.value()
        t_len = self.t_max_input.value() - self.t_min_input.value()

        first_val = a * (math.log(h) / math.log(b)) + k
        last_val = a * (math.log(t_len + h) / math.log(b)) + k

        self.param_first.setValue(first_val)
        self.param_last.setValue(last_val)

    def update_eq_from_derived(self):
        first = self.param_first.value()
        last = self.param_last.value()
        a = self.param_a.value()
        b = self.get_effective_base()
        h = self.param_h.value()
        t_len = self.t_max_input.value() - self.t_min_input.value()

        k = first - a * (math.log(h) / math.log(b))
        self.param_k.setValue(k)

        if t_len > 0:
            denom = (math.log(t_len + h) - math.log(h)) / math.log(b)
            if denom != 0:
                new_a = (last - first) / denom
                self.param_a.setValue(new_a)

    def match_previous(self):
        
        self.param_first.setValue(self.previous_v_end)
        self.trigger_derived_update()
        
class CustomDialog(SegmentDialog):
    """Dialog for a custome function V = f(t) + c
    
    :param previous_v_end: The final voltage value of the previous segment
    :type previous_v_end: float
    :param max_time: The maximum time the segment can go to (e.g. the length of the experiment)
    :type max_time: float
    :param parent: Parent
    :type parent: SegmentDialog
    """
    def __init__(self, previous_v_end=0.0, max_time=60.0, parent=None):
        equation_html = "V = f(t) + c"
        super().__init__("Custom", equation_html, previous_v_end, max_time, parent)

    def build_parameters(self):
        # Equation Parameters
        self.expr_input = QLineEdit("1000 * sin(0.01 * t)")
        self.param_offset = self.create_spinbox(default=0.0)

        self.eq_layout.addRow("Formula f(t):", self.expr_input)
        self.eq_layout.addRow("Offset Shift (c):", self.param_offset)

        help_label = QLabel("<small>Use <b>t</b> for relative time.<br>Supports: sin, cos, tan, exp, log, sqrt, abs, pi, e</small>")
        help_label.setStyleSheet("color: #555;")
        self.eq_layout.addRow(help_label)

        self.param_first = self.create_spinbox()
        self.param_last = self.create_spinbox()
        self.param_min = self.create_spinbox()
        self.param_max = self.create_spinbox()

        self.param_first.setReadOnly(True)
        self.param_last.setReadOnly(True)
        self.param_min.setReadOnly(True)
        self.param_max.setReadOnly(True)

        self.derived_layout.addRow("First Value:", self.param_first)
        self.derived_layout.addRow("Last Value:", self.param_last)
        self.derived_layout.addRow("Min Value in Range:", self.param_min)
        self.derived_layout.addRow("Max Value in Range:", self.param_max)

        # Connections
        self.expr_input.textChanged.connect(self.trigger_eq_update)
        self.param_offset.valueChanged.connect(self.trigger_eq_update)

        self.update_derived_from_eq()

    def eval_expression(self, t_val):
        """Safely evaluates the formula string at a given time t."""
        expr_str = self.expr_input.text()
        
        allowed_globals = {
            "__builtins__": None,
            "t": t_val,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "exp": math.exp,
            "log": math.log,
            "sqrt": math.sqrt,
            "abs": abs,
            "pi": math.pi,
            "e": math.e
        }
        
        try:
            raw_v = eval(expr_str, allowed_globals)
            return float(raw_v)
        except Exception:
            return None

    def update_derived_from_eq(self):
        t_len = self.t_max_input.value() - self.t_min_input.value()
        offset = self.param_offset.value()

        raw_first = self.eval_expression(0.0)
        raw_last = self.eval_expression(t_len)

        if raw_first is not None and raw_last is not None:
            self.param_first.setValue(raw_first + offset)
            self.param_last.setValue(raw_last + offset)

            samples = []
            steps = 50
            for i in range(steps + 1):
                sample_t = (t_len / steps) * i
                v = self.eval_expression(sample_t)
                if v is not None:
                    samples.append(v + offset)

            if samples:
                self.param_min.setValue(min(samples))
                self.param_max.setValue(max(samples))

    def match_previous(self):
        """Adjusts first value of current segment to equal the last value of the previous segment"""
        raw_first = self.eval_expression(0.0)
        if raw_first is not None:
            needed_offset = self.previous_v_end - raw_first
            self.param_offset.setValue(needed_offset)