import os
import yaml
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir="logs", log_filename="system.log", log_level=logging.INFO):
    """
    Sets up the logging framework for the operating system.
    Configures standard console output and a rotating file logger.
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_path = os.path.join(log_dir, log_filename)
    
    # Define logger formatter
    log_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Set up rotating file handler (10MB limit, keep 30 backup files)
    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=30
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(log_level)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(log_level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers to prevent duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info("Logging framework initialized successfully.")

def load_config(config_path="config/config.yaml"):
    """
    Helper function to load the YAML configuration parameters.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
        
    with open(config_path, "r") as file:
        config_data = yaml.safe_load(file)
        
    return config_data
