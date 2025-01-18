import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from .error_handling import ConfigurationError
from .logging_utils import HolographicWatchLogger

class SystemConfiguration:
    """Configuration management for the holographic watch system."""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.logger = HolographicWatchLogger(__name__)
        
        # Set default config directory if none provided
        self.config_dir = config_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config'
        )
        
        # Ensure config directory exists
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize configuration storage
        self._config: Dict[str, Any] = {}
        self._load_default_config()

    def _load_default_config(self) -> None:
        """Load default system configuration."""
        default_config = {
            'system': {
                'debug_mode': False,
                'performance_logging': True,
                'safety_checks_interval': 0.1,
                'status_update_interval': 1.0
            },
            'projection': {
                'default_brightness': 0.8,
                'min_refresh_rate': 30,
                'max_refresh_rate': 120,
                'default_resolution': (800, 600),
                'color_depth': 8
            },
            'power': {
                'low_battery_threshold': 20.0,
                'critical_battery_threshold': 10.0,
                'power_save_mode_threshold': 30.0,
                'charging_threshold': 85.0
            },
            'safety': {
                'max_temperature': 45.0,
                'max_power_draw': 5.0,
                'max_laser_power': 50.0,
                'emergency_shutdown_delay': 0.5
            },
            'interaction': {
                'gesture_sensitivity': 0.7,
                'voice_recognition_confidence': 0.8,
                'interaction_timeout': 30.0,
                'max_range': 50.0
            }
        }
        self._config.update(default_config)

    def load_config(self, config_file: str) -> None:
        """Load configuration from file."""
        try:
            config_path = os.path.join(self.config_dir, config_file)
            
            if not os.path.exists(config_path):
                raise ConfigurationError(f"Configuration file not found: {config_path}")
            
            file_extension = os.path.splitext(config_file)[1].lower()
            
            if file_extension == '.json':
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
            elif file_extension in ['.yml', '.yaml']:
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
            else:
                raise ConfigurationError(f"Unsupported configuration file format: {file_extension}")
            
            # Update configuration with loaded data
            self._update_config_recursive(self._config, config_data)
            
            self.logger.info(
                "Configuration loaded successfully",
                {"config_file": config_file}
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")

    def _update_config_recursive(self, base_config: Dict[str, Any],
                               new_config: Dict[str, Any]) -> None:
        """Recursively update configuration while preserving structure."""
        for key, value in new_config.items():
            if key in base_config and isinstance(base_config[key], dict):
                if isinstance(value, dict):
                    self._update_config_recursive(base_config[key], value)
                else:
                    raise ConfigurationError(
                        f"Invalid configuration structure for key: {key}"
                    )
            else:
                base_config[key] = value

    def save_config(self, config_file: str) -> None:
        """Save current configuration to file."""
        try:
            config_path = os.path.join(self.config_dir, config_file)
            
            file_extension = os.path.splitext(config_file)[1].lower()
            
            if file_extension == '.json':
                with open(config_path, 'w') as f:
                    json.dump(self._config, f, indent=4)
            elif file_extension in ['.yml', '.yaml']:
                with open(config_path, 'w') as f:
                    yaml.safe_dump(self._config, f, default_flow_style=False)
            else:
                raise ConfigurationError(f"Unsupported configuration file format: {file_extension}")
            
            self.logger.info(
                "Configuration saved successfully",
                {"config_file": config_file}
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {str(e)}")

    def get_config(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve configuration settings."""
        try:
            if section:
                if section not in self._config:
                    raise ConfigurationError(f"Configuration section not found: {section}")
                return self._config[section].copy()
            return self._config.copy()
            
        except Exception as e:
            raise ConfigurationError(f"Failed to retrieve configuration: {str(e)}")

    def update_config(self, updates: Dict[str, Any], section: Optional[str] = None) -> None:
        """Update configuration settings."""
        try:
            if section:
                if section not in self._config:
                    raise ConfigurationError(f"Configuration section not found: {section}")
                self._update_config_recursive(self._config[section], updates)
            else:
                self._update_config_recursive(self._config, updates)
                
            self.logger.info(
                "Configuration updated successfully",
                {"section": section if section else "all", "updates": updates}
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to update configuration: {str(e)}")

    def validate_config(self) -> bool:
        """Validate current configuration settings."""
        try:
            # Validate system configuration
            self._validate_system_config()
            
            # Validate projection configuration
            self._validate_projection_config()
            
            # Validate power configuration
            self._validate_power_config()
            
            # Validate safety configuration
            self._validate_safety_config()
            
            # Validate interaction configuration
            self._validate_interaction_config()
            
            self.logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            self.logger.error("Configuration validation failed", error=e)
            return False

    def _validate_system_config(self) -> None:
        """Validate system configuration settings."""
        system_config = self._config.get('system', {})
        
        if not isinstance(system_config.get('safety_checks_interval'), (int, float)):
            raise ConfigurationError("Invalid safety_checks_interval value")
            
        if not isinstance(system_config.get('status_update_interval'), (int, float)):
            raise ConfigurationError("Invalid status_update_interval value")

    def _validate_projection_config(self) -> None:
        """Validate projection configuration settings."""
        proj_config = self._config.get('projection', {})
        
        if not 0 <= proj_config.get('default_brightness', 0) <= 1:
            raise ConfigurationError("Invalid default_brightness value")
            
        if not isinstance(proj_config.get('min_refresh_rate'), (int, float)):
            raise ConfigurationError("Invalid min_refresh_rate value")
            
        if not isinstance(proj_config.get('max_refresh_rate'), (int, float)):
            raise ConfigurationError("Invalid max_refresh_rate value")

    def _validate_power_config(self) -> None:
        """Validate power configuration settings."""
        power_config = self._config.get('power', {})
        
        if not 0 <= power_config.get('low_battery_threshold', 0) <= 100:
            raise ConfigurationError("Invalid low_battery_threshold value")
            
        if not 0 <= power_config.get('critical_battery_threshold', 0) <= 100:
            raise ConfigurationError("Invalid critical_battery_threshold value")

    def _validate_safety_config(self) -> None:
        """Validate safety configuration settings."""
        safety_config = self._config.get('safety', {})
        
        if not isinstance(safety_config.get('max_temperature'), (int, float)):
            raise ConfigurationError("Invalid max_temperature value")
            
        if not isinstance(safety_config.get('max_power_draw'), (int, float)):
            raise ConfigurationError("Invalid max_power_draw value")

    def _validate_interaction_config(self) -> None:
        """Validate interaction configuration settings."""
        interaction_config = self._config.get('interaction', {})
        
        if not 0 <= interaction_config.get('gesture_sensitivity', 0) <= 1:
            raise ConfigurationError("Invalid gesture_sensitivity value")
            
        if not 0 <= interaction_config.get('voice_recognition_confidence', 0) <= 1:
            raise ConfigurationError("Invalid voice_recognition_confidence value")

    def reset_to_default(self, section: Optional[str] = None) -> None:
        """Reset configuration to default settings."""
        try:
            if section:
                if section not in self._config:
                    raise ConfigurationError(f"Configuration section not found: {section}")
                self._load_default_config()
                self._config[section] = self._config[section].copy()
            else:
                self._load_default_config()
                
            self.logger.info(
                "Configuration reset to default",
                {"section": section if section else "all"}
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to reset configuration: {str(e)}")

    def export_config(self, export_path: str, format: str = 'json') -> None:
        """Export configuration to specified format and location."""
        try:
            if format.lower() == 'json':
                with open(export_path, 'w') as f:
                    json.dump(self._config, f, indent=4)
            elif format.lower() in ['yaml', 'yml']:
                with open(export_path, 'w') as f:
                    yaml.safe_dump(self._config, f, default_flow_style=False)
            else:
                raise ConfigurationError(f"Unsupported export format: {format}")
                
            self.logger.info(
                "Configuration exported successfully",
                {"path": export_path, "format": format}
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to export configuration: {str(e)}")

    def import_config(self, import_path: str) -> None:
        """Import configuration from file."""
        try:
            file_extension = os.path.splitext(import_path)[1].lower()
            
            if file_extension == '.json':
                with open(import_path, 'r') as f:
                    imported_config = json.load(f)
            elif file_extension in ['.yml', '.yaml']:
                with open(import_path, 'r') as f:
                    imported_config = yaml.safe_load(f)
            else:
                raise ConfigurationError(f"Unsupported import format: {file_extension}")
            
            # Validate imported configuration before applying
            self._validate_imported_config(imported_config)
            
            # Apply imported configuration
            self._config = imported_config
            
            self.logger.info(
                "Configuration imported successfully",
                {"path": import_path}
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to import configuration: {str(e)}")

    def _validate_imported_config(self, config: Dict[str, Any]) -> None:
        """Validate structure and values of imported configuration."""
        required_sections = ['system', 'projection', 'power', 'safety', 'interaction']
        
        # Check for required sections
        for section in required_sections:
            if section not in config:
                raise ConfigurationError(f"Missing required configuration section: {section}")
        
        # Store current config
        current_config = self._config
        
        try:
            # Temporarily set config to imported values for validation
            self._config = config
            
            # Validate all sections
            self.validate_config()
            
        finally:
            # Restore current config if validation fails
            self._config = current_config