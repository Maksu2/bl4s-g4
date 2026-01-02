import sys
import subprocess
import os
import re
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QCheckBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTextEdit, QMessageBox, QFrame,
                             QStyleFactory)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

class SimulationWorker(QThread):
    progress_signal = pyqtSignal(int, str) # row_index, status
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.is_running = True

    def run(self):
        self.log_signal.emit("--- Starting Batch Execution ---")
        
        for i, task in enumerate(self.queue):
            if not self.is_running: break
            if task["status"] == "Done": continue
            
            self.progress_signal.emit(i, "Running...")
            self.log_signal.emit(f"Processing #{task['id']} (E={task['energy']}, Th={task['thickness']})...")
            
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
                # Capture output
                result = subprocess.run(["./build/GeantSim", mac_filename], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.log_signal.emit(f"Error in #{task['id']}: {result.stderr}")
                    self.progress_signal.emit(i, "Error")
                    continue
                
                # Parse output
                match = re.search(r"Results written to '(.*\.csv)'", result.stdout)
                if match:
                    csv_file = match.group(1)
                    self.log_signal.emit(f"  -> Generated: {csv_file}")
                    
                    # 3. Visualization
                    if task["svg"]:
                        cmd = [
                            "python3", "visualize_results.py", 
                            csv_file,
                            "--energy", task["energy"],
                            "--electrons", task["electrons"],
                            "--thickness", task["thickness"]
                        ]
                        subprocess.run(cmd, check=True)
                        self.log_signal.emit(f"  -> SVG created.")
                    
                    self.progress_signal.emit(i, "Done")
                    task["status"] = "Done"
                else:
                    self.log_signal.emit("  -> Warning: Could not find output filename.")
                    self.progress_signal.emit(i, "Unknown")
                    
            except Exception as e:
                self.log_signal.emit(f"Exception in #{task['id']}: {e}")
                self.progress_signal.emit(i, "Failed")
        
        if os.path.exists("temp_queue_run.mac"):
            os.remove("temp_queue_run.mac")
            
        self.log_signal.emit("--- All Tasks Completed ---")
        self.finished_signal.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Geant4 Simulation Manager")
        self.setGeometry(100, 100, 750, 800)
        
        # Apply Fusion Style (base for good custom styling)
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        
        # --- Dark Palette Setup ---
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(dark_palette)
        
        # --- Custom Stylesheet ---
        self.setStyleSheet("""
            QWidget { 
                font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 14px;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 6px;
                margin-top: 20px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #ccc;
            }
            QLineEdit { 
                padding: 8px; 
                border: 1px solid #555; 
                border-radius: 4px; 
                background: #333; 
                color: #eee;
                selection-background-color: #007AFF;
            }
            QLineEdit:focus { border: 1px solid #007AFF; }
            QPushButton {
                background-color: #0d6efd; 
                color: white; 
                border-radius: 6px; 
                padding: 10px 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #0b5ed7; }
            QPushButton:pressed { background-color: #0a58ca; }
            QPushButton:disabled { background-color: #555; color: #888; }
            
            QTableWidget {
                border: none;
                background-color: #2d2d2d;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #333;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #007AFF;
                color: white;
                font-weight: bold;
            }
            QTableWidget::item { padding: 5px; }
            
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 4px;
                color: #ddd;
                font-family: 'Courier New', Courier, monospace;
            }
            QLabel { color: #eee; }
        """)

        self.queue = []
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # --- Header ---
        lbl_title = QLabel("Geant4 Simulation Manager")
        lbl_title.setFont(QFont("Helvetica", 24, QFont.Bold))
        lbl_title.setStyleSheet("color: white; margin-bottom: 10px;")
        main_layout.addWidget(lbl_title)
        
        # --- Input Section ---
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: #383838; border-radius: 8px;")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 20, 20, 20)
        
        # Form Grid
        grid_layout = QHBoxLayout()
        
        # Column 1
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Number of Electrons:"))
        self.entry_electrons = QLineEdit("1000")
        v1.addWidget(self.entry_electrons)
        grid_layout.addLayout(v1)
        
        # Column 2
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Beam Energy:"))
        self.entry_energy = QLineEdit("1 GeV")
        v2.addWidget(self.entry_energy)
        grid_layout.addLayout(v2)
        
        # Column 3
        v3 = QVBoxLayout()
        v3.addWidget(QLabel("Lead Thickness:"))
        self.entry_thickness = QLineEdit("1 cm")
        v3.addWidget(self.entry_thickness)
        grid_layout.addLayout(v3)
        
        input_layout.addLayout(grid_layout)
        
        # Row 2 (Checkbox + Button)
        h_bottom = QHBoxLayout()
        self.chk_svg = QCheckBox("Generate SVG Visualization")
        self.chk_svg.setChecked(True)
        self.chk_svg.setStyleSheet("QCheckBox { color: #ccc; spacing: 5px; } QCheckBox::indicator { width: 18px; height: 18px; }")
        h_bottom.addWidget(self.chk_svg)
        
        h_bottom.addStretch()
        
        btn_add = QPushButton("+ Add to Queue")
        btn_add.setStyleSheet("""
            background-color: #198754; 
            padding: 8px 24px;
        """) # Green for add
        btn_add.clicked.connect(self.add_to_queue)
        h_bottom.addWidget(btn_add)
        
        input_layout.addLayout(h_bottom)
        main_layout.addWidget(input_frame)
        
        # --- Queue Section ---
        queue_label = QLabel("Execution Queue")
        queue_label.setFont(QFont("Helvetica", 14, QFont.Bold))
        queue_label.setStyleSheet("margin-top: 10px;")
        main_layout.addWidget(queue_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Energy", "Electrons", "Thickness", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table)
        
        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        
        btn_clear = QPushButton("Clear Queue")
        btn_clear.setStyleSheet("background-color: #dc3545;") # Red
        btn_clear.clicked.connect(self.clear_queue)
        btn_layout.addWidget(btn_clear)
        
        btn_layout.addStretch()
        
        self.btn_run = QPushButton("RUN QUEUE")
        self.btn_run.setFont(QFont("Helvetica", 12, QFont.Bold))
        # Blue is default from global style
        self.btn_run.clicked.connect(self.run_queue)
        btn_layout.addWidget(self.btn_run)
        
        main_layout.addLayout(btn_layout)
        
        # --- Log Section ---
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setFixedHeight(120)
        self.text_log.setPlaceholderText("Execution log will appear here...")
        main_layout.addWidget(self.text_log)

    def log(self, text):
        self.text_log.append(text)
        self.text_log.verticalScrollBar().setValue(self.text_log.verticalScrollBar().maximum())

    def add_to_queue(self):
        e = self.entry_electrons.text()
        en = self.entry_energy.text()
        th = self.entry_thickness.text()
        
        if not e or not en or not th:
            QMessageBox.warning(self, "Missing Info", "Please fill all fields")
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
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(task_id)))
        self.table.setItem(row, 1, QTableWidgetItem(en))
        self.table.setItem(row, 2, QTableWidgetItem(e))
        self.table.setItem(row, 3, QTableWidgetItem(th))
        self.table.setItem(row, 4, QTableWidgetItem("Pending"))
        
        # Center align items
        for c in range(5):
            self.table.item(row, c).setTextAlignment(Qt.AlignCenter)
        
        self.log(f"Queue added: ID {task_id}")

    def clear_queue(self):
        self.queue = []
        self.table.setRowCount(0)
        self.log("Queue cleared.")

    def run_queue(self):
        if not self.queue:
            QMessageBox.information(self, "Empty", "Queue is empty!")
            return
            
        self.btn_run.setEnabled(False)
        self.worker = SimulationWorker(self.queue)
        self.worker.progress_signal.connect(self.update_status)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def update_status(self, row, status):
        item = self.table.item(row, 4)
        item.setText(status)
        
        # Color coding
        if status == "Running...": 
            item.setForeground(QColor("#0d6efd")) # Blue
        elif status == "Done": 
            item.setForeground(QColor("#198754")) # Green
        elif status == "Error" or status == "Failed": 
            item.setForeground(QColor("#dc3545")) # Red
        else:
            item.setForeground(QColor("white"))

    def on_finished(self):
        self.btn_run.setEnabled(True)
        QMessageBox.information(self, "Finished", "Batch processing execution completed.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
