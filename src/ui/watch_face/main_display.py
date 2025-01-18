import asyncio
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from src.utils.error_handling import InteractionError
from src.utils.logging_utils import HolographicWatchLogger
from src.core.system_interface.status_monitor import StatusMonitor

class DisplayMode(Enum):
    TIME = "time"
    DATE = "date"
    HOLOGRAM = "hologram"
    NOTIFICATIONS = "notifications"
    SETTINGS = "settings"
    POWER = "power"

class DisplayState(Enum):
    ACTIVE = "active"
    DIM = "dim"
    SLEEP = "sleep"
    OFF = "off"

@dataclass
class DisplayConfiguration:
    brightness: float  # 0.0-1.0
    contrast: float   # 0.0-1.0
    color_temperature: int  # Kelvin
    refresh_rate: int  # Hz
    resolution: Tuple[int, int]
    power_mode: str  # "normal", "eco", "ultra_low"

@dataclass
class DisplayElement:
    id: str
    type: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    content: Dict
    visible: bool = True
    active: bool = True

class MainDisplay:
    """Manages the watch face display system."""
    
    def __init__(self, status_monitor: StatusMonitor):
        self.logger = HolographicWatchLogger(__name__)
        self._status_monitor = status_monitor
        self._initialized = False
        
        # Display state
        self._current_mode = DisplayMode.TIME
        self._current_state = DisplayState.OFF
        self._display_elements: Dict[str, DisplayElement] = {}
        
        # Display configuration
        self._config = DisplayConfiguration(
            brightness=0.8,
            contrast=0.9,
            color_temperature=6500,
            refresh_rate=60,
            resolution=(400, 400),
            power_mode="normal"
        )
        
        # Power management
        self._power_threshold = 0.2  # 20% battery threshold for power saving
        self._dim_timeout = 10.0  # seconds
        self._sleep_timeout = 30.0  # seconds
        self._last_activity = 0.0
        
        # Performance monitoring
        self._frame_times: List[float] = []
        self._MAX_FRAME_HISTORY = 100
        self._fps_target = 60.0
        self._power_consumption = 0.0  # mW

    async def initialize(self) -> bool:
        """Initialize the display system."""
        try:
            self.logger.info("Initializing main display")
            
            # Initialize display hardware
            await self._initialize_display()
            
            # Create default display elements
            await self._create_default_elements()
            
            # Start display update loop
            asyncio.create_task(self._update_loop())
            
            # Start power management loop
            asyncio.create_task(self._power_management_loop())
            
            self._initialized = True
            self.logger.info("Main display initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Display initialization failed", error=e)
            raise InteractionError(
                "Failed to initialize display",
                "display",
                details={"original_error": str(e)}
            )

    async def _initialize_display(self) -> None:
        """Initialize display hardware."""
        try:
            # In production, this would initialize actual display hardware
            # For simulation, we'll set up our display state
            self._current_state = DisplayState.ACTIVE
            self._last_activity = asyncio.get_event_loop().time()
            
            # Configure initial display parameters
            await self._configure_display(self._config)
            
        except Exception as e:
            raise InteractionError(
                "Failed to initialize display hardware",
                "display",
                details={"original_error": str(e)}
            )

    async def _create_default_elements(self) -> None:
        """Create default display elements."""
        try:
            # Time display
            self._display_elements["time"] = DisplayElement(
                id="time",
                type="text",
                position=(200, 200),
                size=(120, 40),
                content={
                    "text": datetime.now().strftime("%H:%M"),
                    "font": "digital",
                    "size": 36,
                    "color": "white"
                }
            )
            
            # Date display
            self._display_elements["date"] = DisplayElement(
                id="date",
                type="text",
                position=(200, 250),
                size=(100, 30),
                content={
                    "text": datetime.now().strftime("%Y-%m-%d"),
                    "font": "regular",
                    "size": 24,
                    "color": "gray"
                }
            )
            
            # Battery indicator
            self._display_elements["battery"] = DisplayElement(
                id="battery",
                type="icon",
                position=(350, 50),
                size=(30, 15),
                content={
                    "icon": "battery",
                    "level": 100,
                    "color": "green"
                }
            )
            
            # Notification indicator
            self._display_elements["notifications"] = DisplayElement(
                id="notifications",
                type="icon",
                position=(50, 50),
                size=(20, 20),
                content={
                    "icon": "bell",
                    "count": 0,
                    "color": "white"
                },
                visible=False
            )
            
        except Exception as e:
            raise InteractionError(
                "Failed to create display elements",
                "display",
                details={"original_error": str(e)}
            )

    async def _update_loop(self) -> None:
        """Main display update loop."""
        while self._initialized:
            try:
                start_time = asyncio.get_event_loop().time()
                
                if self._current_state == DisplayState.ACTIVE:
                    # Update time display
                    await self._update_time()
                    
                    # Update status indicators
                    await self._update_status()
                    
                    # Render frame
                    await self._render_frame()
                    
                    # Calculate frame time
                    frame_time = asyncio.get_event_loop().time() - start_time
                    await self._track_performance(frame_time)
                
                # Maintain target frame rate
                target_frame_time = 1.0 / self._fps_target
                remaining_time = max(0, target_frame_time - frame_time)
                await asyncio.sleep(remaining_time)
                
            except Exception as e:
                self.logger.error("Display update error", error=e)
                await asyncio.sleep(1.0)

    async def _power_management_loop(self) -> None:
        """Power management loop."""
        while self._initialized:
            try:
                current_time = asyncio.get_event_loop().time()
                time_since_activity = current_time - self._last_activity
                
                # Get battery status
                battery_status = await self._status_monitor.get_component_status(
                    "power"
                )
                battery_level = battery_status.get("battery_level", 100)
                
                # Update power state based on battery level and activity
                if battery_level < self._power_threshold:
                    await self._enter_power_saving_mode()
                elif time_since_activity > self._sleep_timeout:
                    await self.set_display_state(DisplayState.SLEEP)
                elif time_since_activity > self._dim_timeout:
                    await self.set_display_state(DisplayState.DIM)
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                self.logger.error("Power management error", error=e)
                await asyncio.sleep(5.0)

    async def _update_time(self) -> None:
        """Update time display."""
        try:
            current_time = datetime.now()
            
            # Update time element
            time_element = self._display_elements.get("time")
            if time_element:
                time_element.content["text"] = current_time.strftime("%H:%M")
            
            # Update date element
            date_element = self._display_elements.get("date")
            if date_element:
                date_element.content["text"] = current_time.strftime("%Y-%m-%d")
            
        except Exception as e:
            raise InteractionError(
                "Failed to update time display",
                "display",
                details={"original_error": str(e)}
            )

    async def _update_status(self) -> None:
        """Update status indicators."""
        try:
            # Update battery status
            battery_status = await self._status_monitor.get_component_status(
                "power"
            )
            battery_level = battery_status.get("battery_level", 100)
            
            battery_element = self._display_elements.get("battery")
            if battery_element:
                battery_element.content["level"] = battery_level
                battery_element.content["color"] = self._get_battery_color(
                    battery_level
                )
            
            # Update notification status
            notification_status = await self._status_monitor.get_component_status(
                "notifications"
            )
            notification_count = notification_status.get("count", 0)
            
            notification_element = self._display_elements.get("notifications")
            if notification_element:
                notification_element.content["count"] = notification_count
                notification_element.visible = notification_count > 0
            
        except Exception as e:
            raise InteractionError(
                "Failed to update status indicators",
                "display",
                details={"original_error": str(e)}
            )

    def _get_battery_color(self, level: float) -> str:
        """Get appropriate color for battery level."""
        if level > 50:
            return "green"
        elif level > 20:
            return "yellow"
        else:
            return "red"

    async def _render_frame(self) -> None:
        """Render display frame."""
        try:
            # In production, this would render to actual display hardware
            # For simulation, we'll just log the frame render
            self.logger.debug("Rendered display frame")
            
            # Calculate power consumption
            self._power_consumption = self._calculate_power_consumption()
            
        except Exception as e:
            raise InteractionError(
                "Failed to render display frame",
                "display",
                details={"original_error": str(e)}
            )

    async def _track_performance(self, frame_time: float) -> None:
        """Track display performance metrics."""
        self._frame_times.append(frame_time)
        
        # Maintain maximum history size
        if len(self._frame_times) > self._MAX_FRAME_HISTORY:
            self._frame_times.pop(0)

    async def _configure_display(self, config: DisplayConfiguration) -> None:
        """Configure display parameters."""
        try:
            # In production, this would configure actual display hardware
            self._config = config
            
            # Update power consumption calculation
            self._power_consumption = self._calculate_power_consumption()
            
            self.logger.debug(
                f"Display configured: brightness={config.brightness}, "
                f"refresh_rate={config.refresh_rate}Hz"
            )
            
        except Exception as e:
            raise InteractionError(
                "Failed to configure display",
                "display",
                details={"original_error": str(e)}
            )

    async def set_display_mode(self, mode: DisplayMode) -> None:
        """Set display mode."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Display not initialized",
                    "display"
                )
            
            self._current_mode = mode
            await self._update_mode_specific_elements(mode)
            
            self.logger.debug(f"Display mode set to {mode.value}")
            
        except Exception as e:
            raise InteractionError(
                "Failed to set display mode",
                "display",
                details={"mode": mode.value, "original_error": str(e)}
            )

    async def set_display_state(self, state: DisplayState) -> None:
        """Set display state."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Display not initialized",
                    "display"
                )
            
            # Update display state
            self._current_state = state
            
            # Apply state-specific configurations
            if state == DisplayState.DIM:
                await self._configure_display(
                    DisplayConfiguration(
                        brightness=0.3,
                        contrast=self._config.contrast,
                        color_temperature=self._config.color_temperature,
                        refresh_rate=30,
                        resolution=self._config.resolution,
                        power_mode="eco"
                    )
                )
            elif state == DisplayState.ACTIVE:
                await self._configure_display(self._config)
            
            self.logger.debug(f"Display state set to {state.value}")
            
        except Exception as e:
            raise InteractionError(
                "Failed to set display state",
                "display",
                details={"state": state.value, "original_error": str(e)}
            )

    async def _update_mode_specific_elements(self, mode: DisplayMode) -> None:
        """Update display elements for specific mode."""
        try:
            # Hide all elements first
            for element in self._display_elements.values():
                element.visible = False
            
            # Show mode-specific elements
            if mode == DisplayMode.TIME:
                self._display_elements["time"].visible = True
                self._display_elements["date"].visible = True
            elif mode == DisplayMode.NOTIFICATIONS:
                self._display_elements["notifications"].visible = True
            
            # Status indicators always visible
            self._display_elements["battery"].visible = True
            
        except Exception as e:
            raise InteractionError(
                "Failed to update mode elements",
                "display",
                details={"mode": mode.value, "original_error": str(e)}
            )

    async def _enter_power_saving_mode(self) -> None:
        """Enter power saving mode."""
        try:
            await self.set_display_state(DisplayState.DIM)
            
            # Configure for power saving
            await self._configure_display(
                DisplayConfiguration(
                    brightness=0.3,
                    contrast=0.8,
                    color_temperature=5000,
                    refresh_rate=30,
                    resolution=self._config.resolution,
                    power_mode="eco"
                )
            )
            
            self.logger.info("Entered power saving mode")
            
        except Exception as e:
            raise InteractionError(
                "Failed to enter power saving mode",
                "display",
                details={"original_error": str(e)}
            )

    def _calculate_power_consumption(self) -> float:
        """Calculate current power consumption in mW."""
        try:
            base_power = 100.0  # mW
            
            # Factor in display parameters
            brightness_factor = self._config.brightness
            refresh_factor = self._config.refresh_rate / 60.0
            resolution_factor = (
                self._config.resolution[0] * self._config.resolution[1]
            ) / (400 * 400)
            
            # Calculate total power consumption
            total_power = (
                base_power * 
                brightness_factor * 
                refresh_factor * 
                resolution_factor
            )
            
            # Apply power mode adjustments
            if self._config.power_mode == "eco":
                total_power *= 0.7
            elif self._config.power_mode == "ultra_low":
                total_power *= 0.4
            
            return total_power
            
        except Exception as e:
            self.logger.error("Power calculation failed", error=e)
            return base_power

    async def notify_activity(self) -> None:
        """Notify the display of user activity."""
        try:
            self._last_activity = asyncio.get_event_loop().time()
            
            # Reactivate display if needed
            if self._current_state != DisplayState.ACTIVE:
                await self.set_display_state(DisplayState.ACTIVE)
            
        except Exception as e:
            raise InteractionError(
                "Failed to notify activity",
                "display",
                details={"original_error": str(e)}
            )

    async def add_display_element(self, element: DisplayElement) -> None:
        """Add new display element."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Display not initialized",
                    "display"
                )
            
            # Validate element position and size
            if not self._validate_element_bounds(element):
                raise ValueError("Element bounds outside display area")
            
            # Add element to display
            self._display_elements[element.id] = element
            
            self.logger.debug(f"Added display element: {element.id}")
            
        except Exception as e:
            raise InteractionError(
                "Failed to add display element",
                "display",
                details={"element_id": element.id, "original_error": str(e)}
            )

    async def remove_display_element(self, element_id: str) -> None:
        """Remove display element."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Display not initialized",
                    "display"
                )
            
            if element_id in self._display_elements:
                del self._display_elements[element_id]
                self.logger.debug(f"Removed display element: {element_id}")
            
        except Exception as e:
            raise InteractionError(
                "Failed to remove display element",
                "display",
                details={"element_id": element_id, "original_error": str(e)}
            )

    async def update_element_content(self, element_id: str,
                                   content: Dict) -> None:
        """Update display element content."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Display not initialized",
                    "display"
                )
            
            if element_id not in self._display_elements:
                raise ValueError(f"Element not found: {element_id}")
            
            # Update element content
            self._display_elements[element_id].content.update(content)
            
            self.logger.debug(f"Updated content for element: {element_id}")
            
        except Exception as e:
            raise InteractionError(
                "Failed to update element content",
                "display",
                details={"element_id": element_id, "original_error": str(e)}
            )

    def _validate_element_bounds(self, element: DisplayElement) -> bool:
        """Validate element position and size."""
        try:
            # Check if element fits within display bounds
            max_x = self._config.resolution[0]
            max_y = self._config.resolution[1]
            
            element_right = element.position[0] + element.size[0]
            element_bottom = element.position[1] + element.size[1]
            
            return (
                element.position[0] >= 0 and
                element.position[1] >= 0 and
                element_right <= max_x and
                element_bottom <= max_y
            )
            
        except Exception as e:
            self.logger.error("Element validation failed", error=e)
            return False

    async def get_performance_metrics(self) -> Dict:
        """Get display performance metrics."""
        try:
            if not self._frame_times:
                return {
                    "average_fps": 0.0,
                    "frame_time": 0.0,
                    "power_consumption": 0.0
                }
            
            average_frame_time = sum(self._frame_times) / len(self._frame_times)
            current_fps = 1.0 / average_frame_time if average_frame_time > 0 else 0
            
            return {
                "average_fps": current_fps,
                "frame_time": average_frame_time * 1000,  # Convert to ms
                "power_consumption": self._power_consumption
            }
            
        except Exception as e:
            self.logger.error("Failed to get performance metrics", error=e)
            return {
                "error": str(e)
            }

    async def get_status(self) -> Dict:
        """Get current display status."""
        return {
            "initialized": self._initialized,
            "mode": self._current_mode.value,
            "state": self._current_state.value,
            "brightness": self._config.brightness,
            "refresh_rate": self._config.refresh_rate,
            "power_mode": self._config.power_mode,
            "active_elements": len(self._display_elements),
            "power_consumption": self._power_consumption,
            "time_since_activity": (
                asyncio.get_event_loop().time() - self._last_activity
            )
        }

    async def cleanup(self) -> None:
        """Cleanup display resources."""
        try:
            self._initialized = False
            
            # Turn off display
            await self.set_display_state(DisplayState.OFF)
            
            # Clear all elements
            self._display_elements.clear()
            
            # Clear performance metrics
            self._frame_times.clear()
            
            self.logger.info("Display cleaned up successfully")
            
        except Exception as e:
            self.logger.error("Failed to cleanup display", error=e)
            raise InteractionError(
                "Cleanup failed",
                "display",
                details={"original_error": str(e)}
            )