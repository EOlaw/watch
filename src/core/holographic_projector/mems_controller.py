from typing import Dict, Tuple, Optional
import logging
import asyncio
import numpy as np
from dataclasses import dataclass
from src.hardware.drivers.mems_driver import MEMSDriver
from src.utils.error_handling import MEMSError

@dataclass
class MEMSConfig:
    scan_frequency: Tuple[float, float]  # Hz (horizontal, vertical)
    scan_amplitude: Tuple[float, float]  # degrees
    phase_offset: Tuple[float, float]  # degrees
    resonant_frequency: float  # Hz
    damping_factor: float

class MEMSController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mems_driver = MEMSDriver()
        self._current_config: Optional[MEMSConfig] = None
        self._is_scanning = False
        
        # Operating limits
        self._max_frequency = (2000.0, 1000.0)  # Hz (horizontal, vertical)
        self._max_amplitude = (15.0, 15.0)  # degrees
        self._min_frequency = (100.0, 50.0)  # Hz
        self._min_amplitude = (0.1, 0.1)  # degrees

    async def initialize(self) -> bool:
        """Initialize the MEMS scanning system."""
        try:
            self.logger.info("Initializing MEMS controller...")
            await self.mems_driver.initialize()
            
            # Set default configuration
            default_config = MEMSConfig(
                scan_frequency=(500.0, 250.0),
                scan_amplitude=(10.0, 10.0),
                phase_offset=(0.0, 90.0),
                resonant_frequency=500.0,
                damping_factor=0.7
            )
            
            await self.configure(default_config)
            return True
            
        except Exception as e:
            self.logger.error(f"MEMS initialization failed: {str(e)}")
            raise MEMSError(f"Failed to initialize MEMS system: {str(e)}")

    async def configure(self, config: MEMSConfig) -> bool:
        """Configure MEMS scanner parameters."""
        try:
            # Validate configuration
            self._validate_config(config)
            
            # Apply configuration to hardware
            await self.mems_driver.set_scanning_parameters(
                h_freq=config.scan_frequency[0],
                v_freq=config.scan_frequency[1],
                h_amp=config.scan_amplitude[0],
                v_amp=config.scan_amplitude[1]
            )
            
            await self.mems_driver.set_phase_offset(
                h_phase=config.phase_offset[0],
                v_phase=config.phase_offset[1]
            )
            
            await self.mems_driver.set_resonant_parameters(
                freq=config.resonant_frequency,
                damping=config.damping_factor
            )
            
            self._current_config = config
            return True
            
        except Exception as e:
            self.logger.error(f"MEMS configuration failed: {str(e)}")
            raise MEMSError(f"Failed to configure MEMS scanner: {str(e)}")

    def _validate_config(self, config: MEMSConfig) -> None:
        """Validate MEMS configuration parameters."""
        # Validate frequencies
        if not (self._min_frequency[0] <= config.scan_frequency[0] <= self._max_frequency[0]):
            raise ValueError(f"Horizontal frequency must be between {self._min_frequency[0]} and {self._max_frequency[0]} Hz")
        
        if not (self._min_frequency[1] <= config.scan_frequency[1] <= self._max_frequency[1]):
            raise ValueError(f"Vertical frequency must be between {self._min_frequency[1]} and {self._max_frequency[1]} Hz")
        
        # Validate amplitudes
        if not (self._min_amplitude[0] <= config.scan_amplitude[0] <= self._max_amplitude[0]):
            raise ValueError(f"Horizontal amplitude must be between {self._min_amplitude[0]} and {self._max_amplitude[0]} degrees")
        
        if not (self._min_amplitude[1] <= config.scan_amplitude[1] <= self._max_amplitude[1]):
            raise ValueError(f"Vertical amplitude must be between {self._min_amplitude[1]} and {self._max_amplitude[1]} degrees")
        
        # Validate phase offsets
        if not (0 <= config.phase_offset[0] < 360 and 0 <= config.phase_offset[1] < 360):
            raise ValueError("Phase offsets must be between 0 and 360 degrees")
        
        # Validate damping factor
        if not (0 < config.damping_factor < 2):
            raise ValueError("Damping factor must be between 0 and 2")

    async def start_scanning(self) -> bool:
        """Start MEMS scanning operation."""
        try:
            if self._is_scanning:
                self.logger.warning("MEMS scanner is already active")
                return True
            
            # Perform pre-start checks
            if not await self._check_scanner_health():
                raise MEMSError("Scanner health check failed")
            
            # Start scanning
            await self.mems_driver.enable_scanning()
            self._is_scanning = True
            
            # Start monitoring
            asyncio.create_task(self._monitor_scanning())
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start scanning: {str(e)}")
            await self.emergency_stop()
            raise MEMSError(f"Failed to start MEMS scanning: {str(e)}")

    async def stop_scanning(self) -> bool:
        """Stop MEMS scanning operation."""
        try:
            if not self._is_scanning:
                return True
            
            await self.mems_driver.disable_scanning()
            self._is_scanning = False
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop scanning: {str(e)}")
            await self.emergency_stop()
            return False

    async def _check_scanner_health(self) -> bool:
        """Check MEMS scanner health status."""
        try:
            # Check mechanical resonance
            resonance_check = await self.mems_driver.check_resonance()
            if not resonance_check:
                return False
            
            # Check mirror deflection
            deflection_check = await self.mems_driver.check_deflection()
            if not deflection_check:
                return False
            
            # Check temperature
            temperature = await self.mems_driver.get_temperature()
            if temperature > 60.0:  # Maximum safe temperature
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False

    async def _monitor_scanning(self) -> None:
        """Monitor scanning operation."""
        while self._is_scanning:
            try:
                if not await self._check_scanner_health():
                    await self.emergency_stop()
                    break
                    
                # Monitor scanning stability
                stability = await self.mems_driver.get_scanning_stability()
                if stability < 0.9:  # Stability threshold
                    self.logger.warning("Scanning stability below threshold")
                    await self.emergency_stop()
                    break
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {str(e)}")
                await self.emergency_stop()
                break

    async def emergency_stop(self) -> None:
        """Emergency stop procedure."""
        try:
            self.logger.warning("Initiating emergency stop")
            await self.mems_driver.emergency_stop()
            self._is_scanning = False
        except Exception as e:
            self.logger.critical(f"Emergency stop failed: {str(e)}")

    async def get_status(self) -> Dict[str, any]:
        """Get current MEMS scanner status."""
        try:
            temperature = await self.mems_driver.get_temperature()
            stability = await self.mems_driver.get_scanning_stability()
            position = await self.mems_driver.get_mirror_position()
            
            return {
                'is_scanning': self._is_scanning,
                'temperature': temperature,
                'stability': stability,
                'position': position,
                'configuration': self._current_config.__dict__ if self._current_config else None
            }
        except Exception as e:
            self.logger.error(f"Failed to get scanner status: {str(e)}")
            return {
                'error': str(e),
                'is_scanning': self._is_scanning
            }

    async def cleanup(self) -> None:
        """Cleanup resources and shutdown."""
        try:
            await self.stop_scanning()
            await self.mems_driver.shutdown()
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise MEMSError(f"Failed to cleanup MEMS controller: {str(e)}")