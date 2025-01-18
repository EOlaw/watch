import asyncio
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from src.utils.error_handling import InteractionError
from src.utils.logging_utils import HolographicWatchLogger
from src.hardware.drivers.motion_driver import MotionDriver

class GestureType(Enum):
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    PINCH = "pinch"
    SPREAD = "spread"
    ROTATE_CW = "rotate_clockwise"
    ROTATE_CCW = "rotate_counterclockwise"
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    HOLD = "hold"

@dataclass
class GestureData:
    type: GestureType
    confidence: float
    velocity: Optional[Tuple[float, float, float]] = None
    position: Optional[Tuple[float, float, float]] = None
    duration: Optional[float] = None
    rotation: Optional[float] = None
    scale: Optional[float] = None

class GestureRecognizer:
    """Recognizes and processes holographic interface gestures."""
    
    def __init__(self):
        self.logger = HolographicWatchLogger(__name__)
        self._motion_driver = MotionDriver()
        self._initialized = False
        
        # Gesture recognition parameters
        self._min_confidence = 0.7
        self._max_gesture_duration = 1.0  # seconds
        self._min_gesture_velocity = 0.1   # m/s
        self._min_rotation_angle = 15.0    # degrees
        
        # Gesture state tracking
        self._current_gesture: Optional[GestureData] = None
        self._gesture_start_time: Optional[float] = None
        self._gesture_history: List[GestureData] = []
        self._MAX_HISTORY = 100
        
        # Motion tracking
        self._motion_buffer: List[Tuple[float, float, float]] = []
        self._BUFFER_SIZE = 50  # samples
        
        # Performance metrics
        self._recognition_count = 0
        self._error_count = 0
        self._average_confidence = 0.0

    async def initialize(self) -> bool:
        """Initialize the gesture recognition system."""
        try:
            self.logger.info("Initializing gesture recognition system")
            
            # Initialize motion tracking
            if not await self._motion_driver.initialize():
                raise InteractionError(
                    "Failed to initialize motion driver",
                    "gesture"
                )
            
            # Start motion monitoring
            await self._motion_driver.start_monitoring()
            
            # Start gesture processing
            asyncio.create_task(self._process_motion_data())
            
            self._initialized = True
            self.logger.info("Gesture recognition system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Gesture recognition initialization failed", error=e)
            raise InteractionError(
                "Failed to initialize gesture recognition",
                "gesture",
                details={"original_error": str(e)}
            )

    async def process_gesture(self, gesture_data: Dict) -> GestureData:
        """Process and classify incoming gesture data."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Gesture recognition not initialized",
                    "gesture"
                )
            
            # Extract motion data
            motion = await self._extract_motion_features(gesture_data)
            
            # Classify gesture
            gesture = await self._classify_gesture(motion)
            
            if gesture.confidence >= self._min_confidence:
                await self._record_gesture(gesture)
                self._recognition_count += 1
                self._update_metrics(gesture)
                
                self.logger.debug(
                    f"Recognized gesture: {gesture.type.value} "
                    f"(confidence: {gesture.confidence:.2f})"
                )
                return gesture
            else:
                raise InteractionError(
                    "Gesture confidence too low",
                    "gesture",
                    details={"confidence": gesture.confidence}
                )
            
        except Exception as e:
            self._error_count += 1
            self.logger.error("Gesture processing failed", error=e)
            raise InteractionError(
                "Failed to process gesture",
                "gesture",
                details={"original_error": str(e)}
            )

    async def _extract_motion_features(self, gesture_data: Dict) -> Dict:
        """Extract relevant motion features from gesture data."""
        try:
            # Get acceleration and angular velocity
            accel = await self._motion_driver.measure_acceleration()
            gyro = await self._motion_driver.measure_angular_velocity()
            
            # Update motion buffer
            self._motion_buffer.append(accel)
            if len(self._motion_buffer) > self._BUFFER_SIZE:
                self._motion_buffer.pop(0)
            
            # Calculate motion features
            velocity = self._calculate_velocity(self._motion_buffer)
            position = self._calculate_position(velocity)
            rotation = self._calculate_rotation(gyro)
            
            return {
                "velocity": velocity,
                "position": position,
                "rotation": rotation,
                "acceleration": accel,
                "angular_velocity": gyro
            }
            
        except Exception as e:
            raise InteractionError(
                "Feature extraction failed",
                "gesture",
                details={"original_error": str(e)}
            )

    async def _classify_gesture(self, motion: Dict) -> GestureData:
        """Classify gesture based on motion features."""
        try:
            velocity = motion["velocity"]
            position = motion["position"]
            rotation = motion["rotation"]
            
            # Detect primary gesture type
            gesture_type = None
            confidence = 0.0
            
            # Check for swipe gestures
            if abs(velocity[0]) > self._min_gesture_velocity:
                gesture_type = (
                    GestureType.SWIPE_RIGHT if velocity[0] > 0
                    else GestureType.SWIPE_LEFT
                )
                confidence = min(abs(velocity[0]) / 2.0, 1.0)
            
            elif abs(velocity[1]) > self._min_gesture_velocity:
                gesture_type = (
                    GestureType.SWIPE_UP if velocity[1] > 0
                    else GestureType.SWIPE_DOWN
                )
                confidence = min(abs(velocity[1]) / 2.0, 1.0)
            
            # Check for rotation gestures
            elif abs(rotation) > self._min_rotation_angle:
                gesture_type = (
                    GestureType.ROTATE_CW if rotation > 0
                    else GestureType.ROTATE_CCW
                )
                confidence = min(abs(rotation) / 90.0, 1.0)
            
            # Default to tap for small movements
            else:
                gesture_type = GestureType.TAP
                confidence = 0.8
            
            return GestureData(
                type=gesture_type,
                confidence=confidence,
                velocity=velocity,
                position=position,
                duration=self._calculate_duration(),
                rotation=rotation
            )
            
        except Exception as e:
            raise InteractionError(
                "Gesture classification failed",
                "gesture",
                details={"original_error": str(e)}
            )

    async def _process_motion_data(self) -> None:
        """Continuous motion data processing loop."""
        while self._initialized:
            try:
                # Process motion buffer
                if len(self._motion_buffer) >= self._BUFFER_SIZE:
                    # Detect potential gestures
                    if self._detect_gesture_start():
                        # Process complete gesture
                        await self._process_complete_gesture()
                
                await asyncio.sleep(0.01)  # 100Hz processing rate
                
            except Exception as e:
                self.logger.error("Motion processing error", error=e)
                await asyncio.sleep(1.0)

    def _detect_gesture_start(self) -> bool:
        """Detect the start of a potential gesture."""
        try:
            if len(self._motion_buffer) < 2:
                return False
            
            # Calculate acceleration magnitude
            current = sum(x*x for x in self._motion_buffer[-1])
            previous = sum(x*x for x in self._motion_buffer[-2])
            
            # Detect sudden motion
            if current > previous * 1.5:
                self._gesture_start_time = asyncio.get_event_loop().time()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("Gesture detection error", error=e)
            return False

    async def _process_complete_gesture(self) -> None:
        """Process a complete gesture sequence."""
        try:
            if not self._gesture_start_time:
                return
            
            # Check gesture duration
            duration = (
                asyncio.get_event_loop().time() - self._gesture_start_time
            )
            
            if duration > self._max_gesture_duration:
                self._gesture_start_time = None
                return
            
            # Create gesture data structure
            gesture_data = {"duration": duration}
            
            # Process gesture
            await self.process_gesture(gesture_data)
            
            # Reset gesture state
            self._gesture_start_time = None
            
        except Exception as e:
            self.logger.error("Complete gesture processing failed", error=e)

    def _calculate_velocity(self, accel_buffer: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        """Calculate velocity from acceleration buffer."""
        if len(accel_buffer) < 2:
            return (0.0, 0.0, 0.0)
        
        # Simple integration of acceleration
        dt = 0.01  # 10ms sample rate
        vx = vy = vz = 0.0
        
        for ax, ay, az in accel_buffer:
            vx += ax * dt
            vy += ay * dt
            vz += az * dt
        
        return (vx, vy, vz)

    def _calculate_position(self, velocity: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Calculate position from velocity."""
        # Simple integration of velocity
        dt = 0.01  # 10ms sample rate
        return (
            velocity[0] * dt,
            velocity[1] * dt,
            velocity[2] * dt
        )

    def _calculate_rotation(self, angular_velocity: Tuple[float, float, float]) -> float:
        """Calculate rotation angle from angular velocity."""
        # Use z-axis rotation for gesture detection
        dt = 0.01  # 10ms sample rate
        return angular_velocity[2] * dt

    def _calculate_duration(self) -> float:
        """Calculate gesture duration."""
        if not self._gesture_start_time:
            return 0.0
        return asyncio.get_event_loop().time() - self._gesture_start_time

    async def _record_gesture(self, gesture: GestureData) -> None:
        """Record gesture for history tracking."""
        self._gesture_history.append(gesture)
        
        # Maintain maximum history size
        if len(self._gesture_history) > self._MAX_HISTORY:
            self._gesture_history.pop(0)

    def _update_metrics(self, gesture: GestureData) -> None:
        """Update gesture recognition metrics."""
        self._average_confidence = (
            (self._average_confidence * self._recognition_count + gesture.confidence) /
            (self._recognition_count + 1)
        )

    async def get_status(self) -> Dict:
        """Get current gesture recognition status."""
        return {
            "initialized": self._initialized,
            "recognition_count": self._recognition_count,
            "error_count": self._error_count,
            "average_confidence": self._average_confidence,
            "current_gesture": self._current_gesture.type.value if self._current_gesture else None,
            "buffer_size": len(self._motion_buffer)
        }

    async def cleanup(self) -> None:
        """Cleanup gesture recognition resources."""
        try:
            self._initialized = False
            
            # Stop motion monitoring
            await self._motion_driver.stop_monitoring()
            await self._motion_driver.cleanup()
            
            # Clear state
            self._motion_buffer.clear()
            self._gesture_history.clear()
            self._current_gesture = None
            
            self.logger.info("Gesture recognition system cleaned up successfully")
            
        except Exception as e:
            self.logger.error("Failed to cleanup gesture recognition", error=e)
            raise InteractionError(
                "Cleanup failed",
                "gesture",
                details={"original_error": str(e)}
            )