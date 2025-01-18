from typing import Dict, Optional
import logging
import asyncio
from src.hardware.drivers.laser_driver import LaserDriver
from src.utils.error_handling import LaserError
from dataclasses import dataclass

@dataclass
class LaserConfig:
    power_level: float  # mW
    wavelength: float  # nm
    pulse_duration: float  # ns
    beam_diameter: float  # mm
    divergence: float  # mrad

class LaserController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.laser_driver = LaserDriver()
        self._current_config: Optional[LaserConfig] = None
        self._is_active = False
        self._safety_timeout = 0.1  # seconds
        
        # Safety limits
        self._max_power = 50.0  # mW
        self._min_power = 1.0  # mW
        self._safe_temperature_range = (15.0, 40.0)  # °C

    async def initialize(self) -> bool:
        """Initialize the laser system."""
        try:
            self.logger.info("Initializing laser controller...")
            await self.laser_driver.initialize()
            
            # Set default configuration
            default_config = LaserConfig(
                power_level=5.0,
                wavelength=520.0,  # Green laser
                pulse_duration=100.0,
                beam_diameter=1.0,
                divergence=1.0
            )
            
            await self.configure(default_config)
            return True
            
        except Exception as e:
            self.logger.error(f"Laser initialization failed: {str(e)}")
            raise LaserError(f"Failed to initialize laser system: {str(e)}")

    async def configure(self, config: LaserConfig) -> bool:
        """Configure laser parameters."""
        try:
            # Validate configuration
            self._validate_config(config)
            
            # Apply configuration to hardware
            await self.laser_driver.set_power(config.power_level)
            await self.laser_driver.set_pulse_params(config.pulse_duration)
            await self.laser_driver.set_beam_params(config.beam_diameter, config.divergence)
            
            self._current_config = config
            return True
            
        except Exception as e:
            self.logger.error(f"Laser configuration failed: {str(e)}")
            raise LaserError(f"Failed to configure laser: {str(e)}")

    def _validate_config(self, config: LaserConfig) -> None:
        """Validate laser configuration parameters."""
        if not self._min_power <= config.power_level <= self._max_power:
            raise ValueError(f"Power level must be between {self._min_power} and {self._max_power} mW")
        
        if not 400 <= config.wavelength <= 700:
            raise ValueError("Wavelength must be in visible spectrum (400-700 nm)")
        
        if config.pulse_duration <= 0:
            raise ValueError("Pulse duration must be positive")
        
        if config.beam_diameter <= 0:
            raise ValueError("Beam diameter must be positive")
        
        if config.divergence <= 0:
            raise ValueError("Beam divergence must be positive")

    async def start_emission(self) -> bool:
        """Start laser emission."""
        try:
            if self._is_active:
                self.logger.warning("Laser is already active")
                return True
            
            # Check safety conditions
            if not await self._check_safety_conditions():
                raise LaserError("Safety check failed")
            
            # Start emission
            await self.laser_driver.enable_emission()
            self._is_active = True
            
            # Start safety monitoring
            asyncio.create_task(self._safety_monitor())
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start laser emission: {str(e)}")
            await self.emergency_shutdown()
            raise LaserError(f"Failed to start laser emission: {str(e)}")

    async def stop_emission(self) -> bool:
        """Stop laser emission."""
        try:
            if not self._is_active:
                return True
            
            await self.laser_driver.disable_emission()
            self._is_active = False
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop laser emission: {str(e)}")
            await self.emergency_shutdown()
            return False

    async def _check_safety_conditions(self) -> bool:
        """Check all safety conditions before laser operation."""
        try:
            temperature = await self.laser_driver.get_temperature()
            if not (self._safe_temperature_range[0] <= temperature <= self._safe_temperature_range[1]):
                return False
            
            power_check = await self.laser_driver.check_power_stability()
            if not power_check:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Safety check failed: {str(e)}")
            return False

    async def _safety_monitor(self) -> None:
        """Continuous safety monitoring during operation."""
        while self._is_active:
            try:
                if not await self._check_safety_conditions():
                    await self.emergency_shutdown()
                    break
                await asyncio.sleep(self._safety_timeout)
            except Exception as e:
                self.logger.error(f"Safety monitor error: {str(e)}")
                await self.emergency_shutdown()
                break

    async def emergency_shutdown(self) -> None:
        """Emergency shutdown procedure."""
        try:
            self.logger.warning("Initiating emergency shutdown")
            await self.laser_driver.disable_emission()
            await self.laser_driver.reset()
            self._is_active = False
        except Exception as e:
            self.logger.critical(f"Emergency shutdown failed: {str(e)}")

    async def get_status(self) -> Dict[str, any]:
        """Get current laser status."""
        try:
            temperature = await self.laser_driver.get_temperature()
            power_level = await self.laser_driver.get_power()
            
            return {
                'is_active': self._is_active,
                'temperature': temperature,
                'power_level': power_level,
                'configuration': self._current_config.__dict__ if self._current_config else None
            }
        except Exception as e:
            self.logger.error(f"Failed to get laser status: {str(e)}")
            return {
                'error': str(e),
                'is_active': self._is_active
            }

    async def cleanup(self) -> None:
        """Cleanup resources and shutdown."""
        try:
            await self.stop_emission()
            await self.laser_driver.shutdown()
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise LaserError(f"Failed to cleanup laser controller: {str(e)}")