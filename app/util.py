import json

from minio import Minio
import pika

from app import app


def get_minio_client():
    return Minio(f'{app.config["MINIO_HOST"]}:{app.config["MINIO_PORT"]}',
        access_key=app.config["MINIO_ACESS_KEY"],
        secret_key=app.config["MINIO_SECRET_KEY"],
        secure=False
    )


def push_to_mq(routing_key, body):
    with pika.BlockingConnection(
            pika.ConnectionParameters(
               app.config["RABBITMQ_HOST"],
               app.config["RABBITMQ_PORT"],
               credentials=pika.credentials.PlainCredentials(
                   app.config["RABBITMQ_USERNAME"],
                   app.config["RABBITMQ_PASSWORD"]
               )
            )
        ) as connection:
            with connection.channel() as channel:
                channel.queue_declare(queue=routing_key)
                channel.basic_publish(
                    exchange='',
                    routing_key=routing_key,
                    body=json.dumps(body)
                )
