from enum import Enum
from datetime import datetime
import io
import uuid

from flask_login import UserMixin
from sqlalchemy_utils import PasswordType

from app import app
from app.models import db
from app.util import get_minio_client

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(PasswordType(
        schemes=['pbkdf2_sha512', 'md5_crypt'],
        deprecated=['md5_crypt']
    ))
    display_name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text(), nullable=False)

    posts = db.relationship('Post', backref='user', lazy=True)
    icons = db.relationship('Icon', backref='icon', lazy=True)

    def __repr__(self):
        return '<User %r>' % self.username

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon.to_dict()
        }

    @property
    def icon(self):
        ret = db.session \
                    .query(Icon) \
                    .filter(
                        Icon.user_id == self.id,
                        Icon.status == IconStatus.publish
                    ) \
                    .one_or_none() \

        if ret is None:
            return Icon(
                status=IconStatus.publish,
                original_icon_image_src = app.config["DEFAULT_ORIGINAL_ICON_IMAGE_SRC"],
                large_icon_image_src    = app.config["DEFAULT_LARGE_ICON_IMAGE_SRC"],
                middle_icon_image_src   = app.config["DEFAULT_MIDDLE_ICON_IMAGE_SRC"],
                small_icon_image_src    = app.config["DEFAULT_SMALL_ICON_IMAGE_SRC"],
                created_at = datetime.now()
            )

        return ret

    @staticmethod
    def get_by_username(username, session):
        return session.query(User).filter_by(username=username).one_or_none()

    @staticmethod
    def get_by_id(user_id, session):
        return session.query(User).filter_by(id=user_id).one_or_none()

class IconStatus(Enum):
    pending = 0
    work_in_progress = 1
    publish = 2
    freezed = 3
    fail = 4

class Icon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(IconStatus), nullable=False, default=IconStatus.pending)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_icon_image_src = db.Column(db.String(200), nullable=False)
    small_icon_image_src  = db.Column(db.String(200), nullable=False)
    middle_icon_image_src = db.Column(db.String(200), nullable=False)
    large_icon_image_src  = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.TIMESTAMP(), nullable=False)

    def __repr__(self):
        return '<Icon %r>' % self.id

    def to_dict(self):
        return {
            "id": self.id,
            "large_icon_image_src": self.large_icon_image_src,
            "middle_icon_image_src": self.middle_icon_image_src,
            "small_icon_image_src": self.small_icon_image_src
        }

    def put_icon(self, fs):
        ext = fs.content_type.split("/")[1] # Validate
        raw_data = fs.stream.read()
        data_stream = io.BytesIO(raw_data)

        src = f"{str(uuid.uuid4())}/original_image.{ext}"

        minio_client = get_minio_client()

        minio_client.put_object(
            app.config["MINIO_ICONS_BUCKET"],
            src,
            data_stream,
            len(raw_data),
            content_type=fs.content_type
        )

        self.status = IconStatus.pending
        self.original_icon_image_src = "/".join([app.config["MINIO_URL_BASE"], app.config["MINIO_ICONS_BUCKET"], src])
        self.large_icon_image_src   = app.config["DEFAULT_LARGE_ICON_IMAGE_SRC"]
        self.middle_icon_image_src  = app.config["DEFAULT_MIDDLE_ICON_IMAGE_SRC"]
        self.small_icon_image_src   = app.config["DEFAULT_SMALL_ICON_IMAGE_SRC"]
        self.created_at = datetime.now()