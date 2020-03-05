from datetime import datetime

from flask import Flask, render_template, request, url_for, redirect, abort, Markup

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError
from flask_login import login_user, current_user

from app import app
from app.models import db
from app.models.user import User, Icon, IconStatus
from app.models.post import Post, PostOrder, PostStatus
from app.util import push_to_mq


@app.route('/')
@app.route('/posts')
def recent_posts():
    page_index = int(request.args.get('page', "1")) - 1
    offset = app.config["PAGENATION_LIMIT"] * page_index
    posts, pagenation = Post.get_posts(
        limit=app.config["PAGENATION_LIMIT"],
        offset=offset,
        order_by=PostOrder.update_at_desc,
        session=db.session
    )

    data = {
        "posts": list(map(lambda p: p.to_dict(), posts)),
        "pagenation": {
            k: {
                "url": url_for(
                    'recent_posts',
                    page=v + 1
                ),
                "index": v + 1
            }
            for k, v in pagenation.items()
        },
    }
    return render_template(
        'posts.j2.html',
        data=data
    )
