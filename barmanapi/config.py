import StringIO
import tempfile

from barmanapi import Command, BarmanException
from baseexception import BaseBarmenException
import flask
from flask import request
from flask.ext.restful import Resource
import os
from parser import BarmanCommandParser, ConfigParser


class Configuration(Resource):
    def __init__(self):
        self.current_app = flask.current_app
        self.barman_config = self.current_app.config.config_main.read_section('barman')

    def get_config(self, type='live'):
        if type == 'live':
            config = ConfigParser('/etc/barmanapi.conf')
        else:
            config = self.current_app.config.config_main
        conf = {}
        for cc in config.sections():
            conf[cc] = config.read_section(cc)
        return conf

    def get_barman_config(self):
        command_text = '%s'
        if self.barman_config.get('remote').lower() == 'true':
            command_text = self.barman_config.get('remote_ssh') + ' "%s"'
        command_text = command_text.replace('%s', 'cat ' + self.barman_config.get('config_file'))
        result = Command().execute_command(command_text, parse_line=False)
        if result.get('status_code') == 200:
            buf = StringIO.StringIO(result.get('list'))
            config = ConfigParser(io=buf)
            conf = {}
            for cc in config.sections():
                conf[cc] = config.read_section(cc)

            return conf
        else:
            raise BarmanException('Command not found(' + command_text + ')', 404, BarmanException.COMMAND_NOT_FOUND)

    def get(self, command=None, option=None):
        from auth import Auth
        from app import message_format
        Auth().verify_access('config', command, option)
        Auth().verify_deny('config', command, option)

        if command == 'barman' and option == 'help':
            return message_format(200,'', BarmanCommandParser().load_barman_config())
        elif command == 'barman' and option == 'reload':
            return message_format(200,'',BarmanCommandParser().parse_man_5())
        elif command == 'barman' and option == 'change':
            config_set_str = None
            for param in request.args:
                if param != 'token':
                    spl = param.split('.')
                    config_set_str = "parser.set('" + spl[0] + "','" + spl[1] + "','" + request.args.get(
                        param) + "')\\n"
            with open(flask.current_app.config.config_directory + '/template/config_change_template',
                      'rb') as configfile:
                template = configfile.read()
                template = template.replace('{config_file}', self.barman_config.get('config_file')).replace(
                    '{config_set}',
                    config_set_str)
            f = tempfile.NamedTemporaryFile(delete=False,
                                            dir=flask.current_app.config.config_main.read_section('application').get(
                                                'store_directory') + '/garbage/')

            temp_file = f.name
            with open(temp_file, 'wb') as configfile:
                configfile.write(template)
            os.chmod(temp_file, 775)
            command_text = ''
            if self.barman_config.get('remote').lower() == 'true':
                command_text = self.barman_config.get('remote_ssh') + ' < '
            command_text += '' + temp_file
            result = Command().execute_command(command_text)
            return message_format(200,'',self.get_barman_config())

        elif command == 'barman':
            return message_format(200,'',self.get_barman_config())

        elif command == 'barmanapi' and option == 'change':
            config = self.current_app.config.config_main
            for param in request.args:
                if param != 'token':
                    spl = param.split('.')
                    if request.args.get(param) != config.get(spl[0], spl[1]):
                        config.set(spl[0], spl[1], request.args.get(param))
                        config.write_config()
            return message_format(200,'',self.get_config())

        elif command == 'barmanapi':
            return message_format(200,'',self.get_config('dead'))

        else:
            raise ConfigurationException('Api not found(config/' + command + ')', 405, ConfigurationException.NOT_FOUND)


class ConfigurationException(BaseBarmenException):
    pass
