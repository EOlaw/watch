import asyncio
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
from src.utils.error_handling import InteractionError
from src.utils.logging_utils import HolographicWatchLogger
from src.ui.hologram_ui.gesture_recognition import GestureType, GestureData

class InteractionState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    PROCESSING = "processing"
    ERROR = "error"

class InteractionMode(Enum):
    NAVIGATION = "navigation"
    SELECTION = "selection"
    MANIPULATION = "manipulation"
    COMMAND = "command"

@dataclass
class InteractionContext:
    state: InteractionState
    mode: InteractionMode
    selected_element: Optional[str] = None
    active_command: Optional[str] = None
    last_gesture: Optional[GestureData] = None
    interaction_data: Optional[Dict] = None

class InteractionHandler:
    """Handles holographic interface interactions."""
    
    def __init__(self):
        self.logger = HolographicWatchLogger(__name__)
        self._initialized = False
        
        # Interaction state
        self._context = InteractionContext(
            state=InteractionState.IDLE,
            mode=InteractionMode.NAVIGATION
        )
        
        # Command mapping
        self._gesture_commands = {
            GestureType.SWIPE_LEFT: self._handle_swipe_left,
            GestureType.SWIPE_RIGHT: self._handle_swipe_right,
            GestureType.SWIPE_UP: self._handle_swipe_up,
            GestureType.SWIPE_DOWN: self._handle_swipe_down,
            GestureType.PINCH: self._handle_pinch,
            GestureType.SPREAD: self._handle_spread,
            GestureType.ROTATE_CW: self._handle_rotate_clockwise,
            GestureType.ROTATE_CCW: self._handle_rotate_counterclockwise,
            GestureType.TAP: self._handle_tap,
            GestureType.DOUBLE_TAP: self._handle_double_tap,
            GestureType.HOLD: self._handle_hold
        }
        
        # Interaction history
        self._interaction_history: List[Dict] = []
        self._MAX_HISTORY = 100
        
        # Performance metrics
        self._interaction_count = 0
        self._error_count = 0
        self._average_response_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the interaction handler."""
        try:
            self.logger.info("Initializing interaction handler")
            
            # Initialize interaction state
            self._context = InteractionContext(
                state=InteractionState.IDLE,
                mode=InteractionMode.NAVIGATION
            )
            
            self._initialized = True
            self.logger.info("Interaction handler initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Interaction handler initialization failed", error=e)
            raise InteractionError(
                "Failed to initialize interaction handler",
                "handler",
                details={"original_error": str(e)}
            )

    async def handle_gesture(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle gesture-based interaction."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Interaction handler not initialized",
                    "handler"
                )
            
            start_time = asyncio.get_event_loop().time()
            
            # Update context
            self._context.state = InteractionState.PROCESSING
            self._context.last_gesture = gesture
            
            # Get appropriate handler for gesture type
            handler = self._gesture_commands.get(gesture.type)
            if not handler:
                raise InteractionError(
                    f"Unsupported gesture type: {gesture.type}",
                    "handler"
                )
            
            # Execute gesture handler
            response = await handler(gesture)
            
            # Update metrics
            self._interaction_count += 1
            self._update_response_time(
                asyncio.get_event_loop().time() - start_time
            )
            
            # Record interaction
            await self._record_interaction(gesture, response)
            
            # Update context state
            self._context.state = InteractionState.ACTIVE
            
            return response
            
        except Exception as e:
            self._error_count += 1
            self._context.state = InteractionState.ERROR
            self.logger.error("Gesture handling failed", error=e)
            raise InteractionError(
                "Failed to handle gesture",
                "handler",
                details={"gesture_type": gesture.type.value, "original_error": str(e)}
            )

    async def handle_voice_command(self, command_data: Dict) -> Dict[str, Any]:
        """Handle voice command interaction."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Interaction handler not initialized",
                    "handler"
                )
            
            start_time = asyncio.get_event_loop().time()
            
            # Update context
            self._context.state = InteractionState.PROCESSING
            self._context.active_command = command_data.get('command')
            
            # Process voice command
            response = await self._process_voice_command(command_data)
            
            # Update metrics
            self._interaction_count += 1
            self._update_response_time(
                asyncio.get_event_loop().time() - start_time
            )
            
            # Record interaction
            await self._record_interaction(command_data, response)
            
            # Update context state
            self._context.state = InteractionState.ACTIVE
            
            return response
            
        except Exception as e:
            self._error_count += 1
            self._context.state = InteractionState.ERROR
            self.logger.error("Voice command handling failed", error=e)
            raise InteractionError(
                "Failed to handle voice command",
                "handler",
                details={"command": command_data.get('command'), "original_error": str(e)}
            )

    async def _handle_swipe_left(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle left swipe gesture."""
        try:
            response = {
                "action": "navigate",
                "direction": "previous",
                "velocity": gesture.velocity
            }
            
            if self._context.mode == InteractionMode.NAVIGATION:
                response["view_update"] = "slide_right"
            elif self._context.mode == InteractionMode.MANIPULATION:
                response["object_update"] = "move_left"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle left swipe",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_swipe_right(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle right swipe gesture."""
        try:
            response = {
                "action": "navigate",
                "direction": "next",
                "velocity": gesture.velocity
            }
            
            if self._context.mode == InteractionMode.NAVIGATION:
                response["view_update"] = "slide_left"
            elif self._context.mode == InteractionMode.MANIPULATION:
                response["object_update"] = "move_right"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle right swipe",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_swipe_up(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle upward swipe gesture."""
        try:
            response = {
                "action": "navigate",
                "direction": "up",
                "velocity": gesture.velocity
            }
            
            if self._context.mode == InteractionMode.NAVIGATION:
                response["view_update"] = "slide_down"
            elif self._context.mode == InteractionMode.MANIPULATION:
                response["object_update"] = "move_up"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle up swipe",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_swipe_down(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle downward swipe gesture."""
        try:
            response = {
                "action": "navigate",
                "direction": "down",
                "velocity": gesture.velocity
            }
            
            if self._context.mode == InteractionMode.NAVIGATION:
                response["view_update"] = "slide_up"
            elif self._context.mode == InteractionMode.MANIPULATION:
                response["object_update"] = "move_down"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle down swipe",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_pinch(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle pinch gesture."""
        try:
            response = {
                "action": "scale",
                "direction": "decrease",
                "scale_factor": gesture.scale
            }
            
            if gesture.scale:
                response["view_update"] = "zoom_out"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle pinch",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_spread(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle spread gesture."""
        try:
            response = {
                "action": "scale",
                "direction": "increase",
                "scale_factor": gesture.scale
            }
            
            if gesture.scale:
                response["view_update"] = "zoom_in"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle spread",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_rotate_clockwise(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle clockwise rotation gesture."""
        try:
            response = {
                "action": "rotate",
                "direction": "clockwise",
                "angle": gesture.rotation
            }
            
            if self._context.mode == InteractionMode.MANIPULATION:
                response["object_update"] = "rotate_cw"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle clockwise rotation",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_rotate_counterclockwise(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle counterclockwise rotation gesture."""
        try:
            response = {
                "action": "rotate",
                "direction": "counterclockwise",
                "angle": gesture.rotation
            }
            
            if self._context.mode == InteractionMode.MANIPULATION:
                response["object_update"] = "rotate_ccw"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle counterclockwise rotation",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_tap(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle tap gesture."""
        try:
            response = {
                "action": "select",
                "position": gesture.position
            }
            
            if self._context.mode == InteractionMode.SELECTION:
                response["object_update"] = "select"
                self._context.selected_element = "tapped_element"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle tap",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_double_tap(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle double tap gesture."""
        try:
            response = {
                "action": "activate",
                "position": gesture.position
            }
            
            if self._context.mode == InteractionMode.SELECTION:
                response["object_update"] = "activate"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle double tap",
                "handler",
                details={"original_error": str(e)}
            )

    async def _handle_hold(self, gesture: GestureData) -> Dict[str, Any]:
        """Handle hold gesture."""
        try:
            response = {
                "action": "context_menu",
                "position": gesture.position,
                "duration": gesture.duration
            }
            
            if self._context.mode == InteractionMode.COMMAND:
                response["menu_update"] = "show_context_menu"
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to handle hold",
                "handler",
                details={"original_error": str(e)}
            )

    async def _process_voice_command(self, command_data: Dict) -> Dict[str, Any]:
        """Process voice command."""
        try:
            command = command_data.get('command', '').lower()
            response = {
                "action": "voice_command",
                "command": command
            }
            
            # Add command-specific responses
            if "select" in command:
                response["interaction_mode"] = InteractionMode.SELECTION.value
            elif "navigate" in command:
                response["interaction_mode"] = InteractionMode.NAVIGATION.value
            elif "manipulate" in command:
                response["interaction_mode"] = InteractionMode.MANIPULATION.value
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to process voice command",
                "handler",
                details={"command": command_data.get('command'), "original_error": str(e)}
            )

    async def _record_interaction(self, input_data: Any,
                                response: Dict[str, Any]) -> None:
        """Record interaction for history tracking."""
        interaction = {
            "timestamp": asyncio.get_event_loop().time(),
            "context_state": self._context.state.value,
            "context_mode": self._context.mode.value,
            "input": input_data,
            "response": response
        }
        
        self._interaction_history.append(interaction)
        
        # Maintain maximum history size
        if len(self._interaction_history) > self._MAX_HISTORY:
            self._interaction_history.pop(0)

    def _update_response_time(self, response_time: float) -> None:
        """Update average response time metric."""
        self._average_response_time = (
            (self._average_response_time * self._interaction_count + response_time) /
            (self._interaction_count + 1)
        )

    async def get_status(self) -> Dict:
        """Get current interaction handler status."""
        return {
            "initialized": self._initialized,
            "state": self._context.state.value,
            "mode": self._context.mode.value,
            "selected_element": self._context.selected_element,
            "active_command": self._context.active_command,
            "interaction_count": self._interaction_count,
            "error_count": self._error_count,
            "average_response_time": self._average_response_time
        }

    async def cleanup(self) -> None:
        """Cleanup interaction handler resources."""
        try:
            self._initialized = False
            
            # Reset state
            self._context = InteractionContext(
                state=InteractionState.IDLE,
                mode=InteractionMode.NAVIGATION
            )
            
            # Clear history
            self._interaction_history.clear()
            
            self.logger.info("Interaction handler cleaned up successfully")
            
        except Exception as e:
            self.logger.error("Failed to cleanup interaction handler", error=e)
            raise InteractionError(
                "Cleanup failed",
                "handler",
                details={"original_error": str(e)}
            )