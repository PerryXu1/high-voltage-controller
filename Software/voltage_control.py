import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QVBoxLayout, QListWidget, QLabel, QAbstractItemView)
import pyqtgraph as pg
from dialogs import (ConstantDialog, LinearDialog, SineDialog, QuadraticDialog, ExponentialDialog,
                     ExponentialAsymptoteDialog, LogarithmicDialog, CustomDialog)

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

    def on_available_item_clicked(self, item):
        function_name = item.text()
        
        prev_voltage = 0.0
        
        if function_name == "Constant":
            dlg = ConstantDialog(previous_v_end=prev_voltage, parent=self)
        elif function_name == "Linear":
            dlg = LinearDialog(previous_v_end=prev_voltage, parent=self)
        elif function_name == "Sine":
            dlg = SineDialog(previous_v_end=prev_voltage, parent=self)
        elif function_name == "Quadratic":
            dlg = QuadraticDialog(previous_v_end=prev_voltage, parent=self)
        elif function_name == "Exponential":
            dlg = ExponentialDialog(previous_v_end=prev_voltage, parent=self)
        elif function_name == "Exponential Asymptote":
            dlg = ExponentialAsymptoteDialog(previous_v_end=prev_voltage, parent=self)
        elif function_name == "Logarithmic":
            dlg = LogarithmicDialog(previous_v_end=prev_voltage, parent=self)
        elif function_name == "Custom":
            dlg = CustomDialog(previous_v_end=prev_voltage, parent=self)
        else:
            print("Dialog not implemented yet for this function.")
            self.available_functions_list.clearSelection()
            return
            
        if dlg.exec():
            self.active_functions_list.addItem(f"{function_name} Segment")
            
        self.available_functions_list.clearSelection()

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