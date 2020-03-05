from enum import Enum
from datetime import datetime
import io
import uuid

from app import app
from app.models import db
from app.util import get_minio_client

class PostStatus(Enum):
    pending = 0
    work_in_progress = 1
    publish = 2
    freezed = 3
    fail = 4

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum(PostStatus), nullable=False, default=PostStatus.pending)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    shooting_at = db.Column(db.TIMESTAMP(), nullable=False)
    updated_at = db.Column(db.TIMESTAMP(), nullable=False)
    created_at = db.Column(db.TIMESTAMP(), nullable=False)

    images = db.relationship('Image', backref='post', lazy=True)

    def __repr__(self):
        return '<Post %r>' % self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "shooting_at": self.shooting_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user": self.user.to_dict(),
            "image": self.image
        }

    @property
    def image(self):
        ret = db.session \
                    .query(Image) \
                    .filter(
                        Image.post_id == self.id,
                        Image.status == PostContentStatus.publish
                    ) \
                    .one_or_none() \

        if ret is None:
            return Image(
                card_image_src = app.config["DEFAULT_CARD_IMAGE_SRC"],
                card_image_placeholder_src = app.config["DEFAULT_CARD_IMAGE_PLACEHOLDER_SRC"],
                original_image_src = app.config["DEFAULT_ORIGINAL_IMAGE_SRC"],
                created_at=datetime.now()
            )

        return ret

    @staticmethod
    def get_by_id(post_id, session):
        return session.query(Post).filter_by(id=post_id).one_or_none()

    @staticmethod
    def get_posts(limit, offset, order_by, session, user_id = None, status=PostStatus.publish):
        query = session.query(Post).filter(Post.status == status)
        if user_id is not None:
            query = session.query(Post).filter(Post.status == status, Post.user_id == user_id)
        count = query.count()
        query = query.order_by(order_by.value).limit(limit).offset(offset)

        posts = query.all()


        pagenation = {}
        if count // limit == 0:
            return posts, pagenation

        current_index = offset // limit if offset % limit != 0 else max([0, (offset // limit)])  
        last_index = count // limit if count % limit != 0 else max([0, (count // limit) - 1])  
        pagenation["current"] = current_index

        if current_index > 0:
            pagenation["prev"] = current_index - 1

        if current_index > 1:
            pagenation["first"] = 0

        if current_index < last_index:
            pagenation["next"] = current_index + 1    

        if current_index < last_index - 1:
            pagenation["last"] = last_index

        return posts, pagenation

class PostOrder(Enum):
    update_at_asc = Post.updated_at
    update_at_desc = Post.updated_at.desc()

class PostContentStatus(Enum):
    pending = 0
    work_in_progress = 1
    publish = 2
    freezed = 3
    fail = 4

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    status = db.Column(db.Enum(PostContentStatus), nullable=False, default=PostContentStatus.pending)
    original_image_src = db.Column(db.String(80), nullable=False)
    card_image_src = db.Column(db.String(80), nullable=False)
    card_image_placeholder_src = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.TIMESTAMP(), nullable=False)

    def __repr__(self):
        return '<Image %r>' % self.id

    def to_dict(self):
        return {
            "id": self.id,
            "original_image_src": self.original_image_src,
            "card_image_src": self.card_image_src,
            "card_image_placeholder_src": self.card_image_placeholder_src,
        }

    
    def put_image(self, fs):
        ext = fs.content_type.split("/")[1] # Validate
        raw_data = fs.stream.read()
        data_stream = io.BytesIO(raw_data)

        src = f"{str(uuid.uuid4())}/original_image.{ext}"

        minio_client = get_minio_client()

        minio_client.put_object(
            app.config["MINIO_IMAGES_BUCKET"],
            src,
            data_stream,
            len(raw_data),
            content_type=fs.content_type
        )

        self.card_image_src             = app.config["DEFAULT_CARD_IMAGE_SRC"]
        self.card_image_placeholder_src = app.config["DEFAULT_CARD_IMAGE_PLACEHOLDER_SRC"]
        self.original_image_src         = "/".join([
                                            app.config["MINIO_URL_BASE"],
                                            app.config["MINIO_IMAGES_BUCKET"],
                                            src
                                        ])
        self.created_at = datetime.now()
