# src/ui/gui_interface.py

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Optional
from ..core.system_interface import HolographicSystemInterface, SystemStatus

class HolographicWatchGUI:
    def __init__(self, system_interface: HolographicSystemInterface):
        self.system = system_interface
        self.root = tk.Tk()
        self.root.title("Holographic Watch Control Interface")
        self.root.geometry("800x600")
        
        # Initialize UI components
        self._init_ui()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.is_running = True
        
    def _init_ui(self):
        # Create main containers
        self.control_frame = ttk.LabelFrame(self.root, text="System Controls")
        self.control_frame.pack(fill="x", padx=5, pady=5)
        
        self.status_frame = ttk.LabelFrame(self.root, text="System Status")
        self.status_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Control buttons
        self.start_button = ttk.Button(
            self.control_frame, 
            text="Start Hologram",
            command=self._start_hologram
        )
        self.start_button.pack(side="left", padx=5, pady=5)
        
        self.stop_button = ttk.Button(
            self.control_frame,
            text="Stop Hologram",
            command=self._stop_hologram
        )
        self.stop_button.pack(side="left", padx=5, pady=5)
        
        # Status displays
        self.status_labels = {}
        status_items = [
            "Power State",
            "Battery Level",
            "Temperature",
            "Power Consumption",
            "System Health"
        ]
        
        for item in status_items:
            frame = ttk.Frame(self.status_frame)
            frame.pack(fill="x", padx=5, pady=2)
            
            label = ttk.Label(frame, text=f"{item}:")
            label.pack(side="left", padx=5)
            
            value = ttk.Label(frame, text="--")
            value.pack(side="left", padx=5)
            
            self.status_labels[item] = value
            
    def _start_hologram(self):
        if self.system.start_hologram():
            self.start_button.state(['disabled'])
            self.stop_button.state(['!disabled'])
            
    def _stop_hologram(self):
        self.system.stop_hologram()
        self.start_button.state(['!disabled'])
        self.stop_button.state(['disabled'])
        
    def _update_status_display(self, status: SystemStatus):
        self.status_labels["Power State"].config(
            text=status.power_state.value
        )
        self.status_labels["Battery Level"].config(
            text=f"{status.battery_level:.1f}%"
        )
        self.status_labels["Temperature"].config(
            text=f"{status.temperature:.1f}°C"
        )
        self.status_labels["Power Consumption"].config(
            text=f"{status.current_power_consumption:.2f}W"
        )
        self.status_labels["System Health"].config(
            text=", ".join(f"{k}: {v}" for k, v in status.system_health.items())
        )
        
    def _update_loop(self):
        while self.is_running:
            status = self.system.get_system_status()
            self.root.after(0, self._update_status_display, status)
            time.sleep(0.1)
            
    def run(self):
        self.update_thread.start()
        self.root.mainloop()
        
    def shutdown(self):
        self.is_running = False
        self.update_thread.join()
        self.system.shutdown()
        self.root.quit()

def main():
    system = HolographicSystemInterface()
    if not system.initialize_system():
        print("Failed to initialize system")
        return
        
    gui = HolographicWatchGUI(system)
    try:
        gui.run()
    finally:
        gui.shutdown()

if __name__ == "__main__":
    main()