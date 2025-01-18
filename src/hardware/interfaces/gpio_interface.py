import asyncio
from typing import Dict, Optional, List, Callable
from enum import Enum
from src.utils.error_handling import HardwareError
from src.utils.logging_utils import HolographicWatchLogger

class GPIODirection(Enum):
    INPUT = "input"
    OUTPUT = "output"

class GPIOEdge(Enum):
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"
    NONE = "none"

class GPIOPull(Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"

class GPIOInterface:
    """Interface for GPIO operations."""
    
    def __init__(self):
        self.logger = HolographicWatchLogger(__name__)
        self._initialized = False
        
        # GPIO state tracking
        self._pin_states: Dict[int, bool] = {}
        self._pin_directions: Dict[int, GPIODirection] = {}
        self._pin_edges: Dict[int, GPIOEdge] = {}
        self._pin_pulls: Dict[int, GPIOPull] = {}
        
        # Interrupt handling
        self._interrupt_handlers: Dict[int, List[Callable]] = {}
        self._interrupt_tasks: Dict[int, asyncio.Task] = {}
        
        # Event monitoring
        self._event_history: List[Dict] = []
        self._MAX_HISTORY = 1000
        
        # Error tracking
        self._error_count = 0
        self._last_error = None

    async def initialize(self) -> bool:
        """Initialize the GPIO interface."""
        try:
            self.logger.info("Initializing GPIO interface")
            
            # In production, this would initialize actual GPIO hardware
            # For simulation, we'll create a mock GPIO system
            await self._initialize_hardware()
            
            # Test GPIO functionality
            if not await self._test_gpio():
                raise HardwareError(
                    "GPIO test failed",
                    "gpio"
                )
            
            self._initialized = True
            self.logger.info("GPIO interface initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("GPIO initialization failed", error=e)
            raise HardwareError(
                "Failed to initialize GPIO interface",
                "gpio",
                details={"original_error": str(e)}
            )

    async def _initialize_hardware(self) -> None:
        """Initialize GPIO hardware system."""
        try:
            # In production, this would use platform-specific GPIO libraries
            # For simulation, we'll just set up our tracking dictionaries
            self._pin_states.clear()
            self._pin_directions.clear()
            self._pin_edges.clear()
            self._pin_pulls.clear()
            
        except Exception as e:
            raise HardwareError(
                "Failed to initialize GPIO hardware",
                "gpio",
                details={"original_error": str(e)}
            )

    async def _test_gpio(self) -> bool:
        """Test GPIO functionality."""
        try:
            # Test pin configuration
            await self.configure_pin(18, GPIODirection.OUTPUT)
            if self._pin_directions.get(18) != GPIODirection.OUTPUT:
                return False
            
            # Test write/read operations
            await self.write_pin(18, True)
            if not self._pin_states.get(18, False):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("GPIO test failed", error=e)
            return False

    async def configure_pin(self, pin: int, direction: GPIODirection,
                          pull: GPIOPull = GPIOPull.NONE,
                          edge: GPIOEdge = GPIOEdge.NONE) -> None:
        """Configure GPIO pin settings."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "GPIO interface not initialized",
                    "gpio"
                )
            
            # Validate pin number
            if not self._is_valid_pin(pin):
                raise ValueError(f"Invalid pin number: {pin}")
            
            # In production, this would configure actual GPIO hardware
            self._pin_directions[pin] = direction
            self._pin_pulls[pin] = pull
            self._pin_edges[pin] = edge
            
            # Initialize pin state
            if direction == GPIODirection.OUTPUT:
                self._pin_states[pin] = False
            
            await self._record_event("configure", pin, {
                "direction": direction.value,
                "pull": pull.value,
                "edge": edge.value
            })
            
            self.logger.debug(
                f"Configured GPIO pin {pin}: "
                f"direction={direction.value}, pull={pull.value}, edge={edge.value}"
            )
            
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            raise HardwareError(
                "Failed to configure GPIO pin",
                "gpio",
                details={
                    "pin": pin,
                    "direction": direction.value,
                    "original_error": str(e)
                }
            )

    async def write_pin(self, pin: int, value: bool) -> None:
        """Write value to GPIO output pin."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "GPIO interface not initialized",
                    "gpio"
                )
            
            # Validate pin configuration
            if pin not in self._pin_directions:
                raise ValueError(f"Pin {pin} not configured")
            
            if self._pin_directions[pin] != GPIODirection.OUTPUT:
                raise ValueError(f"Pin {pin} not configured as output")
            
            # In production, this would set actual GPIO hardware
            self._pin_states[pin] = value
            
            await self._record_event("write", pin, {"value": value})
            
            self.logger.debug(f"Write GPIO pin {pin}: {value}")
            
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            raise HardwareError(
                "Failed to write to GPIO pin",
                "gpio",
                details={
                    "pin": pin,
                    "value": value,
                    "original_error": str(e)
                }
            )

    async def read_pin(self, pin: int) -> bool:
        """Read value from GPIO input pin."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "GPIO interface not initialized",
                    "gpio"
                )
            
            # Validate pin configuration
            if pin not in self._pin_directions:
                raise ValueError(f"Pin {pin} not configured")
            
            # In production, this would read actual GPIO hardware
            value = self._pin_states.get(pin, False)
            
            await self._record_event("read", pin, {"value": value})
            
            return value
            
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            raise HardwareError(
                "Failed to read from GPIO pin",
                "gpio",
                details={
                    "pin": pin,
                    "original_error": str(e)
                }
            )

    async def register_interrupt(self, pin: int,
                               callback: Callable[[int, bool], None]) -> None:
        """Register interrupt handler for GPIO pin."""
        try:
            if not self._initialized:
                raise HardwareError(
                    "GPIO interface not initialized",
                    "gpio"
                )
            
            # Validate pin configuration
            if pin not in self._pin_directions:
                raise ValueError(f"Pin {pin} not configured")
            
            if self._pin_edges[pin] == GPIOEdge.NONE:
                raise ValueError(f"Pin {pin} not configured for interrupts")
            
            # Add callback to handlers
            if pin not in self._interrupt_handlers:
                self._interrupt_handlers[pin] = []
            self._interrupt_handlers[pin].append(callback)
            
            # Start interrupt monitoring if not already running
            if pin not in self._interrupt_tasks:
                self._interrupt_tasks[pin] = asyncio.create_task(
                    self._monitor_interrupts(pin)
                )
            
            await self._record_event("register_interrupt", pin, {})
            
            self.logger.debug(f"Registered interrupt handler for pin {pin}")
            
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            raise HardwareError(
                "Failed to register interrupt handler",
                "gpio",
                details={
                    "pin": pin,
                    "original_error": str(e)
                }
            )

    async def _monitor_interrupts(self, pin: int) -> None:
        """Monitor pin for interrupt conditions."""
        try:
            last_value = await self.read_pin(pin)
            
            while self._initialized and pin in self._interrupt_handlers:
                value = await self.read_pin(pin)
                edge = self._pin_edges[pin]
                
                if value != last_value:
                    if (edge == GPIOEdge.BOTH or
                        (edge == GPIOEdge.RISING and value) or
                        (edge == GPIOEdge.FALLING and not value)):
                        # Trigger callbacks
                        for handler in self._interrupt_handlers[pin]:
                            try:
                                handler(pin, value)
                            except Exception as handler_error:
                                self.logger.error(
                                    f"Interrupt handler error for pin {pin}",
                                    error=handler_error
                                )
                
                last_value = value
                await asyncio.sleep(0.001)  # 1ms polling interval
                
        except Exception as e:
            self.logger.error(
                f"Interrupt monitoring failed for pin {pin}",
                error=e
            )

    async def _record_event(self, operation: str, pin: int,
                          details: Dict) -> None:
        """Record GPIO event for monitoring."""
        event = {
            "timestamp": asyncio.get_event_loop().time(),
            "operation": operation,
            "pin": pin,
            **details
        }
        
        self._event_history.append(event)
        
        # Maintain maximum history size
        if len(self._event_history) > self._MAX_HISTORY:
            self._event_history.pop(0)

    def _is_valid_pin(self, pin: int) -> bool:
        """Validate GPIO pin number."""
        # In production, this would check against actual hardware capabilities
        return 0 <= pin <= 40  # Example range for Raspberry Pi

    async def get_status(self) -> Dict:
        """Get current GPIO interface status."""
        return {
            "initialized": self._initialized,
            "configured_pins": list(self._pin_directions.keys()),
            "active_interrupts": list(self._interrupt_tasks.keys()),
            "error_count": self._error_count,
            "last_error": self._last_error,
            "event_count": len(self._event_history)
        }

    async def cleanup(self) -> None:
        """Cleanup GPIO interface resources."""
        try:
            # Cancel all interrupt monitoring tasks
            for task in self._interrupt_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(
                *self._interrupt_tasks.values(),
                return_exceptions=True
            )
            
            # Reset all pins to safe state
            for pin in list(self._pin_directions.keys()):
                await self.configure_pin(pin, GPIODirection.INPUT, GPIOPull.NONE)
            
            # Clear all state
            self._pin_states.clear()
            self._pin_directions.clear()
            self._pin_edges.clear()
            self._pin_pulls.clear()
            self._interrupt_handlers.clear()
            self._interrupt_tasks.clear()
            
            self._initialized = False
            self.logger.info("GPIO interface cleaned up successfully")
            
        except Exception as e:
            self.logger.error("Failed to cleanup GPIO interface", error=e)
            raise HardwareError(
                "Cleanup failed",
                "gpio",
                details={"original_error": str(e)}
            )