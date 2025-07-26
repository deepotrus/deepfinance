import logging

DEFAULT_LOGGING_LEVEL = logging.ERROR

logging.basicConfig(
    level=DEFAULT_LOGGING_LEVEL,
    format='[%(levelname)s]: %(message)s'
)

# Create a logger for the package
Logger = logging.getLogger(__name__)

def set_logging_level(user_level : str):
    """Set the logging level for the logger."""

    log_level = None
    if (user_level == "INFO"):
        log_level = logging.INFO
    elif (user_level == "DEBUG"):
        log_level = logging.DEBUG
    elif (user_level == "WARNING"):
        log_level = logging.WARNING
    elif (user_level == "ERROR"):
        log_level = logging.ERROR
    else:
        print("Invalid log level, choose among DEBUG, WARNING and ERROR")

    Logger.setLevel(log_level)