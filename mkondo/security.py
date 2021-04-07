import enum

from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_claims


class UserType(enum.Enum):
    SA = 'super admin'
    A = 'admin'
    C = 'creator'
    U = 'user'
    V = 'visitor'


def authorized_users(user_type_keys=[]):
    def actual_decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt_claims()
            user_type_key = UserType(claims['user_type']).name
            for key in user_type_keys:
                if key not in UserType.__members__:
                    return {'success': False, 'message': 'User type unknown.'}, 500
            if user_type_key not in user_type_keys:
                return {'success': False, 'message': 'You are not authorized to access this endpoint'}, 403
            return fn(*args, **kwargs)
        return wrapper
    return actual_decorator
