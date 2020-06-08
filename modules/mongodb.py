import interface
import logs
import re
import utils
import os
import yaml
import yaml.parser


class MongoDB(interface.Interface):
    def __init__(self, conf_path=None):
        super().__init__()
        self.conf_path = conf_path
        if not conf_path:
            self.conf_path = self.get_paths("mongodb.conf")
        self.conf_file = os.path.join(self.conf_path, 'mongodb.conf')
        logs.INFO(f"Evaluating {self.conf_file}")
        self.conf_content = None
        self.read_content()

    def enumerate_path(self):
        return list({
            *utils.whereis("mongodb"),
            "/usr/local/etc/", # homebrew
            "/etc/", # apt & yum
        })

    def read_content(self):
        try:
            with open(self.conf_file) as fp:
                self.conf_content = yaml.load(fp)
                logs.DEBUG("Using MongoDB > 2.4, with conf file in YAML")
                return True
        except yaml.parser.ParserError:
            try:
                with open(self.conf_file) as fp:
                    self.conf_content = fp.read()
            except FileNotFoundError:
                logs.ERROR("Failed to open MongoDB conf file")
            logs.DEBUG("Using MongoDB <= 2.4")
            return False
        except FileNotFoundError:
            logs.ERROR("Failed to open MongoDB conf file")

    def is_auth_0(self):
        auth_re = re.compile("auth *= *(.+)")
        matches = auth_re.findall(self.conf_content)
        if len(matches) == 0:
            return False
        return matches[-1] == "true"

    def get_bind_ip_0(self):
        ip_re = re.compile("bind_ip *= *(.+)")
        matches = ip_re.findall(self.conf_content)
        if len(matches) == 0:
            return ""
        return matches[-1]

    def is_support_scripting_0(self):
        ip_re = re.compile("noscripting *= *(.+)")
        matches = ip_re.findall(self.conf_content)
        if len(matches) == 0:
            return False
        return matches[-1] == True

    def config_extraction(self):
        config_re = re.compile("((# |)rename-command (.+) (.+))")
        temp_result = {}
        for i in config_re.findall(self.conf_content):
            if i[0][0] != "#":
                temp_result[i[2].lower()] = i[3]
        return temp_result

    def check_exposure(self):
        try:
            ip = self.ip_extraction()[0]
            if "127.0.0.1" == ip:
                logs.INFO("Redis is only exposed to this computer")
            elif utils.is_ip_internal(ip):
                logs.INFO("Redis is only exposed to the intranet")
            else:
                logs.WARN("Redis is set to be exposed to the internet, "
                          "try setting 'bind [internal_ip]' in config file")
        except IndexError:
            logs.ERROR("No IP is extracted from config file. Is the config file correct?")

    def check_password_setting(self):
        if not len(self.password_extraction()):
            logs.WARN("No password has been set, "
                       "try setting 'requirepass [your_password]' in config file")
            return 0
        password = self.password_extraction()[0]
        if utils.check_pwd(password):
            logs.INFO('Password is strong')
        else:
            logs.WARN('Password is weak')

    def check_command(self):
        rename_settings = self.config_extraction()
        if "config" not in rename_settings:
            logs.WARN('Config command is exposed to every user, '
                       'try renaming this command')
        else:
            if utils.check_pwd(rename_settings['config']) or rename_settings['config'] == '""':
                logs.INFO('Config command is protected by random string')
            else:
                logs.WARN('Config command is not well protected by renaming '
                           'try to rename config command by a longer string ')
        if "flushall" not in rename_settings:
            logs.WARN('Flushall command is exposed to every user, '
                       'try renaming this command')
        else:
            if utils.check_pwd(rename_settings['flushall']) or rename_settings['flushall'] == '""':
                logs.INFO('Flushall command is protected by random string')
            else:
                logs.WARN('Flushall command is not well protected by renaming '
                           'try to rename flushall command by a longer string ')
        if "flushdb" not in rename_settings:
            logs.WARN('Flushdb command is exposed to every user, '
                       'try renaming this command')
        else:
            if utils.check_pwd(rename_settings['flushdb']) or rename_settings['flushdb'] == '""':
                logs.INFO('Flushdb command is protected by random string')
            else:
                logs.WARN('Flushdb command is not well protected by renaming '
                           'try to rename flushdb command by a longer string ')

    def check_conf(self):
        logs.INFO("Checking exposure...")
        self.check_exposure()
        logs.INFO("Checking setting of password...")
        self.check_password_setting()
        logs.INFO("Checking commands...")
        self.check_command()
