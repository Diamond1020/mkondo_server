import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

load_dotenv()

from mkondo.settings import app_config
from mkondo import create_app
# from app import init_app, db

# env_name = os.environ.get('FLASK_ENV')

# app = init_app()
app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')

db = SQLAlchemy(app)

migrate = Migrate(app=app, db=db, compare_type=True)
manager = Manager(app=app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
  manager.run()
