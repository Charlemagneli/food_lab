class APIError(Exception):
    def __init__(self, code, message, status=400, fields=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields or {}


def error_payload(code, message, fields=None):
    payload = {"code": code, "error": message}
    if fields:
        payload["fields"] = fields
    return payload
