import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
import json
from pathlib import Path

class HolographicWatchLogger:
    """Custom logger for the holographic watch system."""
    
    def __init__(self, name: str, log_dir: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.name = name
        
        # Set default log directory if none provided
        self.log_dir = log_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'logs'
        )
        
        # Ensure log directory exists
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure logger with appropriate handlers and formatters."""
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatters
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # File handlers
        main_file_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'{self.name}.log')
        )
        main_file_handler.setLevel(logging.DEBUG)
        main_file_handler.setFormatter(file_formatter)
        
        error_file_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'{self.name}_error.log')
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(file_formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(main_file_handler)
        self.logger.addHandler(error_file_handler)

    def _format_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format log message with optional context."""
        if context:
            return f"{message} | Context: {json.dumps(context)}"
        return message

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message with optional context."""
        self.logger.debug(self._format_message(message, context))

    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log info message with optional context."""
        self.logger.info(self._format_message(message, context))

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message with optional context."""
        self.logger.warning(self._format_message(message, context))

    def error(self, message: str, error: Optional[Exception] = None,
              context: Optional[Dict[str, Any]] = None) -> None:
        """Log error message with optional error details and context."""
        error_context = context or {}
        if error:
            error_context.update({
                'error_type': type(error).__name__,
                'error_message': str(error)
            })
        self.logger.error(self._format_message(message, error_context))

    def critical(self, message: str, error: Optional[Exception] = None,
                context: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message with optional error details and context."""
        error_context = context or {}
        if error:
            error_context.update({
                'error_type': type(error).__name__,
                'error_message': str(error)
            })
        self.logger.critical(self._format_message(message, error_context))

    def log_system_status(self, status: Dict[str, Any]) -> None:
        """Log system status information."""
        self.info("System Status Update", status)

    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log system performance metrics."""
        self.debug("Performance Metrics", metrics)

    def log_safety_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log safety-related events."""
        self.warning(f"Safety Event: {event_type}", details)

    def start_operation(self, operation: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Log the start of an operation."""
        self.info(f"Starting Operation: {operation}", params)

    def end_operation(self, operation: str, result: Dict[str, Any]) -> None:
        """Log the completion of an operation."""
        self.info(f"Completed Operation: {operation}", result)

    def log_error_with_traceback(self, message: str, error: Exception,
                               context: Optional[Dict[str, Any]] = None) -> None:
        """Log error with full traceback information."""
        import traceback
        error_context = context or {}
        error_context.update({
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        })
        self.error(message, error, error_context)