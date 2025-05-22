# # hardware_simulator.py
# """
# Hardware interface system for the holographic watch.
# Manages input processing and system interaction.
# """

# import numpy as np
# from enum import Enum
# from typing import Optional, List, Dict, Tuple
# import threading
# import time
# from dataclasses import dataclass

# from hardware_components import (
#     GestureDetector,
#     TouchSensor,
#     MotionSensor,
#     VoiceProcessor
# )

# class InputType(Enum):
#     TOUCH = "touch"
#     GESTURE = "gesture"
#     MOTION = "motion"
#     VOICE = "voice"

# @dataclass
# class InputEvent:
#     type: InputType
#     value: str
#     timestamp: float
#     coordinates: Optional[Tuple[float, float, float]] = None

# class HardwareInterface:
#     def __init__(self, system_interface):
#         """Initialize the hardware interface with system reference."""
#         self.system = system_interface
#         self.gesture_detector = GestureDetector()
#         self.touch_sensor = TouchSensor()
#         self.motion_sensor = MotionSensor()
#         self.voice_processor = VoiceProcessor()
        
#         # Event processing queue and thread management
#         self.input_queue: List[InputEvent] = []
#         self._processing_thread: Optional[threading.Thread] = None
#         self._is_processing = False
        
#         # System status
#         self._system_ready = False
#         self._last_event_time = 0
        
#     def initialize(self) -> bool:
#         """Initialize all hardware components and start processing."""
#         try:
#             # Initialize all sensor systems
#             sensor_init = all([
#                 self.gesture_detector.initialize(),
#                 self.touch_sensor.initialize(),
#                 self.motion_sensor.initialize(),
#                 self.voice_processor.initialize()
#             ])
            
#             if not sensor_init:
#                 raise RuntimeError("Sensor initialization failed")
            
#             # Start input processing
#             self._start_input_processing()
#             self._system_ready = True
            
#             return True
            
#         except Exception as e:
#             print(f"Hardware interface initialization failed: {str(e)}")
#             return False
            
#     def _start_input_processing(self):
#         """Start the input processing thread."""
#         self._is_processing = True
#         self._processing_thread = threading.Thread(target=self._process_input_loop)
#         self._processing_thread.daemon = True
#         self._processing_thread.start()
        
#     def _process_input_loop(self):
#         """Main input processing loop."""
#         while self._is_processing and self._system_ready:
#             try:
#                 # Process physical inputs
#                 self._process_all_inputs()
                
#                 # Handle queued events
#                 self._process_event_queue()
                
#                 # Maintain processing rate
#                 time.sleep(0.01)  # 100Hz processing rate
                
#             except Exception as e:
#                 print(f"Error in input processing: {str(e)}")
                
#     def _process_all_inputs(self):
#         """Process all input types."""
#         # Process touch input
#         touch_data = self.touch_sensor.read_touch_input()
#         if touch_data:
#             self._queue_touch_event(touch_data)
            
#         # Process gesture input
#         gesture_data = self.gesture_detector.detect_gesture()
#         if gesture_data:
#             self._queue_gesture_event(gesture_data)
            
#         # Process motion input
#         motion_data = self.motion_sensor.detect_motion()
#         if motion_data:
#             self._queue_motion_event(motion_data)
            
#         # Process voice input
#         voice_data = self.voice_processor.process_audio()
#         if voice_data:
#             self._queue_voice_event(voice_data)
            
#     def _process_event_queue(self):
#         """Process queued input events."""
#         while self.input_queue:
#             event = self.input_queue.pop(0)
#             self._handle_input_event(event)
            
#     def _queue_touch_event(self, touch_data: Tuple[str, Tuple[float, float]]):
#         """Queue a touch event."""
#         event = InputEvent(
#             type=InputType.TOUCH,
#             value=touch_data[0],
#             timestamp=time.time(),
#             coordinates=(touch_data[1][0], touch_data[1][1], 0.0)
#         )
#         self.input_queue.append(event)
        
#     def _queue_gesture_event(self, gesture_data: Tuple[str, float]):
#         """Queue a gesture event."""
#         event = InputEvent(
#             type=InputType.GESTURE,
#             value=gesture_data[0],
#             timestamp=time.time(),
#             coordinates=(0.0, 0.0, gesture_data[1])
#         )
#         self.input_queue.append(event)
        
#     def _queue_motion_event(self, motion_data: Tuple[str, np.ndarray]):
#         """Queue a motion event."""
#         event = InputEvent(
#             type=InputType.MOTION,
#             value=motion_data[0],
#             timestamp=time.time(),
#             coordinates=tuple(motion_data[1])
#         )
#         self.input_queue.append(event)
        
#     def _queue_voice_event(self, voice_command: str):
#         """Queue a voice event."""
#         event = InputEvent(
#             type=InputType.VOICE,
#             value=voice_command,
#             timestamp=time.time()
#         )
#         self.input_queue.append(event)
        
#     def _handle_input_event(self, event: InputEvent):
#         """Process and route input events to appropriate handlers."""
#         try:
#             if time.time() - event.timestamp > 0.1:  # 100ms timeout
#                 return  # Discard old events
                
#             if event.type == InputType.TOUCH:
#                 self._handle_touch_event(event)
#             elif event.type == InputType.GESTURE:
#                 self._handle_gesture_event(event)
#             elif event.type == InputType.MOTION:
#                 self._handle_motion_event(event)
#             elif event.type == InputType.VOICE:
#                 self._handle_voice_event(event)
                
#         except Exception as e:
#             print(f"Error handling {event.type.value} event: {str(e)}")
            
#     def _handle_touch_event(self, event: InputEvent):
#         """Handle touch input events."""
#         if event.value == "double_tap":
#             self.system.toggle_hologram()
#         elif event.value == "long_press":
#             self.system.show_system_status()
            
#     def _handle_gesture_event(self, event: InputEvent):
#         """Handle gesture input events."""
#         if event.value == "swipe_up":
#             self.system.increase_hologram_size()
#         elif event.value == "swipe_down":
#             self.system.decrease_hologram_size()
#         elif event.value == "rotate":
#             self.system.rotate_hologram(event.coordinates)
            
#     def _handle_motion_event(self, event: InputEvent):
#         """Handle motion input events."""
#         if event.value == "shake":
#             self.system.emergency_shutdown()
#         elif event.value == "tilt":
#             self.system.adjust_projection_angle(event.coordinates)
            
#     def _handle_voice_event(self, event: InputEvent):
#         """Handle voice input events."""
#         if event.value.startswith("activate"):
#             self.system.start_hologram()
#         elif event.value.startswith("deactivate"):
#             self.system.stop_hologram()
            
#     def shutdown(self):
#         """Safely shutdown the hardware interface."""
#         self._is_processing = False
#         if self._processing_thread:
#             self._processing_thread.join(timeout=1.0)
#         self._system_ready = False


# hardware_simulator.py

"""
Hardware interface system for the holographic watch.
This module provides the main interface between physical inputs and the system,
managing all sensor interactions and event processing.
"""

import numpy as np
from enum import Enum
from typing import Optional, List, Dict, Tuple
import threading
import time
from dataclasses import dataclass

from hardware_components import (
    GestureDetector,
    TouchSensor,
    MotionSensor,
    VoiceProcessor
)

class InputType(Enum):
    """Enumeration of supported input types."""
    TOUCH = "touch"      # Direct touch inputs
    GESTURE = "gesture"  # Hand gestures
    MOTION = "motion"    # Device motion
    VOICE = "voice"      # Voice commands

@dataclass
class InputEvent:
    """Data structure for input events."""
    type: InputType      # Type of input detected
    value: str          # Input value or command
    timestamp: float    # When the input occurred
    coordinates: Optional[Tuple[float, float, float]] = None  # 3D coordinates if applicable

class HardwareInterface:
    """
    Main hardware interface managing all physical inputs.
    Coordinates between different input types and the main system.
    """
    
    def __init__(self, system_interface):
        """
        Initialize the hardware interface.
        Args:
            system_interface: Reference to the main system interface
        """
        # Store system reference
        self.system = system_interface
        
        # Initialize sensor components
        self.gesture_detector = GestureDetector()
        self.touch_sensor = TouchSensor()
        self.motion_sensor = MotionSensor()
        self.voice_processor = VoiceProcessor()
        
        # Event processing setup
        self.input_queue: List[InputEvent] = []  # Queue for pending events
        self._processing_thread: Optional[threading.Thread] = None
        self._is_processing = False
        
        # System state tracking
        self._system_ready = False
        self._last_event_time = 0
        
    def initialize(self) -> bool:
        """
        Initialize all hardware components and start processing.
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Initialize all sensor systems
            sensor_init = all([
                self.gesture_detector.initialize(),
                self.touch_sensor.initialize(),
                self.motion_sensor.initialize(),
                self.voice_processor.initialize()
            ])
            
            if not sensor_init:
                raise RuntimeError("Sensor initialization failed")
            
            # Start input processing
            self._start_input_processing()
            self._system_ready = True
            
            return True
            
        except Exception as e:
            print(f"Hardware interface initialization failed: {str(e)}")
            return False
            
    def _start_input_processing(self):
        """Start the input processing thread."""
        self._is_processing = True
        self._processing_thread = threading.Thread(target=self._process_input_loop)
        self._processing_thread.daemon = True  # Thread will terminate with main program
        self._processing_thread.start()
        
    def _process_input_loop(self):
        """Main input processing loop running in separate thread."""
        while self._is_processing and self._system_ready:
            try:
                # Process all physical inputs
                self._process_all_inputs()
                
                # Handle queued events
                self._process_event_queue()
                
                # Maintain consistent processing rate
                time.sleep(0.01)  # 100Hz processing rate
                
            except Exception as e:
                print(f"Error in input processing: {str(e)}")
                
    def _process_all_inputs(self):
        """Process inputs from all sensor types."""
        # Check each input type and queue events if detected
        
        # Process touch input
        touch_data = self.touch_sensor.read_touch_input()
        if touch_data:
            self._queue_touch_event(touch_data)
            
        # Process gesture input
        gesture_data = self.gesture_detector.detect_gesture()
        if gesture_data:
            self._queue_gesture_event(gesture_data)
            
        # Process motion input
        motion_data = self.motion_sensor.detect_motion()
        if motion_data:
            self._queue_motion_event(motion_data)
            
        # Process voice input
        voice_data = self.voice_processor.process_audio()
        if voice_data:
            self._queue_voice_event(voice_data)
            
    def _process_event_queue(self):
        """Process all queued input events."""
        while self.input_queue:
            event = self.input_queue.pop(0)
            self._handle_input_event(event)
            
    def _queue_touch_event(self, touch_data: Tuple[str, Tuple[float, float]]):
        """
        Queue a touch event for processing.
        Args:
            touch_data: Tuple containing touch type and coordinates
        """
        event = InputEvent(
            type=InputType.TOUCH,
            value=touch_data[0],
            timestamp=time.time(),
            coordinates=(touch_data[1][0], touch_data[1][1], 0.0)
        )
        self.input_queue.append(event)
        
    def _queue_gesture_event(self, gesture_data: Tuple[str, float]):
        """
        Queue a gesture event for processing.
        Args:
            gesture_data: Tuple containing gesture type and magnitude
        """
        event = InputEvent(
            type=InputType.GESTURE,
            value=gesture_data[0],
            timestamp=time.time(),
            coordinates=(0.0, 0.0, gesture_data[1])
        )
        self.input_queue.append(event)
        
    def _queue_motion_event(self, motion_data: Tuple[str, np.ndarray]):
        """
        Queue a motion event for processing.
        Args:
            motion_data: Tuple containing motion type and acceleration vector
        """
        event = InputEvent(
            type=InputType.MOTION,
            value=motion_data[0],
            timestamp=time.time(),
            coordinates=tuple(motion_data[1])  # Convert numpy array to tuple
        )
        self.input_queue.append(event)
        
    def _queue_voice_event(self, voice_command: str):
        """
        Queue a voice command event for processing.
        Args:
            voice_command: Detected voice command string
        """
        event = InputEvent(
            type=InputType.VOICE,
            value=voice_command,
            timestamp=time.time()
        )
        self.input_queue.append(event)
        
    def _handle_input_event(self, event: InputEvent):
        """
        Process and route input events to appropriate handlers.
        Args:
            event: InputEvent to be processed
        """
        try:
            # Discard events older than 100ms to maintain responsiveness
            if time.time() - event.timestamp > 0.1:
                return
                
            # Route event to appropriate handler based on type
            if event.type == InputType.TOUCH:
                self._handle_touch_event(event)
            elif event.type == InputType.GESTURE:
                self._handle_gesture_event(event)
            elif event.type == InputType.MOTION:
                self._handle_motion_event(event)
            elif event.type == InputType.VOICE:
                self._handle_voice_event(event)
                
        except Exception as e:
            print(f"Error handling {event.type.value} event: {str(e)}")
            
    def _handle_touch_event(self, event: InputEvent):
        """
        Handle touch input events and trigger appropriate system responses.
        Args:
            event: Touch input event to process
        """
        if event.value == "double_tap":
            # Double tap toggles hologram display
            self.system.toggle_hologram()
        elif event.value == "long_press":
            # Long press shows system status
            self.system.show_system_status()
            
    def _handle_gesture_event(self, event: InputEvent):
        """
        Handle gesture events and trigger appropriate hologram modifications.
        Args:
            event: Gesture event to process
        """
        if event.value == "swipe_up":
            # Upward swipe increases hologram size
            self.system.increase_hologram_size()
        elif event.value == "swipe_down":
            # Downward swipe decreases hologram size
            self.system.decrease_hologram_size()
        elif event.value == "rotate":
            # Rotation gesture rotates the hologram
            self.system.rotate_hologram(event.coordinates)
            
    def _handle_motion_event(self, event: InputEvent):
        """
        Handle device motion events and trigger appropriate system responses.
        Args:
            event: Motion event to process
        """
        if event.value == "shake":
            # Shaking gesture triggers emergency shutdown
            self.system.emergency_shutdown()
        elif event.value == "tilt":
            # Tilting adjusts projection angle
            self.system.adjust_projection_angle(event.coordinates)
            
    def _handle_voice_event(self, event: InputEvent):
        """
        Handle voice command events and trigger appropriate system actions.
        Args:
            event: Voice command event to process
        """
        if event.value.startswith("activate"):
            # Voice command to start hologram
            self.system.start_hologram()
        elif event.value.startswith("deactivate"):
            # Voice command to stop hologram
            self.system.stop_hologram()
            
    def shutdown(self):
        """
        Safely shutdown the hardware interface.
        Ensures proper cleanup of resources and thread termination.
        """
        self._is_processing = False
        if self._processing_thread:
            self._processing_thread.join(timeout=1.0)  # Wait up to 1 second for thread to finish
        self._system_ready = False

def main():
    """
    Main function for testing and demonstrating the hardware interface.
    Sets up the system and runs a demonstration of various input types.
    """
    # Create mock system interface for testing
    class MockSystem:
        def toggle_hologram(self): print("Toggling hologram")
        def show_system_status(self): print("Showing status")
        def increase_hologram_size(self): print("Increasing size")
        def decrease_hologram_size(self): print("Decreasing size")
        def rotate_hologram(self, coords): print(f"Rotating to {coords}")
        def emergency_shutdown(self): print("Emergency shutdown")
        def adjust_projection_angle(self, coords): print(f"Adjusting angle to {coords}")
        def start_hologram(self): print("Starting hologram")
        def stop_hologram(self): print("Stopping hologram")
    
    # Initialize the hardware interface with mock system
    interface = HardwareInterface(MockSystem())
    
    print("Initializing hardware interface...")
    if not interface.initialize():
        print("Initialization failed!")
        return
    
    print("\nRunning interface test...")
    try:
        # Run for 10 seconds
        time.sleep(10)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        print("\nShutting down interface...")
        interface.shutdown()
        print("Test complete")

if __name__ == "__main__":
    main()