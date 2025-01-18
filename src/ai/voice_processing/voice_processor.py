import asyncio
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from src.utils.error_handling import InteractionError
from src.utils.logging_utils import HolographicWatchLogger
import numpy as np

class VoiceCommandType(Enum):
    SYSTEM = "system"
    NAVIGATION = "navigation"
    ACTION = "action"
    QUERY = "query"
    CONTROL = "control"

@dataclass
class AudioConfig:
    sample_rate: int
    channels: int
    bit_depth: int
    frame_duration: float
    vad_threshold: float
    noise_threshold: float

@dataclass
class VoiceCommand:
    type: VoiceCommandType
    text: str
    confidence: float
    timestamp: float
    audio_duration: float
    parameters: Optional[Dict] = None

class VoiceProcessor:
    """Processes voice commands for the holographic watch system."""
    
    def __init__(self):
        self.logger = HolographicWatchLogger(__name__)
        self._initialized = False
        
        # Audio configuration
        self._config = AudioConfig(
            sample_rate=16000,
            channels=1,
            bit_depth=16,
            frame_duration=0.03,  # 30ms frames
            vad_threshold=0.3,
            noise_threshold=0.1
        )
        
        # Voice processing state
        self._is_listening = False
        self._is_processing = False
        self._current_audio_buffer = []
        self._noise_profile = None
        
        # Command recognition
        self._command_history: List[VoiceCommand] = []
        self._MAX_HISTORY = 100
        self._min_command_confidence = 0.7
        
        # Performance monitoring
        self._processing_times: List[float] = []
        self._recognition_accuracy: float = 0.0
        self._total_commands = 0
        self._successful_commands = 0

    async def initialize(self) -> bool:
        """Initialize the voice processing system."""
        try:
            self.logger.info("Initializing voice processor")
            
            # Initialize audio processing
            await self._initialize_audio()
            
            # Initialize voice recognition
            await self._initialize_recognition()
            
            # Calibrate noise profile
            await self._calibrate_noise_profile()
            
            # Start audio monitoring
            asyncio.create_task(self._audio_monitoring_loop())
            
            self._initialized = True
            self.logger.info("Voice processor initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Voice processor initialization failed", error=e)
            raise InteractionError(
                "Failed to initialize voice processor",
                "voice",
                details={"original_error": str(e)}
            )

    async def _initialize_audio(self) -> None:
        """Initialize audio processing system."""
        try:
            # In production, this would initialize actual audio hardware
            # For simulation, we'll set up our audio processing state
            self._current_audio_buffer = []
            self._is_listening = False
            
            # Initialize audio processing parameters
            frame_size = int(
                self._config.sample_rate * self._config.frame_duration
            )
            self._frame_size = frame_size
            
        except Exception as e:
            raise InteractionError(
                "Failed to initialize audio system",
                "voice",
                details={"original_error": str(e)}
            )

    async def _initialize_recognition(self) -> None:
        """Initialize voice recognition system."""
        try:
            # Initialize command templates
            self._command_templates = {
                VoiceCommandType.SYSTEM: [
                    "system shutdown",
                    "system restart",
                    "system status"
                ],
                VoiceCommandType.NAVIGATION: [
                    "go back",
                    "go forward",
                    "scroll up",
                    "scroll down"
                ],
                VoiceCommandType.ACTION: [
                    "select item",
                    "activate",
                    "deactivate",
                    "confirm"
                ],
                VoiceCommandType.QUERY: [
                    "what is",
                    "how to",
                    "show me",
                    "find"
                ],
                VoiceCommandType.CONTROL: [
                    "increase volume",
                    "decrease volume",
                    "brighten display",
                    "dim display"
                ]
            }
            
        except Exception as e:
            raise InteractionError(
                "Failed to initialize recognition system",
                "voice",
                details={"original_error": str(e)}
            )

    async def _calibrate_noise_profile(self) -> None:
        """Calibrate ambient noise profile."""
        try:
            # In production, this would record actual ambient noise
            # For simulation, we'll create a synthetic noise profile
            noise_duration = 1.0  # seconds
            num_samples = int(self._config.sample_rate * noise_duration)
            
            # Generate synthetic noise profile
            self._noise_profile = np.random.normal(
                0,
                0.1,
                num_samples
            )
            
            self.logger.debug("Noise profile calibrated")
            
        except Exception as e:
            raise InteractionError(
                "Failed to calibrate noise profile",
                "voice",
                details={"original_error": str(e)}
            )

    async def _audio_monitoring_loop(self) -> None:
        """Continuous audio monitoring loop."""
        while self._initialized:
            try:
                if self._is_listening:
                    # Read audio frame
                    frame = await self._read_audio_frame()
                    
                    if frame is not None:
                        # Process audio frame
                        if await self._detect_voice_activity(frame):
                            self._current_audio_buffer.extend(frame)
                        elif len(self._current_audio_buffer) > 0:
                            # End of utterance detected
                            await self._process_utterance()
                            self._current_audio_buffer.clear()
                
                await asyncio.sleep(self._config.frame_duration)
                
            except Exception as e:
                self.logger.error("Audio monitoring error", error=e)
                await asyncio.sleep(1.0)

    async def _read_audio_frame(self) -> Optional[List[float]]:
        """Read audio frame from input."""
        try:
            # In production, this would read from actual audio input
            # For simulation, return None to indicate no audio
            return None
            
        except Exception as e:
            self.logger.error("Audio frame read failed", error=e)
            return None

    async def _detect_voice_activity(self, frame: List[float]) -> bool:
        """Detect voice activity in audio frame."""
        try:
            # Calculate frame energy
            frame_energy = np.mean(np.square(frame))
            
            # Calculate signal-to-noise ratio
            noise_energy = np.mean(np.square(self._noise_profile))
            snr = 10 * np.log10(frame_energy / noise_energy) if noise_energy > 0 else 0
            
            # Check if frame energy exceeds VAD threshold
            return (
                frame_energy > self._config.vad_threshold and
                snr > 10.0  # 10dB SNR threshold
            )
            
        except Exception as e:
            self.logger.error("Voice activity detection failed", error=e)
            return False

    async def _process_utterance(self) -> None:
        """Process complete utterance."""
        try:
            if not self._current_audio_buffer:
                return
            
            self._is_processing = True
            start_time = asyncio.get_event_loop().time()
            
            # Convert buffer to numpy array
            audio_data = np.array(self._current_audio_buffer)
            
            # Perform voice recognition
            command = await self._recognize_command(audio_data)
            
            if command and command.confidence >= self._min_command_confidence:
                # Record successful command
                await self._record_command(command)
                self._successful_commands += 1
            
            self._total_commands += 1
            
            # Update performance metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            await self._update_performance_metrics(processing_time)
            
            self._is_processing = False
            
        except Exception as e:
            self._is_processing = False
            raise InteractionError(
                "Failed to process utterance",
                "voice",
                details={"original_error": str(e)}
            )

    async def _recognize_command(self, audio_data: np.ndarray) -> Optional[VoiceCommand]:
        """Perform voice command recognition."""
        try:
            # In production, this would use actual voice recognition
            # For simulation, we'll return a mock command
            command_type = VoiceCommandType.SYSTEM
            command_text = "system status"
            confidence = 0.85
            
            return VoiceCommand(
                type=command_type,
                text=command_text,
                confidence=confidence,
                timestamp=asyncio.get_event_loop().time(),
                audio_duration=len(audio_data) / self._config.sample_rate
            )
            
        except Exception as e:
            self.logger.error("Command recognition failed", error=e)
            return None

    async def start_listening(self) -> None:
        """Start voice command listening."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Voice processor not initialized",
                    "voice"
                )
            
            self._is_listening = True
            self.logger.info("Voice command listening started")
            
        except Exception as e:
            raise InteractionError(
                "Failed to start listening",
                "voice",
                details={"original_error": str(e)}
            )

    async def stop_listening(self) -> None:
        """Stop voice command listening."""
        try:
            self._is_listening = False
            self._current_audio_buffer.clear()
            self.logger.info("Voice command listening stopped")
            
        except Exception as e:
            raise InteractionError(
                "Failed to stop listening",
                "voice",
                details={"original_error": str(e)}
            )

    async def process_audio(self, audio_data: Dict) -> Dict[str, Any]:
        """Process audio data for voice commands."""
        try:
            if not self._initialized:
                raise InteractionError(
                    "Voice processor not initialized",
                    "voice"
                )
            
            start_time = asyncio.get_event_loop().time()
            
            # Extract audio samples
            samples = audio_data.get('samples', [])
            if not samples:
                raise ValueError("No audio data provided")
            
            # Process audio
            command = await self._recognize_command(np.array(samples))
            
            if command and command.confidence >= self._min_command_confidence:
                # Record command
                await self._record_command(command)
                self._successful_commands += 1
                
                response = {
                    "command": command.text,
                    "type": command.type.value,
                    "confidence": command.confidence,
                    "timestamp": command.timestamp,
                    "duration": command.audio_duration,
                    "parameters": command.parameters
                }
            else:
                response = {
                    "error": "Command not recognized",
                    "confidence": command.confidence if command else 0.0
                }
            
            self._total_commands += 1
            
            # Update performance metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            await self._update_performance_metrics(processing_time)
            
            return response
            
        except Exception as e:
            raise InteractionError(
                "Failed to process audio",
                "voice",
                details={"original_error": str(e)}
            )

    async def _record_command(self, command: VoiceCommand) -> None:
        """Record voice command for history."""
        self._command_history.append(command)
        
        # Maintain maximum history size
        if len(self._command_history) > self._MAX_HISTORY:
            self._command_history.pop(0)

    async def _update_performance_metrics(self, processing_time: float) -> None:
        """Update performance metrics."""
        self._processing_times.append(processing_time)
        
        # Maintain maximum history size
        if len(self._processing_times) > self._MAX_HISTORY:
            self._processing_times.pop(0)
        
        # Update recognition accuracy
        if self._total_commands > 0:
            self._recognition_accuracy = (
                self._successful_commands / self._total_commands
            )

    async def get_performance_metrics(self) -> Dict:
        """Get voice processing performance metrics."""
        try:
            if not self._processing_times:
                return {
                    "average_processing_time": 0.0,
                    "recognition_accuracy": 0.0,
                    "total_commands": 0,
                    "successful_commands": 0
                }
            
            return {
                "average_processing_time": (
                    sum(self._processing_times) /
                    len(self._processing_times) * 1000  # Convert to ms
                ),
                "recognition_accuracy": self._recognition_accuracy,
                "total_commands": self._total_commands,
                "successful_commands": self._successful_commands
            }
            
        except Exception as e:
            self.logger.error("Failed to get performance metrics", error=e)
            return {
                "error": str(e)
            }

    async def get_status(self) -> Dict:
        """Get current voice processor status."""
        return {
            "initialized": self._initialized,
            "listening": self._is_listening,
            "processing": self._is_processing,
            "buffer_size": len(self._current_audio_buffer),
            "recognition_accuracy": self._recognition_accuracy,
            "command_history_size": len(self._command_history)
        }

    async def cleanup(self) -> None:
        """Cleanup voice processor resources."""
        try:
            self._initialized = False
            
            # Stop listening
            await self.stop_listening()
            
            # Clear buffers and history
            self._current_audio_buffer.clear()
            self._command_history.clear()
            self._processing_times.clear()
            
            self.logger.info("Voice processor cleaned up successfully")
            
        except Exception as e:
            self.logger.error("Failed to cleanup voice processor", error=e)
            raise InteractionError(
                "Cleanup failed",
                "voice",
                details={"original_error": str(e)}
            )