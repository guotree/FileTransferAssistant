import os
from flask import Flask, render_template, redirect, url_for, send_file, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy.exc import IntegrityError
from models import db, User, File, Message
from forms import LoginForm, RegistrationForm, UploadForm, MessageForm
from config import Config
from utils import safe_filename

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('The form has expired. Please try again.')
    return redirect('/')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
@login_required
def index():
    upload_form = UploadForm()
    message_form = MessageForm()
    files = current_user.files.all()
    messages = current_user.messages.order_by(Message.timestamp.desc()).all()
    return render_template('index.html', upload_form=upload_form, message_form=message_form, files=files, messages=messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect("/")
        flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect("/")
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    form = UploadForm()
    if not form.validate_on_submit():
        # Surface validation failures (missing file, bad CSRF token, ...)
        # instead of silently redirecting.
        for errors in form.errors.values():
            for error in errors:
                flash(error)
        return redirect("/")

    filename = safe_filename(form.file.data.filename)
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)
    filepath = os.path.join(user_dir, filename)

    # Refuse same-name files instead of overwriting them (and never let a
    # crafted filename escape user_dir: safe_filename removed separators).
    if os.path.exists(filepath) or File.query.filter_by(user_id=current_user.id, filename=filename).first():
        flash('A file with the same name already exists')
        return redirect("/")

    form.file.data.save(filepath)
    db.session.add(File(filename=filename, filepath=filepath, owner=current_user))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if os.path.isfile(filepath):
            os.remove(filepath)
        flash('A file with the same name already exists')
        return redirect("/")
    flash('File uploaded successfully')
    return redirect("/")

@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    if file.owner != current_user:
        flash('You do not have permission to download this file')
        return redirect("/")
    if not os.path.isfile(file.filepath):
        flash('The file is no longer available on the server')
        return redirect("/")
    return send_file(file.filepath,
                     as_attachment=True,
                     download_name=file.filename)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    form = MessageForm()
    if form.validate_on_submit():
        message = Message(content=form.content.data, author=current_user)
        db.session.add(message)
        db.session.commit()
        flash('Message sent')
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error)
    return redirect("/")


def delete_user_files(user):
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user.id))
    for file in File.query.filter_by(user_id=user.id).all():
        if os.path.isfile(file.filepath):
            os.remove(file.filepath)
        db.session.delete(file)
    db.session.commit()
    if os.path.isdir(user_dir) and not os.listdir(user_dir):
        os.rmdir(user_dir)


def delete_user_messages(user):
    Message.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.commit()


@app.route("/delete_file", methods=["POST"])
@login_required
def delete_file():
    delete_user_files(current_user)
    return redirect("/")

@app.route("/delete_message", methods=["POST"])
@login_required
def delete_message():
    delete_user_messages(current_user)
    return redirect("/")

@app.route("/delete_all", methods=["POST"])
@login_required
def delete_all():
    delete_user_messages(current_user)
    delete_user_files(current_user)
    flash("All the files and messages are deleted!")
    return redirect("/")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
