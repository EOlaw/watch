from typing import Dict, Optional, List, Callable
import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from src.utils.error_handling import SystemMonitorError
from src.core.power_management.battery_controller import BatteryController
from src.core.holographic_projector.projection_optimizer import ProjectionOptimizer

class SystemComponent(Enum):
    POWER = "power"
    PROJECTION = "projection"
    THERMAL = "thermal"
    MOTION = "motion"
    INTERFACE = "interface"
    SAFETY = "safety"

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class SystemAlert:
    component: SystemComponent
    level: AlertLevel
    message: str
    timestamp: datetime
    data: Optional[Dict] = None

@dataclass
class ComponentStatus:
    component: SystemComponent
    status: str
    health: float  # 0-100%
    last_update: datetime
    metrics: Dict[str, float]
    alerts: List[SystemAlert]

class StatusMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._component_status: Dict[SystemComponent, ComponentStatus] = {}
        self._alert_history: List[SystemAlert] = []
        self._alert_callbacks: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.INFO: [],
            AlertLevel.WARNING: [],
            AlertLevel.ERROR: [],
            AlertLevel.CRITICAL: []
        }
        self._is_monitoring = False
        self._status_update_interval = 1.0  # seconds
        self._alert_retention_period = 3600  # 1 hour in seconds

    async def initialize(self) -> bool:
        """Initialize the status monitoring system."""
        try:
            self.logger.info("Initializing status monitor...")
            
            # Initialize component status tracking
            for component in SystemComponent:
                self._component_status[component] = ComponentStatus(
                    component=component,
                    status="initializing",
                    health=100.0,
                    last_update=datetime.now(),
                    metrics={},
                    alerts=[]
                )
            
            # Start monitoring tasks
            self._is_monitoring = True
            asyncio.create_task(self._status_update_loop())
            asyncio.create_task(self._alert_cleanup_loop())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Status monitor initialization failed: {str(e)}")
            raise SystemMonitorError(f"Failed to initialize status monitor: {str(e)}")

    async def _status_update_loop(self) -> None:
        """Main status update loop."""
        while self._is_monitoring:
            try:
                await self._update_all_components()
                await self._analyze_system_health()
                await asyncio.sleep(self._status_update_interval)
                
            except Exception as e:
                self.logger.error(f"Status update loop error: {str(e)}")
                await asyncio.sleep(5.0)  # Back off on error

    async def _update_all_components(self) -> None:
        """Update status for all system components."""
        try:
            update_tasks = []
            for component in SystemComponent:
                update_tasks.append(self._update_component_status(component))
            
            await asyncio.gather(*update_tasks)
            
        except Exception as e:
            self.logger.error(f"Component status update failed: {str(e)}")

    async def _update_component_status(self, component: SystemComponent) -> None:
        """Update status for a specific component."""
        try:
            metrics = await self._collect_component_metrics(component)
            health = await self._calculate_component_health(component, metrics)
            
            self._component_status[component] = ComponentStatus(
                component=component,
                status="operational" if health > 50 else "degraded",
                health=health,
                last_update=datetime.now(),
                metrics=metrics,
                alerts=self._component_status[component].alerts
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update {component.value} status: {str(e)}")
            self._record_alert(
                component=component,
                level=AlertLevel.ERROR,
                message=f"Status update failed: {str(e)}"
            )

    async def _collect_component_metrics(self, component: SystemComponent) -> Dict[str, float]:
        """Collect performance metrics for a component."""
        try:
            metrics = {}
            
            if component == SystemComponent.POWER:
                battery_status = await self._get_battery_status()
                metrics.update({
                    'battery_level': battery_status.level,
                    'power_consumption': battery_status.current * battery_status.voltage,
                    'temperature': battery_status.temperature
                })
                
            elif component == SystemComponent.PROJECTION:
                projection_metrics = await self._get_projection_metrics()
                metrics.update({
                    'brightness': projection_metrics.get('brightness', 0),
                    'resolution': projection_metrics.get('resolution', 0),
                    'stability': projection_metrics.get('stability', 0)
                })
                
            elif component == SystemComponent.THERMAL:
                thermal_metrics = await self._get_thermal_metrics()
                metrics.update({
                    'temperature_gradient': thermal_metrics.get('gradient', 0),
                    'cooling_efficiency': thermal_metrics.get('efficiency', 0)
                })
                
            elif component == SystemComponent.MOTION:
                motion_metrics = await self._get_motion_metrics()
                metrics.update({
                    'acceleration': motion_metrics.get('acceleration', 0),
                    'stability': motion_metrics.get('stability', 0)
                })
                
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics for {component.value}: {str(e)}")
            return {}

    async def _analyze_system_health(self) -> None:
        """Analyze overall system health and generate alerts."""
        try:
            for component, status in self._component_status.items():
                # Check for critical health conditions
                if status.health < 20.0:
                    self._record_alert(
                        component=component,
                        level=AlertLevel.CRITICAL,
                        message=f"Critical {component.value} health: {status.health}%"
                    )
                elif status.health < 50.0:
                    self._record_alert(
                        component=component,
                        level=AlertLevel.WARNING,
                        message=f"Low {component.value} health: {status.health}%"
                    )
                
                # Check for stale status updates
                time_since_update = (datetime.now() - status.last_update).total_seconds()
                if time_since_update > self._status_update_interval * 3:
                    self._record_alert(
                        component=component,
                        level=AlertLevel.ERROR,
                        message=f"Stale status for {component.value}"
                    )
                
        except Exception as e:
            self.logger.error(f"Health analysis failed: {str(e)}")

    def _record_alert(self, component: SystemComponent, level: AlertLevel, message: str, data: Dict = None) -> None:
        """Record a system alert."""
        try:
            alert = SystemAlert(
                component=component,
                level=level,
                message=message,
                timestamp=datetime.now(),
                data=data
            )
            
            # Add to component alerts
            self._component_status[component].alerts.append(alert)
            
            # Add to global alert history
            self._alert_history.append(alert)
            
            # Trigger alert callbacks
            for callback in self._alert_callbacks[level]:
                try:
                    callback(alert)
                except Exception as cb_error:
                    self.logger.error(f"Alert callback failed: {str(cb_error)}")
            
            self.logger.log(
                logging.CRITICAL if level == AlertLevel.CRITICAL else
                logging.ERROR if level == AlertLevel.ERROR else
                logging.WARNING if level == AlertLevel.WARNING else
                logging.INFO,
                f"{level.value.upper()}: {message}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to record alert: {str(e)}")

    async def _alert_cleanup_loop(self) -> None:
        """Cleanup old alerts periodically."""
        while self._is_monitoring:
            try:
                current_time = datetime.now()
                cutoff_time = current_time.timestamp() - self._alert_retention_period
                
                # Cleanup component alerts
                for status in self._component_status.values():
                    status.alerts = [
                        alert for alert in status.alerts
                        if alert.timestamp.timestamp() > cutoff_time
                    ]
                
                # Cleanup global alert history
                self._alert_history = [
                    alert for alert in self._alert_history
                    if alert.timestamp.timestamp() > cutoff_time
                ]
                
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Alert cleanup failed: {str(e)}")
                await asyncio.sleep(60)

    def register_alert_callback(self, level: AlertLevel, callback: Callable[[SystemAlert], None]) -> None:
        """Register a callback for specific alert levels."""
        self._alert_callbacks[level].append(callback)

    def unregister_alert_callback(self, level: AlertLevel, callback: Callable[[SystemAlert], None]) -> None:
        """Unregister an alert callback."""
        if callback in self._alert_callbacks[level]:
            self._alert_callbacks[level].remove(callback)

    async def get_component_status(self, component: SystemComponent) -> ComponentStatus:
        """Get current status for a specific component."""
        if component not in self._component_status:
            raise SystemMonitorError(f"Unknown component: {component.value}")
        return self._component_status[component]

    async def get_system_health(self) -> Dict[SystemComponent, float]:
        """Get health status for all components."""
        return {
            component: status.health
            for component, status in self._component_status.items()
        }

    async def get_alerts(self, 
                        component: Optional[SystemComponent] = None,
                        level: Optional[AlertLevel] = None,
                        limit: int = 100) -> List[SystemAlert]:
        """Get filtered system alerts."""
        alerts = self._alert_history
        
        if component:
            alerts = [a for a in alerts if a.component == component]
        if level:
            alerts = [a for a in alerts if a.level == level]
            
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)[:limit]

    async def cleanup(self) -> None:
        """Cleanup resources and shutdown monitoring."""
        try:
            self._is_monitoring = False
            self.logger.info("Status monitor cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise SystemMonitorError(f"Failed to cleanup status monitor: {str(e)}")
        
    # Add these methods to StatusMonitor class
    async def _get_battery_status(self) -> BatteryStatus:
        power_status = await self._component_status[SystemComponent.POWER]
        return power_status.metrics

    async def _calculate_component_health(self, component: SystemComponent, metrics: Dict[str, float]) -> float:
        """Calculate health score for a component based on its metrics."""
        try:
            if component == SystemComponent.POWER:
                return self._calculate_power_health(metrics)
            elif component == SystemComponent.THERMAL:
                return self._calculate_thermal_health(metrics)
            # Add similar calculations for other components
            return 100.0  # Default health score
        except Exception as e:
            self.logger.error(f"Health calculation failed for {component.value}")
            return 0.0