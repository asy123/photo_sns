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
from app.models.post import Post, PostStatus, Image
from app.util import push_to_mq


class UpdatePostForm(FlaskForm):
    title = StringField(
        'Title', [DataRequired(message="This filed is required")])
    description = StringField(
        'Description', [DataRequired(message="This filed is required")])
    shooting_at = DateField(
        'Shooting At', [DataRequired(message="This filed is required")])
    image = FileField('FileField')


@app.route('/posts/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.get_by_id(post_id, db.session)
    if post.status == PostStatus.freezed:
        return abort(404)

    form = UpdatePostForm()
    if form.validate_on_submit():
        if form.image.data is not None:
            fs = request.files[form.image.name]
            image = Image()
            image.put_image(fs)
            post.images.append(image)
            db.session.add(image)

        post.title = form.title.data
        post.description = form.description.data
        post.shooting_at = form.shooting_at.data
        post.updated_at = datetime.now()
        db.session.add(post)
        db.session.commit()

        if form.image.data is not None:
            push_to_mq(
                "image",
                {
                    "image_id": image.id
                }
            )

        return redirect(url_for('get_post', post_id=post.id))

    data = {
        "post": post.to_dict()
    }

    return render_template(
        'create_post.j2.html',
        data=data,
        form=form
    )
