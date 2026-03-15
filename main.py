import sys
import subprocess
import os
import re
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFrame,
    QGraphicsDropShadowEffect, QSpinBox,
    QDoubleSpinBox, QRadioButton
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

    def __init__(self, queue, repeats):
        super().__init__()
        self.queue = queue
        self.repeats = repeats
        self.is_running = True

    def run(self):
        # 1. Create Main Batch Folder
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        main_folder = f"Results_Batch_{timestamp}"
        os.makedirs(main_folder, exist_ok=True)
        self.log.emit(f"📂 Output Directory: {main_folder}")
        self.log.emit(f"🔁 Batch Cycles: {self.repeats}")
        
        # Initialize summary.csv (semicolon-delimited for Excel)
        summary_path = os.path.join(main_folder, "summary.csv")
        with open(summary_path, 'w') as sf:
            sf.write("thickness_cm;total_hits\n")

        for run_idx in range(1, self.repeats + 1):
            if not self.is_running: break
            
            # 2. Create Run Subfolder
            run_folder = os.path.join(main_folder, f"run{run_idx}")
            os.makedirs(run_folder, exist_ok=True)
            self.log.emit(f" ▶ Starting Run {run_idx}/{self.repeats}")

            for i, task in enumerate(self.queue):
                if not self.is_running: break
                
                self.progress.emit(i, f"Run {run_idx}: Processing...")
                
                task_id = task['id']
                # Prepare macro
                # Use absolute path for safety or just current dir
                mac = f"""
/run/numberOfThreads {task.get('threads', 1)}
/det/setTargetMaterial {task.get('material', 'G4_Pb')}
/det/setTargetThickness {task['thickness']}
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
                        self.log.emit(f"❌ Run {run_idx} Task #{task_id} Error:\n{result.stderr}")
                        continue

                    # Parse filename
                    stdout = result.stdout
                    match = re.search(r"Results written to\s+['\"](.*?)['\"]", stdout)
                    
                    if match:
                        csv_filename = match.group(1)
                        
                        # Check total hits
                        total_hits = 0
                        try:
                            with open(csv_filename, 'r') as cf:
                                header = next(cf, None) # skip header
                                for line in cf:
                                    parts = line.strip().split(',')
                                    if len(parts) >= 3:
                                        total_hits += int(parts[2])
                        except Exception:
                            pass # default to keeping if read fails
                        
                        # Parse thickness value for summary
                        thickness_str = task['thickness']
                        thickness_cm = self._parse_thickness_to_cm(thickness_str)

                        if total_hits == 0:
                            self.log.emit(f"   🚫 Run {run_idx}: 0 Hits - Discarded")
                            if os.path.exists(csv_filename):
                                os.remove(csv_filename)
                            self.progress.emit(i, f"Run {run_idx}: 0 Hits")
                        else:
                            self.log.emit(f"   ✔ Generated: {csv_filename} ({total_hits} hits)")
                            
                            # Append metadata to CSV
                            with open(csv_filename, 'a') as cf:
                                cf.write(f"# METADATA: thickness={thickness_str}, total_hits={total_hits}\n")
                            
                            # Append to summary.csv
                            with open(summary_path, 'a') as sf:
                                sf.write(f"{thickness_cm:.4f};{total_hits}\n")
                            
                            # Generate SVG if requested
                            if task["svg"]:
                                cmd = [
                                    sys.executable, "visualize_results.py", 
                                    csv_filename,
                                    "--energy", task["energy"],
                                    "--electrons", task["electrons"],
                                    "--thickness", task["thickness"]
                                ]
                                subprocess.run(cmd, check=True)
                            
                            # Move Files to Run Folder
                            shutil.move(csv_filename, os.path.join(run_folder, csv_filename))
                            
                            svg_filename = csv_filename.replace(".csv", ".svg")
                            if os.path.exists(svg_filename):
                                 shutil.move(svg_filename, os.path.join(run_folder, svg_filename))
                            
                            self.progress.emit(i, f"Run {run_idx}: Done")
                    else:
                        self.log.emit(f"⚠️  Parsing Failed in Run {run_idx}.")
                        self.progress.emit(i, "Unknown")

                except Exception as e:
                    self.progress.emit(i, "Error")
                    self.log.emit(f"💥 Exception: {str(e)}")
                    
                finally:
                    if os.path.exists(mac_file):
                        os.remove(mac_file)

        self.log.emit(f"📊 Summary saved: {summary_path}")
        self.log.emit("🏁 All Sequences Completed")
        self.finished.emit()
    
    def _parse_thickness_to_cm(self, thickness_str):
        """Parse thickness string (e.g. '5 cm', '10 mm') to cm float."""
        import re as regex
        match = regex.match(r"([\d.]+)\s*(mm|cm|m)?", thickness_str.strip().lower())
        if match:
            value = float(match.group(1))
            unit = match.group(2) or 'cm'
            if unit == 'mm':
                return value / 10.0
            elif unit == 'm':
                return value * 100.0
            else:
                return value
        return 0.0

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
        self.resize(1150, 850)
        
        # --- Theme: Cyber-Tailwind ---
        self.setStyleSheet("""
        QMainWindow {
            background-color: #0B1120;
        }
        QWidget {
            color: #E2E8F0;
            font-family: 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', sans-serif;
            font-size: 13px;
        }
        /* TYPOGRAPHY */
        QLabel.title {
            font-size: 28px;
            font-weight: 800;
            color: #38BDF8;
            letter-spacing: -0.5px;
        }
        QLabel.subtitle {
            font-size: 13px;
            color: #94A3B8;
            font-weight: 500;
        }
        QLabel.section-header {
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 1.2px;
            color: #06B6D4;
            margin-bottom: 8px;
        }
        /* CARDS */
        QFrame.card {
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 16px;
        }
        /* INPUTS */
        QLineEdit, QSpinBox {
            background-color: #0F172A;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
            color: #F8FAFC;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-weight: 500;
        }
        QLineEdit:focus, QSpinBox:focus {
            border: 1px solid #38BDF8;
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
            padding-top: 14px;
        }
        QPushButton.primary {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0EA5E9, stop:1 #6366F1);
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
            background-color: #1E293B;
            color: #38BDF8;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 11px;
            border: none;
            border-bottom: 2px solid #334155;
            padding: 12px 8px;
            text-align: left;
        }
        QTableWidget::item {
            padding: 12px 8px;
            border-bottom: 1px solid #334155;
            color: #E2E8F0;
        }
        QTableWidget::item:selected {
            background-color: rgba(56, 189, 248, 0.1);
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
        
        sub = QLabel("Geant4 Control Center • v4.0 • Batch Pro")
        sub.setProperty("class", "subtitle")
        
        v_head.addWidget(title)
        v_head.addWidget(sub)
        
        header.addLayout(v_head)
        header.addStretch()
        
        status = QLabel("● SYSTEM READY")
        status.setStyleSheet("color: #4ADE80; font-weight: 700; font-size: 11px; background: rgba(74, 222, 128, 0.1); padding: 8px 12px; border-radius: 20px;")
        header.addWidget(status)
        
        main.addLayout(header)

        # Content Area
        content = QHBoxLayout()
        content.setSpacing(32)

        content.addWidget(self.build_config_card())
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
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(24)

        lbl = QLabel("CONFIGURE PARAMETERS")
        lbl.setProperty("class", "section-header")
        layout.addWidget(lbl)

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
        
        import multiprocessing
        cores = multiprocessing.cpu_count()
        self.input_threads = add_input("Threads", str(cores))

        # Add Material Selector
        mat_row = QHBoxLayout()
        mat_row.setSpacing(12)
        self.radio_pb = QRadioButton("Lead (Pb)")
        self.radio_pb.setChecked(True)
        self.radio_cu = QRadioButton("Copper (Cu)")
        
        mat_lbl = QLabel("Material:")
        mat_lbl.setStyleSheet("color: #CBD5E1; font-weight: 600; font-size: 12px;")
        mat_row.addWidget(mat_lbl)
        mat_row.addWidget(self.radio_pb)
        mat_row.addWidget(self.radio_cu)
        mat_row.addStretch()
        layout.addLayout(mat_row)

        layout.addSpacing(12)
        
        self.chk_svg = QCheckBox("Generate Visualization (SVG)")
        self.chk_svg.setChecked(True)
        layout.addWidget(self.chk_svg)

        btn_add = QPushButton("ADD TO QUEUE")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.add_to_queue)
        layout.addWidget(btn_add)
        
        # ========== QUICK BATCH GENERATOR ==========
        layout.addSpacing(16)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #334155; max-height: 1px;")
        layout.addWidget(sep)
        
        layout.addSpacing(8)
        
        lbl_gen = QLabel("QUICK BATCH GENERATOR")
        lbl_gen.setProperty("class", "section-header")
        lbl_gen.setStyleSheet("color: #A78BFA; font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 1.2px;")
        layout.addWidget(lbl_gen)
        
        # Range inputs row
        range_row = QHBoxLayout()
        range_row.setSpacing(8)
        
        self.spin_from = QDoubleSpinBox()
        self.spin_from.setRange(0.1, 1000)
        self.spin_from.setValue(1)
        self.spin_from.setDecimals(1)
        self.spin_from.setPrefix("Od: ")
        self.spin_from.setFixedWidth(90)
        
        self.spin_to = QDoubleSpinBox()
        self.spin_to.setRange(0.1, 1000)
        self.spin_to.setValue(10)
        self.spin_to.setDecimals(1)
        self.spin_to.setPrefix("Do: ")
        self.spin_to.setFixedWidth(90)
        
        self.spin_step = QDoubleSpinBox()
        self.spin_step.setRange(0.1, 100)
        self.spin_step.setValue(1)
        self.spin_step.setDecimals(1)
        self.spin_step.setPrefix("Co: ")
        self.spin_step.setFixedWidth(90)
        
        range_row.addWidget(self.spin_from)
        range_row.addWidget(self.spin_to)
        range_row.addWidget(self.spin_step)
        layout.addLayout(range_row)
        
        # Unit selector row
        unit_row = QHBoxLayout()
        unit_row.setSpacing(12)
        
        self.radio_cm = QRadioButton("cm")
        self.radio_cm.setChecked(True)
        self.radio_mm = QRadioButton("mm")
        
        unit_row.addWidget(QLabel("Jednostka:"))
        unit_row.addWidget(self.radio_cm)
        unit_row.addWidget(self.radio_mm)
        unit_row.addStretch()
        layout.addLayout(unit_row)
        
        btn_generate = QPushButton("⚡ GENERATE BATCH")
        btn_generate.setCursor(Qt.PointingHandCursor)
        btn_generate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #EC4899);
                color: white;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 10px;
                padding: 12px 24px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C3AED, stop:1 #DB2777);
            }
        """)
        btn_generate.clicked.connect(self.generate_batch)
        layout.addWidget(btn_generate)
        
        layout.addStretch()

        return card

    # ==================================================
    def build_queue_section(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Header Row
        h = QHBoxLayout()
        lbl = QLabel("ACTIVE QUEUE")
        lbl.setProperty("class", "section-header")
        
        # Repeats Input
        h.addWidget(lbl)
        h.addStretch()
        
        l_cyc = QLabel("Cycles:")
        l_cyc.setStyleSheet("color: #94A3B8; font-weight: 600;")
        h.addWidget(l_cyc)
        
        self.spin_repeats = QSpinBox()
        self.spin_repeats.setRange(1, 1000)
        self.spin_repeats.setValue(1)
        self.spin_repeats.setFixedWidth(80)
        self.spin_repeats.setAlignment(Qt.AlignCenter)
        h.addWidget(self.spin_repeats)

        h.addSpacing(10)

        self.btn_run = QPushButton("INITIATE SEQUENCE")
        self.btn_run.setProperty("class", "primary")
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self.run_queue)
        self.btn_run.setFixedWidth(180)
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
        thr = self.input_threads.text()
        mat = "G4_Pb" if self.radio_pb.isChecked() else "G4_Cu"
        
        if not e or not en or not th: return

        task = {
            "id": len(self.queue) + 1,
            "electrons": e,
            "energy": en,
            "thickness": th,
            "threads": thr,
            "material": mat,
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
        status_item.setForeground(QColor("#64748B"))
        status_item.setFont(QFont("Inter", 13, QFont.Bold))
        self.table.setItem(row, 4, status_item)

        self.log.append(f"➕ [QUEUE] Task #{task['id']} added")

    # ==================================================
    def generate_batch(self):
        """Generate multiple tasks based on range settings."""
        start = self.spin_from.value()
        end = self.spin_to.value()
        step = self.spin_step.value()
        unit = "cm" if self.radio_cm.isChecked() else "mm"
        
        if start > end:
            self.log.append("⚠️ [BATCH] Error: 'Od' must be <= 'Do'")
            return
        
        if step <= 0:
            self.log.append("⚠️ [BATCH] Error: Step must be > 0")
            return
        
        count = 0
        val = start
        while val <= end + 0.0001:  # floating point tolerance
            # Format thickness string
            if unit == "mm" and val == int(val):
                th = f"{int(val)} mm"
            elif unit == "cm" and val == int(val):
                th = f"{int(val)} cm"
            else:
                th = f"{val:.1f} {unit}"
            
            # Create task using current electrons/energy settings
            e = self.input_electrons.text()
            en = self.input_energy.text()
            thr = self.input_threads.text()
            mat = "G4_Pb" if self.radio_pb.isChecked() else "G4_Cu"
            
            task = {
                "id": len(self.queue) + 1,
                "electrons": e,
                "energy": en,
                "thickness": th,
                "threads": thr,
                "material": mat,
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
            status_item.setForeground(QColor("#64748B"))
            status_item.setFont(QFont("Inter", 13, QFont.Bold))
            self.table.setItem(row, 4, status_item)
            
            count += 1
            val += step
        
        self.log.append(f"⚡ [BATCH] Generated {count} tasks from {start} to {end} {unit}")

    # ==================================================
    def run_queue(self):
        if not self.queue:
            return

        repeats = self.spin_repeats.value()
        self.btn_run.setEnabled(False)
        self.btn_run.setText("PROCESSING...")
        
        self.worker = SimulationWorker(self.queue, repeats)
        self.worker.progress.connect(self.update_status)
        self.worker.log.connect(self.log.append)
        self.worker.finished.connect(self.finish)
        self.worker.start()

    def update_status(self, row, status):
        item = self.table.item(row, 4)
        item.setText(status)

        colors = {
            "Processing...": "#38BDF8", 
            "Done": "#4ADE80",
            "Failed": "#F87171",
            "Error": "#F87171",
            "Waiting": "#64748B"
        }
        
        # Simple color matching based on substring
        color_code = "#94A3B8"
        if "Processing" in status: color_code = colors["Processing..."]
        elif "Done" in status: color_code = colors["Done"]
        elif "Failed" in status or "Error" in status: color_code = colors["Failed"]
        elif "Waiting" in status: color_code = colors["Waiting"]
        
        item.setForeground(QColor(color_code))
        
        if "Processing" in status:
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