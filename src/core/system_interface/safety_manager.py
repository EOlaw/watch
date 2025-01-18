from typing import Dict, List, Optional, Callable
import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from src.utils.error_handling import SafetyError
from src.core.system_interface.status_monitor import StatusMonitor, AlertLevel, SystemComponent, SystemAlert

class SafetyCondition(Enum):
    TEMPERATURE = "temperature"
    POWER = "power"
    PROJECTION = "projection"
    MECHANICAL = "mechanical"
    ENVIRONMENT = "environment"

class SafetyAction(Enum):
    NOTIFY = "notify"
    THROTTLE = "throttle"
    SHUTDOWN = "shutdown"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"

@dataclass
class SafetyThreshold:
    condition: SafetyCondition
    warning_level: float
    critical_level: float
    action: SafetyAction
    recovery_level: float

@dataclass
class SafetyEvent:
    condition: SafetyCondition
    level: float
    action_taken: SafetyAction
    timestamp: datetime
    description: str

class SafetyManager:
    def __init__(self, status_monitor: StatusMonitor):
        self.logger = logging.getLogger(__name__)
        self._status_monitor = status_monitor
        self._is_monitoring = False
        self._safety_check_interval = 0.1  # seconds
        
        # Safety thresholds
        self._thresholds = {
            SafetyCondition.TEMPERATURE: SafetyThreshold(
                condition=SafetyCondition.TEMPERATURE,
                warning_level=40.0,  # °C
                critical_level=50.0,  # °C
                action=SafetyAction.SHUTDOWN,
                recovery_level=35.0  # °C
            ),
            SafetyCondition.POWER: SafetyThreshold(
                condition=SafetyCondition.POWER,
                warning_level=15.0,  # %
                critical_level=5.0,  # %
                action=SafetyAction.SHUTDOWN,
                recovery_level=20.0  # %
            ),
            SafetyCondition.PROJECTION: SafetyThreshold(
                condition=SafetyCondition.PROJECTION,
                warning_level=80.0,  # % of max power
                critical_level=95.0,  # % of max power
                action=SafetyAction.THROTTLE,
                recovery_level=70.0  # %
            ),
            SafetyCondition.MECHANICAL: SafetyThreshold(
                condition=SafetyCondition.MECHANICAL,
                warning_level=85.0,  # % of max stress
                critical_level=95.0,  # % of max stress
                action=SafetyAction.EMERGENCY_SHUTDOWN,
                recovery_level=75.0  # %
            ),
            SafetyCondition.ENVIRONMENT: SafetyThreshold(
                condition=SafetyCondition.ENVIRONMENT,
                warning_level=85.0,  # % of safe range
                critical_level=95.0,  # % of safe range
                action=SafetyAction.NOTIFY,
                recovery_level=75.0  # %
            )
        }
        
        # Safety state tracking
        self._current_conditions: Dict[SafetyCondition, float] = {}
        self._active_warnings: Dict[SafetyCondition, datetime] = {}
        self._safety_events: List[SafetyEvent] = []
        self._event_handlers: Dict[SafetyAction, List[Callable]] = {
            action: [] for action in SafetyAction
        }
        
        # Register alert handlers
        self._status_monitor.register_alert_callback(
            AlertLevel.WARNING, self._handle_system_warning)
        self._status_monitor.register_alert_callback(
            AlertLevel.CRITICAL, self._handle_system_critical)

    async def initialize(self) -> bool:
        """Initialize the safety management system."""
        try:
            self.logger.info("Initializing safety manager...")
            
            # Initialize condition monitoring
            for condition in SafetyCondition:
                self._current_conditions[condition] = 0.0
            
            # Start safety monitoring
            self._is_monitoring = True
            asyncio.create_task(self._safety_monitor_loop())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Safety manager initialization failed: {str(e)}")
            raise SafetyError(f"Failed to initialize safety manager: {str(e)}")

    async def _safety_monitor_loop(self) -> None:
        """Main safety monitoring loop."""
        while self._is_monitoring:
            try:
                # Update safety conditions
                await self._update_safety_conditions()
                
                # Check all safety thresholds
                for condition in SafetyCondition:
                    await self._check_safety_threshold(condition)
                
                # Process any pending safety actions
                await self._process_safety_actions()
                
                await asyncio.sleep(self._safety_check_interval)
                
            except Exception as e:
                self.logger.error(f"Safety monitoring error: {str(e)}")
                await asyncio.sleep(1.0)

    async def _update_safety_conditions(self) -> None:
        """Update current safety conditions from system status."""
        try:
            # Get component status updates
            power_status = await self._status_monitor.get_component_status(SystemComponent.POWER)
            thermal_status = await self._status_monitor.get_component_status(SystemComponent.THERMAL)
            projection_status = await self._status_monitor.get_component_status(SystemComponent.PROJECTION)
            
            # Update condition values
            self._current_conditions[SafetyCondition.TEMPERATURE] = thermal_status.metrics.get('temperature', 0.0)
            self._current_conditions[SafetyCondition.POWER] = power_status.metrics.get('battery_level', 0.0)
            self._current_conditions[SafetyCondition.PROJECTION] = projection_status.metrics.get('power_level', 0.0)
            
            # Update mechanical and environmental conditions
            await self._update_mechanical_conditions()
            await self._update_environmental_conditions()
            
        except Exception as e:
            self.logger.error(f"Failed to update safety conditions: {str(e)}")
            raise SafetyError(f"Safety condition update failed: {str(e)}")

    async def _update_mechanical_conditions(self) -> None:
        """Update mechanical safety conditions."""
        try:
            motion_status = await self._status_monitor.get_component_status(SystemComponent.MOTION)
            
            # Calculate mechanical stress level
            acceleration = motion_status.metrics.get('acceleration', 0.0)
            vibration = motion_status.metrics.get('vibration', 0.0)
            stress_level = self._calculate_mechanical_stress(acceleration, vibration)
            
            self._current_conditions[SafetyCondition.MECHANICAL] = stress_level
            
        except Exception as e:
            self.logger.error(f"Mechanical condition update failed: {str(e)}")

    async def _update_environmental_conditions(self) -> None:
        """Update environmental safety conditions."""
        try:
            # In production, this would interface with environmental sensors
            # For now, using placeholder values
            self._current_conditions[SafetyCondition.ENVIRONMENT] = 50.0
            
        except Exception as e:
            self.logger.error(f"Environmental condition update failed: {str(e)}")

    def _calculate_mechanical_stress(self, acceleration: float, vibration: float) -> float:
        """Calculate mechanical stress level from motion parameters."""
        try:
            # Simplified stress calculation
            max_acceleration = 10.0  # m/s²
            max_vibration = 100.0  # Hz
            
            acceleration_factor = min(acceleration / max_acceleration, 1.0)
            vibration_factor = min(vibration / max_vibration, 1.0)
            
            return (acceleration_factor * 0.7 + vibration_factor * 0.3) * 100.0
            
        except Exception as e:
            self.logger.error(f"Mechanical stress calculation failed: {str(e)}")
            return 0.0

    async def _check_safety_threshold(self, condition: SafetyCondition) -> None:
        """Check if a safety condition exceeds its thresholds."""
        try:
            current_value = self._current_conditions[condition]
            threshold = self._thresholds[condition]
            
            # Check critical level
            if current_value >= threshold.critical_level:
                await self._handle_critical_condition(condition, current_value)
            # Check warning level
            elif current_value >= threshold.warning_level:
                await self._handle_warning_condition(condition, current_value)
            # Check recovery
            elif condition in self._active_warnings and current_value <= threshold.recovery_level:
                await self._handle_condition_recovery(condition)
                
        except Exception as e:
            self.logger.error(f"Safety threshold check failed for {condition}: {str(e)}")

    async def _handle_critical_condition(self, condition: SafetyCondition, value: float) -> None:
        """Handle a critical safety condition."""
        try:
            threshold = self._thresholds[condition]
            
            # Record safety event
            event = SafetyEvent(
                condition=condition,
                level=value,
                action_taken=threshold.action,
                timestamp=datetime.now(),
                description=f"Critical {condition.value} level: {value:.1f}"
            )
            self._safety_events.append(event)
            
            # Take immediate action
            await self._execute_safety_action(threshold.action, condition, value)
            
            # Notify status monitor
            await self._status_monitor._record_alert(
                component=SystemComponent.SAFETY,
                level=AlertLevel.CRITICAL,
                message=f"Critical safety condition: {condition.value}"
            )
            
        except Exception as e:
            self.logger.error(f"Critical condition handler failed: {str(e)}")

    async def _handle_warning_condition(self, condition: SafetyCondition, value: float) -> None:
        """Handle a warning level safety condition."""
        try:
            if condition not in self._active_warnings:
                self._active_warnings[condition] = datetime.now()
                
                # Record safety event
                event = SafetyEvent(
                    condition=condition,
                    level=value,
                    action_taken=SafetyAction.NOTIFY,
                    timestamp=datetime.now(),
                    description=f"Warning {condition.value} level: {value:.1f}"
                )
                self._safety_events.append(event)
                
                # Notify status monitor
                await self._status_monitor._record_alert(
                    component=SystemComponent.SAFETY,
                    level=AlertLevel.WARNING,
                    message=f"Safety warning condition: {condition.value}"
                )
                
        except Exception as e:
            self.logger.error(f"Warning condition handler failed: {str(e)}")

    async def _handle_condition_recovery(self, condition: SafetyCondition) -> None:
        """Handle recovery from a warning condition."""
        try:
            if condition in self._active_warnings:
                del self._active_warnings[condition]
                
                # Record recovery event
                event = SafetyEvent(
                    condition=condition,
                    level=self._current_conditions[condition],
                    action_taken=SafetyAction.NOTIFY,
                    timestamp=datetime.now(),
                    description=f"{condition.value} recovered to safe level"
                )
                self._safety_events.append(event)
                
                # Notify status monitor
                await self._status_monitor._record_alert(
                    component=SystemComponent.SAFETY,
                    level=AlertLevel.INFO,
                    message=f"Safety condition recovered: {condition.value}"
                )
                
        except Exception as e:
            self.logger.error(f"Condition recovery handler failed: {str(e)}")

    async def _execute_safety_action(self, action: SafetyAction, condition: SafetyCondition, value: float) -> None:
        """Execute a safety action."""
        try:
            self.logger.warning(f"Executing safety action: {action.value} for {condition.value}")
            
            # Execute registered handlers for this action
            for handler in self._event_handlers[action]:
                try:
                    await handler(condition, value)
                except Exception as handler_error:
                    self.logger.error(f"Safety action handler failed: {str(handler_error)}")
            
            # Perform built-in actions
            if action == SafetyAction.EMERGENCY_SHUTDOWN:
                await self._perform_emergency_shutdown()
            elif action == SafetyAction.SHUTDOWN:
                await self._perform_controlled_shutdown()
            elif action == SafetyAction.THROTTLE:
                await self._perform_system_throttling(condition)
                
        except Exception as e:
            self.logger.error(f"Safety action execution failed: {str(e)}")

    async def _perform_emergency_shutdown(self) -> None:
        """Perform emergency system shutdown."""
        try:
            self.logger.critical("Initiating emergency shutdown")
            # Implement emergency shutdown sequence
            # This would interface with actual hardware shutdown procedures
            
        except Exception as e:
            self.logger.critical(f"Emergency shutdown failed: {str(e)}")

    async def _perform_controlled_shutdown(self) -> None:
        """Perform controlled system shutdown."""
        try:
            self.logger.warning("Initiating controlled shutdown")
            # Implement controlled shutdown sequence
            # This would interface with actual hardware shutdown procedures
            
        except Exception as e:
            self.logger.error(f"Controlled shutdown failed: {str(e)}")

    async def _perform_system_throttling(self, condition: SafetyCondition) -> None:
        """Perform system throttling for the specified condition."""
        try:
            self.logger.warning(f"Initiating system throttling for {condition.value}")
            # Implement throttling logic based on condition
            # This would interface with actual system controllers
            
        except Exception as e:
            self.logger.error(f"System throttling failed: {str(e)}")

    async def _handle_system_warning(self, alert: SystemAlert) -> None:
        """Handle system warning alerts."""
        try:
            # Convert system alerts to safety conditions if applicable
            condition = self._map_alert_to_condition(alert)
            if condition:
                current_value = self._current_conditions.get(condition, 0.0)
                await self._handle_warning_condition(condition, current_value)
                
        except Exception as e:
            self.logger.error(f"System warning handler failed: {str(e)}")

    async def _handle_system_critical(self, alert: SystemAlert) -> None:
        """Handle system critical alerts."""
        try:
            # Convert system alerts to safety conditions if applicable
            condition = self._map_alert_to_condition(alert)
            if condition:
                current_value = self._current_conditions.get(condition, 0.0)
                await self._handle_critical_condition(condition, current_value)
                
        except Exception as e:
            self.logger.error(f"System critical handler failed: {str(e)}")

    def _map_alert_to_condition(self, alert: SystemAlert) -> Optional[SafetyCondition]:
        """Map system alerts to safety conditions."""
        component_to_condition = {
            SystemComponent.POWER: SafetyCondition.POWER,
            SystemComponent.THERMAL: SafetyCondition.TEMPERATURE,
            SystemComponent.PROJECTION: SafetyCondition.PROJECTION,
            SystemComponent.MOTION: SafetyCondition.MECHANICAL
        }
        return component_to_condition.get(alert.component)

    def register_safety_handler(self, action: SafetyAction, handler: Callable) -> None:
        """Register a handler for safety actions."""
        self._event_handlers[action].append(handler)

    def unregister_safety_handler(self, action: SafetyAction, handler: Callable) -> None:
        """Unregister a safety action handler."""
        if handler in self._event_handlers[action]:
            self._event_handlers[action].remove(handler)

    async def get_safety_status(self) -> Dict[SafetyCondition, float]:
        """Get current safety status for all conditions."""
        return self._current_conditions.copy()

    async def get_active_warnings(self) -> Dict[SafetyCondition, datetime]:
        """Get currently active warning conditions."""
        return self._active_warnings.copy()

    async def get_safety_events(self, limit: int = 100) -> List[SafetyEvent]:
        """Get recent safety events."""
        return sorted(self._safety_events, key=lambda x: x.timestamp, reverse=True)[:limit]

    async def cleanup(self) -> None:
        """Cleanup resources and shutdown safety monitoring."""
        try:
            self._is_monitoring = False
            self.logger.info("Safety manager cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise SafetyError(f"Failed to cleanup safety manager: {str(e)}")
        
    async def _process_safety_actions(self) -> None:
        """Process pending safety actions."""
        try:
            for condition, value in self._current_conditions.items():
                threshold = self._thresholds[condition]
                if value >= threshold.critical_level:
                    await self._execute_safety_action(threshold.action, condition, value)
        except Exception as e:
            self.logger.error(f"Failed to process safety actions: {str(e)}")