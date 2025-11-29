"""
Logging utility module using Python standard library logging with file location info.
"""

import logging
import logging.handlers
import sys
import os
import inspect
from datetime import datetime
import io


class LocationFormatter(logging.Formatter):
    """Custom formatter that adds file location information."""
    
    def format(self, record):
        # Use location info if provided via extra, otherwise extract from record
        if not hasattr(record, 'location'):
            # Fallback: extract from record itself
            filename = os.path.basename(record.pathname) if record.pathname else "unknown"
            function_name = record.funcName if record.funcName else "unknown"
            line_number = record.lineno if record.lineno else 0
            record.location = f"{filename}:{function_name}:{line_number}"
        
        return super().format(record)


def setup_logger():
    """Setup the main logger with console and file handlers."""
    # Create logger
    logger = logging.getLogger('comfyui_copilot')
    logger.setLevel(logging.DEBUG)
    
    # Prevent duplicate logs
    if logger.handlers:
        return logger
    
    # Console handler with safer encoding handling on Windows consoles
    # Prefer reconfiguring the existing stderr to replace unencodable chars
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass
        console_handler = logging.StreamHandler(sys.stderr)
    else:
        # Fallback: wrap the underlying buffer with a TextIOWrapper that replaces errors
        try:
            encoding = getattr(sys.stderr, "encoding", None) or "utf-8"
            console_stream = io.TextIOWrapper(sys.stderr.buffer, encoding=encoding, errors="replace")
            console_handler = logging.StreamHandler(console_stream)
        except Exception:
            console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    
    # Console formatter with colors (simple format for better compatibility)
    console_format = '%(asctime)s | %(levelname)-8s | %(location)s | %(message)s'
    console_formatter = LocationFormatter(console_format, datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(console_formatter)
    
    # File handler
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "comfyui_copilot.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # File formatter
    file_format = '%(asctime)s | %(levelname)-8s | %(location)s | %(message)s'
    file_formatter = LocationFormatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


class Logger:
    """Logger wrapper that provides convenient logging methods with automatic location detection."""
    
    def __init__(self, name=None):
        self._logger = setup_logger()
        if name:
            self._logger = logging.getLogger(f'comfyui_copilot.{name}')
            self._logger.setLevel(logging.DEBUG)
            # Prevent propagation to parent logger to avoid duplicate messages
            self._logger.propagate = False
            
            # Copy handlers from parent logger if the named logger doesn't have any
            if not self._logger.handlers:
                parent_logger = logging.getLogger('comfyui_copilot')
                for handler in parent_logger.handlers:
                    self._logger.addHandler(handler)
    
    def _log_with_location(self, level, message, *args, **kwargs):
        """Log message with automatic location detection."""
        # Get the caller's frame (2 levels up: _log_with_location -> debug/info/etc -> actual caller)
        frame = inspect.currentframe().f_back.f_back
        try:
            filename = os.path.basename(frame.f_code.co_filename)
            function_name = frame.f_code.co_name
            line_number = frame.f_lineno
            
            # Create a log record manually to ensure no duplicate processing
            if self._logger.isEnabledFor(level):
                record = self._logger.makeRecord(
                    self._logger.name, level, frame.f_code.co_filename, line_number,
                    message, args, None, function_name
                )
                record.location = f"{filename}:{function_name}:{line_number}"
                
                # Process the record through handlers directly to avoid duplication
                for handler in self._logger.handlers:
                    if record.levelno >= handler.level:
                        handler.handle(record)
        finally:
            del frame
    
    def debug(self, message, *args, **kwargs):
        """Log debug message."""
        self._log_with_location(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        """Log info message."""
        self._log_with_location(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """Log warning message."""
        self._log_with_location(logging.WARNING, message, *args, **kwargs)
    
    def warn(self, message, *args, **kwargs):
        """Log warning message (alias for warning)."""
        self.warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        """Log error message."""
        self._log_with_location(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        """Log critical message."""
        self._log_with_location(logging.CRITICAL, message, *args, **kwargs)
    
    def exception(self, message, *args, **kwargs):
        """Log exception message with traceback."""
        # For exceptions, we want to use the standard logger.exception which includes traceback
        frame = inspect.currentframe().f_back
        try:
            filename = os.path.basename(frame.f_code.co_filename)
            function_name = frame.f_code.co_name
            line_number = frame.f_lineno
            
            # Use the standard exception logging with location info
            self._logger.exception(message, *args, **kwargs, 
                                 extra={'location': f"{filename}:{function_name}:{line_number}"},
                                 stacklevel=2)
        finally:
            del frame


# Create default logger instance
log = Logger()

# For backward compatibility and convenience
debug = log.debug
info = log.info
warning = log.warning
warn = log.warn
error = log.error
critical = log.critical
exception = log.exception

# Allow creating named loggers
def get_logger(name=None):
    """Get a logger instance, optionally with a specific name."""
    return Logger(name)


__all__ = [
    'log', 'Logger', 'get_logger',
    'debug', 'info', 'warning', 'warn', 'error', 'critical', 'exception'
]