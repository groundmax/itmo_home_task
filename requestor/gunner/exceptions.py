class DuplicatedRecommendationsError(Exception):
    pass


class HTTPAuthorizationError(Exception):
    pass


class HTTPResponseNotOKError(Exception):
    """Raised when response from /health is not ok"""


class RequestTimeoutError(Exception):
    """Raised when reco request exceeds given deadline"""


class RecommendationsLimitSizeError(Exception):
    pass


class HugeResponseSizeError(Exception):
    pass


class RequestLimitByUserError(Exception):
    pass
