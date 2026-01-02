import sys
import subprocess
import os
import re
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QCheckBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTextEdit, QMessageBox, QFrame,
                             QStyleFactory, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

class SimulationWorker(QThread):
    progress_signal = pyqtSignal(int, str) 
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.is_running = True

    def run(self):
        self.log_signal.emit("Batch execution started.")
        
        for i, task in enumerate(self.queue):
            if not self.is_running: break
            if task["status"] == "Completed": continue
            
            self.progress_signal.emit(i, "Running...")
            self.log_signal.emit(f"Processing Task #{task['id']} (E={task['energy']}, Th={task['thickness']})")
            
            # 1. Create temporary macro
            mac_content = f"""
/det/setLeadThickness {task['thickness']}
/run/initialize
/gun/particle e-
/gun/energy {task['energy']}
/run/beamOn {task['electrons']}
"""
            mac_filename = "temp_queue_run.mac"
            with open(mac_filename, "w") as f:
                f.write(mac_content)
                
            # 2. Run Simulation
            try:
                result = subprocess.run(["./build/GeantSim", mac_filename], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.log_signal.emit(f"Error in task #{task['id']}: {result.stderr}")
                    self.progress_signal.emit(i, "Error")
                    continue
                
                # Parse output
                match = re.search(r"Results written to '(.*\.csv)'", result.stdout)
                if match:
                    csv_file = match.group(1)
                    self.log_signal.emit(f"  -> Generated: {csv_file}")
                    
                    if task["svg"]:
                        cmd = [
                            "python3", "visualize_results.py", 
                            csv_file,
                            "--energy", task["energy"],
                            "--electrons", task["electrons"],
                            "--thickness", task["thickness"]
                        ]
                        subprocess.run(cmd, check=True)
                        self.log_signal.emit(f"  -> Visualization created.")
                    
                    self.progress_signal.emit(i, "Completed")
                    task["status"] = "Completed"
                else:
                    self.log_signal.emit("  -> Warning: Output filename not detected.")
                    self.progress_signal.emit(i, "Unknown")
                    
            except Exception as e:
                self.log_signal.emit(f"Exception in task #{task['id']}: {e}")
                self.progress_signal.emit(i, "Failed")
        
        if os.path.exists("temp_queue_run.mac"):
            os.remove("temp_queue_run.mac")
            
        self.log_signal.emit("Batch processing finished.")
        self.finished_signal.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulation Manager")
        self.setGeometry(100, 100, 850, 700)
        
        # --- "Quiet Modern" Theme ---
        # Background: #181818 (Unified, dark, calm)
        # Accent: #E0E0E0 (Subtle white/grey for interactions) or a very desaturated blue
        # Text: #B0B0B0 (Soft grey, not harsh white)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #181818;
                color: #B0B0B0;
                font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
                font-size: 13px;
                font-weight: 300;
            }
            
            /* HEADERS */
            QLabel#Header {
                color: #E0E0E0;
                font-size: 16px;
                font-weight: 400;
                letter-spacing: 0.5px;
            }
            
            QLabel#SubHeader {
                color: #707070;
                font-size: 12px;
                font-weight: 400;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-top: 10px;
            }
            
            /* INPUT FIELDS - Minimalist */
            QLineEdit {
                background-color: transparent;
                border: none;
                border-bottom: 1px solid #333333;
                color: #E0E0E0;
                padding: 5px 0px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-bottom: 1px solid #606060;
                color: #FFFFFF;
            }
            QLabel#FieldLabel {
                color: #666666;
                font-size: 12px;
            }

            /* BUTTONS - Subtle, Ghost-like or Soft Fill */
            QPushButton {
                background-color: #222222;
                color: #B0B0B0;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2A2A2A;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #1F1F1F;
            }
            
            QPushButton#PrimaryButton {
                background-color: #E0E0E0; /* Soft White/Grey */
                color: #121212;
                font-weight: 500;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #FFFFFF;
            }
            
            QPushButton#TextButton {
                background-color: transparent;
                color: #666666;
                text-align: right;
            }
            QPushButton#TextButton:hover {
                color: #AA4444; /* Subtle danger hint only on hover */
            }

            /* TABLE - Clean, airy, no borders */
            QTableWidget {
                background-color: transparent;
                border: none;
                gridline-color: transparent;
            }
            QHeaderView::section {
                background-color: transparent;
                color: #555555;
                border: none;
                padding: 5px;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 1px;
                text-align: left;
            }
            QTableWidget::item {
                padding: 10px 5px;
                border-bottom: 1px solid #222222; /* Very subtle separator */
                color: #AAAAAA;
            }
            QTableWidget::item:selected {
                background-color: #1F1F1F;
                color: #FFFFFF;
            }

            /* CHECKBOX */
            QCheckBox {
                color: #666666;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #444444;
                border-radius: 2px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #606060;
                border-color: #606060;
            }

            /* LOG AREA */
            QTextEdit {
                background-color: transparent;
                border: none;
                border-top: 1px solid #222222;
                color: #666666;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                line-height: 1.5;
            }
            
            /* SCROLLBAR - Minimal */
             QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #333333;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.queue = []
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main Layout: Use plenty of whitespace
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(40)
        main_layout.setContentsMargins(60, 60, 60, 60)

        # 1. TOP SECTION: Header & Config
        top_layout = QHBoxLayout()
        top_layout.setSpacing(60)
        
        # Left: Title
        header_vbox = QVBoxLayout()
        title = QLabel("Simulation\nManager")
        title.setObjectName("Header")
        header_vbox.addWidget(title)
        
        # Spacer
        header_vbox.addStretch()
        top_layout.addLayout(header_vbox, 1) # Ratio 1

        # Right: Config Grid (Inputs)
        config_grid = QWidget()
        config_layout = QVBoxLayout(config_grid)
        config_layout.setContentsMargins(0,0,0,0)
        config_layout.setSpacing(25)
        
        # Input Rows
        row1 = QHBoxLayout() 
        self.entry_electrons = self.create_input("Particles", "1000")
        self.entry_energy = self.create_input("Energy", "1 GeV")
        row1.addWidget(self.entry_electrons)
        row1.addSpacing(30)
        row1.addWidget(self.entry_energy)
        
        row2 = QHBoxLayout()
        self.entry_thickness = self.create_input("Target Thickness", "1 cm")
        
        # Add Button (Aligned with input)
        btn_add = QPushButton("Add to Queue")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.add_to_queue)
        
        row2.addWidget(self.entry_thickness)
        row2.addSpacing(30)
        row2.addWidget(btn_add)
        
        config_layout.addLayout(row1)
        config_layout.addLayout(row2)
        
        # SVG Checkbox
        self.chk_svg = QCheckBox("Generate Visualization (SVG)")
        self.chk_svg.setChecked(True)
        config_layout.addWidget(self.chk_svg)

        top_layout.addWidget(config_grid, 3) # Ratio 3 (Wider)
        
        main_layout.addLayout(top_layout)

        # 2. MIDDLE SECTION: Queue List
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(15)
        
        # Header Row
        queue_header_layout = QHBoxLayout()
        lbl_queue = QLabel("Queue")
        lbl_queue.setObjectName("SubHeader")
        queue_header_layout.addWidget(lbl_queue)
        
        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("TextButton")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self.clear_queue)
        queue_header_layout.addWidget(btn_clear)
        
        middle_layout.addLayout(queue_header_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Energy", "Count", "Thickness", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setMinimumHeight(200)
        middle_layout.addWidget(self.table)
        
        main_layout.addLayout(middle_layout)

        # 3. BOTTOM SECTION: Actions & Log
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(40)
        
        # Log (Left side, subtle)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("System status...")
        bottom_layout.addWidget(self.log_text, 3)
        
        # Run Button (Right side, prominent)
        self.btn_run = QPushButton("Run Batch")
        self.btn_run.setObjectName("PrimaryButton")
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.setMinimumHeight(50)
        self.btn_run.clicked.connect(self.run_queue)
        bottom_layout.addWidget(self.btn_run, 1)
        
        main_layout.addLayout(bottom_layout)

    def create_input(self, label_text, default_val):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(5)
        
        lbl = QLabel(label_text)
        lbl.setObjectName("FieldLabel")
        layout.addWidget(lbl)
        
        entry = QLineEdit(default_val)
        layout.addWidget(entry)
        
        widget.entry = entry # Attach ref
        return widget 

    def add_to_queue(self):
        e = self.entry_electrons.entry.text()
        en = self.entry_energy.entry.text()
        th = self.entry_thickness.entry.text()
        
        if not e or not en or not th:
            return
            
        task_id = len(self.queue) + 1
        task = {
            "id": task_id,
            "electrons": e,
            "energy": en,
            "thickness": th,
            "svg": self.chk_svg.isChecked(),
            "status": "Pending"
        }
        self.queue.append(task)
        
        # Add to table
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        def make_item(text):
            it = QTableWidgetItem(str(text))
            it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            return it
            
        self.table.setItem(row, 0, make_item(f"{task_id:03d}"))
        self.table.setItem(row, 1, make_item(en))
        self.table.setItem(row, 2, make_item(e))
        self.table.setItem(row, 3, make_item(th))
        
        status_item = make_item("Pending")
        status_item.setForeground(QColor("#666666"))
        self.table.setItem(row, 4, status_item)
        
        self.log(f"Queued task #{task_id}")

    def clear_queue(self):
        self.queue = []
        self.table.setRowCount(0)
        self.log("Queue cleared")

    def run_queue(self):
        if not self.queue:
            return
            
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Processing...")
        
        self.worker = SimulationWorker(self.queue)
        self.worker.progress_signal.connect(self.update_status)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def update_status(self, row, status):
        item = self.table.item(row, 4)
        item.setText(status)
        
        if status == "Running...": 
            item.setForeground(QColor("#FFFFFF"))
        elif status == "Completed": 
            item.setForeground(QColor("#A0A0A0")) 
        elif status == "Error" or status == "Failed": 
            item.setForeground(QColor("#CC6666")) 
        else:
            item.setForeground(QColor("#666666"))

    def on_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Run Batch")
        self.log("Batch run complete.")

    def log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
