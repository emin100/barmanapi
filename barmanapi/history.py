from datetime import datetime
import json
import tarfile
import flask
from flask import request
from flask.ext.restful import Resource
import os
from baseexception import BaseBarmenException


class History(Resource):
    current_app = None
    api_directory = None

    def __init__(self):
        self.current_app = flask.current_app
        self.api_directory = flask.current_app.config.config_main.get('application', 'store_directory')

    @staticmethod
    def get_file(folder):
        from app import message_format
        try:
            with open(folder + '/result.json', "rb") as file_open:
                log = json.load(file_open)
        except IOError:
            log = message_format(-99, 'Command not execute yet.')
        return log

    def get(self, command, option=None):
        from auth import Auth
        from app import message_format

        Auth().verify_access('history', command, option)
        Auth().verify_deny('history', command, option)

        if command == 'list':
            list_async = []
            active_folder = self.api_directory + '/active/' + datetime.today().strftime('%Y%m')
            status_code = 200
            message = ''
            try:
                if request.args.get('past'):
                    tar = tarfile.open(self.api_directory + '/archive/' + request.args.get('past') + '.tar.gz')
                    tar.extractall(self.api_directory + '/garbage/')
                    tar.close()
                    active_folder = self.api_directory + '/garbage/' + request.args.get('past')
                for folder in os.listdir(active_folder):
                    obj = {}
                    exp = folder.split('_')
                    obj['date'] = exp[0]
                    obj['command'] = exp[1]
                    obj['ticket'] = Auth().generate_token(dict({'folder': folder}), exp=False)
                    obj['result'] = self.get_file(
                        active_folder + '/' + folder)

                    list_async.append(obj)
            except IOError:
                status_code = 500
                message = 'IOError Past Log Not Found'
                list_async = []
            except OSError:
                status_code = 600
                message = 'OSError Past Log Not Found'
                list_async = []
            return message_format(status_code, message, list_async)
        elif command == 'result':
            decode = Auth().verify_token(request.args.get('ticket'))
            return self.get_file(decode['folder'])
        else:
            raise HistoryException('Api not found(history/' + command + ')', 405, HistoryException.NOT_FOUND)


class HistoryException(BaseBarmenException):
    pass
