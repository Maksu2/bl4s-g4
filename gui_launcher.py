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
    progress_signal = pyqtSignal(int, str) 
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.is_running = True

    def run(self):
        self.log_signal.emit(">>> BATCH EXECUTION STARTED")
        
        for i, task in enumerate(self.queue):
            if not self.is_running: break
            if task["status"] == "DONE": continue
            
            self.progress_signal.emit(i, "RUNNING")
            self.log_signal.emit(f"PROCESSING TASK #{task['id']} [E={task['energy']} | Th={task['thickness']}]")
            
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
                    self.log_signal.emit(f"[ERROR] Task #{task['id']}: {result.stderr}")
                    self.progress_signal.emit(i, "ERROR")
                    continue
                
                # Parse output
                match = re.search(r"Results written to '(.*\.csv)'", result.stdout)
                if match:
                    csv_file = match.group(1)
                    self.log_signal.emit(f"   -> Output: {csv_file}")
                    
                    if task["svg"]:
                        cmd = [
                            "python3", "visualize_results.py", 
                            csv_file,
                            "--energy", task["energy"],
                            "--electrons", task["electrons"],
                            "--thickness", task["thickness"]
                        ]
                        subprocess.run(cmd, check=True)
                        self.log_signal.emit(f"   -> Visualization generated.")
                    
                    self.progress_signal.emit(i, "DONE")
                    task["status"] = "DONE"
                else:
                    self.log_signal.emit("   -> Warning: Output filename not detected.")
                    self.progress_signal.emit(i, "UNKNOWN")
                    
            except Exception as e:
                self.log_signal.emit(f"[EXCEPTION] Task #{task['id']}: {e}")
                self.progress_signal.emit(i, "FAILED")
        
        if os.path.exists("temp_queue_run.mac"):
            os.remove("temp_queue_run.mac")
            
        self.log_signal.emit(">>> BATCH EXECUTION FINISHED")
        self.finished_signal.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Geant4 Simulation Manager")
        self.setGeometry(100, 100, 900, 700)
        
        # --- Deep Graphite Technical Theme ---
        # Palette:
        # Background: #1E1E1E (Deep Graphite)
        # Panels: #252526 (Lighter Anthracite)
        # Accent: #007ACC (Technical Blue) or #4CC9F0 (Cyan). Let's use a calm Technical Blue: #3ca9e2
        # Text: #CCCCCC (Readable Grey)
        # Inputs: #333333
        
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #CCCCCC;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
                font-size: 13px;
            }
            
            /* HEADERS */
            QLabel#Header {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: 600;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
            }
            
            QLabel#Label {
                color: #AAAAAA;
                font-weight: 500;
            }

            /* PANELS */
            QFrame#Panel {
                background-color: #252526;
                border: none;
                border-radius: 4px;
            }

            /* INPUTS */
            QLineEdit {
                background-color: #333333;
                border: 1px solid #3E3E3E;
                border-radius: 2px;
                padding: 8px;
                color: #FFFFFF;
                font-family: 'Consolas', 'Courier New', monospace; 
            }
            QLineEdit:focus {
                border: 1px solid #3ca9e2;
                background-color: #383838;
            }

            /* BUTTONS - Flat, No Shadows */
            QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: none;
                border-radius: 2px;
                padding: 8px 16px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #3E3E3E;
                color: #3ca9e2; /* Text glow on hover */
            }
            QPushButton:pressed {
                background-color: #2D2D2D;
            }
            
            QPushButton#AccentButton {
                background-color: #3ca9e2;
                color: #1E1E1E;
            }
            QPushButton#AccentButton:hover {
                background-color: #4db8f0;
            }
            
            QPushButton#DangerButton {
                color: #bd4848;
                background-color: transparent;
                border: 1px solid #bd4848;
            }
            QPushButton#DangerButton:hover {
                background-color: #bd4848;
                color: white;
            }

            /* TABLE */
            QTableWidget {
                background-color: #252526;
                border: none;
                gridline-color: #333333;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #CCCCCC;
                border: none;
                padding: 8px;
                font-weight: 600;
                text-transform: uppercase;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #2D2D2D;
            }
            QTableWidget::item:selected {
                background-color: #3ca9e2;
                color: #1E1E1E;
            }

            /* CHECKBOX */
            QCheckBox {
                spacing: 8px;
                color: #AAAAAA;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background: #333333;
                border: 1px solid #3E3E3E;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #3ca9e2;
                border: 1px solid #3ca9e2;
            }

            /* SCROLLBAR */
            QScrollBar:vertical {
                border: none;
                background: #252526;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                min-height: 20px;
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            /* LOG */
            QTextEdit {
                background-color: #1A1A1A;
                border: 1px solid #333333;
                color: #888888;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)

        self.queue = []
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main Layout (Grid-based approach)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 1. HEADER
        header_layout = QHBoxLayout()
        title = QLabel("GEANT4 SIMULATION MANAGER")
        title.setObjectName("Header")
        header_layout.addWidget(title)
        
        status_badge = QLabel("v2.0 • READY")
        status_badge.setStyleSheet("color: #3ca9e2; font-family: 'Consolas'; font-size: 11px;")
        header_layout.addStretch()
        header_layout.addWidget(status_badge)
        
        main_layout.addLayout(header_layout)

        # 2. CONFIG PANEL
        config_panel = QFrame()
        config_panel.setObjectName("Panel")
        config_layout = QHBoxLayout(config_panel)
        config_layout.setContentsMargins(20, 20, 20, 20)
        config_layout.setSpacing(30) # Airy spacing

        # Col 1: Electrons
        v1 = QVBoxLayout()
        l1 = QLabel("PARTICLE COUNT")
        l1.setObjectName("Label")
        self.entry_electrons = QLineEdit("1000")
        v1.addWidget(l1)
        v1.addWidget(self.entry_electrons)
        config_layout.addLayout(v1)
        
        # Col 2: Energy
        v2 = QVBoxLayout()
        l2 = QLabel("BEAM ENERGY")
        l2.setObjectName("Label")
        self.entry_energy = QLineEdit("1 GeV")
        v2.addWidget(l2)
        v2.addWidget(self.entry_energy)
        config_layout.addLayout(v2)
        
        # Col 3: Thickness
        v3 = QVBoxLayout()
        l3 = QLabel("TARGET THICKNESS")
        l3.setObjectName("Label")
        self.entry_thickness = QLineEdit("1 cm")
        v3.addWidget(l3)
        v3.addWidget(self.entry_thickness)
        config_layout.addLayout(v3)
        
        # Col 4: Action
        v4 = QVBoxLayout()
        self.chk_svg = QCheckBox("GENERATE SVG")
        self.chk_svg.setChecked(True)
        
        btn_add = QPushButton("ADD TO QUEUE")
        btn_add.setObjectName("AccentButton")
        btn_add.clicked.connect(self.add_to_queue)
        
        v4.addWidget(self.chk_svg)
        v4.addWidget(btn_add)
        v4.setAlignment(Qt.AlignBottom)
        config_layout.addLayout(v4)
        
        main_layout.addWidget(config_panel)

        # 3. QUEUE LIST
        queue_header = QHBoxLayout()
        q_title = QLabel("EXECUTION QUEUE")
        q_title.setObjectName("Header")
        q_title.setStyleSheet("font-size: 14px; margin-top: 10px;")
        
        btn_clear = QPushButton("CLEAR ALL")
        btn_clear.setObjectName("DangerButton")
        btn_clear.setFixedWidth(100)
        btn_clear.clicked.connect(self.clear_queue)
        
        queue_header.addWidget(q_title)
        queue_header.addStretch()
        queue_header.addWidget(btn_clear)
        main_layout.addLayout(queue_header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "ENERGY", "PARTICLES", "THICKNESS", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False) # Cleaner look
        self.table.setFocusPolicy(Qt.NoFocus)
        main_layout.addWidget(self.table)

        # 4. FOOTER / LOGS
        footer_layout = QHBoxLayout()
        
        # Run Button (Large)
        self.btn_run = QPushButton("INITIALIZE & RUN BATCH")
        self.btn_run.setObjectName("AccentButton")
        self.btn_run.setFixedHeight(40)
        self.btn_run.clicked.connect(self.run_queue)
        
        footer_layout.addWidget(self.btn_run)
        main_layout.addLayout(footer_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(100)
        self.log_text.setPlaceholderText("> System Ready. Awaiting commands...")
        self.log_text.setFrameShape(QFrame.NoFrame)
        main_layout.addWidget(self.log_text)

    def log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def add_to_queue(self):
        e = self.entry_electrons.text()
        en = self.entry_energy.text()
        th = self.entry_thickness.text()
        
        if not e or not en or not th:
            return
            
        task_id = len(self.queue) + 1
        task = {
            "id": task_id,
            "electrons": e,
            "energy": en,
            "thickness": th,
            "svg": self.chk_svg.isChecked(),
            "status": "PENDING"
        }
        self.queue.append(task)
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Helper to create clean items
        def make_item(text, align=Qt.AlignCenter):
            it = QTableWidgetItem(str(text))
            it.setTextAlignment(align)
            return it
            
        self.table.setItem(row, 0, make_item(f"{task_id:03d}"))
        self.table.setItem(row, 1, make_item(en))
        self.table.setItem(row, 2, make_item(e))
        self.table.setItem(row, 3, make_item(th))
        
        status_item = make_item("PENDING")
        status_item.setForeground(QColor("#777777"))
        self.table.setItem(row, 4, status_item)
        
        self.log(f"> Task #{task_id:03d} added to queue.")

    def clear_queue(self):
        self.queue = []
        self.table.setRowCount(0)
        self.log("> Queue cleared.")

    def run_queue(self):
        if not self.queue:
            QMessageBox.information(self, "Queue Empty", "Please add tasks to the queue first.")
            return
            
        self.btn_run.setEnabled(False)
        self.btn_run.setText("PROCESSING...")
        self.btn_run.setStyleSheet("background-color: #444; color: #888;")
        
        self.worker = SimulationWorker(self.queue)
        self.worker.progress_signal.connect(self.update_status)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def update_status(self, row, status):
        item = self.table.item(row, 4)
        item.setText(status)
        
        if status == "RUNNING": 
            item.setForeground(QColor("#3ca9e2"))
        elif status == "DONE": 
            item.setForeground(QColor("#58D68D")) # Tech Green
        elif status == "ERROR" or status == "FAILED": 
            item.setForeground(QColor("#bd4848")) # Muted Red
        else:
            item.setForeground(QColor("#777777"))

    def on_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("INITIALIZE & RUN BATCH")
        self.btn_run.setStyleSheet("") # Reset to style sheet default
        QMessageBox.information(self, "Sequence Complete", "All tasks in the queue have been processed.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
