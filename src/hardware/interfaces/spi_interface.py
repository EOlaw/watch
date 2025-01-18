import asyncio
from typing import Dict, Optional, List, Tuple
from src.utils.error_handling import HardwareError
from src.utils.logging_utils import HolographicWatchLogger

class SPIInterface:
    """Interface for SPI communication protocol."""
    
    def __init__(self, bus_number: int = 0, chip_select: int = 0):
        self.logger = HolographicWatchLogger(__name__)
        self._bus_number = bus_number
        self._chip_select = chip_select
        self._device = None
        self._initialized = False
        
        # SPI parameters
        self._clock_speed = 1000000  # 1 MHz
        self._mode = 0  # CPOL=0, CPHA=0
        self._bits_per_word = 8
        self._timeout = 1.0  # seconds
        self._retries = 3
        
        # Transaction tracking
        self._active_transactions = 0
        self._last_error = None
        self._error_count = 0
        
        # Performance monitoring
        self._transaction_history: List[Dict] = []
        self._MAX_HISTORY = 1000

    async def initialize(self) -> bool:
        """Initialize the SPI interface."""
        try:
            self.logger.info(
                f"Initializing SPI interface on bus {self._bus_number}, "
                f"CS {self._chip_select}"
            )
            
            # In production, this would initialize actual SPI hardware
            # For simulation, we'll create a mock device
            self._device = await self._initialize_hardware()
            
            # Test device functionality
            if not await self._test_device():
                raise HardwareError(
                    "SPI device test failed",
                    "spi",
                    details={
                        "bus_number": self._bus_number,
                        "chip_select": self._chip_select
                    }
                )
            
            self._initialized = True
            self.logger.info("SPI interface initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("SPI initialization failed", error=e)
            raise HardwareError(
                "Failed to initialize SPI interface",
                "spi",
                details={
                    "bus_number": self._bus_number,
                    "chip_select": self._chip_select,
                    "original_error": str(e)
                }
            )

    async def _initialize_hardware(self) -> any:
        """Initialize SPI hardware interface."""
        try:
            # In production, this would use platform-specific SPI libraries
            # For simulation, return a mock device object
            return {
                "active": True,
                "clock_speed": self._clock_speed,
                "mode": self._mode,
                "bits_per_word": self._bits_per_word
            }
            
        except Exception as e:
            raise HardwareError(
                "Failed to initialize SPI hardware",
                "spi",
                details={"original_error": str(e)}
            )

    async def _test_device(self) -> bool:
        """Test SPI device functionality."""
        try:
            # In production, this would perform actual device testing
            # For simulation, verify mock device parameters
            return (
                self._device is not None and
                self._device["active"] and
                self._device["clock_speed"] == self._clock_speed and
                self._device["mode"] == self._mode
            )
            
        except Exception as e:
            self.logger.error("SPI device test failed", error=e)
            return False

    async def write_register(self, register: int, value: int,
                           retries: Optional[int] = None) -> None:
        """Write value to device register via SPI."""
        retries = retries if retries is not None else self._retries
        
        try:
            if not self._initialized:
                raise HardwareError(
                    "SPI interface not initialized",
                    "spi"
                )
            
            success = False
            last_error = None
            
            for attempt in range(retries):
                try:
                    await self._write_transaction(register, value)
                    success = True
                    break
                except Exception as e:
                    last_error = e
                    await asyncio.sleep(0.01 * (attempt + 1))
            
            if not success:
                raise HardwareError(
                    "SPI write failed after retries",
                    "spi",
                    details={
                        "register": hex(register),
                        "value": hex(value),
                        "original_error": str(last_error)
                    }
                )
            
            await self._record_transaction("write", register, value)
            
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            raise HardwareError(
                "SPI write failed",
                "spi",
                details={
                    "register": hex(register),
                    "value": hex(value),
                    "original_error": str(e)
                }
            )

    async def read_register(self, register: int,
                          retries: Optional[int] = None) -> int:
        """Read value from device register via SPI."""
        retries = retries if retries is not None else self._retries
        
        try:
            if not self._initialized:
                raise HardwareError(
                    "SPI interface not initialized",
                    "spi"
                )
            
            success = False
            last_error = None
            value = None
            
            for attempt in range(retries):
                try:
                    value = await self._read_transaction(register)
                    success = True
                    break
                except Exception as e:
                    last_error = e
                    await asyncio.sleep(0.01 * (attempt + 1))
            
            if not success:
                raise HardwareError(
                    "SPI read failed after retries",
                    "spi",
                    details={
                        "register": hex(register),
                        "original_error": str(last_error)
                    }
                )
            
            await self._record_transaction("read", register, value)
            return value
            
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            raise HardwareError(
                "SPI read failed",
                "spi",
                details={
                    "register": hex(register),
                    "original_error": str(e)
                }
            )

    async def transfer(self, data: List[int], retries: Optional[int] = None) -> List[int]:
        """Perform full-duplex SPI data transfer."""
        retries = retries if retries is not None else self._retries
        
        try:
            if not self._initialized:
                raise HardwareError(
                    "SPI interface not initialized",
                    "spi"
                )
            
            success = False
            last_error = None
            response = None
            
            for attempt in range(retries):
                try:
                    response = await self._transfer_transaction(data)
                    success = True
                    break
                except Exception as e:
                    last_error = e
                    await asyncio.sleep(0.01 * (attempt + 1))
            
            if not success:
                raise HardwareError(
                    "SPI transfer failed after retries",
                    "spi",
                    details={
                        "data_length": len(data),
                        "original_error": str(last_error)
                    }
                )
            
            await self._record_transaction("transfer", None, response)
            return response
            
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            raise HardwareError(
                "SPI transfer failed",
                "spi",
                details={
                    "data_length": len(data),
                    "original_error": str(e)
                }
            )

    async def _write_transaction(self, register: int, value: int) -> None:
        """Execute SPI write transaction."""
        try:
            self._active_transactions += 1
            
            # In production, this would perform actual SPI write
            # For simulation, we'll just log the transaction
            self.logger.debug(
                f"SPI Write: Register 0x{register:02X}, Value 0x{value:02X}"
            )
            
            # Simulate transaction time
            await asyncio.sleep(0.0005)  # 500µs
            
        finally:
            self._active_transactions -= 1

    async def _read_transaction(self, register: int) -> int:
        """Execute SPI read transaction."""
        try:
            self._active_transactions += 1
            
            # In production, this would perform actual SPI read
            # For simulation, return a mock value
            self.logger.debug(f"SPI Read: Register 0x{register:02X}")
            
            # Simulate transaction time
            await asyncio.sleep(0.0005)  # 500µs
            
            # Return mock value based on register
            return (register ^ 0xAA) & 0xFF
            
        finally:
            self._active_transactions -= 1

    async def _transfer_transaction(self, data: List[int]) -> List[int]:
        """Execute full-duplex SPI transfer transaction."""
        try:
            self._active_transactions += 1
            
            # In production, this would perform actual SPI transfer
            # For simulation, return mock response
            self.logger.debug(f"SPI Transfer: {len(data)} bytes")
            
            # Simulate transaction time
            await asyncio.sleep(0.001 * len(data))  # 1ms per byte
            
            # Generate mock response
            response = [(b ^ 0xAA) & 0xFF for b in data]
            return response
            
        finally:
            self._active_transactions -= 1

    async def _record_transaction(self, operation: str, register: Optional[int],
                                data: any) -> None:
        """Record SPI transaction for monitoring."""
        transaction = {
            "timestamp": asyncio.get_event_loop().time(),
            "operation": operation,
            "register": hex(register) if register is not None else None,
            "data": data if isinstance(data, (int, type(None)))
                   else [hex(b) for b in data]
        }
        
        self._transaction_history.append(transaction)
        
        # Maintain maximum history size
        if len(self._transaction_history) > self._MAX_HISTORY:
            self._transaction_history.pop(0)

    async def set_clock_speed(self, speed: int) -> None:
        """Set SPI clock speed in Hz."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "SPI interface not initialized",
                    "spi"
                )
            
            # In production, this would configure actual hardware
            self._clock_speed = speed
            self.logger.debug(f"SPI clock speed set to {speed} Hz")
            
        except Exception as e:
            raise HardwareError(
                "Failed to set clock speed",
                "spi",
                details={"speed": speed, "original_error": str(e)}
            )

    async def set_mode(self, mode: int) -> None:
        """Set SPI mode (0-3)."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "SPI interface not initialized",
                    "spi"
                )
            
            if not 0 <= mode <= 3:
                raise ValueError("SPI mode must be 0-3")
            
            # In production, this would configure actual hardware
            self._mode = mode
            self.logger.debug(f"SPI mode set to {mode}")
            
        except Exception as e:
            raise HardwareError(
                "Failed to set mode",
                "spi",
                details={"mode": mode, "original_error": str(e)}
            )

    async def get_status(self) -> Dict:
        """Get current SPI interface status."""
        return {
            "initialized": self._initialized,
            "bus_number": self._bus_number,
            "chip_select": self._chip_select,
            "active_transactions": self._active_transactions,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "clock_speed": self._clock_speed,
            "mode": self._mode,
            "transaction_count": len(self._transaction_history)
        }

    async def cleanup(self) -> None:
        """Cleanup SPI interface resources."""
        try:
            # Wait for active transactions to complete
            while self._active_transactions > 0:
                await asyncio.sleep(0.01)
            
            # In production, this would close the SPI device
            self._device = None
            self._initialized = False
            
            self.logger.info("SPI interface cleaned up successfully")
            
        except Exception as e:
            self.logger.error("Failed to cleanup SPI interface", error=e)
            raise HardwareError(
                "Cleanup failed",
                "spi",
                details={"original_error": str(e)}
            )