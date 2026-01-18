"""
Logging configuration for JARVISv4
"""
import logging
from typing import Optional
from .metrics import MetricsCollector

class LoggerConfig:
    """Configuration for logging in JARVISv4"""
    
    @staticmethod
    def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
        """Set up logging configuration"""
        # Create custom logger
        logger = logging.getLogger("JARVISv4")
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create handlers
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Create formatters and add to handlers
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        if not logger.handlers:  # Avoid adding multiple handlers
            logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger

# Global instances for simple access
metrics_collector = MetricsCollector()

def setup_observability(log_level: str = "INFO", log_file: Optional[str] = None):
    """Set up observability for the entire system"""
    logger = LoggerConfig.setup_logging(log_level, log_file)
    logger.info("Observability system initialized")
    return logger
