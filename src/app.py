from datetime import timedelta
import logging
import os

from flask import Flask
from flask import has_request_context, request
from flask.logging import default_handler
from flask_wtf.csrf import CSRFProtect

from redis import Redis

from config import config
from werkzeug.middleware.proxy_fix import ProxyFix

from logging.config import dictConfig

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": config.ROOT_LOG_LEVEL, "handlers": ["wsgi"]},
    }
)

app = Flask(__name__)
app.config.from_object(config)
# fixes when behind nginx
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

csrf = CSRFProtect()
csrf.init_app(app)


class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None

        return super().format(record)


formatter = RequestFormatter(
    "[%(asctime)s] %(remote_addr)s requested %(url)s\n"
    "%(levelname)s in %(module)s: %(message)s"
)
root = logging.getLogger()
root.addHandler(default_handler)

from routes import *

# from routes_auth import bpauth
# from routes_errors import bperrors

# app.register_blueprint(bpauth)
# app.register_blueprint(bperrors)


@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=60)
