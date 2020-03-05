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
from app.models.post import Post, PostStatus
from app.util import push_to_mq

@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.get_by_id(post_id, db.session)

    if post is None or post.status != PostStatus.publish:
        return abort(404)
    
    data = {
        "post": post.to_dict()
    }

    return render_template('post.j2.html',
        data = data
    )