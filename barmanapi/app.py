import json
import sys
import traceback

from auth import Auth, User
from baseexception import BaseBarmenException
from config import Configuration
from flask import Flask, g, make_response, request
from flask.ext.httpauth import HTTPTokenAuth, HTTPBasicAuth
from flask.ext.restful import Api
from flask.ext.script import Manager
from flask.json import jsonify
from history import History
import os
from parser import ConfigParser
from barmanapi import Barman, Command


def control_structure(file_or_directory):
    if not os.path.exists(file_or_directory):
        return False
    return True


def create_directory(directory):
    try:
        if not control_structure(directory):
            os.mkdir(directory)
    except os:
        BaseBarmenException('Directory Not Found(' + directory + ')', 404, BaseBarmenException.NOT_FOUND)


config_main = ConfigParser('/etc/barmanapi.conf')

if not control_structure('/etc/barmanapi.conf'):
    print('/etc/barmanapi.conf not found')
    exit()

if not control_structure('/usr/share/barmanapi/'):
    print('/usr/share/barmanapi/ directory not found')
    exit()

api_directory = config_main.get('application', 'store_directory')

if not control_structure(api_directory):
    print(api_directory + ' directory not found')
    exit()

if not os.access(api_directory, os.W_OK):
    print(api_directory + ' directory not have write permission')
    exit()

# create_directory(api_directory)
create_directory(api_directory + '/archive')
create_directory(api_directory + '/active')
create_directory(api_directory + '/config')
create_directory(api_directory + '/garbage')
create_directory(api_directory + '/logs')

app = Flask(__name__, instance_relative_config=True)
api = Api(app)
manager = Manager(app)

auth_token = HTTPTokenAuth(scheme='Barman')

auth = HTTPBasicAuth()

app.config.config_main = config_main
app.config.config_directory = '/usr/share/barmanapi/'


def message_format(status_code=200, message='', list_return=None):
    message_return = {'status_code': status_code, 'message': message}
    if list_return is not None:
        message_return.update({'list': list_return})
    return message_return


if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler
    from logging import Formatter

    log_config = config_main.read_section('log')
    file_handler = RotatingFileHandler(api_directory + '/logs/general.log', maxBytes=log_config.get('max_bytes'),
                                       backupCount=log_config.get('backup_count'))
    file_handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.ERROR)
    app.logger.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)


@auth_token.verify_token
def verify_token(token):
    if not token:
        token = request.args.get('token')
    verify = Auth().verify_token(token)
    g.user = verify.get('user')
    g.user['password'] = ''
    return True


@auth.hash_password
def hash_pw(password):
    return User().hash_password(password)


@auth.get_password
def get_password(username):
    user = User().get_user(username)
    user['username'] = username
    g.user = user.copy()
    g.user['password'] = ''
    return user.get('password')


def write_log(error_message, error_type):
    if hasattr(g, 'user'):
        message = ('User: %s ' % g.user.get('username'))
    else:
        message = ('User: %s ' % None)
    message += (str(error_type) + ': %s ' % (error_message))
    if request.url:
        message += ('Url: %s ' % request.url)
    if request.args:
        message += ('Arg: %s ' % request.args)
    app.logger.error(message)


@app.errorhandler(404)
def handle_not_found(error):
    response = jsonify({'message': 'Api Not Found', 'type': 404, 'status_code': BaseBarmenException.NOT_FOUND})
    write_log(error, 404)
    return make_response(response, 404)


@app.errorhandler(500)
def handle_not_found(error):
    response = jsonify({'message': 'Api Error', 'type': 500, 'status_code': BaseBarmenException.ERROR})
    write_log(error, 500)
    return make_response(response, 500)


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    inf = traceback.print_exc(file=sys.stdout)
    print(inf)
    try:
        err = error.to_dict()
        write_log(err['message'], err['type'])
    except Exception:
        write_log(error, 500)
        err = {'status_code': 500}
    response = jsonify(err)
    return make_response(response, err['status_code'])


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'message': 'Unauthorized access'}), 401)


#
class BarmanApi(Barman):
    decorators = [auth_token.login_required]

    pass


class AuthApi(Auth):
    decorators = [auth.login_required]
    pass


class ConfigApi(Configuration):
    decorators = [auth_token.login_required]
    pass


class HistoryApi(History):
    decorators = [auth_token.login_required]
    pass


api.add_resource(BarmanApi, '/barman/<command>/<option>', '/barman/<command>', methods=['GET', 'POST'])
api.add_resource(AuthApi, '/auth/<command>/<option>', '/auth/<command>', methods=['GET', 'POST'])
api.add_resource(ConfigApi, '/config/<command>/<option>', '/config/<command>', methods=['GET', 'POST'])
api.add_resource(HistoryApi, '/history/<command>/<option>', '/history/<command>',
                 methods=['GET', 'POST'])


@manager.command
def runserver():
    """Start BARMAN API Server"""
    app.config.update(
        DEBUG=eval(config_main.get('application', 'debug')),
        PROPAGATE_EXCEPTIONS=True
    )
    app.run(port=int(config_main.get('application', 'port')),
            host=config_main.get('application', 'host'))


@manager.command
def execute(directory):
    """Execute Async Commands"""
    ret = Command().execute_command('sh ' + directory + '/command')
    with open(directory + '/result.json', "wb") as file_open:
        json.dump(ret, file_open)


def main():
    manager.run()


if __name__ == '__main__':
    manager.run()
