
import json
class BaseXomifyException(Exception):
    def __init__(self, error, handler, function, status=500, base="💥 Error in Xomify 💥"):
        self.error = error
        self.handler = handler
        self.function = function
        self.status = status
        self.base = base
        self.message = f'{self.base}: {self.error}'
    def get_message(self):
        return self.message
    def get_handler(self):
        return self.handler
    def get_function(self):
        return self.function
    def get_status(self):
        return self.status
    def __str__(self):
        return json.dumps({
            'message': self.get_message(),
            'callingHandler': self.get_handler(),
            'fileAndFunction': self.get_function(),
            'status': self.get_status()
        })
class LambdaAuthorizerError(BaseXomifyException):
    def __init__(self, error, handler, function, status=404, base="💥 Error in Lambda Authorizer 💥"):
        super().__init__(error, handler, function, status, base)

class UnauthorizedError(BaseXomifyException):
    def __init__(self, error, handler, function, status=401, base="💥 Unauthorized in Token Service to access account💥"):
        super().__init__(error, handler, function, status, base)

class DynamodbError(BaseXomifyException):
    def __init__(self, error, handler, function, status=500, base="💥 Error in Xomify Dynamodb Service 💥"):
        super().__init__(error, handler, function, status, base)

class WrappednError(BaseXomifyException):
    def __init__(self, error, handler, function, status=500, base="💥 Error in Xomify Wrapped 💥"):
        super().__init__(error, handler, function, status, base)

