class BaseBarmenException(Exception):
    NOT_FOUND = "Not Found"
    ERROR = 'Error'
    status_code = 401
    type = None

    def __init__(self, message, status_code=None, type=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if type is not None:
            self.type = type
        else:
            self.type = message
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['status_code'] = self.status_code
        rv['type'] = self.type
        rv['message'] = self.message
        return rv
