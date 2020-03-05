from flask import Flask, render_template, request, url_for, redirect, abort, Markup

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError
from flask_login import login_user

from app import app
from app.models import db
from app.models.user import User

class LoginForm(FlaskForm):
    username = StringField('Username', [DataRequired(message="This filed is required")])
    password = PasswordField('Password', [DataRequired(message="This filed is required")])
    remember_me = BooleanField('Remember Me')

@app.route('/login',  methods = ['POST', 'GET'])
def login():
    form = LoginForm()
    error = {
        "failedToAuth": False
    }
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = bool(form.remember_me.data)
        user = User.get_by_username(username, db.session)
        if user is not None and user.password == password:
            login_user(user, remember=remember)
            return redirect(url_for('recent_posts'))

        error["failedToAuth"] = True
    return render_template('login.j2.html',
         form = form,
         error = error
    )
