# src/ui/display_components.py

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import time

class StatusDisplay(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._init_components()
        
    def _init_components(self):
        self.status_values: Dict[str, ttk.Label] = {}
        
        # Create status indicators
        status_items = [
            ("System State", "system_state"),
            ("Battery Level", "battery_level"),
            ("Temperature", "temperature"),
            ("Power Usage", "power_usage")
        ]
        
        for row, (label, key) in enumerate(status_items):
            ttk.Label(self, text=f"{label}:").grid(row=row, column=0, padx=5, pady=2, sticky="e")
            value_label = ttk.Label(self, text="--")
            value_label.grid(row=row, column=1, padx=5, pady=2, sticky="w")
            self.status_values[key] = value_label
            
    def update_status(self, status_data: Dict[str, Any]):
        for key, label in self.status_values.items():
            if key in status_data:
                label.config(text=str(status_data[key]))

class PowerGraph(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._init_graph()
        
    def _init_graph(self):
        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize empty data
        self.power_data = []
        self.time_data = []
        
    def update_graph(self, power_value: float, timestamp: Optional[float] = None):
        if timestamp is None:
            timestamp = len(self.time_data)
            
        self.power_data.append(power_value)
        self.time_data.append(timestamp)
        
        # Keep only last 100 points
        if len(self.power_data) > 100:
            self.power_data = self.power_data[-100:]
            self.time_data = self.time_data[-100:]
            
        self._redraw()
        
    def _redraw(self):
        self.ax.clear()
        self.ax.plot(self.time_data, self.power_data, 'b-')
        self.ax.set_title('Power Consumption Over Time')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Power (W)')
        self.canvas.draw()

class ProjectionControls(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._init_controls()
        
    def _init_controls(self):
        # Projection parameters
        self.parameters = {
            'brightness': tk.DoubleVar(value=50),
            'contrast': tk.DoubleVar(value=50),
            'size': tk.DoubleVar(value=50)
        }
        
        # Create sliders
        for row, (param, var) in enumerate(self.parameters.items()):
            ttk.Label(self, text=f"{param.title()}:").grid(
                row=row, column=0, padx=5, pady=2, sticky="e"
            )
            slider = ttk.Scale(
                self,
                from_=0,
                to=100,
                variable=var,
                orient="horizontal"
            )
            slider.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
            
    def get_parameters(self) -> Dict[str, float]:
        return {
            param: var.get()
            for param, var in self.parameters.items()
        }

class AlertPanel(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._init_panel()
        
    def _init_panel(self):
        self.alerts_text = tk.Text(self, height=5, width=40)
        self.alerts_text.pack(fill=tk.BOTH, expand=True)
        self.alerts_text.config(state=tk.DISABLED)
        
    def add_alert(self, message: str, level: str = "info"):
        self.alerts_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        
        # Color code based on alert level
        tags = {
            "info": "black",
            "warning": "orange",
            "error": "red"
        }
        
        self.alerts_text.insert(tk.END, f"[{timestamp}] {message}\n", tags.get(level, "black"))
        self.alerts_text.see(tk.END)
        self.alerts_text.config(state=tk.DISABLED)
        
    def clear_alerts(self):
        self.alerts_text.config(state=tk.NORMAL)
        self.alerts_text.delete(1.0, tk.END)
        self.alerts_text.config(state=tk.DISABLED)