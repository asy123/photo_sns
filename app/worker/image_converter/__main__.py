import json
import logging
import time

import pika
from minio import Minio
import io
from PIL import Image as PILImage
from urllib.parse import urlparse

from app import app as App
import app.config
from app.util import get_minio_client
from app.models import db
from app.models.user import Icon, User, IconStatus
from app.models.post import Image, PostContentStatus, PostStatus


LARGE_PORTLAIT = (340, 640)
LARGE_LANDSCAPE = (640, 340)

fh = logging.StreamHandler()
fh.setLevel(logging.DEBUG)
image_logger = logging.getLogger("image_converter")
icon_logger = logging.getLogger("icon_converter")

image_logger.addHandler(fh)
icon_logger.addHandler(fh)

def extract_minio_path(url):
    url = urlparse(url)
    bucket = url.path.split("/")[2]
    path = "/".join(url.path.split("/")[3:])
    return bucket, path


def db_worker(worker):
    def _db_worker(ch, method, properties, body):
        session = db.create_scoped_session()
        try:
            worker(session, ch, method, properties, body)
        except Exception as e:
            image_logger.error(f"{str(e)}")
            session.rollback()
        finally:
            session.close()

    return _db_worker

@db_worker
def convert_image(session, ch, method, properties, body):
    data = json.loads(body)
    image_id = data["image_id"]
    image_logger.info(f"try convert image. ID:{image_id}")
    image = session.query(Image).filter_by(id=data["image_id"]).one()

    minioClient = get_minio_client()

    try:
        bucket, path = extract_minio_path(image.original_image_src)
        original_image = minioClient.get_object(
            App.config["MINIO_IMAGES_BUCKET"],
            path
        )

        original_image = PILImage.open(io.BytesIO(original_image.data))
        original_image = original_image.convert("RGB")

        if original_image.width > original_image.height:
            size = LARGE_LANDSCAPE
        else:
            size = LARGE_PORTLAIT

        thumbnail = original_image.copy()
        thumbnail.thumbnail(size, PILImage.ANTIALIAS)
        buffer = io.BytesIO()
        thumbnail.save(buffer, format='jpeg')

        raw_data = buffer.getvalue()
        data_stream = io.BytesIO(raw_data)

        src_dir = path.split("/")[0]
        card_image_src = f"{src_dir}/card_image.jpeg"

        minioClient = get_minio_client()

        minioClient.put_object(
            App.config["MINIO_IMAGES_BUCKET"],
            card_image_src,
            data_stream,
            len(raw_data),
            content_type="image/jpeg"
        )
    except Exception as e:
        image.status = PostContentStatus.fail
        post = image.post
        post.status = PostStatus.fail
        session.add(image)
        session.add(post)
        session.commit()
        image_logger.error(f"Error is occured. ID: {image_id}. {str(e)}")
        return

    image.card_image_src = "/".join([
        App.config["MINIO_URL_BASE"],
        App.config["MINIO_IMAGES_BUCKET"],
        card_image_src
    ])
    image.status = PostContentStatus.publish
    post = image.post
    post.status = PostStatus.publish

    old_images = session.query(Image).filter(
        Image.post_id == image.post_id,
        Image.id != image.id
    ).all()

    for old_image in old_images:
        old_image.status = PostContentStatus.freezed

    session.add(image)
    session.add(post)
    session.add_all(old_images)
    session.commit()

    image_logger.info("Success to convert image. ID: {image_id}")


def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))


def crop_max_square(pil_img):
    return crop_center(pil_img, min(pil_img.size), min(pil_img.size))


def put_icon(targ, dir, name):
    buffer = io.BytesIO()
    targ.save(buffer, format='jpeg')

    raw_data = buffer.getvalue()
    data_stream = io.BytesIO(raw_data)

    image_src = f"{dir}/{name}.jpeg"

    minioClient = get_minio_client()

    minioClient.put_object(
        App.config["MINIO_ICONS_BUCKET"],
        image_src,
        data_stream,
        len(raw_data),
        content_type="image/jpeg"
    )

    return image_src

@db_worker
def convert_icon(session, ch, method, properties, body):
    data = json.loads(body)
    icon_id = data["icon_id"]
    image_logger.info(f"try convert icon. ID:{icon_id}")
    icon = session.query(Icon).filter_by(id=data["icon_id"]).one()
    minioClient = get_minio_client()

    try:
        bucket, path = extract_minio_path(icon.original_icon_image_src)
        original_image = minioClient.get_object(
            App.config["MINIO_ICONS_BUCKET"],
            path
        )

        original_image = PILImage.open(io.BytesIO(original_image.data))
        original_image = original_image.convert("RGB")

        squear_image = crop_max_square(original_image)

        small_icon = squear_image.copy().resize((48, 48), PILImage.ANTIALIAS)
        middle_icon = squear_image.copy().resize((150, 150), PILImage.ANTIALIAS)
        large_icon = squear_image.copy().resize((300, 300), PILImage.ANTIALIAS)

        src_dir = path.split("/")[0]
        small_icon_image_src = put_icon(small_icon, src_dir, "small_icon_image")
        middle_icon_image_src = put_icon(middle_icon, src_dir, "middle_icon_image")
        large_icon_image_src = put_icon(large_icon, src_dir, "large_icon_image")
    except Exception as e:
        icon.status = IconStatus.fail
        session.add(icon)
        session.commit()
        image_logger.error(f"Error is occured. ID: {icon_id}. {str(e)}")
        return

    icon.small_icon_image_src = "/".join([
            App.config["MINIO_URL_BASE"],
            App.config["MINIO_ICONS_BUCKET"],
            small_icon_image_src
        ])
    icon.middle_icon_image_src = "/".join([
        App.config["MINIO_URL_BASE"],
        App.config["MINIO_ICONS_BUCKET"],
        middle_icon_image_src
    ])
    icon.large_icon_image_src = "/".join([
        App.config["MINIO_URL_BASE"],
        App.config["MINIO_ICONS_BUCKET"],
        large_icon_image_src
    ])
    icon.status = IconStatus.publish

    old_icons = session.query(Icon).filter(
        Icon.user_id == icon.user_id,
        Icon.id != icon.id
    ).all()

    for old_icon in old_icons:
        old_icon.status = IconStatus.freezed

    session.add(icon)
    session.add_all(old_icons)
    session.commit()
    image_logger.info(f"Success to convert icon. ID: {icon_id}")



def main():
    while True:
        try:
            with pika.BlockingConnection(
                pika.ConnectionParameters(
                    App.config["RABBITMQ_HOST"],
                    App.config["RABBITMQ_PORT"],
                    credentials=pika.credentials.PlainCredentials(
                        App.config["RABBITMQ_USERNAME"],
                        App.config["RABBITMQ_PASSWORD"]
                    )
                )
            ) as connection:
                break
        except pika.exceptions.AMQPConnectionError:
            time.sleep(5)
            print("Wait to rabbitmq connection establish.")
        except Exception as e:
            raise e

    with pika.BlockingConnection(
        pika.ConnectionParameters(
            App.config["RABBITMQ_HOST"],
            App.config["RABBITMQ_PORT"],
            credentials=pika.credentials.PlainCredentials(
                App.config["RABBITMQ_USERNAME"],
                App.config["RABBITMQ_PASSWORD"]
            )
        )
    ) as connection:
        with connection.channel() as channel:
            channel.queue_declare(queue=App.config["RABBITMQ_IMAGES_QUEUE"])
            channel.queue_declare(queue=App.config["RABBITMQ_ICONS_QUEUE"])

            channel.basic_consume(
                queue=App.config["RABBITMQ_IMAGES_QUEUE"],
                auto_ack=True,
                on_message_callback=convert_image
            )

            channel.basic_consume(
                queue=App.config["RABBITMQ_ICONS_QUEUE"],
                auto_ack=True,
                on_message_callback=convert_icon
            )

            print(' [*] Waiting for messages. To exit press CTRL+C')
            channel.start_consuming()


if __name__ == "__main__":
    main()
