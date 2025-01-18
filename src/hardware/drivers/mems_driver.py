import asyncio
from typing import Dict, Optional, Tuple
from src.utils.error_handling import MEMSError, HardwareError
from src.utils.logging_utils import HolographicWatchLogger
from src.hardware.interfaces.i2c_interface import I2CInterface
from src.hardware.interfaces.spi_interface import SPIInterface

class MEMSDriver:
    """Driver for controlling the MEMS scanning system."""
    
    def __init__(self):
        self.logger = HolographicWatchLogger(__name__)
        self._i2c = I2CInterface()
        self._spi = SPIInterface()
        
        # MEMS control registers
        self._CONTROL_REG = 0x10
        self._H_FREQ_REG = 0x11
        self._V_FREQ_REG = 0x12
        self._H_AMP_REG = 0x13
        self._V_AMP_REG = 0x14
        self._STATUS_REG = 0x15
        self._POSITION_REG = 0x16
        
        # Status flags
        self._initialized = False
        self._scanning_active = False
        
        # Operating parameters
        self._current_h_freq = 0.0
        self._current_v_freq = 0.0
        self._current_h_amp = 0.0
        self._current_v_amp = 0.0
        
        # Safety limits
        self._MAX_H_FREQ = 2000.0  # Hz
        self._MAX_V_FREQ = 1000.0  # Hz
        self._MAX_AMPLITUDE = 15.0  # degrees
        self._MIN_FREQ = 50.0      # Hz

    async def initialize(self) -> bool:
        """Initialize the MEMS hardware."""
        try:
            # Initialize communication interfaces
            await self._i2c.initialize()
            await self._spi.initialize()
            
            # Perform hardware self-test
            if not await self._perform_self_test():
                raise MEMSError("MEMS self-test failed")
            
            # Set initial configuration
            await self._write_register(self._CONTROL_REG, 0x00)  # Scanner disabled
            await self._write_register(self._H_FREQ_REG, 0x00)   # Zero frequency
            await self._write_register(self._V_FREQ_REG, 0x00)
            await self._write_register(self._H_AMP_REG, 0x00)    # Zero amplitude
            await self._write_register(self._V_AMP_REG, 0x00)
            
            self._initialized = True
            self.logger.info("MEMS driver initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("MEMS initialization failed", error=e)
            raise MEMSError(
                "Failed to initialize MEMS driver",
                details={"original_error": str(e)}
            )

    async def _perform_self_test(self) -> bool:
        """Perform MEMS system self-test."""
        try:
            # Read identification registers
            device_id = await self._read_register(0x00)
            if device_id != 0xB3:  # Expected device ID
                return False
            
            # Test scanner movement
            await self._write_register(self._H_FREQ_REG, 0x01)
            freq_readback = await self._read_register(self._H_FREQ_REG)
            if freq_readback != 0x01:
                return False
            
            # Reset test configuration
            await self._write_register(self._H_FREQ_REG, 0x00)
            return True
            
        except Exception as e:
            self.logger.error("Self-test failed", error=e)
            return False

    async def set_scanning_parameters(self, h_freq: float, v_freq: float,
                                   h_amp: float, v_amp: float) -> None:
        """Set scanning frequency and amplitude parameters."""
        try:
            if not self._initialized:
                raise MEMSError("MEMS driver not initialized")
            
            # Validate parameters
            if not (self._MIN_FREQ <= h_freq <= self._MAX_H_FREQ):
                raise MEMSError(
                    f"Horizontal frequency out of range ({self._MIN_FREQ}-{self._MAX_H_FREQ}Hz)",
                    scan_frequency=h_freq
                )
            
            if not (self._MIN_FREQ <= v_freq <= self._MAX_V_FREQ):
                raise MEMSError(
                    f"Vertical frequency out of range ({self._MIN_FREQ}-{self._MAX_V_FREQ}Hz)",
                    scan_frequency=v_freq
                )
            
            if not (0 <= h_amp <= self._MAX_AMPLITUDE):
                raise MEMSError(
                    f"Horizontal amplitude out of range (0-{self._MAX_AMPLITUDE}°)",
                    scan_amplitude=h_amp
                )
            
            if not (0 <= v_amp <= self._MAX_AMPLITUDE):
                raise MEMSError(
                    f"Vertical amplitude out of range (0-{self._MAX_AMPLITUDE}°)",
                    scan_amplitude=v_amp
                )
            
            # Convert parameters to register values
            h_freq_reg = int((h_freq / self._MAX_H_FREQ) * 255)
            v_freq_reg = int((v_freq / self._MAX_V_FREQ) * 255)
            h_amp_reg = int((h_amp / self._MAX_AMPLITUDE) * 255)
            v_amp_reg = int((v_amp / self._MAX_AMPLITUDE) * 255)
            
            # Apply settings
            await self._write_register(self._H_FREQ_REG, h_freq_reg)
            await self._write_register(self._V_FREQ_REG, v_freq_reg)
            await self._write_register(self._H_AMP_REG, h_amp_reg)
            await self._write_register(self._V_AMP_REG, v_amp_reg)
            
            # Update current parameters
            self._current_h_freq = h_freq
            self._current_v_freq = v_freq
            self._current_h_amp = h_amp
            self._current_v_amp = v_amp
            
            self.logger.debug(
                f"Scanning parameters set: H({h_freq}Hz, {h_amp}°), V({v_freq}Hz, {v_amp}°)"
            )
            
        except Exception as e:
            self.logger.error("Failed to set scanning parameters", error=e)
            raise MEMSError(
                "Parameter setting failed",
                scan_frequency=max(h_freq, v_freq),
                scan_amplitude=max(h_amp, v_amp),
                details={"original_error": str(e)}
            )

    async def enable_scanning(self) -> None:
        """Enable MEMS scanning."""
        try:
            if not self._initialized:
                raise MEMSError("MEMS driver not initialized")
            
            # Check scanning conditions
            await self._check_scanning_conditions()
            
            # Enable scanner
            await self._write_register(self._CONTROL_REG, 0x01)
            
            # Verify scanning state
            status = await self._read_register(self._STATUS_REG)
            if not (status & 0x01):
                raise MEMSError("Failed to enable scanning")
            
            self._scanning_active = True
            self.logger.info("MEMS scanning enabled")
            
        except Exception as e:
            self.logger.error("Failed to enable scanning", error=e)
            raise MEMSError(
                "Scanning enable failed",
                details={"original_error": str(e)}
            )

    async def disable_scanning(self) -> None:
        """Disable MEMS scanning."""
        try:
            if not self._initialized:
                raise MEMSError("MEMS driver not initialized")
            
            # Disable scanner
            await self._write_register(self._CONTROL_REG, 0x00)
            
            # Verify scanning state
            status = await self._read_register(self._STATUS_REG)
            if (status & 0x01):
                raise MEMSError("Failed to disable scanning")
            
            self._scanning_active = False
            self.logger.info("MEMS scanning disabled")
            
        except Exception as e:
            self.logger.error("Failed to disable scanning", error=e)
            self._scanning_active = False  # Force state update for safety
            raise MEMSError(
                "Scanning disable failed",
                details={"original_error": str(e)}
            )

    async def check_scanning_stability(self) -> float:
        """Check scanning stability and return stability metric."""
        try:
            if not self._initialized or not self._scanning_active:
                return 0.0
            
            # Read current position and frequency metrics
            position_error = await self._read_position_error()
            frequency_error = await self._read_frequency_error()
            
            # Calculate stability metric (0-1.0)
            stability = 1.0 - max(position_error, frequency_error)
            return max(min(stability, 1.0), 0.0)
            
        except Exception as e:
            self.logger.error("Stability check failed", error=e)
            return 0.0

    async def get_mirror_position(self) -> Tuple[float, float]:
        """Get current mirror position (horizontal, vertical) in degrees."""
        try:
            if not self._initialized:
                raise MEMSError("MEMS driver not initialized")
            
            # Read position registers
            position_raw = await self._read_register(self._POSITION_REG)
            h_pos = ((position_raw >> 4) & 0x0F) * (self._MAX_AMPLITUDE / 15.0)
            v_pos = (position_raw & 0x0F) * (self._MAX_AMPLITUDE / 15.0)
            
            return (h_pos, v_pos)
            
        except Exception as e:
            self.logger.error("Failed to read mirror position", error=e)
            raise MEMSError(
                "Position reading failed",
                details={"original_error": str(e)}
            )

    async def _check_scanning_conditions(self) -> None:
        """Check conditions for safe scanning operation."""
        try:
            # Check scanning stability
            stability = await self.check_scanning_stability()
            if stability < 0.8:  # Minimum stability threshold
                raise MEMSError("Insufficient scanning stability")
            
            # Check resonant conditions
            if not await self._check_resonance():
                raise MEMSError("Resonance check failed")
            
        except Exception as e:
            raise MEMSError(
                "Safety check failed",
                scan_frequency=max(self._current_h_freq, self._current_v_freq),
                details={"original_error": str(e)}
            )

    async def _read_position_error(self) -> float:
        """Read position tracking error."""
        try:
            error_raw = await self._read_register(0x17)  # Position error register
            return error_raw / 255.0  # Normalize to 0-1.0
        except Exception as e:
            self.logger.error("Failed to read position error", error=e)
            return 1.0  # Return maximum error on failure

    async def _read_frequency_error(self) -> float:
        """Read frequency tracking error."""
        try:
            error_raw = await self._read_register(0x18)  # Frequency error register
            return error_raw / 255.0  # Normalize to 0-1.0
        except Exception as e:
            self.logger.error("Failed to read frequency error", error=e)
            return 1.0  # Return maximum error on failure

    async def _check_resonance(self) -> bool:
        """Check if scanner is operating at resonance."""
        try:
            resonance_raw = await self._read_register(0x19)  # Resonance register
            return (resonance_raw & 0x01) == 0x01
        except Exception as e:
            self.logger.error("Resonance check failed", error=e)
            return False

    async def emergency_stop(self) -> None:
        """Perform emergency stop of MEMS scanner."""
        try:
            # Force control register to stop state
            await self._write_register(self._CONTROL_REG, 0x00)
            
            # Force zero amplitude
            await self._write_register(self._H_AMP_REG, 0x00)
            await self._write_register(self._V_AMP_REG, 0x00)
            
            self._scanning_active = False
            self.logger.warning("Emergency stop performed")
            
        except Exception as e:
            self.logger.critical("Emergency stop failed", error=e)
            raise MEMSError(
                "Emergency stop failed",
                details={"original_error": str(e)}
            )

    async def _write_register(self, register: int, value: int) -> None:
        """Write value to MEMS hardware register."""
        try:
            await self._spi.write_register(register, value)
        except Exception as e:
            raise HardwareError(
                f"Failed to write to register 0x{register:02X}",
                "mems",
                details={"value": value, "original_error": str(e)}
            )

    async def _read_register(self, register: int) -> int:
        """Read value from MEMS hardware register."""
        try:
            return await self._spi.read_register(register)
        except Exception as e:
            raise HardwareError(
                f"Failed to read from register 0x{register:02X}",
                "mems",
                details={"original_error": str(e)}
            )

    async def shutdown(self) -> None:
        """Shutdown MEMS hardware."""
        try:
            # Stop scanning if active
            if self._scanning_active:
                await self.disable_scanning()
            
            # Reset scanner position
            await self._write_register(self._H_AMP_REG, 0x00)
            await self._write_register(self._V_AMP_REG, 0x00)
            
            # Close communication interfaces
            await self._spi.cleanup()
            await self._i2c.cleanup()
            
            self._initialized = False
            self.logger.info("MEMS driver shut down successfully")
            
        except Exception as e:
            self.logger.error("Failed to shutdown MEMS driver", error=e)
            raise MEMSError(
                "Shutdown failed",
                details={"original_error": str(e)}
            )