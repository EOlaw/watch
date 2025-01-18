import asyncio
from typing import Dict, Optional, Tuple, List
from src.utils.error_handling import HardwareError
from src.utils.logging_utils import HolographicWatchLogger
from src.hardware.interfaces.i2c_interface import I2CInterface

class ThermalDriver:
    """Driver for thermal sensing and management system."""
    
    def __init__(self):
        self.logger = HolographicWatchLogger(__name__)
        self._i2c = I2CInterface()
        
        # Thermal sensor registers
        self._CONTROL_REG = 0x40
        self._TEMP_HOT_REG = 0x41
        self._TEMP_COLD_REG = 0x42
        self._GRADIENT_REG = 0x43
        self._THERMOELECTRIC_REG = 0x44
        self._STATUS_REG = 0x45
        
        # Status flags
        self._initialized = False
        self._monitoring_active = False
        
        # Operating parameters
        self._sample_rate = 10  # Hz
        self._thermoelectric_power = 0.0  # 0-1.0
        
        # Temperature limits
        self._MAX_TEMP = 85.0  # °C
        self._MIN_TEMP = -40.0  # °C
        self._MAX_GRADIENT = 50.0  # °C
        
        # Current readings
        self._current_hot_temp = 25.0
        self._current_cold_temp = 25.0

    async def initialize(self) -> bool:
        """Initialize the thermal management hardware."""
        try:
            await self._i2c.initialize()
            
            if not await self._perform_self_test():
                raise HardwareError(
                    "Thermal sensor self-test failed",
                    "thermal_sensor"
                )
            
            # Configure sensor
            await self._write_register(self._CONTROL_REG, 0x00)  # System disabled
            await self._configure_sampling()
            
            self._initialized = True
            self.logger.info("Thermal driver initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Thermal driver initialization failed", error=e)
            raise HardwareError(
                "Failed to initialize thermal driver",
                "thermal_sensor",
                details={"original_error": str(e)}
            )

    async def _perform_self_test(self) -> bool:
        """Perform thermal sensor self-test."""
        try:
            # Read identification register
            device_id = await self._read_register(0x00)
            if device_id != 0xE6:  # Expected device ID
                return False
            
            # Test temperature sensors
            await self._write_register(self._CONTROL_REG, 0x01)  # Enable sensor
            await asyncio.sleep(0.1)  # Wait for sensor startup
            
            # Read test measurements
            hot_temp = await self.measure_hot_side_temperature()
            cold_temp = await self.measure_cold_side_temperature()
            
            # Verify measurements are within reasonable range
            if not (self._MIN_TEMP <= hot_temp <= self._MAX_TEMP):
                return False
            if not (self._MIN_TEMP <= cold_temp <= self._MAX_TEMP):
                return False
            
            await self._write_register(self._CONTROL_REG, 0x00)  # Disable sensor
            return True
            
        except Exception as e:
            self.logger.error("Self-test failed", error=e)
            return False

    async def _configure_sampling(self) -> None:
        """Configure temperature sampling rate."""
        try:
            # Set sample rate divider
            rate_div = int(100 / self._sample_rate) - 1
            await self._write_register(0x46, rate_div)
            
        except Exception as e:
            raise HardwareError(
                "Failed to configure sampling rate",
                "thermal_sensor",
                details={"original_error": str(e)}
            )

    async def start_monitoring(self) -> None:
        """Start thermal monitoring."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "Thermal driver not initialized",
                    "thermal_sensor"
                )
            
            # Enable thermal monitoring
            await self._write_register(self._CONTROL_REG, 0x01)
            
            # Verify monitoring state
            status = await self._read_register(self._STATUS_REG)
            if not (status & 0x01):
                raise HardwareError(
                    "Failed to start monitoring",
                    "thermal_sensor"
                )
            
            self._monitoring_active = True
            self.logger.info("Thermal monitoring started")
            
        except Exception as e:
            self.logger.error("Failed to start thermal monitoring", error=e)
            raise HardwareError(
                "Monitoring start failed",
                "thermal_sensor",
                details={"original_error": str(e)}
            )

    async def stop_monitoring(self) -> None:
        """Stop thermal monitoring."""
        try:
            if not self._initialized:
                return
            
            # Disable thermal monitoring
            await self._write_register(self._CONTROL_REG, 0x00)
            
            # Disable thermoelectric cooling
            await self.set_thermoelectric_power(0.0)
            
            self._monitoring_active = False
            self.logger.info("Thermal monitoring stopped")
            
        except Exception as e:
            self.logger.error("Failed to stop thermal monitoring", error=e)
            self._monitoring_active = False  # Force state update
            raise HardwareError(
                "Monitoring stop failed",
                "thermal_sensor",
                details={"original_error": str(e)}
            )

    async def measure_hot_side_temperature(self) -> float:
        """Measure hot side temperature in Celsius."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "Thermal driver not initialized",
                    "thermal_sensor"
                )
            
            # Read temperature register
            temp_raw = await self._read_register(self._TEMP_HOT_REG)
            
            # Convert to temperature (°C)
            temperature = (temp_raw * 0.0625) - 40.0
            
            self._current_hot_temp = temperature
            return temperature
            
        except Exception as e:
            self.logger.error("Failed to measure hot side temperature", error=e)
            raise HardwareError(
                "Temperature measurement failed",
                "thermal_sensor",
                details={"original_error": str(e)}
            )

    async def measure_cold_side_temperature(self) -> float:
        """Measure cold side temperature in Celsius."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "Thermal driver not initialized",
                    "thermal_sensor"
                )
            
            # Read temperature register
            temp_raw = await self._read_register(self._TEMP_COLD_REG)
            
            # Convert to temperature (°C)
            temperature = (temp_raw * 0.0625) - 40.0
            
            self._current_cold_temp = temperature
            return temperature
            
        except Exception as e:
            self.logger.error("Failed to measure cold side temperature", error=e)
            raise HardwareError(
                "Temperature measurement failed",
                "thermal_sensor",
                details={"original_error": str(e)}
            )

    async def measure_temperature_gradient(self) -> float:
        """Measure temperature gradient between hot and cold sides."""
        try:
            hot_temp = await self.measure_hot_side_temperature()
            cold_temp = await self.measure_cold_side_temperature()
            return abs(hot_temp - cold_temp)
            
        except Exception as e:
            self.logger.error("Failed to measure temperature gradient", error=e)
            raise HardwareError(
                "Gradient measurement failed",
                "thermal_sensor",
                details={"original_error": str(e)}
            )

    async def set_thermoelectric_power(self, power: float) -> None:
        """Set thermoelectric cooling power (0-1.0)."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "Thermal driver not initialized",
                    "thermal_sensor"
                )
            
            if not 0 <= power <= 1.0:
                raise ValueError("Power must be between 0 and 1")
            
            # Convert power to register value
            power_reg = int(power * 255)
            await self._write_register(self._THERMOELECTRIC_REG, power_reg)
            
            self._thermoelectric_power = power
            self.logger.debug(f"Thermoelectric power set to {power:.2f}")
            
        except Exception as e:
            self.logger.error("Failed to set thermoelectric power", error=e)
            raise HardwareError(
                "Power setting failed",
                "thermal_sensor",
                details={"power": power, "original_error": str(e)}
            )

    async def get_thermal_status(self) -> Dict[str, any]:
        """Get current thermal system status."""
        try:
            if not self._initialized:
                return {
                    "active": False,
                    "error": "Not initialized"
                }
            
            hot_temp = await self.measure_hot_side_temperature()
            cold_temp = await self.measure_cold_side_temperature()
            gradient = await self.measure_temperature_gradient()
            
            status = await self._read_register(self._STATUS_REG)
            
            return {
                "active": self._monitoring_active,
                "hot_temperature": hot_temp,
                "cold_temperature": cold_temp,
                "gradient": gradient,
                "thermoelectric_power": self._thermoelectric_power,
                "overtemperature": bool(status & 0x02),
                "sensor_error": bool(status & 0x04)
            }
            
        except Exception as e:
            self.logger.error("Failed to get thermal status", error=e)
            return {
                "active": self._monitoring_active,
                "error": str(e)
            }

    async def check_thermal_limits(self) -> bool:
        """Check if temperatures are within safe limits."""
        try:
            hot_temp = await self.measure_hot_side_temperature()
            cold_temp = await self.measure_cold_side_temperature()
            gradient = await self.measure_temperature_gradient()
            
            # Check temperature limits
            if not (self._MIN_TEMP <= hot_temp <= self._MAX_TEMP):
                return False
            if not (self._MIN_TEMP <= cold_temp <= self._MAX_TEMP):
                return False
            if gradient > self._MAX_GRADIENT:
                return False
                
            return True
            
        except Exception as e:
            self.logger.error("Failed to check thermal limits", error=e)
            return False

    async def _write_register(self, register: int, value: int) -> None:
        """Write value to thermal sensor register."""
        try:
            await self._i2c.write_register(register, value)
        except Exception as e:
            raise HardwareError(
                f"Failed to write to register 0x{register:02X}",
                "thermal_sensor",
                details={"value": value, "original_error": str(e)}
            )

    async def _read_register(self, register: int) -> int:
        """Read value from thermal sensor register."""
        try:
            return await self._i2c.read_register(register)
        except Exception as e:
            raise HardwareError(
                f"Failed to read from register 0x{register:02X}",
                "thermal_sensor",
                details={"original_error": str(e)}
            )

    async def shutdown(self) -> None:
        """Shutdown thermal management hardware."""
        try:
            # Stop monitoring if active
            if self._monitoring_active:
                await self.stop_monitoring()
            
            # Disable thermoelectric cooling
            await self.set_thermoelectric_power(0.0)
            
            # Close communication interface
            await self._i2c.cleanup()
            
            self._initialized = False
            self.logger.info("Thermal driver shut down successfully")
            
        except Exception as e:
            self.logger.error("Failed to shutdown thermal driver", error=e)
            raise HardwareError(
                "Shutdown failed",
                "thermal_sensor",
                details={"original_error": str(e)}
            )