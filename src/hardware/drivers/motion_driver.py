import asyncio
from typing import Dict, Optional, Tuple, List
from src.utils.error_handling import HardwareError
from src.utils.logging_utils import HolographicWatchLogger
from src.hardware.interfaces.i2c_interface import I2CInterface

class MotionDriver:
    """Driver for motion detection and measurement system."""
    
    def __init__(self):
        self.logger = HolographicWatchLogger(__name__)
        self._i2c = I2CInterface()
        
        # Motion sensor registers
        self._CONTROL_REG = 0x30
        self._ACCEL_X_REG = 0x31
        self._ACCEL_Y_REG = 0x32
        self._ACCEL_Z_REG = 0x33
        self._GYRO_X_REG = 0x34
        self._GYRO_Y_REG = 0x35
        self._GYRO_Z_REG = 0x36
        self._STATUS_REG = 0x37
        
        # Status flags
        self._initialized = False
        self._monitoring_active = False
        
        # Operating parameters
        self._accel_range = 2.0  # g
        self._gyro_range = 250.0  # degrees/second
        self._sample_rate = 100  # Hz
        
        # Motion thresholds
        self._MIN_ACCEL = 0.01  # g
        self._MAX_ACCEL = 8.0   # g
        self._MIN_GYRO = 0.1    # degrees/second
        self._MAX_GYRO = 2000.0 # degrees/second

    async def initialize(self) -> bool:
        """Initialize the motion sensor hardware."""
        try:
            await self._i2c.initialize()
            
            if not await self._perform_self_test():
                raise HardwareError(
                    "Motion sensor self-test failed",
                    "motion_sensor"
                )
            
            # Configure sensor
            await self._write_register(self._CONTROL_REG, 0x00)  # Sensor disabled
            await self._configure_ranges()
            await self._configure_sampling()
            
            self._initialized = True
            self.logger.info("Motion driver initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Motion driver initialization failed", error=e)
            raise HardwareError(
                "Failed to initialize motion driver",
                "motion_sensor",
                details={"original_error": str(e)}
            )

    async def _perform_self_test(self) -> bool:
        """Perform motion sensor self-test."""
        try:
            # Read identification register
            device_id = await self._read_register(0x00)
            if device_id != 0xD5:  # Expected device ID
                return False
            
            # Test basic measurements
            await self._write_register(self._CONTROL_REG, 0x01)  # Enable sensor
            await asyncio.sleep(0.1)  # Wait for sensor startup
            
            # Read test measurements
            accel = await self.measure_acceleration()
            gyro = await self.measure_angular_velocity()
            
            # Verify measurements include gravity
            if abs(accel[2] - 1.0) > 0.2:  # Z acceleration should be ~1g
                return False
            
            await self._write_register(self._CONTROL_REG, 0x00)  # Disable sensor
            return True
            
        except Exception as e:
            self.logger.error("Self-test failed", error=e)
            return False

    async def _configure_ranges(self) -> None:
        """Configure acceleration and gyroscope ranges."""
        try:
            # Set accelerometer range
            accel_config = 0x10  # 2g range
            await self._write_register(0x38, accel_config)
            
            # Set gyroscope range
            gyro_config = 0x10   # 250 deg/s range
            await self._write_register(0x39, gyro_config)
            
        except Exception as e:
            raise HardwareError(
                "Failed to configure sensor ranges",
                "motion_sensor",
                details={"original_error": str(e)}
            )

    async def _configure_sampling(self) -> None:
        """Configure sensor sampling rate."""
        try:
            # Set sample rate divider
            rate_div = int(1000 / self._sample_rate) - 1
            await self._write_register(0x3A, rate_div)
            
        except Exception as e:
            raise HardwareError(
                "Failed to configure sampling rate",
                "motion_sensor",
                details={"original_error": str(e)}
            )

    async def start_monitoring(self) -> None:
        """Start motion monitoring."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "Motion driver not initialized",
                    "motion_sensor"
                )
            
            # Enable sensor
            await self._write_register(self._CONTROL_REG, 0x01)
            
            # Verify sensor state
            status = await self._read_register(self._STATUS_REG)
            if not (status & 0x01):
                raise HardwareError(
                    "Failed to start monitoring",
                    "motion_sensor"
                )
            
            self._monitoring_active = True
            self.logger.info("Motion monitoring started")
            
        except Exception as e:
            self.logger.error("Failed to start motion monitoring", error=e)
            raise HardwareError(
                "Monitoring start failed",
                "motion_sensor",
                details={"original_error": str(e)}
            )

    async def stop_monitoring(self) -> None:
        """Stop motion monitoring."""
        try:
            if not self._initialized:
                return
            
            # Disable sensor
            await self._write_register(self._CONTROL_REG, 0x00)
            
            self._monitoring_active = False
            self.logger.info("Motion monitoring stopped")
            
        except Exception as e:
            self.logger.error("Failed to stop motion monitoring", error=e)
            self._monitoring_active = False  # Force state update
            raise HardwareError(
                "Monitoring stop failed",
                "motion_sensor",
                details={"original_error": str(e)}
            )

    async def measure_acceleration(self) -> List[float]:
        """Measure acceleration in g (9.81 m/s²)."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "Motion driver not initialized",
                    "motion_sensor"
                )
            
            # Read acceleration registers
            x_raw = await self._read_register(self._ACCEL_X_REG)
            y_raw = await self._read_register(self._ACCEL_Y_REG)
            z_raw = await self._read_register(self._ACCEL_Z_REG)
            
            # Convert to g
            scale = self._accel_range / 32768.0
            x = x_raw * scale
            y = y_raw * scale
            z = z_raw * scale
            
            return [x, y, z]
            
        except Exception as e:
            self.logger.error("Failed to measure acceleration", error=e)
            raise HardwareError(
                "Acceleration measurement failed",
                "motion_sensor",
                details={"original_error": str(e)}
            )

    async def measure_angular_velocity(self) -> List[float]:
        """Measure angular velocity in degrees per second."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "Motion driver not initialized",
                    "motion_sensor"
                )
            
            # Read gyroscope registers
            x_raw = await self._read_register(self._GYRO_X_REG)
            y_raw = await self._read_register(self._GYRO_Y_REG)
            z_raw = await self._read_register(self._GYRO_Z_REG)
            
            # Convert to degrees/second
            scale = self._gyro_range / 32768.0
            x = x_raw * scale
            y = y_raw * scale
            z = z_raw * scale
            
            return [x, y, z]
            
        except Exception as e:
            self.logger.error("Failed to measure angular velocity", error=e)
            raise HardwareError(
                "Angular velocity measurement failed",
                "motion_sensor",
                details={"original_error": str(e)}
            )

    async def get_motion_status(self) -> Dict[str, any]:
        """Get current motion sensor status."""
        try:
            if not self._initialized:
                return {
                    "active": False,
                    "error": "Not initialized"
                }
            
            status = await self._read_register(self._STATUS_REG)
            return {
                "active": self._monitoring_active,
                "data_ready": bool(status & 0x02),
                "self_test_ok": bool(status & 0x04),
                "system_error": bool(status & 0x08)
            }
            
        except Exception as e:
            self.logger.error("Failed to get motion status", error=e)
            return {
                "active": self._monitoring_active,
                "error": str(e)
            }

    async def _write_register(self, register: int, value: int) -> None:
        """Write value to motion sensor register."""
        try:
            await self._i2c.write_register(register, value)
        except Exception as e:
            raise HardwareError(
                f"Failed to write to register 0x{register:02X}",
                "motion_sensor",
                details={"value": value, "original_error": str(e)}
            )

    async def _read_register(self, register: int) -> int:
        """Read value from motion sensor register."""
        try:
            return await self._i2c.read_register(register)
        except Exception as e:
            raise HardwareError(
                f"Failed to read from register 0x{register:02X}",
                "motion_sensor",
                details={"original_error": str(e)}
            )

    async def shutdown(self) -> None:
        """Shutdown motion sensor hardware."""
        try:
            # Stop monitoring if active
            if self._monitoring_active:
                await self.stop_monitoring()
            
            # Close communication interface
            await self._i2c.cleanup()
            
            self._initialized = False
            self.logger.info("Motion driver shut down successfully")
            
        except Exception as e:
            self.logger.error("Failed to shutdown motion driver", error=e)
            raise HardwareError(
                "Shutdown failed",
                "motion_sensor",
                details={"original_error": str(e)}
            )