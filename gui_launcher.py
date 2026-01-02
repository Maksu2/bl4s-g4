import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import os
import re

class SimulationManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Geant4 Simulation Manager")
        self.root.geometry("600x650")
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 11))
        style.configure("TButton", font=("Helvetica", 11))
        style.configure("Header.TLabel", font=("Helvetica", 12, "bold"))
        
        self.root.configure(bg="#f0f0f0")
        
        # Variables
        self.energy_var = tk.StringVar(value="1 GeV")
        self.electrons_var = tk.StringVar(value="1000")
        self.thickness_var = tk.StringVar(value="1 cm")
        self.svg_var = tk.BooleanVar(value=True)
        
        self.queue = []
        self.is_running = False

        self.setup_ui()

    def setup_ui(self):
        # --- Input Section ---
        input_frame = ttk.LabelFrame(self.root, text="Simulation Parameters", padding=15)
        input_frame.pack(fill="x", padx=15, pady=10)
        
        # Grid layout for inputs
        ttk.Label(input_frame, text="Electrons (count):").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(input_frame, textvariable=self.electrons_var, width=15).grid(row=0, column=1, sticky="w", padx=10)
        
        ttk.Label(input_frame, text="Beam Energy:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(input_frame, textvariable=self.energy_var, width=15).grid(row=1, column=1, sticky="w", padx=10)
        ttk.Label(input_frame, text="(e.g. 1 GeV, 100 MeV)").grid(row=1, column=2, sticky="w")
        
        ttk.Label(input_frame, text="Lead Thickness:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(input_frame, textvariable=self.thickness_var, width=15).grid(row=2, column=1, sticky="w", padx=10)
        ttk.Label(input_frame, text="(e.g. 1 cm, 2.5 mm)").grid(row=2, column=2, sticky="w")
        
        ttk.Checkbutton(input_frame, text="Generate SVG Visualization", variable=self.svg_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=10)
        
        ttk.Button(input_frame, text="Add to Queue", command=self.add_to_queue).grid(row=3, column=2, sticky="e")

        # --- Queue Section ---
        queue_frame = ttk.LabelFrame(self.root, text="Output Queue", padding=15)
        queue_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.tree = ttk.Treeview(queue_frame, columns=("ID", "Energy", "Electrons", "Thickness", "Status"), show="headings", height=8)
        self.tree.heading("ID", text="#")
        self.tree.heading("Energy", text="Energy")
        self.tree.heading("Electrons", text="Count")
        self.tree.heading("Thickness", text="Thickness")
        self.tree.heading("Status", text="Status")
        
        self.tree.column("ID", width=30)
        self.tree.column("Status", width=100)
        
        self.tree.pack(fill="both", expand=True)

        # Controls
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x")
        
        self.run_btn = ttk.Button(btn_frame, text="RUN QUEUE", command=self.run_process, width=20)
        self.run_btn.pack(side="right", padx=15)
        
        ttk.Button(btn_frame, text="Clear Queue", command=self.clear_queue).pack(side="left", padx=15)

        # --- Log Section ---
        log_frame = ttk.LabelFrame(self.root, text="Log", padding=10)
        log_frame.pack(fill="x", padx=15, pady=10)
        
        self.log_text = tk.Text(log_frame, height=6, state="disabled", font=("Courier", 10))
        self.log_text.pack(fill="x")

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def add_to_queue(self):
        e = self.electrons_var.get()
        en = self.energy_var.get()
        th = self.thickness_var.get()
        svg = self.svg_var.get()
        
        if not e or not en or not th:
            messagebox.showerror("Error", "All fields are required")
            return

        item_id = len(self.queue) + 1
        self.queue.append({
            "id": item_id,
            "electrons": e,
            "energy": en,
            "thickness": th,
            "svg": svg,
            "status": "Pending"
        })
        
        self.tree.insert("", "end", values=(item_id, en, e, th, "Pending"))
        self.log(f"Added simulation #{item_id} to queue.")

    def clear_queue(self):
        self.queue = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.log("Queue cleared.")

    def run_process(self):
        if self.is_running:
            return
        
        if not self.queue:
            messagebox.showinfo("Info", "Queue is empty")
            return
            
        self.is_running = True
        self.run_btn.config(state="disabled")
        
        thread = threading.Thread(target=self.worker)
        thread.start()

    def worker(self):
        self.log("--- Starting Batch Execution ---")
        
        for i, task in enumerate(self.queue):
            if task["status"] == "Done":
                continue
                
            self.update_status(i, "Running...")
            self.log(f"Processing #{task['id']} (E={task['energy']}, Th={task['thickness']})...")
            
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
                # Capture output to find the CSV name
                result = subprocess.run(["./build/GeantSim", mac_filename], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.log(f"Error in #{task['id']}: {result.stderr}")
                    self.update_status(i, "Error")
                    continue
                
                # Parse output for CSV filename
                # Output format: Results written to 'results_1cm_3.csv'
                match = re.search(r"Results written to '(.*\.csv)'", result.stdout)
                if match:
                    csv_file = match.group(1)
                    self.log(f"  -> Generated: {csv_file}")
                    
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
                        self.log(f"  -> SVG created.")
                    
                    self.update_status(i, "Done")
                else:
                    self.log("  -> Warning: Could not find output filename in logs.")
                    self.update_status(i, "Unknown")
                    
            except Exception as e:
                self.log(f"Exception in #{task['id']}: {e}")
                self.update_status(i, "Failed")
                
        self.log("--- All Tasks Completed ---")
        self.is_running = False
        self.root.after(0, lambda: self.run_btn.config(state="normal"))
        
        # Cleanup temp file
        if os.path.exists("temp_queue_run.mac"):
            os.remove("temp_queue_run.mac")

    def update_status(self, index, status):
        # Update Treeview safely
        child_id = self.tree.get_children()[index]
        self.tree.set(child_id, "Status", status)
        self.queue[index]["status"] = status

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationManager(root)
    root.mainloop()
