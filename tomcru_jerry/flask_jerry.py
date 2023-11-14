from collections import defaultdict
import os.path

from flask import Flask, Response, request
from werkzeug.routing import BaseConverter


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


class FlaskAppJerrySetup:
    CTRL_ATTRIBUTES = ['server', 'app']

    def __init__(self, app: Flask, config: dict, path: str, modify=True):
        self.custom_routes = defaultdict(set)
        self.module_route = app.module_route if hasattr(app, 'module_route') else ""
        self.mockedapi = None

        if modify:
            webconf = config.get('website', {})
            tags = webconf.get('tags', set())

            app.host = webconf.get('host', '0.0.0.0')
            app.port = webconf.get('port', '5000')
            app.debug = self.debug = webconf.get('debug', False)
            app.threaded = webconf.get('threaded', True)

            headers = config.get('headers', {})
            if 'cors' in tags:
                self.http_verbs = webconf.get('methods', ["GET","HEAD","OPTIONS","POST","PUT","PATCH","DELETE"])

                headers.update({
                    "Access-Control-Allow-Methods":  ",".join(self.http_verbs),
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Origin, Accept, X-Requested-With, Content-Type, Authorization"
                })

            if 'webapi' in tags or 'api' in tags:
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'application/json'
                    headers['Referrer-Policy'] = 'no-referrer-when-downgrade'

            if path:
                app.template_folder = os.path.join(path, webconf.get('template_folder', 'templates'))
                app.static_folder = os.path.join(path, webconf.get('static_folder', 'public'))
                app.static_url = webconf.get('static_url_path', '')

            app.url_map.converters['regex'] = RegexConverter
            app.config['SESSION_TYPE'] = 'filesystem'

            if 'cors' in webconf:
                from .control import cors
                _cors = cors(webconf['cors'])
                app.after_request(lambda response: _cors(request, response))

            @app.after_request
            def after_request(response: Response):
                #_headers = self._custom_headers[response.]
                #response.headers.update(headers)
                # flask workaround for pythonanywhere
                if not hasattr(response.headers, 'update'):
                    for header, header_val in headers.items():
                        response.headers[header] = header_val
                else:
                    response.headers.update(headers)
                return response


flask_apps: dict[str, FlaskAppJerrySetup] = {}


