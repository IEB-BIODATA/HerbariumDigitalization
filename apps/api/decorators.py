import datetime as dt

import jwt
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest, HttpResponseForbidden

from web import settings


def backend_authenticated(view_func):
    def wrapped_view(request, *args, **kwargs):
        authorization_header = request.META['HTTP_AUTHORIZATION']
        if not authorization_header:
            return HttpResponseBadRequest('Authorization header missing')

        auth_type, auth_token = authorization_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return HttpResponseBadRequest('Invalid authentication type')

        # Verify JWT token
        try:
            payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload['user_id']
            username = payload['username']
            if dt.datetime.utcnow() > dt.datetime.fromtimestamp(payload['exp']):
                raise jwt.ExpiredSignatureError('Token has expired')
            user = User.objects.get(id=user_id, username=username)
            request.user = user
        except (jwt.DecodeError, User.DoesNotExist, KeyError):
            return HttpResponseForbidden('Problems decoding token')
        except jwt.ExpiredSignatureError:
            return HttpResponseForbidden('Token expired')

        return view_func(request, *args, **kwargs)

    return wrapped_view
