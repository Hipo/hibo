import os
import sys

from flask import Flask, render_template


class DashboardApp(object):
    def __init__(self, config_path):
        self.app = self.init_app()
        self.route_methods()
        self.config_reader = ConfigReader(config_path)
        self.config = self.config_reader.parse()

    def init_app(self):
        template_folder = os.path.join(os.path.dirname(__file__), "templates")
        return Flask("hibo", template_folder=template_folder)

    def route_methods(self):
        self.app.route('/')(self.index)

    def index(self):
        return render_template("index.html", config=self.config)


class ConfigParseError(Exception):
    pass


class ConfigReader(object):

    modules = {
        "json": "json",
        "yaml": "yaml"
    }

    def __init__(self, file_path):
        self.file_path = file_path
        self.config_type = file_path.split(".")[-1]

    def parse(self):
        module_name = self.modules[self.config_type]
        try:
            module = __import__(module_name)
        except KeyError:
            raise ConfigParseError("Unknown config type %s" %
                                   self.config_type)
        except ImportError:
            raise ConfigParseError("Requires %s module" % module_name)

        try:
            parsed = module.load(open(self.file_path))
        except IOError:
            raise ConfigParseError('Missing config file: %s' % self.file_path)

        return parsed

def main():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--bind", dest="address",
                      help="Binds an address to hibo")
    parser.add_option("--conf", dest="conf",
                      help="hibo configuration file")
    options, args = parser.parse_args()
    if not options.conf:
        parser.error("You should pass a configuration file.")

    host, port = (options.address or 'localhost'), 8000

    if ':' in host:
        host, port = host.rsplit(':', 1)

    config_path = os.path.join(os.getcwd(), options.conf)

    try:
        dashboard = DashboardApp(config_path=config_path)
    except ConfigParseError:
        sys.stdout.write("foo")
    else:
        dashboard.app.run(host=host, port=port, debug=True)
