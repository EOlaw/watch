from typing import Optional, Dict, Any
from dataclasses import dataclass
import threading
import time
import logging

from .power_management import PowerManagementSystem, PowerState
from .holographic_controller import HolographicProjector

@dataclass
class SystemStatus:
    power_state: PowerState
    battery_level: float
    projection_active: bool
    temperature: float
    current_power_consumption: float
    available_power: float
    system_health: Dict[str, str]

class HolographicSystemInterface:
    def __init__(self):
        self.power_system = PowerManagementSystem()
        self.projector = HolographicProjector()
        
        self.monitoring_interval = 0.1  # seconds
        self._monitor_thread: Optional[threading.Thread] = None
        self._is_monitoring = False
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def initialize_system(self) -> bool:
        """Initialize both power and projector systems."""
        try:
            self.logger.info("Initializing holographic watch system...")
            
            # Initialize power management first
            if not self.power_system.initialize():
                self.logger.error("Power system initialization failed")
                return False
            
            # Initialize projector system
            if not self.projector.initialize_system():
                self.logger.error("Projector system initialization failed")
                return False
            
            # Start system monitoring
            self._start_monitoring()
            
            self.logger.info("System initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {str(e)}")
            return False
    
    def start_hologram(self, hologram_data: Optional[Any] = None) -> bool:
        """Start holographic projection with power management."""
        try:
            # Transition through proper power states for projection
            if not self.power_system.request_power_state(PowerState.ACTIVE):
                self.logger.error("Unable to transition to ACTIVE state")
                return False
                
            # After reaching ACTIVE state, transition to BURST
            if not self.power_system.request_power_state(PowerState.BURST):
                self.logger.error("Unable to transition to BURST state")
                self.power_system.request_power_state(PowerState.STANDBY)  # Fallback to standby
                return False
            
            # Ensure supercapacitor is charged for burst operation
            self.power_system.charge_supercapacitor()
            
            # Start projection
            self.projector.start_projection(hologram_data)
            self.logger.info("Hologram projection started successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start hologram: {str(e)}")
            return False
    
    def stop_hologram(self):
        """Stop holographic projection and return to normal power state."""
        try:
            # Stop projection first
            self.projector.stop_projection()
            
            # Return to standby power state
            self.power_system.request_power_state(PowerState.STANDBY)
            
            self.logger.info("Hologram projection stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping hologram: {str(e)}")
    
    def get_system_status(self) -> SystemStatus:
        """Get current status of the entire system."""
        power_consumption = self.power_system.monitor_power_consumption()
        projector_diagnostic = self.projector.run_diagnostic()
        
        return SystemStatus(
            power_state=self.power_system.current_state,
            battery_level=self.power_system.battery_level,
            projection_active=self.projector.is_projecting,
            temperature=max(power_consumption['temperature'], 
                          projector_diagnostic['temperature']),
            current_power_consumption=power_consumption['primary_power'] + 
                                    power_consumption['supercap_power'],
            available_power=self.power_system.primary_battery.get_available_power() + 
                          self.power_system.supercapacitor.get_available_power(),
            system_health={
                'power_system': 'healthy' if self.power_system.battery_level > 20 else 'low',
                'projector': 'active' if self.projector.is_projecting else 'standby',
                'laser_status': projector_diagnostic['laser_status'],
                'mirror_status': projector_diagnostic['mirror_status'],
                'meta_surface_status': projector_diagnostic['meta_surface_status']
            }
        )
    
    def _start_monitoring(self):
        """Start system monitoring thread."""
        self._is_monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def _monitoring_loop(self):
        """Continuous monitoring loop for system status."""
        while self._is_monitoring:
            try:
                status = self.get_system_status()
                
                # Check for critical conditions
                if status.temperature > 40.0:
                    self.logger.warning("High temperature detected!")
                    self._handle_high_temperature()
                
                if status.battery_level < 15.0:
                    self.logger.warning("Critical battery level!")
                    self._handle_low_battery()
                
                # Optimize power consumption
                self.power_system.optimize_power_consumption()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
    
    def _handle_high_temperature(self):
        """Handle high temperature condition."""
        if self.projector.is_projecting:
            self.stop_hologram()
        self.power_system._activate_thermal_management()
    
    def _handle_low_battery(self):
        """Handle low battery condition."""
        if self.projector.is_projecting:
            self.stop_hologram()
        self.power_system.request_power_state(PowerState.LOW_POWER)
    
    def shutdown(self):
        """Safely shutdown the system."""
        try:
            self.logger.info("Initiating system shutdown...")
            
            # Stop monitoring
            self._is_monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join()
            
            # Stop projection if active
            if self.projector.is_projecting:
                self.stop_hologram()
            
            # Set power state to standby
            self.power_system.request_power_state(PowerState.STANDBY)
            
            self.logger.info("System shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")

def main():
    # Create and initialize the system
    system = HolographicSystemInterface()
    if not system.initialize_system():
        print("Failed to initialize system")
        return
    
    try:
        # Demonstration of system capabilities
        print("\nStarting system demonstration...")
        
        # Get initial status
        status = system.get_system_status()
        print(f"\nInitial system status:")
        print(f"Battery Level: {status.battery_level}%")
        print(f"Power State: {status.power_state.value}")
        print(f"Temperature: {status.temperature}°C")
        
        # Start hologram projection
        print("\nStarting hologram projection...")
        if system.start_hologram():
            print("Hologram started successfully")
            
            # Monitor system for a few seconds
            time.sleep(5)
            
            # Get updated status
            status = system.get_system_status()
            print(f"\nSystem status during projection:")
            print(f"Power Consumption: {status.current_power_consumption}W")
            print(f"Temperature: {status.temperature}°C")
            
            # Stop hologram
            print("\nStopping hologram projection...")
            system.stop_hologram()
        
        # Final status check
        status = system.get_system_status()
        print(f"\nFinal system status:")
        print(f"Battery Level: {status.battery_level}%")
        print(f"Power State: {status.power_state.value}")
        print(f"System Health:", status.system_health)
        
    finally:
        # Ensure proper shutdown
        print("\nShutting down system...")
        system.shutdown()

if __name__ == "__main__":
    main()