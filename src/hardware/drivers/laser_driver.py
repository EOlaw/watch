import asyncio
from typing import Dict, Optional, Tuple
from src.utils.error_handling import LaserError, HardwareError
from src.utils.logging_utils import HolographicWatchLogger
from src.hardware.interfaces.i2c_interface import I2CInterface
from src.hardware.interfaces.spi_interface import SPIInterface

class LaserDriver:
    """Driver for controlling the laser emission system."""
    
    def __init__(self):
        self.logger = HolographicWatchLogger(__name__)
        self._i2c = I2CInterface()
        self._spi = SPIInterface()
        
        # Laser control registers
        self._CONTROL_REG = 0x01
        self._POWER_REG = 0x02
        self._TEMP_REG = 0x03
        self._STATUS_REG = 0x04
        self._PULSE_REG = 0x05
        
        # Status flags
        self._initialized = False
        self._emission_active = False
        
        # Operating parameters
        self._current_power = 0.0
        self._current_temperature = 25.0
        self._pulse_duration = 0.0
        
        # Safety limits
        self._MAX_POWER = 50.0  # mW
        self._MAX_TEMP = 45.0   # °C
        self._MIN_TEMP = 15.0   # °C

    async def initialize(self) -> bool:
        """Initialize the laser hardware."""
        try:
            # Initialize communication interfaces
            await self._i2c.initialize()
            await self._spi.initialize()
            
            # Perform hardware self-test
            if not await self._perform_self_test():
                raise LaserError("Laser self-test failed")
            
            # Set initial configuration
            await self._write_register(self._CONTROL_REG, 0x00)  # Laser disabled
            await self._write_register(self._POWER_REG, 0x00)    # Zero power
            
            self._initialized = True
            self.logger.info("Laser driver initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Laser initialization failed", error=e)
            raise LaserError(
                "Failed to initialize laser driver",
                details={"original_error": str(e)}
            )

    async def _perform_self_test(self) -> bool:
        """Perform laser system self-test."""
        try:
            # Read identification registers
            device_id = await self._read_register(0x00)
            if device_id != 0xA5:  # Expected device ID
                return False
            
            # Test temperature sensor
            temp = await self.get_temperature()
            if not (self._MIN_TEMP <= temp <= self._MAX_TEMP):
                return False
            
            # Test power control
            await self._write_register(self._POWER_REG, 0x00)
            power_readback = await self._read_register(self._POWER_REG)
            if power_readback != 0x00:
                return False
                
            return True
            
        except Exception as e:
            self.logger.error("Self-test failed", error=e)
            return False

    async def set_power(self, power: float) -> None:
        """Set laser power level."""
        try:
            if not self._initialized:
                raise LaserError("Laser driver not initialized")
                
            if not 0 <= power <= self._MAX_POWER:
                raise LaserError(
                    f"Power level out of range (0-{self._MAX_POWER}mW)",
                    laser_power=power
                )
            
            # Convert power to register value
            reg_value = int((power / self._MAX_POWER) * 255)
            await self._write_register(self._POWER_REG, reg_value)
            
            # Verify power setting
            readback = await self._read_register(self._POWER_REG)
            if readback != reg_value:
                raise LaserError("Power setting verification failed")
            
            self._current_power = power
            self.logger.debug(f"Laser power set to {power}mW")
            
        except Exception as e:
            self.logger.error("Failed to set laser power", error=e)
            raise LaserError(
                "Power setting failed",
                laser_power=power,
                details={"original_error": str(e)}
            )

    async def set_pulse_params(self, duration: float) -> None:
        """Set laser pulse parameters."""
        try:
            if not self._initialized:
                raise LaserError("Laser driver not initialized")
                
            if duration <= 0:
                raise LaserError("Pulse duration must be positive")
            
            # Convert duration to register value (ns)
            reg_value = int(duration * 1000)  # Convert to ns
            await self._write_register(self._PULSE_REG, reg_value)
            
            self._pulse_duration = duration
            self.logger.debug(f"Pulse duration set to {duration}ns")
            
        except Exception as e:
            self.logger.error("Failed to set pulse parameters", error=e)
            raise LaserError(
                "Pulse parameter setting failed",
                details={"duration": duration, "original_error": str(e)}
            )

    async def enable_emission(self) -> None:
        """Enable laser emission."""
        try:
            if not self._initialized:
                raise LaserError("Laser driver not initialized")
            
            # Check safety conditions
            await self._check_safety_conditions()
            
            # Enable laser emission
            await self._write_register(self._CONTROL_REG, 0x01)
            
            # Verify emission state
            status = await self._read_register(self._STATUS_REG)
            if not (status & 0x01):
                raise LaserError("Failed to enable emission")
            
            self._emission_active = True
            self.logger.info("Laser emission enabled")
            
        except Exception as e:
            self.logger.error("Failed to enable laser emission", error=e)
            raise LaserError(
                "Emission enable failed",
                details={"original_error": str(e)}
            )

    async def disable_emission(self) -> None:
        """Disable laser emission."""
        try:
            if not self._initialized:
                raise LaserError("Laser driver not initialized")
            
            # Disable laser emission
            await self._write_register(self._CONTROL_REG, 0x00)
            
            # Verify emission state
            status = await self._read_register(self._STATUS_REG)
            if (status & 0x01):
                raise LaserError("Failed to disable emission")
            
            self._emission_active = False
            self.logger.info("Laser emission disabled")
            
        except Exception as e:
            self.logger.error("Failed to disable laser emission", error=e)
            self._emission_active = False  # Force state update for safety
            raise LaserError(
                "Emission disable failed",
                details={"original_error": str(e)}
            )

    async def get_temperature(self) -> float:
        """Get current laser temperature."""
        try:
            if not self._initialized:
                raise LaserError("Laser driver not initialized")
            
            # Read temperature register
            temp_raw = await self._read_register(self._TEMP_REG)
            
            # Convert to temperature (°C)
            temperature = (temp_raw * 0.125) - 40.0
            
            self._current_temperature = temperature
            return temperature
            
        except Exception as e:
            self.logger.error("Failed to read temperature", error=e)
            raise LaserError(
                "Temperature reading failed",
                temperature=self._current_temperature,
                details={"original_error": str(e)}
            )

    async def get_power(self) -> float:
        """Get current laser power level."""
        try:
            if not self._initialized:
                raise LaserError("Laser driver not initialized")
            
            # Read power register
            power_raw = await self._read_register(self._POWER_REG)
            
            # Convert to power (mW)
            power = (power_raw / 255.0) * self._MAX_POWER
            
            return power
            
        except Exception as e:
            self.logger.error("Failed to read power level", error=e)
            raise LaserError(
                "Power reading failed",
                laser_power=self._current_power,
                details={"original_error": str(e)}
            )

    async def check_power_stability(self) -> bool:
        """Check laser power stability."""
        try:
            if not self._initialized:
                return False
            
            # Read current power and compare with set point
            current_power = await self.get_power()
            power_difference = abs(current_power - self._current_power)
            
            return power_difference <= (self._current_power * 0.05)  # 5% tolerance
            
        except Exception as e:
            self.logger.error("Power stability check failed", error=e)
            return False

    async def _check_safety_conditions(self) -> None:
        """Check safety conditions for laser operation."""
        try:
            # Check temperature
            temperature = await self.get_temperature()
            if not (self._MIN_TEMP <= temperature <= self._MAX_TEMP):
                raise LaserError(
                    "Temperature out of safe range",
                    temperature=temperature
                )
            
            # Check power stability
            if not await self.check_power_stability():
                raise LaserError("Power instability detected")
            
        except Exception as e:
            raise LaserError(
                "Safety check failed",
                temperature=self._current_temperature,
                details={"original_error": str(e)}
            )

    async def _write_register(self, register: int, value: int) -> None:
        """Write value to laser hardware register."""
        try:
            await self._spi.write_register(register, value)
        except Exception as e:
            raise HardwareError(
                f"Failed to write to register 0x{register:02X}",
                "laser",
                details={"value": value, "original_error": str(e)}
            )

    async def _read_register(self, register: int) -> int:
        """Read value from laser hardware register."""
        try:
            return await self._spi.read_register(register)
        except Exception as e:
            raise HardwareError(
                f"Failed to read from register 0x{register:02X}",
                "laser",
                details={"original_error": str(e)}
            )

    async def reset(self) -> None:
        """Reset laser hardware."""
        try:
            # Disable emission
            await self.disable_emission()
            
            # Reset registers to default values
            await self._write_register(self._CONTROL_REG, 0x00)
            await self._write_register(self._POWER_REG, 0x00)
            await self._write_register(self._PULSE_REG, 0x00)
            
            self._current_power = 0.0
            self._pulse_duration = 0.0
            
            self.logger.info("Laser hardware reset completed")
            
        except Exception as e:
            self.logger.error("Failed to reset laser hardware", error=e)
            raise LaserError(
                "Hardware reset failed",
                details={"original_error": str(e)}
            )

    async def shutdown(self) -> None:
        """Shutdown laser hardware."""
        try:
            # Disable emission
            if self._emission_active:
                await self.disable_emission()
            
            # Reset hardware
            await self.reset()
            
            # Close communication interfaces
            await self._spi.cleanup()
            await self._i2c.cleanup()
            
            self._initialized = False
            self.logger.info("Laser driver shut down successfully")
            
        except Exception as e:
            self.logger.error("Failed to shutdown laser driver", error=e)
            raise LaserError(
                "Shutdown failed",
                details={"original_error": str(e)}
            )