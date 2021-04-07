import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_argon2 import Argon2
from flask_jwt_extended import JWTManager
from flask_sendgrid import SendGrid
from flask_marshmallow import Marshmallow
from flask_rest_paginate import Pagination
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

from .settings import app_config

environment_name = os.environ.get('FLASK_ENV')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

db = SQLAlchemy()
migrate = Migrate()
argon_2 = Argon2()
jwt = JWTManager()
sendgrid = SendGrid()
marshmallow = Marshmallow()
pagination = Pagination()

celery = Celery(broker='amqp://guest:guest@localhost:5672', include=('mkondo.tasks',))

def create_app():
    """
    Initialize extensions and return the flask instance.
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(ROOT_DIR, 'templates'), 
        static_folder=os.path.join(ROOT_DIR, 'static')
    )
    app.config.from_object(app_config[environment_name])

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    argon_2.init_app(app)
    jwt.init_app(app)
    sendgrid.init_app(app)
    marshmallow.init_app(app)
    pagination.init_app(app, db)
    celery.main = app.import_name
    celery.conf.update(app.config)
    

    return app
