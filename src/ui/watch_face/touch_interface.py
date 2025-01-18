import asyncio
from typing import Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from src.utils.error_handling import InteractionError
from src.utils.logging_utils import HolographicWatchLogger
from src.ui.watch_face.main_display import MainDisplay, DisplayMode

class TouchEventType(Enum):
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    PINCH = "pinch"
    ROTATE = "rotate"

class TouchGestureDirection(Enum):
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"

@dataclass
class TouchPoint:
    x: int
    y: int
    pressure: float
    timestamp: float

@dataclass
class TouchEvent:
    type: TouchEventType
    points: List[TouchPoint]
    direction: TouchGestureDirection
    scale: Optional[float] = None
    rotation: Optional[float] = None
    duration: Optional[float] = None

class TouchInterface:
    """Manages the watch face touch interface."""
    
    def __init__(self, display: MainDisplay):
        self.logger = HolographicWatchLogger(__name__)
        self._display = display
        self._initialized = False
        
        # Touch parameters
        self._touch_threshold = 0.1  # Minimum pressure
        self._double_tap_threshold = 0.3  # seconds
        self._long_press_threshold = 0.5  # seconds
        self._swipe_threshold = 50  # pixels
        
        # Touch state tracking
        self._current_touch: Optional[TouchPoint] = None
        self._last_touch: Optional[TouchPoint] = None
        self._touch_start_time: Optional[float] = None
        self._touch_history: List[TouchPoint] = []
        
        # Event handling
        self._event_handlers: Dict[TouchEventType, List[Callable]] = {
            event_type: [] for event_type in TouchEventType
        }
        
        # Touch regions
        self._touch_regions: Dict[str, Dict] = {}
        
        # Performance monitoring
        self._touch_latency: List[float] = []
        self._MAX_LATENCY_HISTORY = 100

    async def initialize(self) -> bool:
        """Initialize the touch interface."""
        try:
            self.logger.info("Initializing touch interface")
            
            # Initialize touch hardware
            await self._initialize_touch()
            
            # Create default touch regions
            await self._create_default_regions()
            
            # Start touch processing loop
            asyncio.create_task(self._touch_processing_loop())
            
            self._initialized = True
            self.logger.info("Touch interface initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Touch interface initialization failed", error=e)
            raise InteractionError(
                "Failed to initialize touch interface",
                "touch",
                details={"original_error": str(e)}
            )

    async def _initialize_touch(self) -> None:
        """Initialize touch hardware."""
        try:
            # In production, this would initialize actual touch hardware
            # For simulation, we'll just set up our touch state
            self._current_touch = None
            self._last_touch = None
            self._touch_start_time = None
            
            # Clear touch history
            self._touch_history.clear()
            
        except Exception as e:
            raise InteractionError(
                "Failed to initialize touch hardware",
                "touch",
                details={"original_error": str(e)}
            )

    async def _create_default_regions(self) -> None:
        """Create default touch regions."""
        try:
            # Create regions for different areas of the watch face
            self._touch_regions = {
                "center": {
                    "bounds": (150, 150, 250, 250),
                    "actions": {
                        TouchEventType.TAP: self._handle_center_tap,
                        TouchEventType.LONG_PRESS: self._handle_center_long_press
                    }
                },
                "top": {
                    "bounds": (150, 0, 250, 100),
                    "actions": {
                        TouchEventType.SWIPE: self._handle_top_swipe
                    }
                },
                "bottom": {
                    "bounds": (150, 300, 250, 400),
                    "actions": {
                        TouchEventType.SWIPE: self._handle_bottom_swipe
                    }
                }
            }
            
        except Exception as e:
            raise InteractionError(
                "Failed to create touch regions",
                "touch",
                details={"original_error": str(e)}
            )

    async def _touch_processing_loop(self) -> None:
        """Main touch processing loop."""
        while self._initialized:
            try:
                # Read touch input
                touch_data = await self._read_touch_input()
                
                if touch_data:
                    start_time = asyncio.get_event_loop().time()
                    
                    # Process touch data
                    event = await self._process_touch_data(touch_data)
                    
                    if event:
                        # Handle touch event
                        await self._handle_touch_event(event)
                        
                        # Track latency
                        latency = asyncio.get_event_loop().time() - start_time
                        await self._track_latency(latency)
                
                await asyncio.sleep(0.01)  # 100Hz polling rate
                
            except Exception as e:
                self.logger.error("Touch processing error", error=e)
                await asyncio.sleep(1.0)

    async def _read_touch_input(self) -> Optional[Dict]:
        """Read touch input data."""
        try:
            # In production, this would read from actual touch hardware
            # For simulation, we'll return None to indicate no touch
            return None
            
        except Exception as e:
            self.logger.error("Touch input read failed", error=e)
            return None

    async def _process_touch_data(self, touch_data: Dict) -> Optional[TouchEvent]:
        """Process raw touch input data."""
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Create touch point from data
            touch_point = TouchPoint(
                x=touch_data.get("x", 0),
                y=touch_data.get("y", 0),
                pressure=touch_data.get("pressure", 0.0),
                timestamp=current_time
            )
            
            # Update touch state
            self._last_touch = self._current_touch
            self._current_touch = touch_point
            
            if touch_point.pressure > self._touch_threshold:
                # Start of touch
                if not self._touch_start_time:
                    self._touch_start_time = current_time
                    self._touch_history.clear()
                
                # Add to history
                self._touch_history.append(touch_point)
                
                # Detect gesture
                return await self._detect_gesture(touch_point)
            else:
                # End of touch
                if self._touch_start_time:
                    # Process complete gesture
                    event = await self._process_complete_gesture()
                    
                    # Reset touch state
                    self._touch_start_time = None
                    self._touch_history.clear()
                    
                    return event
            
            return None
            
        except Exception as e:
            self.logger.error("Touch processing failed", error=e)
            return None

    async def _detect_gesture(self, touch_point: TouchPoint) -> Optional[TouchEvent]:
        """Detect ongoing gesture from touch point."""
        try:
            current_time = asyncio.get_event_loop().time()
            duration = current_time - self._touch_start_time
            
            # Check for long press
            if duration > self._long_press_threshold:
                return TouchEvent(
                    type=TouchEventType.LONG_PRESS,
                    points=self._touch_history.copy(),
                    direction=TouchGestureDirection.NONE,
                    duration=duration
                )
            
            # Check for swipe
            if len(self._touch_history) > 1:
                start_point = self._touch_history[0]
                dx = touch_point.x - start_point.x
                dy = touch_point.y - start_point.y
                
                if abs(dx) > self._swipe_threshold or abs(dy) > self._swipe_threshold:
                    direction = self._determine_swipe_direction(dx, dy)
                    return TouchEvent(
                        type=TouchEventType.SWIPE,
                        points=self._touch_history.copy(),
                        direction=direction,
                        duration=duration
                    )
            
            return None
            
        except Exception as e:
            self.logger.error("Gesture detection failed", error=e)
            return None

    def _determine_swipe_direction(self, dx: float, dy: float) -> TouchGestureDirection:
        """Determine swipe direction from deltas."""
        if abs(dx) > abs(dy):
            return (
                TouchGestureDirection.RIGHT if dx > 0
                else TouchGestureDirection.LEFT
            )
        else:
            return (
                TouchGestureDirection.UP if dy < 0
                else TouchGestureDirection.DOWN
            )

    async def _process_complete_gesture(self) -> Optional[TouchEvent]:
        """Process completed gesture."""
        try:
            if not self._touch_history:
                return None
            
            current_time = asyncio.get_event_loop().time()
            duration = current_time - self._touch_start_time
            
            # Check for tap or double tap
            if duration < self._long_press_threshold:
                if self._last_touch and (
                    current_time - self._last_touch.timestamp <
                    self._double_tap_threshold
                ):
                    return TouchEvent(
                        type=TouchEventType.DOUBLE_TAP,
                        points=self._touch_history.copy(),
                        direction=TouchGestureDirection.NONE,
                        duration=duration
                    )
                else:
                    return TouchEvent(
                        type=TouchEventType.TAP,
                        points=self._touch_history.copy(),
                        direction=TouchGestureDirection.NONE,
                        duration=duration
                    )
            
            return None
            
        except Exception as e:
            self.logger.error("Complete gesture processing failed", error=e)
            return None

    async def _handle_touch_event(self, event: TouchEvent) -> None:
        """Handle touch event."""
        try:
            # Notify display of activity
            await self._display.notify_activity()
            
            # Find matching touch region
            region = self._find_touch_region(event.points[-1])
            
            if region:
                # Execute region-specific handler
                handler = region["actions"].get(event.type)
                if handler:
                    await handler(event)
            
            # Execute global event handlers
            for handler in self._event_handlers[event.type]:
                try:
                    await handler(event)
                except Exception as handler_error:
                    self.logger.error(
                        f"Event handler error: {str(handler_error)}"
                    )
            
            self.logger.debug(
                f"Processed touch event: {event.type.value}, "
                f"direction: {event.direction.value}"
            )
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle touch event",
                "touch",
                details={"event_type": event.type.value, "original_error": str(e)}
            )

    def _find_touch_region(self, touch_point: TouchPoint) -> Optional[Dict]:
        """Find touch region containing point."""
        try:
            for region_id, region in self._touch_regions.items():
                bounds = region["bounds"]
                if (
                    bounds[0] <= touch_point.x <= bounds[2] and
                    bounds[1] <= touch_point.y <= bounds[3]
                ):
                    return region
            return None
            
        except Exception as e:
            self.logger.error("Touch region search failed", error=e)
            return None

    async def _handle_center_tap(self, event: TouchEvent) -> None:
        """Handle tap in center region."""
        try:
            # Toggle between time and date display
            current_mode = await self._display.get_status()
            if current_mode["mode"] == DisplayMode.TIME.value:
                await self._display.set_display_mode(DisplayMode.DATE)
            else:
                await self._display.set_display_mode(DisplayMode.TIME)
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle center tap",
                "touch",
                details={"original_error": str(e)}
            )

    async def _handle_center_long_press(self, event: TouchEvent) -> None:
        """Handle long press in center region."""
        try:
            # Activate hologram mode
            await self._display.set_display_mode(DisplayMode.HOLOGRAM)
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle center long press",
                "touch",
                details={"original_error": str(e)}
            )

    async def _handle_top_swipe(self, event: TouchEvent) -> None:
        """Handle swipe in top region."""
        try:
            if event.direction == TouchGestureDirection.DOWN:
                # Show notifications
                await self._display.set_display_mode(DisplayMode.NOTIFICATIONS)
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle top swipe",
                "touch",
                details={"original_error": str(e)}
            )

    async def _handle_bottom_swipe(self, event: TouchEvent) -> None:
        """Handle swipe in bottom region."""
        try:
            if event.direction == TouchGestureDirection.UP:
                # Show quick settings
                await self._display.set_display_mode(DisplayMode.SETTINGS)
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle bottom swipe",
                "touch",
                details={"original_error": str(e)}
            )

    async def register_event_handler(self, event_type: TouchEventType,
                                   handler: Callable) -> None:
        """Register handler for touch events."""
        try:
            if event_type not in self._event_handlers:
                raise ValueError(f"Invalid event type: {event_type}")
            
            self._event_handlers[event_type].append(handler)
            
            self.logger.debug(
                f"Registered handler for {event_type.value} events"
            )
            
        except Exception as e:
            raise InteractionError(
                "Failed to register event handler",
                "touch",
                details={"event_type": event_type.value, "original_error": str(e)}
            )

    async def unregister_event_handler(self, event_type: TouchEventType,
                                     handler: Callable) -> None:
        """Unregister touch event handler."""
        try:
            if event_type not in self._event_handlers:
                raise ValueError(f"Invalid event type: {event_type}")
            
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)
                
                self.logger.debug(
                    f"Unregistered handler for {event_type.value} events"
                )
            
        except Exception as e:
            raise InteractionError(
                "Failed to unregister event handler",
                "touch",
                details={"event_type": event_type.value, "original_error": str(e)}
            )

    async def _track_latency(self, latency: float) -> None:
        """Track touch processing latency."""
        self._touch_latency.append(latency)
        
        # Maintain maximum history size
        if len(self._touch_latency) > self._MAX_LATENCY_HISTORY:
            self._touch_latency.pop(0)

    async def get_performance_metrics(self) -> Dict:
        """Get touch interface performance metrics."""
        try:
            if not self._touch_latency:
                return {
                    "average_latency": 0.0,
                    "max_latency": 0.0,
                    "min_latency": 0.0
                }
            
            return {
                "average_latency": (
                    sum(self._touch_latency) / len(self._touch_latency) * 1000
                ),  # Convert to ms
                "max_latency": max(self._touch_latency) * 1000,
                "min_latency": min(self._touch_latency) * 1000
            }
            
        except Exception as e:
            self.logger.error("Failed to get performance metrics", error=e)
            return {
                "error": str(e)
            }

    async def get_status(self) -> Dict:
        """Get current touch interface status."""
        return {
            "initialized": self._initialized,
            "touch_active": bool(self._current_touch),
            "last_touch_time": (
                self._last_touch.timestamp if self._last_touch else None
            ),
            "registered_handlers": {
                event_type.value: len(handlers)
                for event_type, handlers in self._event_handlers.items()
            },
            "touch_regions": list(self._touch_regions.keys())
        }

    async def cleanup(self) -> None:
        """Cleanup touch interface resources."""
        try:
            self._initialized = False
            
            # Clear state
            self._current_touch = None
            self._last_touch = None
            self._touch_start_time = None
            self._touch_history.clear()
            
            # Clear handlers
            for handlers in self._event_handlers.values():
                handlers.clear()
            
            # Clear performance metrics
            self._touch_latency.clear()
            
            self.logger.info("Touch interface cleaned up successfully")
            
        except Exception as e:
            self.logger.error("Failed to cleanup touch interface", error=e)
            raise InteractionError(
                "Cleanup failed",
                "touch",
                details={"original_error": str(e)}
            )