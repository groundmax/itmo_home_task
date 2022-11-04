class DuplicatedRecommendationsError(Exception):
    pass


class RecommendationsLimitSizeError(Exception):
    pass


class HugeResponseSizeError(Exception):
    pass


class RequestLimitByUserError(Exception):
    pass
