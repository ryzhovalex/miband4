from staze import Error


class FreezedMibandError(Error):
    """Error occurs if request to miband chain has been sent, but miband is freezed."""
    pass