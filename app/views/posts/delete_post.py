from datetime import datetime

from flask import Flask, render_template, request, url_for, redirect, abort, Markup

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError
from flask_login import login_user, current_user, login_required

from app import app
from app.models import db
from app.models.user import User, Icon, IconStatus
from app.models.post import Post, PostOrder, PostStatus
from app.util import push_to_mq


class DeletePostForm(FlaskForm):
    pass


@app.route('/posts/<int:post_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    post = Post.get_by_id(post_id, db.session)
    if post.status == PostStatus.freezed:
        return abort(404)

    form = DeletePostForm()
    if form.validate_on_submit():
        post.status = PostStatus.freezed
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('recent_posts'))

    data = {
        "post": post.to_dict()
    }

    if current_user.id != data["post"]["user"]["id"]:
        return abort(401)

    return render_template(
        'post_delete.j2.html',
        form=form,
        data=data
    )
