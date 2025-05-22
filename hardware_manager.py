# hardware_manager.py

import time
import logging
from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass
import serial
import serial.tools.list_ports
import usb.core
import usb.util

class HardwareStatus(Enum):
    NOT_CONNECTED = "not_connected"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    BUSY = "busy"

@dataclass
class HardwareConfig:
    vendor_id: int
    product_id: int
    serial_number: Optional[str]
    port_name: Optional[str]
    baud_rate: Optional[int]

class HardwareComponent:
    def __init__(self, name: str, config: HardwareConfig):
        self.name = name
        self.config = config
        self.status = HardwareStatus.NOT_CONNECTED
        self.device = None
        self.error_message = ""
        
    def is_connected(self) -> bool:
        return self.status != HardwareStatus.NOT_CONNECTED

class HardwareManager:
    def __init__(self):
        self.logger = logging.getLogger("HardwareManager")
        
        # Define hardware configurations
        self.components: Dict[str, HardwareComponent] = {
            "laser_array": HardwareComponent(
                "Laser Array Module",
                HardwareConfig(
                    vendor_id=0x0483,  # Example VID for laser module
                    product_id=0x5740,  # Example PID
                    serial_number=None,
                    port_name=None,
                    baud_rate=115200
                )
            ),
            "mems_controller": HardwareComponent(
                "MEMS Mirror Controller",
                HardwareConfig(
                    vendor_id=0x0484,  # Example VID for MEMS controller
                    product_id=0x5741,  # Example PID
                    serial_number=None,
                    port_name=None,
                    baud_rate=921600
                )
            ),
            "meta_surface": HardwareComponent(
                "Meta-surface Array",
                HardwareConfig(
                    vendor_id=0x0485,  # Example VID for meta-surface
                    product_id=0x5742,  # Example PID
                    serial_number=None,
                    port_name=None,
                    baud_rate=460800
                )
            ),
            "power_controller": HardwareComponent(
                "Power Management Unit",
                HardwareConfig(
                    vendor_id=0x0486,  # Example VID for power controller
                    product_id=0x5743,  # Example PID
                    serial_number=None,
                    port_name=None,
                    baud_rate=115200
                )
            )
        }
        
    def detect_hardware(self) -> Dict[str, HardwareStatus]:
        """Detect all required hardware components."""
        status_report = {}
        
        self.logger.info("Beginning hardware detection...")
        
        # Check USB devices
        for name, component in self.components.items():
            try:
                # Look for USB device
                device = usb.core.find(
                    idVendor=component.config.vendor_id,
                    idProduct=component.config.product_id
                )
                
                if device is not None:
                    component.device = device
                    component.status = HardwareStatus.READY
                    self.logger.info(f"Found {component.name} on USB")
                else:
                    # Check serial ports if USB not found
                    port = self._find_serial_device(component.config)
                    if port:
                        component.device = port
                        component.status = HardwareStatus.READY
                        self.logger.info(f"Found {component.name} on serial port {port}")
                    else:
                        component.status = HardwareStatus.NOT_CONNECTED
                        self.logger.warning(f"{component.name} not found")
                
            except Exception as e:
                component.status = HardwareStatus.ERROR
                component.error_message = str(e)
                self.logger.error(f"Error detecting {component.name}: {str(e)}")
            
            status_report[name] = component.status
            
        return status_report
    
    def _find_serial_device(self, config: HardwareConfig) -> Optional[str]:
        """Find device on serial ports."""
        for port in serial.tools.list_ports.comports():
            try:
                if (hasattr(port, 'vid') and port.vid == config.vendor_id and 
                    hasattr(port, 'pid') and port.pid == config.product_id):
                    return port.device
            except Exception:
                continue
        return None
    
    def initialize_hardware(self) -> bool:
        """Initialize all detected hardware components."""
        all_initialized = True
        
        for name, component in self.components.items():
            if component.status == HardwareStatus.READY:
                try:
                    component.status = HardwareStatus.INITIALIZING
                    
                    # Initialize based on connection type
                    if isinstance(component.device, usb.core.Device):
                        self._initialize_usb_device(component)
                    else:
                        self._initialize_serial_device(component)
                    
                    component.status = HardwareStatus.READY
                    self.logger.info(f"Initialized {component.name}")
                    
                except Exception as e:
                    component.status = HardwareStatus.ERROR
                    component.error_message = str(e)
                    all_initialized = False
                    self.logger.error(f"Failed to initialize {component.name}: {str(e)}")
            
        return all_initialized
    
    def _initialize_usb_device(self, component: HardwareComponent):
        """Initialize USB device."""
        device = component.device
        
        # Reset the device
        try:
            device.reset()
        except Exception:
            pass
        
        # Set the active configuration
        device.set_configuration()
        
        # Get an endpoint instance
        cfg = device.get_active_configuration()
        intf = cfg[(0,0)]
        
        ep = usb.util.find_descriptor(
            intf,
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT
        )
        
        if ep is None:
            raise RuntimeError(f"Could not find endpoint for {component.name}")
    
    def _initialize_serial_device(self, component: HardwareComponent):
        """Initialize serial device."""
        try:
            ser = serial.Serial(
                port=component.device,
                baudrate=component.config.baud_rate,
                timeout=1
            )
            
            if not ser.is_open:
                ser.open()
            
            # Send initialization command and verify response
            ser.write(b'INIT\n')
            response = ser.readline().decode('utf-8').strip()
            
            if response != 'OK':
                raise RuntimeError(f"Invalid response from {component.name}")
                
            ser.close()
            
        except Exception as e:
            raise RuntimeError(f"Serial initialization failed: {str(e)}")
    
    def check_hardware_status(self) -> Dict[str, Dict]:
        """Check current status of all hardware components."""
        status_report = {}
        
        for name, component in self.components.items():
            status_report[name] = {
                'status': component.status.value,
                'error': component.error_message if component.status == HardwareStatus.ERROR else None
            }
            
        return status_report
    
    def shutdown_hardware(self):
        """Safely shutdown all hardware components."""
        for name, component in self.components.items():
            try:
                if component.status == HardwareStatus.READY:
                    if isinstance(component.device, usb.core.Device):
                        usb.util.dispose_resources(component.device)
                    else:
                        # Close serial connection if open
                        try:
                            ser = serial.Serial(component.device)
                            if ser.is_open:
                                ser.close()
                        except Exception:
                            pass
                    
                    component.status = HardwareStatus.NOT_CONNECTED
                    self.logger.info(f"Shutdown {component.name} completed")
                    
            except Exception as e:
                self.logger.error(f"Error during shutdown of {component.name}: {str(e)}")

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize hardware manager
    hw_manager = HardwareManager()
    
    print("\nStarting hardware detection and initialization...")
    
    # Detect hardware
    status = hw_manager.detect_hardware()
    
    print("\nHardware Detection Results:")
    for component, state in status.items():
        print(f"{component}: {state.value}")
    
    # Check if all required components are present
    missing_components = [name for name, state in status.items() 
                         if state == HardwareStatus.NOT_CONNECTED]
    
    if missing_components:
        print("\nERROR: Missing required hardware components:")
        for component in missing_components:
            print(f"- {component}")
        print("\nPlease connect all required hardware and try again.")
        return
    
    print("\nInitializing detected hardware...")
    
    # Initialize hardware
    if hw_manager.initialize_hardware():
        print("Hardware initialization successful!")
        
        # Check detailed status
        status = hw_manager.check_hardware_status()
        print("\nDetailed Hardware Status:")
        for component, info in status.items():
            print(f"{component}:")
            print(f"  Status: {info['status']}")
            if info['error']:
                print(f"  Error: {info['error']}")
    else:
        print("Hardware initialization failed! Check logs for details.")
    
    # Cleanup
    print("\nShutting down hardware...")
    hw_manager.shutdown_hardware()
    print("Hardware shutdown complete.")

if __name__ == "__main__":
    main()