class SmallException(Exception):
    pass


class NoHomeworkError(SmallException):
    pass


class BadServerResponseError(SmallException):
    pass


class ServerConnectionError(SmallException):
    pass
