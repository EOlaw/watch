from dataclasses import dataclass
from typing import Dict, Any, Optional
import numpy as np
import logging
from src.utils.error_handling import ProjectionError
from src.core.power_management.battery_controller import BatteryController

@dataclass
class ProjectionParameters:
    laser_power: float  # mW
    refresh_rate: float  # Hz
    resolution: tuple[int, int]  # pixels
    brightness: float  # 0-1.0
    focus_distance: float  # mm
    scan_angle: tuple[float, float]  # degrees (horizontal, vertical)
    meta_surface_config: Dict[str, float]

class ProjectionOptimizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._current_params: Optional[ProjectionParameters] = None
        self._quality_metrics: Dict[str, float] = {}
        self._battery_controller = BatteryController()

        # Default configuration
        self._min_laser_power = 5.0  # mW
        self._max_laser_power = 50.0  # mW
        self._min_refresh_rate = 30.0  # Hz
        self._max_refresh_rate = 120.0  # Hz
        self._min_brightness = 0.2
        self._max_brightness = 1.0

    def optimize_parameters(self, content: Dict[str, Any], battery_level: float) -> ProjectionParameters:
        """Optimize projection parameters based on content and system state."""
        try:
            # Calculate base parameters
            required_power = self._calculate_required_power(content)
            available_power = self._get_available_power(battery_level)
            
            # Adjust parameters based on power constraints
            adjusted_power = min(required_power, available_power)
            power_ratio = adjusted_power / required_power
            
            # Calculate optimal parameters
            optimal_params = ProjectionParameters(
                laser_power=self._optimize_laser_power(adjusted_power),
                refresh_rate=self._optimize_refresh_rate(power_ratio),
                resolution=self._optimize_resolution(content.get('resolution', (800, 600))),
                brightness=self._optimize_brightness(power_ratio),
                focus_distance=self._calculate_focus_distance(content.get('viewing_distance', 300)),
                scan_angle=self._calculate_scan_angles(content.get('display_size', (50, 50))),
                meta_surface_config=self._optimize_meta_surface()
            )
            
            self._current_params = optimal_params
            self._update_quality_metrics(optimal_params)
            
            return optimal_params
            
        except Exception as e:
            self.logger.error(f"Parameter optimization failed: {str(e)}")
            raise ProjectionError(f"Failed to optimize projection parameters: {str(e)}")

    def _calculate_required_power(self, content: Dict[str, Any]) -> float:
        """Calculate required power based on content characteristics."""
        base_power = 20.0  # mW
        complexity_factor = self._calculate_complexity_factor(content)
        return base_power * complexity_factor

    def _optimize_laser_power(self, available_power: float) -> float:
        """Optimize laser power based on available power budget."""
        return max(min(available_power * 0.8, self._max_laser_power), self._min_laser_power)

    def _optimize_refresh_rate(self, power_ratio: float) -> float:
        """Optimize refresh rate based on power availability."""
        base_rate = 60.0
        adjusted_rate = base_rate * power_ratio
        return max(min(adjusted_rate, self._max_refresh_rate), self._min_refresh_rate)

    def _optimize_resolution(self, requested_resolution: tuple[int, int]) -> tuple[int, int]:
        """Optimize resolution based on system capabilities."""
        max_resolution = (1920, 1080)
        return (
            min(requested_resolution[0], max_resolution[0]),
            min(requested_resolution[1], max_resolution[1])
        )

    def _optimize_brightness(self, power_ratio: float) -> float:
        """Optimize brightness based on power availability."""
        base_brightness = 0.8
        adjusted_brightness = base_brightness * power_ratio
        return max(min(adjusted_brightness, self._max_brightness), self._min_brightness)

    def _calculate_focus_distance(self, viewing_distance: float) -> float:
        """Calculate optimal focus distance based on viewing distance."""
        return max(viewing_distance * 0.9, 200.0)  # Minimum 200mm focus distance

    def _calculate_scan_angles(self, display_size: tuple[float, float]) -> tuple[float, float]:
        """Calculate required scan angles based on desired display size."""
        max_angles = (30.0, 30.0)  # Maximum safe scanning angles
        required_angles = (
            np.arctan(display_size[0] / (2 * self._current_params.focus_distance if self._current_params else 300)) * 2,
            np.arctan(display_size[1] / (2 * self._current_params.focus_distance if self._current_params else 300)) * 2
        )
        return (
            min(required_angles[0], max_angles[0]),
            min(required_angles[1], max_angles[1])
        )

    def _optimize_meta_surface(self) -> Dict[str, float]:
        """Optimize meta-surface configuration for current projection parameters."""
        return {
            'phase_shift': 0.5,
            'diffraction_efficiency': 0.85,
            'polarization_ratio': 0.95
        }

    def _calculate_complexity_factor(self, content: Dict[str, Any]) -> float:
        """Calculate content complexity factor for power requirements."""
        base_factor = 1.0
        if content.get('animation', False):
            base_factor *= 1.2
        if content.get('color_depth', 8) > 8:
            base_factor *= 1.1
        return base_factor

    def _get_available_power(self, battery_level: float) -> float:
        """Determine available power based on battery level."""
        max_available = self._max_laser_power
        if battery_level < 20.0:
            return max_available * 0.6
        elif battery_level < 50.0:
            return max_available * 0.8
        return max_available

    def _update_quality_metrics(self, params: ProjectionParameters) -> None:
        """Update quality metrics based on current parameters."""
        self._quality_metrics = {
            'brightness_quality': params.brightness / self._max_brightness,
            'refresh_quality': params.refresh_rate / self._max_refresh_rate,
            'power_efficiency': params.laser_power / self._max_laser_power,
            'overall_quality': self._calculate_overall_quality(params)
        }

    def _calculate_overall_quality(self, params: ProjectionParameters) -> float:
        """Calculate overall projection quality score."""
        weights = {
            'brightness': 0.3,
            'refresh_rate': 0.3,
            'power_efficiency': 0.4
        }
        
        quality_score = (
            weights['brightness'] * (params.brightness / self._max_brightness) +
            weights['refresh_rate'] * (params.refresh_rate / self._max_refresh_rate) +
            weights['power_efficiency'] * (1 - (params.laser_power / self._max_laser_power))
        )
        
        return max(min(quality_score, 1.0), 0.0)

    def get_quality_metrics(self) -> Dict[str, float]:
        """Return current quality metrics."""
        return self._quality_metrics.copy()

    def get_current_parameters(self) -> Optional[ProjectionParameters]:
        """Return current projection parameters."""
        return self._current_params