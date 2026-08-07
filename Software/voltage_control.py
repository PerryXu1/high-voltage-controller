import sys
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QVBoxLayout, QListWidget, QLabel, QAbstractItemView,
                             QGroupBox, QFormLayout, QDoubleSpinBox, QPushButton)
import pyqtgraph as pg

from dialogs import (ConstantDialog, LinearDialog, SineDialog, QuadraticDialog, ExponentialDialog,
                     ExponentialAsymptoteDialog, LogarithmicDialog, CustomDialog, CheckSamplingDialog)
from voltage_model import VoltageModel, SegmentType, Segment


class ControlPoint(pg.TargetItem):
    """Custom target handle that emits signal updates when dragged on the graph."""
    def __init__(self, x: float, y: float, segment: Segment, point_id: str, color='r', 
                 callback=None, press_callback=None, release_callback=None):
        super().__init__(
            pos=(x, y), 
            size=12, 
            pen=pg.mkPen(color, width=2), 
            brush=pg.mkBrush(255, 255, 255, 220),
            movable=True
        )
        self.segment = segment
        self.point_id = point_id
        self.callback = callback
        self.press_callback = press_callback
        self.release_callback = release_callback
        self.prev_voltage = 0.0
        
        self.sigPositionChanged.connect(self._on_moved)

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        if self.press_callback:
            self.press_callback(self)

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        if self.release_callback:
            self.release_callback(self)

    def mouseDragEvent(self, ev):
        """PyQtGraph drag handler to reliably capture drag start and release."""
        if ev.isStart() and self.press_callback:
            self.press_callback(self)
        elif ev.isFinish() and self.release_callback:
            self.release_callback(self)
        super().mouseDragEvent(ev)

    def _on_moved(self, *args):
        if self.callback:
            pos = self.pos()
            self.callback(self, self.segment, self.point_id, pos.x(), pos.y())


class VoltageControlGUI(QMainWindow):
    """Class that creates and displays the voltage control GUI with draggable handles."""
    
    _DEFAULT_MAX_VOLTAGE = 15000 # in volts
    _DEFAULT_MAX_TIME = 60 # in minutes
    _DEFAULT_WINDOW_WIDTH = 1200
    _DEFAULT_WINDOW_HEIGHT = 700

    # Snapping Tolerances
    _SNAP_TIME_TOLERANCE = 0.5 # minutes
    _SNAP_VOLTAGE_TOLERANCE = 300.0 # volts

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voltage Control")
        self.resize(self._DEFAULT_WINDOW_WIDTH, self._DEFAULT_WINDOW_HEIGHT)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Graph Panel
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=True)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Voltage', units='V')
        self.plot_widget.setLabel('bottom', 'Time', units='min')
        self.plot_widget.setXRange(0, self._DEFAULT_MAX_TIME, padding=0)
        self.plot_widget.setYRange(0, self._DEFAULT_MAX_VOLTAGE, padding=0)
        self.plot_widget.setLimits(xMin=0, yMin=0, yMax=self._DEFAULT_MAX_VOLTAGE)

        # Components Column (Waveform Sequence)
        middle_layout = QVBoxLayout()
        middle_label = QLabel("Waveform Sequence")
        self.active_functions_list = QListWidget()
        self.active_functions_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.active_functions_list.itemDoubleClicked.connect(self.on_active_item_double_clicked)
        
        middle_layout.addWidget(middle_label)
        middle_layout.addWidget(self.active_functions_list)

        # Add Column (Available Functions)
        right_layout = QVBoxLayout()
        right_label = QLabel("Available Functions")
        self.available_functions_list = QListWidget()
        functions = ["Constant", "Linear", "Quadratic", "Sine", "Exponential", 
                     "Exponential Asymptote", "Logarithmic", "Custom"]
        self.available_functions_list.addItems(functions)
        self.available_functions_list.itemClicked.connect(self.on_available_item_clicked)
        
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.available_functions_list)

        # Layout
        top_half_layout = QHBoxLayout()
        top_half_layout.addLayout(middle_layout, stretch=2)
        top_half_layout.addLayout(right_layout, stretch=1)

        bottom_half_layout = QVBoxLayout()

        # Graph
        graph_group = QGroupBox("Graph")
        graph_group_layout = QVBoxLayout()
        graph_form = QFormLayout()

        self.max_time_spin = QDoubleSpinBox()
        self.max_time_spin.setRange(1.0, 1000.0)
        self.max_time_spin.setValue(self._DEFAULT_MAX_TIME)

        self.v_scale_spin = QDoubleSpinBox()
        self.v_scale_spin.setRange(100.0, self._DEFAULT_MAX_VOLTAGE)
        self.v_scale_spin.setValue(self._DEFAULT_MAX_VOLTAGE)

        graph_form.addRow("Max Time (min):", self.max_time_spin)
        graph_form.addRow("Max Voltage (V):", self.v_scale_spin)

        self.reset_scales_btn = QPushButton("Reset Scales")

        graph_group_layout.addLayout(graph_form)
        graph_group_layout.addWidget(self.reset_scales_btn)
        graph_group.setLayout(graph_group_layout)

        # Experimentation Section
        exp_group = QGroupBox("Experimentation")
        exp_group_layout = QVBoxLayout()
        exp_form = QFormLayout()

        self.step_size_spin = QDoubleSpinBox()
        self.step_size_spin.setRange(0.001, 10.0)
        self.step_size_spin.setDecimals(3)
        self.step_size_spin.setValue(0.1)

        exp_form.addRow("Step Size (min):", self.step_size_spin)

        self.sample_btn = QPushButton("Sample Signal")
        self.sample_btn.setMinimumHeight(40)

        self.send_btn = QPushButton("Send to Controller")
        self.send_btn.setMinimumHeight(40)
        self.send_btn.setEnabled(False)

        exp_group_layout.addLayout(exp_form)
        exp_group_layout.addWidget(self.sample_btn)
        exp_group_layout.addWidget(self.send_btn)
        exp_group.setLayout(exp_group_layout)

        bottom_half_layout.addWidget(graph_group)
        bottom_half_layout.addWidget(exp_group)

        right_panel = QVBoxLayout()
        right_panel.addLayout(top_half_layout, stretch=1)
        right_panel.addLayout(bottom_half_layout, stretch=1)

        main_layout.addWidget(self.plot_widget, stretch=6)
        main_layout.addLayout(right_panel, stretch=3)

        self.voltage_model = VoltageModel()
        self.plot_curve = self.plot_widget.plot([], [], pen=pg.mkPen('b', width=2))
        
        self.max_time = float(self._DEFAULT_MAX_TIME)
        self.max_segment_time = 0.0
        self.step_size = 0.1
        self.control_points = []
        
        self.v_line = None
        self.h_line = None
        self._is_updating_handle = False
        
        self.highlight_curve = self.plot_widget.plot([], [], pen=pg.mkPen('b', width=4))
        self.active_functions_list.itemSelectionChanged.connect(self.on_active_item_selected)

        # Connections Between Graph and Experimentation
        self.max_time_spin.editingFinished.connect(self.on_max_time_changed)
        self.v_scale_spin.editingFinished.connect(self.on_v_scale_changed)
        self.reset_scales_btn.clicked.connect(self.reset_scales)
        self.step_size_spin.valueChanged.connect(self.exit_sampled_mode) # <-- ADD THIS LINE
        self.sample_btn.clicked.connect(self.on_sample_signal)
        self.send_btn.clicked.connect(self.on_send_to_controller)

    def clear_control_points(self):
        """Removes all draggable control handles from the plot."""
        for cp in self.control_points:
            self.plot_widget.removeItem(cp)
        self.control_points.clear()

    def clear_guidelines(self):
        """Removes horizontal and vertical guide lines."""
        if self.v_line is not None:
            self.plot_widget.removeItem(self.v_line)
            self.v_line = None
        if self.h_line is not None:
            self.plot_widget.removeItem(self.h_line)
            self.h_line = None

    def show_guidelines(self, cp: ControlPoint):
        """Creates vertical and horizontal guide lines through the active control point."""
        self.clear_guidelines()

        pen = pg.mkPen(color='#888888', width=1, style=Qt.PenStyle.DashLine)
        pos = cp.pos()

        self.v_line = pg.InfiniteLine(pos=pos.x(), angle=90, pen=pen)
        self.h_line = pg.InfiniteLine(pos=pos.y(), angle=0, pen=pen)

        self.plot_widget.addItem(self.v_line)
        self.plot_widget.addItem(self.h_line)

    def update_guidelines(self, cp: ControlPoint):
        """Updates position of active guidelines to track handle position."""
        pos = cp.pos()
        if self.v_line is not None:
            self.v_line.setValue(pos.x())
        if self.h_line is not None:
            self.h_line.setValue(pos.y())

    def on_control_point_pressed(self, cp: ControlPoint):
        """Displays guidelines when a control point handle is clicked."""
        self.show_guidelines(cp)

    def on_control_point_released(self, cp: ControlPoint):
        """Hides guidelines when a control point handle is released."""
        self.clear_guidelines()

    def generate_control_points(self):
        """Generates interactive handles for each active segment."""
        self.clear_control_points()

        for segment in self.voltage_model.segments:
            t_min, t_max = segment.min_time, segment.max_time
            dt = t_max - t_min
            if dt <= 0:
                continue

            p = segment.parameters
            st = segment.segment_type

            if st == SegmentType.CONSTANT:
                v_val = p["a"]
                self._add_handle(t_min, v_val, segment, "start", color='#E91E63')
                self._add_handle(t_max, v_val, segment, "end", color='#E91E63')

            elif st == SegmentType.LINEAR:
                v_start = p["b"]
                v_end = p["a"] * dt + p["b"]
                self._add_handle(t_min, v_start, segment, "start", color='#2196F3')
                self._add_handle(t_max, v_end, segment, "end", color='#2196F3')

            elif st == SegmentType.QUADRATIC:
                a, b, c = p["a"], p["b"], p["c"]
                if a == 0:
                    a = 1.0
                    b = -a * dt
                    p["a"], p["b"] = a, b

                tau_v = -b / (2 * a)
                if not (0.01 * dt <= tau_v <= 0.99 * dt):
                    tau_v = 0.5 * dt
                    b = -2 * a * tau_v
                    p["b"] = b

                tv = t_min + tau_v
                vv = c - (b ** 2) / (4 * a)
                v_start = c
                v_end = a * (dt ** 2) + b * dt + c

                self._add_handle(t_min, v_start, segment, "start", color='#4CAF50')
                self._add_handle(tv, vv, segment, "vertex", color='#FF9800')
                self._add_handle(t_max, v_end, segment, "end", color='#4CAF50')

            elif st == SegmentType.EXPONENTIAL_ASYMPTOTE:
                a, tau, c = p["a"], p["tau"], p["c"]
                v_start = c
                v_end = a * (1 - np.exp(-dt / tau)) + c
                t_tau = t_min + tau
                v_tau = c + a * (1 - np.exp(-1.0))

                self._add_handle(t_min, v_start, segment, "start", color='#9C27B0')
                self._add_handle(t_tau, v_tau, segment, "tau", color='#FF5722')
                self._add_handle(t_max, v_end, segment, "end", color='#9C27B0')

            else:
                v_start = self.voltage_model._calculate_voltage(segment, t_min)
                v_end = self.voltage_model._calculate_voltage(segment, t_max)
                self._add_handle(t_min, v_start, segment, "start", color='#607D8B')
                self._add_handle(t_max, v_end, segment, "end", color='#607D8B')

    def _add_handle(self, x: float, y: float, segment: Segment, point_id: str, color: str):
        cp = ControlPoint(
            x, y, segment, point_id, color=color, 
            callback=self.on_control_point_dragged,
            press_callback=self.on_control_point_pressed,
            release_callback=self.on_control_point_released
        )
        self.plot_widget.addItem(cp)
        self.control_points.append(cp)

    def _get_segment_time_bounds(self, segment: Segment) -> tuple[float, float]:
        """Calculates temporal boundary limits so segments cannot overlap or cross each other."""
        min_bound = 0.0
        max_bound = self.max_time

        sorted_segs = sorted(self.voltage_model.segments, key=lambda s: s.min_time)
        for i, s in enumerate(sorted_segs):
            if s == segment:
                if i > 0:
                    min_bound = sorted_segs[i - 1].max_time
                if i < len(sorted_segs) - 1:
                    max_bound = sorted_segs[i + 1].min_time
                break

        return min_bound, max_bound

    def _apply_endpoint_snapping(self, segment: Segment, point_id: str, new_x: float, new_y: float) -> tuple[float, float]:
        """Snaps endpoint coordinates to nearby endpoint handles of other segments."""
        if point_id not in ("start", "end"):
            return new_x, new_y

        best_snap_x = None
        best_dist_x = self._SNAP_TIME_TOLERANCE

        best_snap_y = None
        best_dist_y = self._SNAP_VOLTAGE_TOLERANCE

        for other_cp in self.control_points:
            if other_cp.segment == segment:
                continue
            if other_cp.point_id in ("start", "end"):
                tx, ty = other_cp.pos().x(), other_cp.pos().y()

                dx = abs(new_x - tx)
                if dx <= best_dist_x:
                    best_dist_x = dx
                    best_snap_x = tx

                dy = abs(new_y - ty)
                if dy <= best_dist_y:
                    best_dist_y = dy
                    best_snap_y = ty

        snapped_x = best_snap_x if best_snap_x is not None else new_x
        snapped_y = best_snap_y if best_snap_y is not None else new_y

        return snapped_x, snapped_y

    def on_control_point_dragged(self, active_cp: ControlPoint, segment: Segment, point_id: str, new_x: float, new_y: float):
        """Callback invoked during handle dragging—enforces bounds, applies snapping, and updates positions."""
        if self._is_updating_handle:
            return
        self._is_updating_handle = True
        self.exit_sampled_mode()

        st = segment.segment_type
        p = segment.parameters

        # Snap to global grid (1 minute, 100 V) before bounds check
        new_x = round(new_x)
        new_y = round(new_y / 100.0) * 100.0

        new_x = max(0.0, min(new_x, self.max_time))

        min_bound, max_bound = self._get_segment_time_bounds(segment)

        # Enforce segment time boundaries
        if point_id == "start":
            new_x = max(min_bound, min(new_x, segment.max_time - 0.1))
        elif point_id == "end":
            new_x = max(segment.min_time + 0.1, min(new_x, max_bound))
        else:
            new_x = max(segment.min_time + 0.01, min(new_x, segment.max_time - 0.01))

        # Apply endpoint snapping (overrides grid if close enough)
        new_x, new_y = self._apply_endpoint_snapping(segment, point_id, new_x, new_y)

        if point_id == "start":
            new_x = max(min_bound, min(new_x, segment.max_time - 0.1))
        elif point_id == "end":
            new_x = max(segment.min_time + 0.1, min(new_x, max_bound))

        active_cp.setPos(new_x, new_y)

        if st == SegmentType.CONSTANT:
            p["a"] = new_y
            if point_id == "start":
                segment.min_time = new_x
            elif point_id == "end":
                segment.max_time = new_x

        elif st == SegmentType.LINEAR:
            dt_old = segment.max_time - segment.min_time
            if point_id == "start":
                v_end = p["a"] * dt_old + p["b"] if dt_old > 0 else p["b"]
                segment.min_time = new_x
                p["b"] = new_y
                dt_new = segment.max_time - segment.min_time
                if dt_new > 0:
                    p["a"] = (v_end - new_y) / dt_new
            elif point_id == "end":
                segment.max_time = new_x
                dt_new = segment.max_time - segment.min_time
                if dt_new > 0:
                    p["a"] = (new_y - p["b"]) / dt_new

        elif st == SegmentType.QUADRATIC:
            if point_id == "start":
                segment.min_time = new_x
                dt = segment.max_time - segment.min_time
                p["c"] = new_y
                
                a_curr, b_curr = p["a"], p["b"]
                tau_v = -b_curr / (2 * a_curr) if a_curr != 0 else 0.5 * dt
                vv = p["c"] - (b_curr ** 2) / (4 * a_curr) if a_curr != 0 else new_y - 10.0
                
                tv = max(segment.min_time + 0.05 * dt, segment.min_time + tau_v)
                tau_v = tv - segment.min_time
                
                if abs(new_y - vv) < 1e-4:
                    vv = new_y - 1.0
                    
                p["a"] = (new_y - vv) / (tau_v ** 2)
                p["b"] = -2 * p["a"] * tau_v

            elif point_id == "vertex":
                dt = segment.max_time - segment.min_time
                tv = max(segment.min_time + 0.02 * dt, min(new_x, segment.max_time - 0.02 * dt))
                tau_v = tv - segment.min_time
                vv = new_y
                c = p["c"]
                
                if abs(c - vv) < 1e-4:
                    c = vv + 1.0
                    
                p["a"] = (c - vv) / (tau_v ** 2)
                p["b"] = -2 * p["a"] * tau_v

            elif point_id == "end":
                segment.max_time = new_x
                dt = segment.max_time - segment.min_time
                v_end = new_y
                c = p["c"]
                
                a_curr, b_curr = p["a"], p["b"]
                vv = c - (b_curr ** 2) / (4 * a_curr) if a_curr != 0 else c - 10.0
                
                if (c - vv) * (v_end - vv) <= 0:
                    v_end = vv + (1.0 if c > vv else -1.0)
                    
                k = np.sqrt(abs(c - vv) / abs(v_end - vv))
                tau_v = (k / (1.0 + k)) * dt
                tau_v = max(0.02 * dt, min(tau_v, 0.98 * dt))
                
                p["a"] = (c - vv) / (tau_v ** 2)
                p["b"] = -2 * p["a"] * tau_v

        elif st == SegmentType.EXPONENTIAL_ASYMPTOTE:
            if point_id == "start":
                segment.min_time = new_x
                p["c"] = new_y
            elif point_id == "end":
                segment.max_time = new_x
                dt = segment.max_time - segment.min_time
                if p["tau"] > 0:
                    p["a"] = (new_y - p["c"]) / (1 - np.exp(-dt / p["tau"]))
            elif point_id == "tau":
                tau = max(0.001, new_x - segment.min_time)
                p["tau"] = tau
                p["a"] = (new_y - p["c"]) / (1 - np.exp(-1.0))

        elif st in (SegmentType.EXPONENTIAL, SegmentType.SINE, SegmentType.LOGARITHM, SegmentType.CUSTOM):
            if point_id == "start":
                segment.min_time = new_x
            elif point_id == "end":
                segment.max_time = new_x

        self.voltage_model.segments.sort(key=lambda s: s.min_time)

        t_data, v_data = self.voltage_model.generate_plot_data(
            max_time=self.max_time, 
            step_size=self.step_size
        )
        self.plot_curve.setData(t_data, v_data)

        self._update_partner_handles(active_cp, segment)
        self._update_active_list_text()
        self.update_guidelines(active_cp)

        self._is_updating_handle = False

    def _update_partner_handles(self, active_cp: ControlPoint, segment: Segment):
        """Adjusts position of partner handles strictly based on this segment's equation."""
        t_min, t_max = segment.min_time, segment.max_time
        dt = t_max - t_min
        p = segment.parameters
        st = segment.segment_type

        for cp in self.control_points:
            if cp.segment != segment or cp == active_cp:
                continue

            if cp.point_id == "start":
                v = p["a"] if st == SegmentType.CONSTANT else self.voltage_model._calculate_voltage(segment, t_min)
                cp.setPos(t_min, v if not np.isnan(v) else 0.0)

            elif cp.point_id == "end":
                if st == SegmentType.QUADRATIC:
                    a, b, c = p["a"], p["b"], p["c"]
                    v = a * (dt ** 2) + b * dt + c
                elif st == SegmentType.CONSTANT:
                    v = p["a"]
                else:
                    v = self.voltage_model._calculate_voltage(segment, t_max)
                cp.setPos(t_max, v if not np.isnan(v) else 0.0)

            elif cp.point_id == "vertex" and st == SegmentType.QUADRATIC:
                a, b, c = p["a"], p["b"], p["c"]
                if a != 0:
                    tau_v = -b / (2 * a)
                    tv = t_min + tau_v
                    vv = c - (b ** 2) / (4 * a)
                else:
                    tv, vv = t_min + 0.5 * dt, c
                cp.setPos(tv, vv)

            elif cp.point_id == "tau" and st == SegmentType.EXPONENTIAL_ASYMPTOTE:
                a, tau, c = p["a"], p["tau"], p["c"]
                cp.setPos(t_min + tau, c + a * (1 - np.exp(-1.0)))

    def _update_active_list_text(self):
        """Updates active list items without destroying handles."""
        self.active_functions_list.clear()
        for segment in self.voltage_model.segments:
            name = segment.segment_type.name.capitalize().replace("_", " ")
            self.active_functions_list.addItem(
                f"{name} ({segment.min_time:.1f} to {segment.max_time:.1f} min)"
            )

    def on_available_item_clicked(self, item):
        function_name = item.text()

        dialog_map = {
            "Constant": (SegmentType.CONSTANT, ConstantDialog),
            "Linear": (SegmentType.LINEAR, LinearDialog),
            "Sine": (SegmentType.SINE, SineDialog),
            "Quadratic": (SegmentType.QUADRATIC, QuadraticDialog),
            "Exponential": (SegmentType.EXPONENTIAL, ExponentialDialog),
            "Exponential Asymptote": (SegmentType.EXPONENTIAL_ASYMPTOTE, ExponentialAsymptoteDialog),
            "Logarithmic": (SegmentType.LOGARITHM, LogarithmicDialog),
            "Custom": (SegmentType.CUSTOM, CustomDialog),
        }

        if function_name not in dialog_map:
            self.available_functions_list.clearSelection()
            return

        seg_type, dialog_class = dialog_map[function_name]
                    
                
        self.prev_voltage = self.voltage_model.get_voltage(self.max_segment_time)
        if np.isnan(self.prev_voltage):
            self.prev_voltage = 0.0

        dlg = dialog_class(previous_v_end=self.prev_voltage, max_time=self.max_time,
                           max_segment_time=self.max_segment_time, parent=self)

        if dlg.exec():
            segment = self.extract_segment(seg_type, dlg)
            if segment:
                self.voltage_model.add_segment(segment)
                self.refresh_gui_and_graph()

        self.available_functions_list.clearSelection()

    def extract_segment(self, seg_type: SegmentType, dlg) -> Segment:
        """Constructs a Segment with parameters stored as a dictionary."""
        min_time = dlg.t_min_input.value()
        max_time = dlg.t_max_input.value()
        params = {}

        if seg_type == SegmentType.CONSTANT:
            params = {"a": dlg.param_a.value()}

        elif seg_type == SegmentType.LINEAR:
            params = {
                "a": dlg.param_a.value(), 
                "b": dlg.param_b.value()
            }

        elif seg_type == SegmentType.QUADRATIC:
            params = {
                "a": dlg.param_a.value(), 
                "b": dlg.param_b.value(), 
                "c": dlg.param_c.value()
            }

        elif seg_type == SegmentType.SINE:
            is_cos = 1.0 if dlg.trig_choice.currentText() == "Cosine" else 0.0
            params = {
                "a": dlg.param_a.value(), 
                "b": dlg.param_b.value(), 
                "c": dlg.param_c.value(), 
                "d": dlg.param_d.value(), 
                "is_cos": is_cos
            }

        elif seg_type == SegmentType.EXPONENTIAL:
            params = {
                "a": dlg.param_a.value(), 
                "k": dlg.param_k.value(), 
                "c": dlg.param_c.value()
            }

        elif seg_type == SegmentType.EXPONENTIAL_ASYMPTOTE:
            params = {
                "a": dlg.param_a.value(), 
                "tau": dlg.param_tau.value(), 
                "c": dlg.param_c.value()
            }

        elif seg_type == SegmentType.LOGARITHM:
            params = {
                "a": dlg.param_a.value(), 
                "b": dlg.get_effective_base(), 
                "h": dlg.param_h.value(), 
                "k": dlg.param_k.value()
            }

        elif seg_type == SegmentType.CUSTOM:
            params = {"offset": dlg.param_offset.value()}
            seg = Segment(seg_type, min_time, max_time, params)
            seg.expression = dlg.expr_input.text()
            return seg

        return Segment(seg_type, min_time, max_time, params)

    def exit_sampled_mode(self):
        """Reverts the UI back to normal mode from sampled mode."""
        if self.sample_btn.text() != "Sample Signal":
            self.sample_btn.setText("Sample Signal")
            self.send_btn.setEnabled(False)

    def on_max_time_changed(self):
        """Updates the graph X-axis bounds and internal max time limit."""
        self.max_time = self.max_time_spin.value()
        self.plot_widget.setXRange(0, self.max_time, padding=0)
        self.exit_sampled_mode()
        self.refresh_gui_and_graph()

    def on_v_scale_changed(self):
        """Updates the graph Y-axis view without affecting internal component data."""
        val = self.v_scale_spin.value()
        self.plot_widget.setYRange(0, val, padding=0)
        self.exit_sampled_mode()

    def reset_scales(self):
        """Resets the graph views to their absolute maximum defaults."""
        self.max_time_spin.setValue(self._DEFAULT_MAX_TIME)
        self.v_scale_spin.setValue(self._DEFAULT_MAX_VOLTAGE)
        self.on_max_time_changed()
        self.on_v_scale_changed()

    def on_sample_signal(self):
        """Samples the signal uniformly or opens the check sampling dialog if already sampled."""
        if self.sample_btn.text() == "Check Sampling":
            t_smooth, v_smooth = self.voltage_model.generate_plot_data(
                max_time=self.max_time, 
                step_size=self.step_size / 10.0
            )
            
            dlg = CheckSamplingDialog(
                t_smooth=t_smooth,
                v_smooth=v_smooth,
                times=self.sampled_times,
                sampled_signal=self.sampled_signal,
                parent=self
            )
            dlg.exec()
            return

        step = self.step_size_spin.value()
        
        # Generate uniform sample time points
        self.sampled_times = np.arange(0, self.max_time + step, step)
        
        # Calculate sampled voltage values
        sampled_v = [self.voltage_model.get_voltage(t) for t in self.sampled_times]
        self.sampled_signal = np.nan_to_num(np.array(sampled_v), nan=0.0)

        print(f"Sampled Signal Array (Step: {step} min):")
        print(self.sampled_signal)

        # Enter Sampled Mode
        self.sample_btn.setText("Check Sampling")
        self.send_btn.setEnabled(True)

    def on_send_to_controller(self):
        print("Sending sampled signal to the STM32 controller over USB...")


    def refresh_gui_and_graph(self):
        """Full rebuild called when adding or removing segments."""
        self.exit_sampled_mode()
        self._update_active_list_text()

        t_data, v_data = self.voltage_model.generate_plot_data(
            max_time=self.max_time, 
            step_size=self.step_size
        )
        self.plot_curve.setData(t_data, v_data)
        self.generate_control_points()
        
        self.on_active_item_selected()

    def on_active_item_double_clicked(self, item):
            """Opens a dialog to edit the properties of an existing segment."""
            row = self.active_functions_list.row(item)
            if row < 0 or row >= len(self.voltage_model.segments):
                return
                
            segment = self.voltage_model.segments[row]
            st = segment.segment_type
            
            dialog_map = {
                SegmentType.CONSTANT: ConstantDialog,
                SegmentType.LINEAR: LinearDialog,
                SegmentType.QUADRATIC: QuadraticDialog,
                SegmentType.SINE: SineDialog,
                SegmentType.EXPONENTIAL: ExponentialDialog,
                SegmentType.EXPONENTIAL_ASYMPTOTE: ExponentialAsymptoteDialog,
                SegmentType.LOGARITHM: LogarithmicDialog,
                SegmentType.CUSTOM: CustomDialog,
            }
            
            dialog_class = dialog_map.get(st)
            if not dialog_class:
                return
                
            prev_voltage = 0.0
            if row > 0:
                prev_seg = self.voltage_model.segments[row - 1]
                prev_voltage = self.voltage_model.get_voltage(prev_seg.max_time)
                if np.isnan(prev_voltage):
                    prev_voltage = 0.0
                    
            dlg = dialog_class(previous_v_end=prev_voltage, 
                            max_time=self.max_time,
                            max_segment_time=self.max_segment_time, 
                            parent=self)
                            
            dlg.setWindowTitle(f"Edit {st.name.capitalize().replace('_', ' ')} Segment")
            dlg.add_btn.setText("Update Segment")
            
            dlg.t_min_input.setValue(segment.min_time)
            dlg.t_max_input.setValue(segment.max_time)
            
            p = segment.parameters
            if st == SegmentType.CONSTANT:
                dlg.param_a.setValue(p.get("a", 0.0))
                
            elif st == SegmentType.LINEAR:
                dlg.param_a.setValue(p.get("a", 0.0))
                dlg.param_b.setValue(p.get("b", 0.0))
                
            elif st == SegmentType.QUADRATIC:
                dlg.param_a.setValue(p.get("a", 0.0))
                dlg.param_b.setValue(p.get("b", 0.0))
                dlg.param_c.setValue(p.get("c", 0.0))
                
            elif st == SegmentType.SINE:
                dlg.param_a.setValue(p.get("a", 0.0))
                dlg.param_b.setValue(p.get("b", 1.0))
                dlg.param_c.setValue(p.get("c", 0.0))
                dlg.param_d.setValue(p.get("d", 0.0))
                dlg.trig_choice.setCurrentText("Cosine" if p.get("is_cos", 0.0) == 1.0 else "Sine")
                
            elif st == SegmentType.EXPONENTIAL:
                dlg.param_a.setValue(p.get("a", 0.0))
                dlg.param_k.setValue(p.get("k", 0.0))
                dlg.param_c.setValue(p.get("c", 0.0))
                if p.get("k", 0.0) < 0:
                    dlg.type_combo.setCurrentIndex(1)
                else:
                    dlg.type_combo.setCurrentIndex(0)
                    
            elif st == SegmentType.EXPONENTIAL_ASYMPTOTE:
                dlg.param_a.setValue(p.get("a", 0.0))
                dlg.param_tau.setValue(p.get("tau", 1.0))
                dlg.param_c.setValue(p.get("c", 0.0))
                
            elif st == SegmentType.LOGARITHM:
                dlg.param_a.setValue(p.get("a", 0.0))
                b_val = p.get("b", np.e)
                
                if abs(b_val - np.e) < 1e-4:
                    dlg.base_combo.setCurrentIndex(0)
                elif abs(b_val - 10.0) < 1e-4:
                    dlg.base_combo.setCurrentIndex(1)
                else:
                    dlg.base_combo.setCurrentIndex(2)
                    dlg.param_b.setValue(b_val)
                    
                dlg.param_h.setValue(p.get("h", 1.0))
                dlg.param_k.setValue(p.get("k", 0.0))
                
            elif st == SegmentType.CUSTOM:
                dlg.param_offset.setValue(p.get("offset", 0.0))
                if hasattr(segment, 'expression'):
                    dlg.expr_input.setText(segment.expression)
                    
            dlg.trigger_eq_update()

            if dlg.exec():
                updated_segment = self.extract_segment(st, dlg)
                
                if updated_segment:
                    self.voltage_model.segments.pop(row)
                    self.voltage_model.add_segment(updated_segment)
                    self.refresh_gui_and_graph()
                    
    def on_active_item_selected(self):
        """Highlights the selected segment on the graph with a thicker red line."""
        row = self.active_functions_list.currentRow()
        
        if row < 0 or row >= len(self.voltage_model.segments):
            self.highlight_curve.setData([], [])
            return

        segment = self.voltage_model.segments[row]
        
        steps = max(2, int((segment.max_time - segment.min_time) / self.step_size))
        t_seg = np.linspace(segment.min_time, segment.max_time, steps)
        v_seg = [self.voltage_model._calculate_voltage(segment, t) for t in t_seg]

        self.highlight_curve.setData(t_seg, v_seg)
    
    def keyPressEvent(self, event):
        """Deletes the highlighted segment when Backspace or Delete is pressed."""
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            row = self.active_functions_list.currentRow()
            
            if 0 <= row < len(self.voltage_model.segments):
                segment = self.voltage_model.segments.pop(row)
                self.max_segment_time = segment.min_time
                print(self.max_segment_time)
                self.highlight_curve.setData([], [])
                self.refresh_gui_and_graph()
                event.accept()
                return

        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = VoltageControlGUI()
    window.show()
    sys.exit(app.exec())