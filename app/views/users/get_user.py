from datetime import datetime

from flask import Flask, render_template, request, url_for, redirect, abort, Markup

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError
from flask_login import login_user

from app import app
from app.models import db
from app.models.user import User
from app.models.post import Post, PostOrder
from app.util import push_to_mq


@app.route('/users/<username>')
def get_user(username):
    user = User.get_by_username(username, db.session)

    if user is None:
        return abort(404)

    page_index = int(request.args.get('page', "1")) - 1
    offset = app.config["PAGENATION_LIMIT"] * page_index

    posts, pagenation = Post.get_posts(
        limit=app.config["PAGENATION_LIMIT"],
        offset=offset,
        order_by=PostOrder.update_at_desc,
        session=db.session,
        user_id=user.id
    )

    data = {
        "posts": list(map(lambda p: p.to_dict(), posts)),
        "pagenation": {
            k: {
                "url": url_for(
                    'get_user',
                    username=username, page=v + 1
                ),
                "index": v + 1
            }
            for k, v in pagenation.items()
        },
        "user": user.to_dict()
    }

    return render_template(
        'user.j2.html',
        data=data
    )
