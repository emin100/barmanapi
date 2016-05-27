from ConfigParser import ConfigParser as Parser
import json

from barmanapi import Command, BarmanException
from baseexception import BaseBarmenException
import flask
import os
import re


class ConfigParser(Parser):
    path = None

    def __init__(self, filename=None, io=None):
        Parser.__init__(self)
        if io is None:
            if filename is None:
                raise IOError('Config File Is Empty')
            if os.path.exists(filename):
                self.path = filename
            elif os.path.exists(os.path.dirname(os.path.realpath(__file__)) + '/' + filename):
                self.path = os.path.dirname(os.path.realpath(__file__)) + '/' + filename
            else:
                raise ConfigParserException('Config File Not Found', 404, ConfigParserException.NOT_FOUND)
            self.read(self.path)
        else:
            if io is None:
                raise IOError('Config File and Io Is Empty')
            self.readfp(io)

    def write_config(self):

        with open(self.path, 'wb') as configfile:
            self.write(configfile)

    def read_section(self, name):
        dict1 = {}
        try:
            options = self.options(name)
            for option in options:
                try:
                    dict1[option] = self.get(name, option)
                    if dict1[option] == -1:
                        print("skip: %s" % option)
                except:
                    print("exception on %s!" % option)
                    dict1[option] = None
        except:
            raise ConfigParserException('Section Not Found', 404, ConfigParserException.NOT_FOUND)
        return dict1


class BarmanCommandParser(Command):
    barman_config = None
    api_directory = None

    def __init__(self):
        Command().__init__()
        self.barman_config = flask.current_app.config.config_main.read_section('barman')
        self.api_directory = flask.current_app.config.config_main.get('application', 'store_directory')

    def parse_man_5(self):
        barman_command = self.barman_config.get('command')
        store_directory = self.api_directory
        barman_ssh = self.barman_config.get('remote_ssh')
        remote = self.barman_config.get('remote')
        barman_config = self.barman_config.get('config_file')
        ssh_command = ''

        first = 0
        second = 0
        tag = ''

        if remote.lower() == 'true':
            ssh_command = barman_ssh + ' "%s"'

        command = self.execute_command(self.prepare_command(" -v"))
        if command.get('status_code') == 200:
            if command.get('list'):
                if command.get('list')[0] != '':
                    version = command.get('list')
                else:
                    version = command.get('message')
            else:
                version = command.get('message')
            version = version.replace('\n', '')

            config_man = ConfigParser(flask.current_app.config.config_directory + '/man.conf')

            for vers in config_man.read_section('versions_man_5').iteritems():
                d = eval(vers[1])
                isright = False
                if d.get('bigger') is True:
                    if version > d.get('version'):
                        isright = True
                elif d.get('bigger') is False:
                    if version < d.get('version'):
                        isright = True
                if d.get('equal') is True:
                    if version == d.get('version'):
                        isright = True
                if isright is True:
                    first = int(d.get('first'))
                    second = int(d.get('second'))
                    tag = d.get('tag')
        command = self.execute_command(ssh_command.replace('%s', 'man 5 barman'))

        command_list = {}
        if command.get('status_code') != 200:
            raise BarmanException('Command Exception', 404, BarmanException.COMMAND_NOT_FOUND)
        else:
            begin = 0
            text = ''
            last_parameter = ''
            for line in command['list']:
                if line == tag:
                    begin = 1
                    text = ''
                    last_parameter = ''
                elif (line.startswith(' ') or line == '') and begin == 1:
                    if line.startswith(' ' * first) and not line.startswith(' ' * int(first + 1)):
                        parse = line.strip(' ').split(' ')
                        if parse[0] != last_parameter and last_parameter != '':
                            config_type = 'Global'
                            if re.search('Global/Server\.', text):
                                config_type = 'Global/Server'
                            elif re.search('Server\.', text):
                                config_type = 'Server'
                            command_list[last_parameter] = {'description': text.strip(' '), 'type': config_type}
                            text = ''

                        last_parameter = parse[0]
                        if len(parse) > 1:
                            text += ' '.join(parse[1:])
                    elif line.startswith((' ' * second)):
                        text += line.strip(' ') + ' '
                else:
                    if begin == 1:
                        command_list[last_parameter] = {'description': text.strip(' ')}
                    begin = 0

        with open(store_directory + '/config/barman_parameters.json', "wb") as file_store:
            json.dump(command_list, file_store)

        return command_list

    def parse_man(self):
        barman_command = self.barman_config.get('command')
        store_directory = self.api_directory
        barman_ssh = self.barman_config.get('remote_ssh')
        remote = self.barman_config.get('remote')
        barman_config = self.barman_config.get('config_file')

        first = 0
        second = 0
        third = 0
        tag = ''
        third_separator = ''
        ssh_command = '%s'

        if remote.lower() == 'true':
            ssh_command = barman_ssh + ' "%s"'

        command = self.execute_command(self.prepare_command(" -v"))
        if command.get('status_code') == 200:
            if command.get('list'):
                if command.get('list')[0] != '':
                    version = command.get('list')
                else:
                    version = command.get('message')
            else:
                version = command.get('message')
            version = version.replace('\n', '')

            config_man = ConfigParser(flask.current_app.config.config_directory + '/man.conf')

            for vers in config_man.read_section('versions').iteritems():
                d = eval(vers[1])
                isright = False
                if d.get('bigger') is True:
                    if version > d.get('version'):
                        isright = True
                elif d.get('bigger') is False:
                    if version < d.get('version'):
                        isright = True
                if d.get('equal') is True:
                    if version == d.get('version'):
                        isright = True
                if isright is True:
                    first = int(d.get('first'))
                    second = int(d.get('second'))
                    third = int(d.get('third'))
                    tag = d.get('tag')
                    third_separator = d.get('third_separator')
        command = self.execute_command(ssh_command.replace('%s', 'man barman'))
        command_list = {}
        if command.get('status_code') != 200:
            raise BarmanException('Command Exception', 404, BarmanException.COMMAND_NOT_FOUND)
        else:
            begin = 0
            for line in command['list']:
                if line == tag:
                    begin = 1
                    text = ''
                    last_command = ''
                    argument_list = {}
                    option_list = {}
                    option_val = ''
                    last_option = ''
                    text_options = ''
                    text_options_val = []
                elif (line.startswith(' ') or line == '') and begin == 1:
                    if line.startswith(' ' * first) and not line.startswith(' ' * int(first + 1)):
                        line = line.lstrip(' ')
                        comm = line.split(' ')
                        if self.execute_command(self.prepare_command(comm[0], '-q --help'))['status_code'] == 200:
                            if last_command != '' and last_command != comm[0]:

                                if len(text_options_val) > 0:
                                    option_val = '/'.join(text_options_val)
                                option_list[last_option] = {'values': option_val.replace('[', '').replace(']', ''),
                                                            'description': text_options}
                                argument_list['description'] = text.strip(' ')

                                if last_option != '':
                                    argument_list['optional'] = option_list
                                command_list[last_command] = argument_list
                                argument_list = {}
                                option_list = {}
                                last_option = ''
                                text = ''
                                option_val = ''
                            last_command = comm[0]
                            req = []
                            if len(comm) > 1 and comm[1] == '[OPTIONS]':
                                req = comm[2:]
                            elif len(comm) > 1 and comm[1] == '':
                                text = ' '.join(comm[1:])
                            else:
                                req = comm[1:]
                            req.append("token")
                            if len(req) > 0:
                                argument_list['required'] = req
                        else:
                            text += line + ' '
                    elif line.startswith((' ' * second) + '--'):
                        parse = line.lstrip((' ' * second) + '--').split(' ')
                        if last_option != '':
                            if len(text_options_val) > 0:
                                option_val = '/'.join(text_options_val)
                            option_list[last_option] = {'values': option_val.replace('[', '').replace(']', ''),
                                                        'description': text_options.strip(' ')}
                            text_options = ''
                            text_options_val = []

                        last_option = parse[0]
                        if len(parse) > 1:
                            option_val = parse[1]
                        else:
                            option_val = 'TRUE/FALSE'

                    elif line.startswith((' ' * third) + '\xc2\xb7'):
                        text_options_val.append(
                            line.lstrip((' ' * third) + '\xc2\xb7').split(third_separator)[0].strip(' '))

                    elif line.startswith(' ' * third):
                        text_options += line.lstrip(' ') + ' '
                    else:
                        text += line.lstrip(' ') + ' '

                else:
                    if begin == 1:
                        argument_list['description'] = text
                        command_list[last_command] = argument_list
                    begin = 0

        with open(store_directory + '/config/barman.json', "wb") as file_open:
            json.dump(command_list, file_open)

        return command_list

    def load_barman_commands(self):
        try:
            with open(self.api_directory + '/config/barman.json', "rb") as file_open:
                return json.load(file_open)
        except IOError:
            raise ConfigParserException('Please run /barman/reload?token=XX rest api for configure barman commands.',
                                        500, ConfigParserException.NOT_FOUND)

    def load_barman_config(self):
        try:
            with open(self.api_directory + '/config/barman_parameters.json', "rb") as file_open:
                return json.load(file_open)
        except IOError:
            raise ConfigParserException('Please run /barman/reload?token=XX rest api for configure barman commands.',
                                        500, ConfigParserException.NOT_FOUND)


class ConfigParserException(BaseBarmenException):
    pass
