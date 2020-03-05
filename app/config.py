import json
import os

from flask import Markup
from flask_login import LoginManager

from app import app
from app.models import db
from app.models.user import User
from app.util import get_minio_client

envs = os.environ

app.config['SECRET_KEY'] = "sectet"

app.config["DEFAULT_ORIGINAL_ICON_IMAGE_SRC"] = "http://placehold.jp/300x300.png"
app.config["DEFAULT_LARGE_ICON_IMAGE_SRC"] = "http://placehold.jp/300x300.png"
app.config["DEFAULT_MIDDLE_ICON_IMAGE_SRC"] = "http://placehold.jp/150x150.png"
app.config["DEFAULT_SMALL_ICON_IMAGE_SRC"] = "http://placehold.jp/48x48.png"

app.config["DEFAULT_CARD_IMAGE_SRC"] = "http://placehold.jp/640x360.png"
app.config["DEFAULT_CARD_IMAGE_PLACEHOLDER_SRC"] = "http://placehold.jp/640x360.png"
app.config["DEFAULT_ORIGINAL_IMAGE_SRC"] = "http://placehold.jp/1920x1080.png"

app.config["PAGENATION_LIMIT"] = 20

app.config["MINIO_HOST"] = envs["MINIO_HOST"]
app.config["MINIO_PORT"] = envs["MINIO_PORT"]
app.config["MINIO_ACESS_KEY"] = envs["MINIO_ACESS_KEY"]
app.config["MINIO_SECRET_KEY"] = envs["MINIO_SECRET_KEY"]

app.config["MINIO_URL_BASE"] = "/contents"
app.config["MINIO_ICONS_BUCKET"] = "icons"
app.config["MINIO_IMAGES_BUCKET"] = "images"

app.config["RABBITMQ_HOST"] = envs["RABBITMQ_HOST"]
app.config["RABBITMQ_PORT"] = envs["RABBITMQ_PORT"]
app.config["RABBITMQ_USERNAME"] = envs["RABBITMQ_USERNAME"]
app.config["RABBITMQ_PASSWORD"] = envs["RABBITMQ_PASSWORD"]

app.config["RABBITMQ_ICONS_QUEUE"] = "icon"
app.config["RABBITMQ_IMAGES_QUEUE"] = "image"

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id, db.session)


@app.before_first_request
def init_app():
    db.create_all()
    minio_client = get_minio_client()

    if not minio_client.bucket_exists(app.config["MINIO_ICONS_BUCKET"]):
        minio_client.make_bucket(app.config["MINIO_ICONS_BUCKET"])
        minio_client.set_bucket_policy(app.config["MINIO_ICONS_BUCKET"], json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": [
                            "*"
                            ]
                        },
                        "Action":[
                            "s3:GetBucketLocation",
                            "s3:ListBucket"
                        ],
                        "Resource":[
                            "arn:aws:s3:::icons"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": [
                            "*"
                            ]
                        },
                        "Action":[
                            "s3:GetObject"
                        ],
                        "Resource":[
                            "arn:aws:s3:::icons/*"
                        ]
                    }
                ]
            }
        ))

    if not minio_client.bucket_exists(app.config["MINIO_IMAGES_BUCKET"]):
        minio_client.make_bucket(app.config["MINIO_IMAGES_BUCKET"])
        minio_client.set_bucket_policy(app.config["MINIO_IMAGES_BUCKET"], json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": [
                            "*"
                            ]
                        },
                        "Action":[
                            "s3:GetBucketLocation",
                            "s3:ListBucket"
                        ],
                        "Resource":[
                            "arn:aws:s3:::images"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": [
                            "*"
                            ]
                        },
                        "Action":[
                            "s3:GetObject"
                        ],
                        "Resource":[
                            "arn:aws:s3:::images/*"
                        ]
                    }
                ]
            }
        ))


@app.template_filter('cr')
def cr(arg):
    return Markup(arg.replace('\r', '<br>'))
