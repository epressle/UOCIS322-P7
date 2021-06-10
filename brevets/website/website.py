from flask import Flask, render_template, request, jsonify
import requests
import os
import sys
import json
from urllib.parse import urlparse, urljoin
from passlib.hash import sha256_crypt as pwd_context
from flask import Flask, request, render_template, redirect, url_for, flash, abort, session
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user, UserMixin,
                         confirm_login, fresh_login_required)
from flask_wtf import FlaskForm as Form
from wtforms import BooleanField, StringField, PasswordField, validators


app = Flask(__name__)

SALT = '4CzsbzrtlOFzWOpr'

app.secret_key = "x6sgBrQRWx2bUoL48xo7Jxt5eH41XN0rkuPneC4lcK42Z4fJoSeGrzwVObg5W2ko"

login_manager = LoginManager()

login_manager.session_protection = "strong"

login_manager.login_view = "login"
login_manager.login_message = u"Please log in to access this page."

login_manager.refresh_view = "login"
login_manager.needs_refresh_message = (
    u"To protect your account, please reauthenticate to access this page."
)
login_manager.needs_refresh_message_category = "info"

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

class LoginForm(Form):
    username = StringField('Username', [
        validators.Length(min=2, max=25,
                          message=u"Username must be 2 to 25 characters in length."),
        validators.InputRequired(u"This field must be filled out.")])
    password = PasswordField('Password', [
        validators.Length(min=6, max=25,
                          message=u"Password must be 6 to 25 characters in length."),
        validators.InputRequired(u"This field must be filled out.")])
    remember = BooleanField('Remember me')

class RegisterForm(Form):
    username = StringField('Username', [
        validators.Length(min=2, max=25,
                          message=u"Username must be 2 to 25 characters in length."),
        validators.InputRequired(u"This field must be filled out.")])
    password = PasswordField('Password', [
        validators.Length(min=6, max=25,
                          message=u"Password must be 6 to 25 characters in length."),
        validators.InputRequired(u"This field must be filled out.")])

class User(UserMixin):
    def __init__(self, id = None, uname = None, token = None):
        self.id = id
        self.username = uname
        self.token = token

@login_manager.user_loader
def load_user(user_id):
    if 'username' in session:
        username = session['username']
        if username is not None:
            app.logger.debug("Session active, creating " + str(username))
            app.logger.debug("Creating user")
            user = User(user_id, username, session['token'])
            return user
    return None

login_manager.init_app(app)

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route("/newregister", methods=["GET", "POST"])
def newregister():
    form = RegisterForm()
    if form.validate_on_submit() and request.method == "POST" and "username" and "password" in request.form:
        uname = request.form["username"]
        app.logger.debug("username = " + str(uname))
        password = pwd_context.using(salt=SALT).encrypt(request.form["password"])
        if pwd_context.verify(request.form["password"], password):
            app.logger.debug("Sending post request!")
            res = requests.post('http://restapi:5000/register?uname=' + uname + '&pass=' + password)
            app.logger.debug("Res = " + str(res))
            if str(res) == '<Response [201]>':
                flash("Registration successful. You may now log in.")
                next = request.args.get("next")
                if not is_safe_url(next):
                    app.logger.debug("URL is not safe!")
                    abort(400)
                return redirect(next or url_for('login'))
            else:
                app.logger.debug("POST failed!")
                flash(u"An error occurred, please try again.")
        else:
            app.logger.debug("Password hash failed!")
            flash(u"An error occurred, please try again.")
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit() and request.method == "POST" and "username" and "password" in request.form:
        uname = request.form["username"]
        remember = request.form.get("remember", "false") == "true"
        password = pwd_context.using(salt=SALT).encrypt(request.form["password"])
        app.logger.debug("Hashed password = " + str(password))
        if not pwd_context.verify(request.form["password"], password):
            app.logger.debug("Hash failed!")
            flash(u"An error occurred, please try again.")
        else:
            res = requests.get('http://restapi:5000/token?uname=' + uname + '&pass=' + password)
            app.logger.debug("res = " + str(res))
            if str(res) == '<Response [200]>':
                app.logger.debug("Everything looks good!")
                jsonified = json.loads(res.text)
                app.logger.debug("res.text = " + str(jsonified))
                token = jsonified.get('token')
                id = jsonified.get('id')
                attempt = User(id, uname, token)
                if login_user(attempt, remember=remember):
                    session['id'] = id
                    session['username'] = uname
                    session['token'] = token
                    flash("Logged in!")
                    flash("Login will be remembered.") if remember else None
                    next = request.args.get("next")
                    if not is_safe_url(next):
                        abort(400)
                    return redirect(next or url_for('index'))
                else:
                    flash("Incorrect username or password.")
            else:
                flash(u"Invalid username or password.")
    return render_template("login.html", form=form)

@app.route('/entries')
@login_required
def dataEntries():
    return render_template("entries.html")

@app.route('/list', methods=['POST'])
@login_required
def listEntries():
    token = session.get('token')
    app.logger.debug("token = " + str(token))
    out = request.form.get('out')
    app.logger.debug("Out = " + str(out))
    k = request.form.get('number')
    if k is not None:
        k = k.replace(" ", "")

    if k is None or k == '' or not k.isdigit() or int(k) < 0:
        k = str(sys.maxsize)

    if out is None or out == '':
        out = 'listAll'

    output = request.form.get('types')
    if output is None:
        output = 'json'
    app.logger.debug("output = " + str(output))
    data = requests.get("http://" + os.environ['BACKEND_ADDR'] + ":" + os.environ['BACKEND_PORT'] + "/" + out + "/" + output + "?top=" + k + "&token=" + token)
    app.logger.debug(data.text)
    if output == 'json':
        ret = data.text
        ret = ret[2:]
        ret = ret[:-3]
        ret = ret.replace('"', "")
        new_ret = "[" + ret + "]"
        return jsonify(new_ret)
    ret = data.text
    ret = ret[1:]
    ret = ret[:-2]
    return jsonify(ret)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.")
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
