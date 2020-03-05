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
from app.models.post import Post, PostOrder, PostStatus, Image
from app.util import push_to_mq


class CreatePostForm(FlaskForm):
    title = StringField(
        'Title', [DataRequired(message="This filed is required")])
    description = StringField(
        'Description', [DataRequired(message="This filed is required")])
    shooting_at = DateField(
        'Shooting At', [DataRequired(message="This filed is required")])
    image = FileField('FileField', [FileRequired()])


@app.route('/posts/create', methods=['GET', 'POST'])
@login_required
def create_post():
    form = CreatePostForm()
    user = current_user

    if form.validate_on_submit():

        post = Post(
            user_id=user.id,
            title=form.title.data,
            description=form.description.data,
            shooting_at=form.shooting_at.data,
            updated_at=datetime.now(),
            created_at=datetime.now(),
        )

        fs = request.files[form.image.name]
        image = Image()
        image.put_image(fs)

        post.images.append(image)
        db.session.add(image)
        db.session.add(post)
        db.session.commit()

        push_to_mq("image", {"image_id": image.id})

        return redirect(url_for('recent_posts'))

    data = {
        "post": {
            "title": "",
            "description": "",
            "shooting_at": datetime.now(),
        }
    }
    return render_template(
        'create_post.j2.html',
        data=data,
        form=form
    )
