class InvalidURLError(Exception):
    """Raised when provided url is not valid"""


class TooManyRequestsError(Exception):
    """Raised when chat requests bot too much"""


class IncorrectValueError(Exception):
    """Raised when given value not matches the requirements"""
