from ConfigParser import NoSectionError
import datetime
import hashlib

import fnmatch
from baseexception import BaseBarmenException
from flask import g
import flask
from flask.ext.restful import Resource, request
import jwt
import os
from parser import ConfigParser, ConfigParserException


class Auth(Resource):
    token_config = None

    def __init__(self):
        self.token_config = flask.current_app.config.config_main.read_section('auth_token')

    def get(self, command, option=None):
        self.verify_access('auth', command, option)
        self.verify_deny('auth', command, option)
        user_config = self.get_user_config()

        if command == 'token':
            return {'token': self.generate_token(dict({'user': g.user}))}

        elif command == 'user' and option == 'list':
            user_list = {}
            for username in user_config.sections():
                user_list[username] = self.get_user_property(username)
            from app import message_format
            # return {'status_code': 200, 'message': '', 'list': user_list}
            return message_format(200, '', user_list)

        elif command == 'user' and option == 'change':
            if not request.args.get('username'):
                raise AuthException("Parameter Not Found(username)", 404,
                                    AuthException.NOT_FOUND)
            try:
                user = user_config.read_section(request.args.get('username'))
                if request.args.get('password') and user.get('password') != User().hash_password(
                        request.args.get('password')):
                    user_config.set(request.args.get('username'), 'password',
                                    User().hash_password(request.args.get('password')))

                if request.args.get('access') and user.get('access') != request.args.get('access'):
                    user_config.set(request.args.get('username'), 'access', request.args.get('access'))

                if request.args.get('deny') and user.get('deny') != request.args.get('deny'):
                    user_config.set(request.args.get('username'), 'deny', request.args.get('deny'))

                user_config.write_config()

                from app import message_format
                return message_format(200, '', self.get_user_property(request.args.get('username')))
            except ConfigParserException:
                raise AuthException("Username not found(" + request.args.get('username') + ")", 403,
                                    AuthException.NOT_FOUND)

        elif command == 'user' and option == 'add':
            if not request.args.get('username'):
                raise AuthException("Parameter Not Found(username)", 404,
                                    AuthException.NOT_FOUND)

            try:
                user = user_config.read_section(request.args.get('username'))
                if user:
                    raise AuthException("Username registered before(" + request.args.get('username') + ")", 403,
                                        AuthException.USER_FOUND)
            except ConfigParserException:
                if request.args.get('username'):
                    user_config.add_section(request.args.get('username'))

                if request.args.get('password'):
                    user_config.set(request.args.get('username'), 'password',
                                    User().hash_password(request.args.get('password')))
                else:
                    raise AuthException("Parameter Not Found(password)", 404,
                                        AuthException.NOT_FOUND)

                if request.args.get('access'):
                    user_config.set(request.args.get('username'), 'access', request.args.get('access'))
                else:
                    user_config.set(request.args.get('username'), 'access', [])

                if request.args.get('deny'):
                    user_config.set(request.args.get('username'), 'deny', request.args.get('deny'))
                else:
                    user_config.set(request.args.get('username'), 'deny', [])

                user_config.write_config()
                from app import message_format
                return message_format(200, '', self.get_user_property(request.args.get('username')))
        elif command == 'user' and option is None:
            from app import message_format
            return message_format(200, '', {'access': eval(g.user.get('access')), 'deny': eval(g.user.get('deny'))})
        else:
            api = 'auth'
            if command:
                api += '/' + command
            if option:
                api += '/' + option
            raise AuthException('Api not found(' + api, '405', AuthException.NOT_FOUND)

    def get_user_property(self, username):
        user_config = self.get_user_config()
        user = user_config.read_section(username)
        prop = {}

        for user_prop in user:
            if user_prop != 'password':
                prop[user_prop] = eval(user.get(user_prop))

        return prop

    @staticmethod
    def get_user_config():
        config = flask.current_app.config.config_main

        if os.path.exists(config.get('user', 'config_file')):
            return ConfigParser(config.get('user', 'config_file'))
        else:
            return ConfigParser(os.path.dirname(os.path.realpath(__file__)) + config.get('user', 'config_file'))

    def verify_access(self, rest, command=None, option=None):
        access = eval(self.get_user_config().read_section(g.user.get('username')).get('access'))

        if command is not None:
            rest += '/' + command

        if option is not None:
            rest += '/' + option

        is_access = False

        for access_item in access:
            if fnmatch.filter([rest], access_item + '*'):
                is_access = True

        if is_access is False and len(access) > 0:
            raise AuthException('You can not see this rest(' + rest + ')', 403, AuthException.ACCESS_DENY)

    def verify_deny(self, rest, command=None, option=None):
        deny = eval(self.get_user_config().read_section(g.user.get('username')).get('deny'))

        if command is not None:
            rest += '/' + command

        if option is not None:
            rest += '/' + option

        for deny_item in deny:

            if fnmatch.filter([rest], deny_item + '*'):
                raise AuthException('You can not see this rest(' + rest + ')', 403, AuthException.ACCESS_DENY)

    def generate_token(self, encoded_string, exp=True):

        if exp is True:
            encoded_string['exp'] = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=int(self.token_config.get('token_life')))

        encoded = jwt.encode(encoded_string, self.token_config.get('secret'),
                             algorithm=self.token_config.get('algorithm'))

        return encoded

    def verify_token(self, token):
        try:
            decode = jwt.decode(token, self.token_config.get('secret'), algorithm=self.token_config.get('algorithm'))
        except jwt.ExpiredSignatureError:
            raise AuthException('Time is up', 401, AuthException.TOKEN_TIME_UP)
        except:
            raise AuthException('Token is not valid', 401, AuthException.TOKEN_ERROR)

        return decode


class User(object):
    user = {}
    user_config = None

    def __init__(self):
        self.user_config = Auth().get_user_config()

    def get_user(self, username):
        try:
            self.user = self.user_config.read_section(username)
        except NoSectionError:
            raise AuthException(AuthException.TOKEN_ERROR)
        except Exception:
            raise AuthException(AuthException.AUTH_ERROR)

        return self.user

    @staticmethod
    def hash_password(password):
        return hashlib.md5(password.strip(' ')).hexdigest()


class AuthException(BaseBarmenException):
    status_code = 401

    AUTH_ERROR = 'Authoratization Error'
    TOKEN_ERROR = 'Invalid Client Token'
    TOKEN_TIME_UP = 'Token time is up'
    ACCESS_DENY = 'Access deny for this rest'
    USER_FOUND = "Registered User"
