class DuplicatedRecommendationsError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class RecommendationsLimitSizeError(Exception):
    pass


class HugeResponseSizeError(Exception):
    pass


class RequestLimitByUserError(Exception):
    pass
