from typing import Optional, Dict, Any
from datetime import datetime

class HolographicWatchError(Exception):
    """Base exception class for holographic watch system."""
    def __init__(self, message: str, error_code: Optional[str] = None,
                 component: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.component = component or "system"
        self.timestamp = datetime.now()
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }

class ProjectionError(HolographicWatchError):
    """Exception for projection system errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="PROJECTION_ERROR",
                        component="projection_system", **kwargs)

class PowerManagementError(HolographicWatchError):
    """Exception for power management system errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="POWER_ERROR",
                        component="power_management", **kwargs)

class SystemMonitorError(HolographicWatchError):
    """Exception for system monitoring errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="MONITOR_ERROR",
                        component="system_monitor", **kwargs)

class SafetyError(HolographicWatchError):
    """Exception for safety system errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="SAFETY_ERROR",
                        component="safety_system", **kwargs)

class HardwareError(HolographicWatchError):
    """Exception for hardware-related errors."""
    def __init__(self, message: str, device: str, **kwargs):
        super().__init__(message, error_code="HARDWARE_ERROR",
                        component=f"hardware_{device}", **kwargs)

class ConfigurationError(HolographicWatchError):
    """Exception for configuration-related errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR",
                        component="configuration", **kwargs)

class InteractionError(HolographicWatchError):
    """Exception for user interaction errors."""
    def __init__(self, message: str, interaction_type: str, **kwargs):
        super().__init__(message, error_code="INTERACTION_ERROR",
                        component=f"interaction_{interaction_type}", **kwargs)

def handle_hardware_error(error: Exception, device: str) -> HardwareError:
    """Convert hardware exceptions to HardwareError."""
    return HardwareError(
        message=str(error),
        device=device,
        details={"original_error": str(error)}
    )

def handle_configuration_error(error: Exception) -> ConfigurationError:
    """Convert configuration exceptions to ConfigurationError."""
    return ConfigurationError(
        message=str(error),
        details={"original_error": str(error)}
    )

class LaserError(HolographicWatchError):
    """Exception for laser system errors."""
    def __init__(self, message: str, laser_power: Optional[float] = None,
                temperature: Optional[float] = None, **kwargs):
        details = kwargs.get('details', {})
        if laser_power is not None:
            details['laser_power'] = laser_power
        if temperature is not None:
            details['temperature'] = temperature
        
        super().__init__(
            message,
            error_code="LASER_ERROR",
            component="laser_system",
            details=details
        )

class MEMSError(HolographicWatchError):
    """Exception for MEMS scanning system errors."""
    def __init__(self, message: str, scan_frequency: Optional[float] = None,
                scan_amplitude: Optional[float] = None, **kwargs):
        details = kwargs.get('details', {})
        if scan_frequency is not None:
            details['scan_frequency'] = scan_frequency
        if scan_amplitude is not None:
            details['scan_amplitude'] = scan_amplitude
        
        super().__init__(
            message,
            error_code="MEMS_ERROR",
            component="mems_system",
            details=details
        )

class MetaSurfaceError(HolographicWatchError):
    """Exception for meta-surface system errors."""
    def __init__(self, message: str, phase_pattern: Optional[str] = None,
                efficiency: Optional[float] = None, **kwargs):
        details = kwargs.get('details', {})
        if phase_pattern is not None:
            details['phase_pattern'] = phase_pattern
        if efficiency is not None:
            details['efficiency'] = efficiency
        
        super().__init__(
            message,
            error_code="METASURFACE_ERROR",
            component="metasurface_system",
            details=details
        )