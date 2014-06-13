import os
import sys

from uuid import uuid4

import feedparser
from TwitterAPI import TwitterAPI

from flask import Flask, render_template, jsonify, request


class ConfigParseError(Exception):
    pass


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
        self.app.route('/fetch_rss')(self.fetch_rss)
        self.app.route('/fetch_tweet')(self.fetch_tweet)

    def index(self):
        return render_template("index.html", config=self.config,
                               boxes=self.boxes)

    def fetch_rss(self):
        rss_url = request.args.get("url")
        parsed = feedparser.parse(rss_url)
        entries = [{"title": entry.title,
                    "url": entry.link
                   } for entry in parsed.entries]
        return jsonify({"entries": entries})

    def fetch_tweet(self):
        keywords = request.args.get("keywords")
        box_id = request.args.get("box_id")

        box = self.get_box_by_id(box_id)

        twitter = TwitterAPI(
            box.parameters.get('api_key'),
            box.parameters.get('api_secret'),
            box.parameters.get('access_token'),
            box.parameters.get('access_token_secret')
        )

        tweets = twitter.request('search/tweets', {'q': keywords})

        try:
            last_tweet = next(iter(tweets))
        except StopIteration:
            last_tweet = {}

        return jsonify(last_tweet)

    def get_box_by_id(self, box_id):
        for box in self.boxes:
            if box.id == int(box_id):
                return box

    def get_template_dir(self):
        return os.path.join(os.path.dirname(__file__), "templates")

    def get_static_dir(self):
        return os.path.join(os.path.dirname(__file__), "static")


class Box(object):
    def __init__(self, title, sizes, color, widget, parameters,
                 box_id=None):
        self.id = box_id or uuid4().hex
        self.title = title
        self.sizes = self.parse_sizes(sizes)
        self.color = color
        self.widget = widget
        self.parameters = parameters


    def parse_sizes(self, sizes):
        try:
            x, y, width, height = [int(size.strip())
                                   for size in sizes.split(",")]
        except (TypeError, ValueError):
            raise ConfigParseError(
                'Wrong size format (%s). You should pass '
                'comma-separated 4 integer value"' % self.sizes)

        return {
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }

    def get_widget_template(self):
        return "widgets/%s.html" % self.widget


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
        return [Box(box_id=index, **data)
                for index, data in
                enumerate(self.parsed['boxes'])]


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
