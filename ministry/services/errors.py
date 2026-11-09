class ServiceError(Exception):
    """Base class for expected, user-facing failures."""


class AlreadyExists(ServiceError):
    pass


class NotFound(ServiceError):
    pass


class NameTooLong(ServiceError):
    def __init__(self, limit: int):
        super().__init__(limit)
        self.limit = limit


class NotEnoughCharacters(ServiceError):
    pass


class CustomGiftsDisabled(ServiceError):
    pass
