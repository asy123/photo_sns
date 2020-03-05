from datetime import datetime

from flask import Flask, render_template, request, url_for, redirect, abort, Markup

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError
from flask_login import current_user, login_required

from app import app
from app.models import db
from app.models.user import User, Icon, IconStatus
from app.util import push_to_mq


class UpdateProfileForm(FlaskForm):
    display_name = StringField(
        'Display name',
        [
            DataRequired(message="This filed is required"),
            Length(min=1, message="Display name must be longer than 0"),
            Length(max=20, message="Display name must be shorter than 21"),
        ]
    )
    description = TextAreaField(
        'Description', [DataRequired(message="This filed is required")])
    icon = FileField(
        'FileField',
        [
            FileAllowed(
                [
                    "jpeg",
                    "jpg",
                    "png",
                    "bmp"
                ],
                "Jpeg, png or bmp are only allowed"
            )
        ]
    )


@app.route('/update_profile', methods=['POST', 'GET'])
@login_required
def update_profile():
    form = UpdateProfileForm()
    user = current_user
    data = {
        "user": user.to_dict()
    }

    if form.validate_on_submit():
        if form.icon.data is not None:
            fs = request.files[form.icon.name]
            icon = Icon()
            icon.put_icon(fs)

            user.icons.append(icon)
            db.session.add(icon)

        user.display_name = form.display_name.data
        user.description = form.description.data
        db.session.add(user)
        db.session.commit()

        if form.icon.data is not None:
            push_to_mq(
                app.config["RABBITMQ_ICONS_QUEUE"],
                {
                    "icon_id": icon.id
                }
            )

    return render_template(
        'update_profile.j2.html',
        data=data,
        form=form
    )
