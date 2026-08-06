import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QVBoxLayout, QListWidget, QLabel, QAbstractItemView)
import pyqtgraph as pg
from dialogs import (ConstantDialog, LinearDialog, SineDialog, QuadraticDialog, ExponentialDialog,
                     ExponentialAsymptoteDialog, LogarithmicDialog, CustomDialog)
from voltage_model import VoltageModel, SegmentType, Segment

class VoltageControlGUI(QMainWindow):
    """Class that creates and displays the voltage control GUI
    """
    
    _DEFAULT_MAX_VOLTAGE = 15000 # in volts
    _DEFAULT_MAX_TIME = 60 # in minutes
    _DEFAULT_WINDOW_WIDTH = 1200
    _DEFAULT_WINDOW_HEIGHT = 700
    
    
    
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
        
        # Components Column
        middle_layout = QVBoxLayout()
        middle_label = QLabel("Waveform Sequence")
        
        self.active_functions_list = QListWidget()
        self.active_functions_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        self.active_functions_list.itemDoubleClicked.connect(self.on_active_item_double_clicked)
        
        middle_layout.addWidget(middle_label)
        middle_layout.addWidget(self.active_functions_list)

        # Add Column
        right_layout = QVBoxLayout()
        right_label = QLabel("Available Functions")
        
        self.available_functions_list = QListWidget()
        
        functions = ["Constant", "Linear", "Quadratic", "Sine", "Exponential", "Exponential Asymptote", "Logarithmic", "Custom"]
        self.available_functions_list.addItems(functions)
        
        self.available_functions_list.itemClicked.connect(self.on_available_item_clicked)
        
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.available_functions_list)

        # Layout
        main_layout.addWidget(self.plot_widget, stretch=6)
        main_layout.addLayout(middle_layout, stretch=2)
        main_layout.addLayout(right_layout, stretch=1)
        
        self.voltage_model = VoltageModel()
        
        self.plot_line = self.plot_widget.plot([], [], pen=pg.mkPen('b', width=2))
        
        self.max_time = 60.0
        self.step_size = 0.1

    def on_available_item_clicked(self, item):
        function_name = item.text()

        # Map display string to SegmentType Enum & Dialog Class
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
            print(f"Dialog not implemented yet for {function_name}")
            self.available_functions_list.clearSelection()
            return

        seg_type, dialog_class = dialog_map[function_name]

        # 1. Fetch ending voltage from the model for seamless matching
        prev_voltage = self.voltage_model.get_voltage(self.max_time)

        # 2. Instantiate and run dialog
        dlg = dialog_class(previous_v_end=prev_voltage, max_time=self.max_time, parent=self)

        if dlg.exec():
            # 3. Extract parameters and build the Segment dataclass instance
            segment = self.extract_segment(seg_type, dlg)

            if segment:
                # 4. Add to the voltage model (handles priority & trimming automatically)
                self.voltage_model.add_segment(segment)

                # 5. Refresh the GUI segment list and redraw plot
                self.refresh_gui_and_graph()

        self.available_functions_list.clearSelection()

    def extract_segment(self, seg_type: SegmentType, dlg) -> Segment:
        """Extracts timing and equation parameters from a dialog into a Segment."""
        min_time = dlg.t_min_input.value()
        max_time = dlg.t_max_input.value()
        params = []

        if seg_type == SegmentType.CONSTANT:
            params = [dlg.param_a.value()]

        elif seg_type == SegmentType.LINEAR:
            params = [dlg.param_a.value(), dlg.param_b.value()]

        elif seg_type == SegmentType.QUADRATIC:
            params = [dlg.param_a.value(), dlg.param_b.value(), dlg.param_c.value()]

        elif seg_type == SegmentType.SINE:
            # Pass 0.0 for Sine, 1.0 for Cosine
            is_cos = 1.0 if dlg.trig_choice.currentText() == "Cosine" else 0.0
            params = [
                dlg.param_a.value(), 
                dlg.param_b.value(), 
                dlg.param_c.value(), 
                dlg.param_d.value(), 
                is_cos
            ]

        elif seg_type == SegmentType.EXPONENTIAL:
            params = [dlg.param_a.value(), dlg.param_k.value(), dlg.param_c.value()]

        elif seg_type == SegmentType.EXPONENTIAL_ASYMPTOTE:
            params = [dlg.param_a.value(), dlg.param_tau.value(), dlg.param_c.value()]

        elif seg_type == SegmentType.LOGARITHM:
            params = [
                dlg.param_a.value(), 
                dlg.get_effective_base(), 
                dlg.param_h.value(), 
                dlg.param_k.value()
            ]

        elif seg_type == SegmentType.CUSTOM:
            # Stores vertical offset shift
            params = [dlg.param_offset.value()]
            # Note: For custom string expressions, store the formula directly onto the segment
            seg = Segment(seg_type, min_time, max_time, params)
            seg.expression = dlg.expr_input.text()
            return seg

        return Segment(seg_type, min_time, max_time, params)

    def refresh_gui_and_graph(self):
        """Syncs the GUI segment list with the model and updates the graph."""
        # Clear and rebuild list from self.voltage_model.segments
        # (This ensures trimmed/modified segments are accurately reflected)
        self.active_functions_list.clear()

        for seg in self.voltage_model.segments:
            name = seg.segment_type.name.capitalize().replace("_", " ")
            self.active_functions_list.addItem(
                f"{name} ({seg.min_time:.1f} to {seg.max_time:.1f})"
            )

        # Fetch uniform sample arrays from model and update PyQTGraph plot
        t_data, v_data = self.voltage_model.generate_plot_data(
            max_time=self.max_time, 
            step_size=self.step_size
        )
        self.plot_curve.setData(t_data, v_data)

    def on_active_item_double_clicked(self, item):
        """
        Triggered when a user double-clicks an existing function in the middle column.
        """
        
        print(f"[Action] Opening Pop-up to edit properties of: {item.text()}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    app.setStyle("Fusion") 
    
    window = VoltageControlGUI()
    window.show()
    sys.exit(app.exec())