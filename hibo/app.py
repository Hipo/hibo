import os
import sys

from flask import Flask, render_template


class DashboardApp(object):
    def __init__(self, config_path):
        self.app = Flask(
            import_name="hibo",
            template_folder=self.get_template_dir(),
            static_folder=self.get_static_dir())

        self.route_methods()

        config_reader = ConfigReader(config_path)
        self.config = config_reader.parsed
        self.boxes = config_reader.boxes

    def route_methods(self):
        self.app.route('/')(self.index)

    def index(self):
        return render_template("index.html",
                               config=self.config,
                               boxes=self.boxes)

    def get_template_dir(self):
        return os.path.join(os.path.dirname(__file__), "templates")

    def get_static_dir(self):
        return os.path.join(os.path.dirname(__file__), "static")


class Box(object):

    def __init__(self, title, sizes, color, widget, parameters):
        self.title = title
        self.sizes = sizes
        self.color = color
        self.widget = widget
        self.parameters = parameters


    def parse_sizes(self):
        x1, y1, x2, y2 = map(str.strip, self.sizes.split(","))
        return {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2
        }


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
        self.parsed = self.parse()
        self.boxes = self.get_boxes()

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

    def get_boxes(self):
        return map(lambda data: Box(**data), self.parsed['boxes'])


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
    except ConfigParseError as e:
        sys.stdout.write(e.message)
    else:
        dashboard.app.run(host=host, port=port, debug=True)
