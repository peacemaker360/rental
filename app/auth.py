from flask import current_app as app
from flask import jsonify, render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse as url_parse
from app import db
from app.forms import LoginForm, RegistrationForm, ResetPasswordForm, UserConfigForm, UserSelectForm
from app.models.User import User
import logging

#################################
# User auth routes
#################################


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # If already logged in, go to the index
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        # Optional: normalize username to lower case if you store usernames that way.
        username = form.username.data.strip().lower()
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            # Log the failed attempt (but be sure not to log sensitive information)
            app.logger.warning("Failed login attempt for username: %s", username)
            return redirect(url_for('login'))
        # Log in the user. Check for any issues returned by login_user.
        if login_user(user, remember=form.remember_me.data):
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        else:
            flash('User sign-in blocked. Contact adminstrator for help.', 'warning')
            return redirect(url_for('login'))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash('Logout successfull!', 'info')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Normalize username and email
        username = form.username.data.strip().lower()
        email = form.email.data.strip().lower()
        # Check if the username or email already exists:
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('register'))
        # Create the user, set password and add them to the database
        try:
            user = User(username=username, email=email)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Congratulations, you are now a registered user!', 'success')
            # Optionally, automatically log in the user after registration:
            # login_user(user)
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error("Error in registration: %s", e)
            flash('An error occurred while creating your account. Please try again.', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html', title='Register', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

# @app.route('/reset_password_request', methods=['GET', 'POST'])
# def reset_password_request():
#     if current_user.is_authenticated:
#         return redirect(url_for('index'))
#     form = ResetPasswordRequestForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         if user:
#             pass
#             #send_password_reset_email(user)
#         flash('Check your email for the instructions to reset your password')
#         return redirect(url_for('login'))
#     return render_template('reset_password_request.html',
#                            title='Reset Password', form=form)

#################################
# Custom Auth / User Routes
# Quelle: Eigenentwicklung
#################################

# Endpoint 'resetpassword': Admins sollen user passwörter zurücksetzen können


@app.route('/resetpassword', methods=['GET', 'POST'])
@login_required
def resetpassword():
    if current_user.role == 0:
        form = ResetPasswordForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user is None:
                flash('User not found.')
                return render_template('resetpassword.html', title='Reset password', form=form)
            user.set_password(form.password.data)
            db.session.commit()
            flash("Password for '{}' was reset!".format(form.email.data), 'success')
            return redirect(url_for('login'))
        elif request.method == 'GET' and request.args.get('email', None, type=str) is not None:
            form.email.data = request.args.get('email', None, type=str)
            return render_template('resetpassword.html', title='Reset password', form=form)
        return render_template('resetpassword.html', title='Reset password', form=form)
    else:
        flash('You need admin level access to perform this acction.', 'danger')
        return redirect(url_for('login'))

# Endpoint 'usercfg': Admins sollen user enablen/disablen können
# Erst ein user object auswählen


@app.route('/usercfg', methods=['GET', 'POST'])
@login_required
def select_user():
    if current_user.role != 0:
        flash('You need admin access to perform this acction.', 'danger')
        return redirect(url_for('login'))
    form = UserSelectForm()
    form.user.query = db.session.query(User)
    form.user.choices = [(u.id, u.username) for u in User.query.order_by('id')]

    if form.validate_on_submit():
        user_id = form.user.data.id
        print(f'User id: {user_id}')
        return redirect(url_for('edit_user', id=user_id))

    return render_template('user.html', title='User select', form=form)

# Dann die eigenschaftern konfigurieren


@app.route('/usercfg/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if current_user.role != 0:
        flash('You need admin access to perform this acction.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get_or_404(id)
    form = UserConfigForm()

    if form.validate_on_submit():
        # Update user properties
        # For example: user.email = form.email.data
        if form.email.data is not None:
            user.email = form.email.data
        if form.enabled.data:
            user.is_active = 1
        else:
            user.is_active = 0
        if form.admin.data:
            user.role = 0
        else:
            user.role = 1
        db.session.commit()
        flash(f"User '{user.username}' updated!", 'success')
        return redirect(url_for('select_user'))

    # Populate the form with the user's existing data
    form.email.data = user.email
    form.enabled.data = user.is_active
    form.admin.data = True if user.role == 0 else False

    return render_template('user.html', title='User update', form=form)

# Endpoint 'user_info': Damit kann ein user prüfen, ob er angemeldet ist oder nicht


@app.route('/user_info', methods=['GET', 'POST'])
# @login_required
def user_info():
    if current_user.is_authenticated:
        resp = {"result": 200,
                "data": current_user.to_json()}
    else:
        resp = {"result": 401,
                "data": {"message": "user not login"}}
    return jsonify(**resp)
