from datetime import datetime

from flask import Flask, render_template, request, url_for, redirect, abort, Markup

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError
from flask_login import login_user

from app import app
from app.models import db
from app.models.user import User, Icon, IconStatus
from app.util import push_to_mq


def unique_username(form, filed):
    if form.username.data is not None:
        user = User.get_by_username(form.username.data, db.session)
        if user is not None:
            raise ValidationError("This username is already used")


class SingUpForm(FlaskForm):
    username = StringField('Username', [
        DataRequired(message="This filed is required"),
        Length(min=6, message="Username must be longer than 5"),
        Length(max=20, message="Username must be shorter than 20"),
        Regexp(
            "^[a-zA-Z0-9]+([_]?[a-zA-Z0-9]){6,18}$", message="Use only alphabet and _"),
        unique_username,
    ])
    display_name = StringField('Display name', [
        DataRequired(message="This filed is required"),
        Length(min=1, message="Display name must be longer than 0"),
        Length(max=20, message="Display name must be shorter than 21"),
    ])
    password = PasswordField('Password', [
        DataRequired(message="This filed is required"),
        Length(min=8, message="password name must be longer than 7"),
        Length(max=20, message="Display name must be shorter than 21"),
        Regexp("^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,20}$",
               message="Minimum eight characters, at least one letter and one number"),
        EqualTo('confirm_password', message="Passwords must match"),
    ])
    confirm_password = PasswordField(
        'Confirm password', [DataRequired(message="This filed is required")])
    description = TextAreaField(
        'Description', [DataRequired(message="This filed is required")])
    icon = FileField('FileField', [
        FileAllowed(["jpeg", "jpg", "png", "bmp"],
                    "Jpeg, png or bmp are only allowed")
    ])


@app.route('/sign_up',  methods=['POST', 'GET'])
def sing_up():
    form = SingUpForm()

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            display_name=form.display_name.data,
            password=form.password.data,
            description=form.description.data
        )

        icon = Icon(
            status=IconStatus.publish,
            original_icon_image_src=app.config["DEFAULT_ORIGINAL_ICON_IMAGE_SRC"],
            large_icon_image_src=app.config["DEFAULT_LARGE_ICON_IMAGE_SRC"],
            middle_icon_image_src=app.config["DEFAULT_MIDDLE_ICON_IMAGE_SRC"],
            small_icon_image_src=app.config["DEFAULT_SMALL_ICON_IMAGE_SRC"],
            created_at=datetime.now()
        )

        if form.icon.data is not None:
            fs = request.files[form.icon.name]
            icon.put_icon(fs)

        user.icons.append(icon)

        db.session.add(user)
        db.session.add(icon)
        db.session.commit()

        if form.icon.data is not None:
            push_to_mq(
                app.config["RABBITMQ_ICONS_QUEUE"],
                {
                    "icon_id": icon.id
                }
            )
    return render_template(
        'sing_up.j2.html',
        form=form
    )
