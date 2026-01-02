import sys
import subprocess
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFrame,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont, QPalette, QIcon

# ==================================================
# Worker Thread
# ==================================================
class SimulationWorker(QThread):
    progress = pyqtSignal(int, str)
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.is_running = True

    def run(self):
        self.log.emit("🚀 Batch Sequence Started")
        
        for i, task in enumerate(self.queue):
            if not self.is_running: break
            
            self.progress.emit(i, "Running...")
            
            task_id = task['id']
            # Prepare macro
            mac = f"""
/det/setLeadThickness {task['thickness']}
/run/initialize
/gun/particle e-
/gun/energy {task['energy']}
/run/beamOn {task['electrons']}
"""
            mac_file = f"temp_task_{task_id}.mac"
            with open(mac_file, "w") as f:
                f.write(mac)

            try:
                # Run Simulation
                result = subprocess.run(
                    ["./build/GeantSim", mac_file],
                    capture_output=True, text=True
                )

                if result.returncode != 0:
                    self.progress.emit(i, "Failed")
                    self.log.emit(f"❌ Task #{task_id} Error:\n{result.stderr}")
                    continue

                # Parse filename - flexible regex
                # Look for "Results written to 'filename'" NOT constrained by start of line
                stdout = result.stdout
                # Debug: print first 50 chars of stdout to see if it's there
                # self.log.emit(f"Debug output: {stdout[:100]}...") 
                
                match = re.search(r"Results written to\s+['\"](.*?)['\"]", stdout)
                
                if match:
                    csv_filename = match.group(1)
                    self.log.emit(f"✅ Generated: {csv_filename}")
                    
                    if task["svg"]:
                        cmd = [
                            "python3", "visualize_results.py", 
                            csv_filename,
                            "--energy", task["energy"],
                            "--electrons", task["electrons"],
                            "--thickness", task["thickness"]
                        ]
                        subprocess.run(cmd, check=True)
                        self.log.emit("   ↳ Viz Rendered")
                    
                    self.progress.emit(i, "Done")
                else:
                    self.log.emit(f"⚠️  Parsing Failed. Raw output snippet:\n{stdout[-100:]}")
                    self.progress.emit(i, "Unknown")

            except Exception as e:
                self.progress.emit(i, "Error")
                self.log.emit(f"💥 Exception: {str(e)}")
                
            finally:
                if os.path.exists(mac_file):
                    os.remove(mac_file)

        self.log.emit("🏁 Sequence Complete")
        self.finished.emit()

    def stop(self):
        self.is_running = False

# ==================================================
# Main Window
# ==================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.queue = []
        self.worker = None

        self.setWindowTitle("Simulation Dashboard Pro")
        self.resize(1150, 800)
        
        # --- Theme: Cyber-Tailwind ---
        # Darker Backgrounds, Neon Accents, High Contrast Text
        self.setStyleSheet("""
        QMainWindow {
            background-color: #0B1120; /* Deep Navy/Black */
        }
        
        QWidget {
            color: #E2E8F0;
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
        }

        /* TYPOGRAPHY */
        QLabel.title {
            font-size: 28px;
            font-weight: 800;
            color: #38BDF8; /* Sky 400 */
            letter-spacing: -0.5px;
        }

        QLabel.subtitle {
            font-size: 13px;
            color: #94A3B8; /* Slate 400 */
            font-weight: 500;
        }
        
        QLabel.section-header {
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 1.2px;
            color: #06B6D4; /* Cyan 500 - Neon accent */
            margin-bottom: 8px;
        }

        /* CARDS */
        QFrame.card {
            background-color: #1E293B; /* Slate 800 */
            border: 1px solid #334155;
            border-radius: 16px;
        }

        /* INPUTS */
        QLineEdit {
            background-color: #0F172A; /* Slate 900 */
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
            color: #F8FAFC;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-weight: 500;
        }
        QLineEdit:focus {
            border: 1px solid #38BDF8; /* Sky 400 */
            background-color: #172033;
        }

        /* CHECKBOX */
        QCheckBox {
            color: #CBD5E1;
            font-weight: 500;
            spacing: 12px;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 6px;
            border: 2px solid #475569;
            background-color: #0F172A;
        }
        QCheckBox::indicator:checked {
            background-color: #38BDF8;
            border-color: #38BDF8;
        }

        /* BUTTONS */
        QPushButton {
            background-color: #334155;
            border: none;
            border-radius: 10px;
            padding: 12px 24px;
            color: #F8FAFC;
            font-weight: 600;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #475569;
        }
        QPushButton:pressed {
            background-color: #1E293B;
            padding-top: 14px; /* tactile effect */
        }

        QPushButton.primary {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0EA5E9, stop:1 #6366F1); /* Sky to Indigo */
            color: white;
            border: 1px solid rgba(255,255,255,0.1);
        }
        QPushButton.primary:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #4F46E5);
        }

        /* TABLE */
        QTableWidget {
            background-color: transparent;
            border: none;
            gridline-color: #334155;
        }
        QHeaderView::section {
            background-color: #1E293B; /* Match card bg */
            color: #38BDF8; /* Neon Blue text for headers */
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 11px;
            border: none;
            border-bottom: 2px solid #334155; /* Strong separator */
            padding: 12px 8px;
            text-align: left;
        }
        QTableWidget::item {
            padding: 12px 8px;
            border-bottom: 1px solid #334155;
            color: #E2E8F0;
        }
        QTableWidget::item:selected {
            background-color: rgba(56, 189, 248, 0.1); /* Sky 400 with opacity */
            color: #FFF;
        }

        /* LOG */
        QTextEdit {
            background-color: #0F172A;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px;
            color: #94A3B8;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 12px;
            line-height: 1.5;
        }
        
        QScrollBar:vertical {
            background: transparent;
            width: 8px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #475569;
            border-radius: 4px;
            min-height: 30px;
        }
        QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
            height: 0px;
        }
        """)

        self.build_ui()

    # ==================================================
    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        main = QVBoxLayout(root)
        main.setContentsMargins(40, 40, 40, 40)
        main.setSpacing(32)

        # Header
        header = QHBoxLayout()
        v_head = QVBoxLayout()
        v_head.setSpacing(4)
        
        title = QLabel("SIMULATION DASHBOARD")
        title.setProperty("class", "title")
        
        sub = QLabel("Geant4 Control Center • v3.0 • Cyber Edition")
        sub.setProperty("class", "subtitle")
        
        v_head.addWidget(title)
        v_head.addWidget(sub)
        
        header.addLayout(v_head)
        header.addStretch()
        
        # Status pill (Visual only)
        status = QLabel("● SYSTEM READY")
        status.setStyleSheet("color: #4ADE80; font-weight: 700; font-size: 11px; background: rgba(74, 222, 128, 0.1); padding: 8px 12px; border-radius: 20px;")
        header.addWidget(status)
        
        main.addLayout(header)

        # Content Area (2 Columns)
        content = QHBoxLayout()
        content.setSpacing(32)

        # Left Column: Configuration (Fixed Width)
        content.addWidget(self.build_config_card())
        
        # Right Column: Queue & Status
        content.addLayout(self.build_queue_section(), 1)
        
        main.addLayout(content, 1)

        # Footer LOG
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText(">> Awaiting command sequence...")
        self.log.setFixedHeight(140)
        main.addWidget(self.log)

    # ==================================================
    def build_config_card(self):
        card = QFrame()
        card.setProperty("class", "card")
        card.setFixedWidth(340)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(24)

        # Section Header
        lbl = QLabel("CONFIGURE PARAMETERS")
        lbl.setProperty("class", "section-header")
        layout.addWidget(lbl)

        # Inputs
        def add_input(label, default):
            vbox = QVBoxLayout()
            vbox.setSpacing(8)
            l = QLabel(label)
            l.setStyleSheet("color: #CBD5E1; font-weight: 600; font-size: 12px;")
            i = QLineEdit(default)
            vbox.addWidget(l)
            vbox.addWidget(i)
            layout.addLayout(vbox)
            return i

        self.input_electrons = add_input("Particle Count", "1000")
        self.input_energy = add_input("Beam Energy", "1 GeV")
        self.input_thickness = add_input("Target Thickness", "1 cm")

        layout.addSpacing(12)
        
        self.chk_svg = QCheckBox("Generate Visualization (SVG)")
        self.chk_svg.setChecked(True)
        layout.addWidget(self.chk_svg)

        layout.addStretch()

        btn_add = QPushButton("ADD TO QUEUE")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.add_to_queue)
        layout.addWidget(btn_add)

        return card

    # ==================================================
    def build_queue_section(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Header Row
        h = QHBoxLayout()
        lbl = QLabel("ACTIVE QUEUE")
        lbl.setProperty("class", "section-header")
        
        self.btn_run = QPushButton("INITIATE SEQUENCE")
        self.btn_run.setProperty("class", "primary")
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self.run_queue)
        self.btn_run.setFixedWidth(180)
        
        h.addWidget(lbl)
        h.addStretch()
        h.addWidget(self.btn_run)
        layout.addLayout(h)

        # Table Card
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "ENERGY", "PARTICLES", "THICKNESS", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setStyleSheet("padding: 10px; alternate-background-color: #1a2333;")
        self.table.setAlternatingRowColors(True)
        
        card_layout.addWidget(self.table)
        layout.addWidget(card)
        
        return layout

    # ==================================================
    def add_to_queue(self):
        e = self.input_electrons.text()
        en = self.input_energy.text()
        th = self.input_thickness.text()
        
        if not e or not en or not th: return

        task = {
            "id": len(self.queue) + 1,
            "electrons": e,
            "energy": en,
            "thickness": th,
            "svg": self.chk_svg.isChecked(),
            "status": "Waiting"
        }
        self.queue.append(task)

        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(f"#{task['id']}"))
        self.table.setItem(row, 1, QTableWidgetItem(en))
        self.table.setItem(row, 2, QTableWidgetItem(e))
        self.table.setItem(row, 3, QTableWidgetItem(th))
        
        status_item = QTableWidgetItem("Waiting")
        status_item.setForeground(QColor("#64748B")) # Slate 500
        status_item.setFont(QFont("Inter", 13, QFont.Bold))
        self.table.setItem(row, 4, status_item)

        self.log.append(f"➕ [QUEUE] Task #{task['id']} added")

    # ==================================================
    def run_queue(self):
        if not self.queue:
            return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("PROCESSING...")
        self.worker = SimulationWorker(self.queue)
        self.worker.progress.connect(self.update_status)
        self.worker.log.connect(self.log.append)
        self.worker.finished.connect(self.finish)
        self.worker.start()

    def update_status(self, row, status):
        item = self.table.item(row, 4)
        item.setText(status)

        colors = {
            "Processing...": "#38BDF8", # Sky 400
            "Done": "#4ADE80", # Green 400
            "Failed": "#F87171", # Red 400
            "Error": "#F87171",
            "Waiting": "#64748B"
        }
        color_code = colors.get(status, "#94A3B8")
        item.setForeground(QColor(color_code))
        
        if status == "Processing...":
             font = item.font()
             font.setBold(True)
             item.setFont(font)

    def finish(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("INITIATE SEQUENCE")
        self.log.append("--- SEQUENCE COMPLETED ---")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())