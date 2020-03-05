import os

from flask_sqlalchemy import SQLAlchemy

from app import app
envs = os.environ
DB_PASSWORD = envs["DB_PASSWORD"]
DB_USERNAME = envs["DB_USERNAME"]
DB_HOST = envs["DB_HOST"]
DB_PORT = envs["DB_PORT"]
DB_DATABASE_NAME = envs["DB_DATABASE_NAME"]

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE_NAME}'
db = SQLAlchemy(app)