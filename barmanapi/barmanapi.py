import shutil
import subprocess
from datetime import datetime
import sys
import tarfile

import flask
from flask.ext.restful import Resource
from baseexception import BaseBarmenException
from flask import request
import os


class Command(object):
    process = None
    command = None
    status = None
    message = None
    barman_config = None

    def __init__(self):
        self.barman_config = flask.current_app.config.config_main.read_section('barman')

    def execute_command(self, command, sync=True, parse_line=True):

        ret = dict()
        if sync is False:
            self.process = subprocess.Popen(sys.executable + ' ' + os.path.dirname(
                os.path.realpath(__file__)) + '/app.py execute ' + command + ' &', shell=True)
        else:
            self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            message = self.process.communicate()
            ret['code'] = self.process.returncode
            if parse_line is True:
                ret['message'] = message[0].replace('\t', '').split('\n')
            else:
                ret['message'] = message[0]
            ret['err'] = message[1]
        return ret

    def prepare_command(self, command, option=None):
        exec_command = self.barman_config.get('command') + ' -c ' + self.barman_config.get(
            'config_file') + ' ' + command

        if option is not None:
            exec_command += ' ' + option

        if self.barman_config.get('remote').lower() == 'true':
            exec_command = self.barman_config.get('remote_ssh') + ' "' + exec_command + '"'
        return exec_command


class Barman(Resource):
    current_app = None
    api_directory = None
    command_directory = None

    def __init__(self):
        self.current_app = flask.current_app
        self.api_directory = flask.current_app.config.config_main.get('application', 'store_directory')

    def create_operation_directory(self, command, token):

        import app

        self.command_directory = self.api_directory + '/active/' + str(
            datetime.now().strftime("%Y%m")) + '/' + str(
            datetime.now().strftime("%Y%m%d%H%M%S")) + '_' + command + '_' + token

        if command != 'help':
            app.create_directory(self.api_directory + '/active/' + str(datetime.now().strftime("%Y%m")) + '/')
            app.create_directory(self.command_directory)

    def compress_history_data(self):
        main_dir = self.api_directory + '/active'
        for dirs in os.listdir(main_dir):
            if dirs < datetime.today().strftime('%Y%m'):
                with tarfile.open(self.api_directory + '/archive/' + dirs + '.tar.gz', "w:gz") as file_open:
                    file_open.add(main_dir + '/' + dirs, dirs)
                    shutil.rmtree(main_dir + '/' + dirs)

    def get(self, command, option=None):
        barman_config = self.current_app.config.config_main.read_section('barman')
        from auth import Auth

        Auth().verify_access('barman', command, option)
        Auth().verify_deny('barman', command, option)

        if not request.args.get('token'):
            from auth import AuthException

            raise AuthException('Please send a token parameter', 401, AuthException.NOT_FOUND)

        from parser import BarmanCommandParser

        self.compress_history_data()

        if command == 'reload':
            BarmanCommandParser().parse_man_5()
            return BarmanCommandParser().parse_man()
        barman_commands = BarmanCommandParser().load_barman_commands()

        if command == 'help':
            return barman_commands

        if barman_commands.get(command):
            if option == 'help':
                return barman_commands[command]
            elif not option:
                required = barman_commands[command].get('required')
                optional = barman_commands[command].get('optional')
                command_option = ''
                option_counter = 1
                if optional:
                    for opt in optional:
                        val = optional.get(opt)
                        if request.args.get(opt):
                            option_counter += 1
                            if val.get('values') == 'TRUE/FALSE' and request.args.get(opt) == 'TRUE':
                                command_option += " --" + opt
                            else:
                                command_option += " --" + opt + ' ' + request.args.get(opt)
                if required:
                    for opt in required:
                        if request.args.get(opt):
                            if opt != 'token':
                                option_counter += 1
                                command_option += ' ' + request.args.get(opt)
                        else:
                            raise BarmanException('Please send a required parameter.(' + opt + ')', 401,
                                                  BarmanException.NOT_FOUND)

                if len(request.args) > option_counter:
                    raise BarmanException('Some parameters are invalid', 403, BarmanException.INVALID_PARAM)

                exec_command = Command().prepare_command(command, command_option)

                if eval(barman_config.get('async_command')).count(command):
                    self.create_operation_directory(command, request.args.get('token'))
                    with open(self.command_directory + '/command', "wb") as file_open:
                        file_open.write(exec_command)
                    Command().execute_command(self.command_directory, sync=False)

                    ticket = Auth().generate_token(dict({'folder': self.command_directory}), exp=False)
                    return {'ticket': ticket, 'message': 'For result /history/result?ticket=' + ticket + '&token=XX'}
                else:
                    return Command().execute_command(exec_command, sync=True)

        else:
            raise BarmanException(BarmanException.NOT_FOUND, '405')

        return


class BarmanException(BaseBarmenException):
    REQ_OPTION_NOT_FOUND = "Required parameters not found"
    INVALID_PARAM = "Invalid parameters"
    COMMAND_NOT_FOUND = "Command Not Found"
