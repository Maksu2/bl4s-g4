import sys
import subprocess
import os
import re
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QCheckBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTextEdit, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

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
        self.setGeometry(100, 100, 700, 750)
        
        # Style
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f7; }
            QLabel { font-size: 13px; color: #333; }
            QLineEdit { 
                padding: 8px; border: 1px solid #ccc; border-radius: 6px; background: white;
            }
            QPushButton {
                background-color: #007AFF; color: white; border-radius: 6px; padding: 8px 16px;
                font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #0062cc; }
            QPushButton:disabled { background-color: #ccc; }
            QTableWidget {
                border: 1px solid #ddd; background: white; gridline-color: #eee;
                selection-background-color: #e3f2fd; selection-color: black;
            }
            QHeaderView::section {
                background-color: #f0f0f0; padding: 4px; border: none; font-weight: bold;
            }
        """)

        self.queue = []
        self.worker = None
        
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Inputs ---
        input_group = QFrame()
        input_group.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        input_layout = QVBoxLayout(input_group)
        
        title = QLabel("Simulation Parameters")
        title.setFont(QFont("Helvetica", 14, QFont.Bold))
        input_layout.addWidget(title)
        
        # Form
        grid = QVBoxLayout()
        
        # Row 1
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Electrons:"))
        self.entry_electrons = QLineEdit("1000")
        h1.addWidget(self.entry_electrons)
        grid.addLayout(h1)
        
        # Row 2
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Energy:"))
        self.entry_energy = QLineEdit("1 GeV")
        h2.addWidget(self.entry_energy)
        grid.addLayout(h2)
        
        # Row 3
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("Thickness:"))
        self.entry_thickness = QLineEdit("1 cm")
        h3.addWidget(self.entry_thickness)
        grid.addLayout(h3)
        
        # SVG Checkbox
        self.chk_svg = QCheckBox("Generate SVG Visualization")
        self.chk_svg.setChecked(True)
        grid.addWidget(self.chk_svg)
        
        input_layout.addLayout(grid)
        
        # Buttons
        h_btn = QHBoxLayout()
        btn_add = QPushButton("Add to Queue")
        btn_add.clicked.connect(self.add_to_queue)
        h_btn.addStretch()
        h_btn.addWidget(btn_add)
        input_layout.addLayout(h_btn)
        
        layout.addWidget(input_group)
        
        # --- Queue ---
        lbl_queue = QLabel("Execution Queue")
        lbl_queue.setFont(QFont("Helvetica", 12, QFont.Bold))
        layout.addWidget(lbl_queue)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Energy", "Electrons", "Thickness", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        btn_clear = QPushButton("Clear Queue")
        btn_clear.setStyleSheet("background-color: #FF3B30;")
        btn_clear.clicked.connect(self.clear_queue)
        
        self.btn_run = QPushButton("RUN QUEUE")
        self.btn_run.setStyleSheet("background-color: #34C759; padding: 10px;")
        self.btn_run.clicked.connect(self.run_queue)
        
        action_layout.addWidget(btn_clear)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_run)
        layout.addLayout(action_layout)
        
        # --- Log ---
        lbl_log = QLabel("Log Output")
        lbl_log.setFont(QFont("Helvetica", 11, QFont.Bold))
        layout.addWidget(lbl_log)
        
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setFixedHeight(120)
        self.text_log.setStyleSheet("font-family: Courier; font-size: 11px; background: #2d2d2d; color: #eee;")
        layout.addWidget(self.text_log)

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
        self.table.setItem(row, 4, QTableWidgetItem(status))
        # Color coding
        color = QColor(0, 0, 0) # Default black
        if status == "Running...": color = QColor("#007AFF")
        elif status == "Done": color = QColor("#34C759")
        elif status == "Error" or status == "Failed": color = QColor("#FF3B30")
        
        item = self.table.item(row, 4)
        item.setForeground(color)
        item.setFont(QFont("Helvetica", 10, QFont.Bold))

    def on_finished(self):
        self.btn_run.setEnabled(True)
        QMessageBox.information(self, "Finished", "Batch processing execution completed.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
