from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import os
from models import db, User, File, Message
from forms import LoginForm, RegistrationForm, UploadForm, MessageForm
from config import Config
from utils import encrypt_file, decrypt_file, secure_filename, restore_filename

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    form = UploadForm()
    if form.validate_on_submit():
        file = form.file.data
        # filename = secure_filename(file.filename)
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        new_file = File(filename=filename, filepath=filepath, owner=current_user)
        db.session.add(new_file)
        db.session.commit()
        flash('File uploaded successfully')
    return redirect("/")

@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    if file.owner != current_user:
        flash('You do not have permission to download this file')
        return redirect("/") 
    # decrypt_file(file.filepath)
    try:
        return_value = send_file(file.filepath, 
                                 as_attachment=True, 
                                 download_name=file.filename)
    except TypeError:
        return_value = send_file(file.filepath, 
                                 as_attachment=True, 
                                 attachment_filename=file.filename)
    
    # encrypt_file(file.filepath)
    return return_value

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    form = MessageForm()
    if form.validate_on_submit():
        message = Message(content=form.content.data, author=current_user)
        db.session.add(message)
        db.session.commit()
        flash('Message sent')
    return redirect("/")


@app.route("/delete_file", methods=["GET"])
def delete_file():
    files_to_delete = File.query.filter(File.user_id==current_user.id).all()
    for file in files_to_delete:
        os.remove(file.filepath)
        db.session.delete(file)
    db.session.commit()
    return redirect("/")

@app.route("/delete_message", methods=["GET"])
def delete_message():
    messages_to_delete = Message.query.filter(Message.user_id==current_user.id).all()
    for message in messages_to_delete:
        db.session.delete(message)
    db.session.commit()
    return redirect("/")

@app.route("/delete_all", methods=["GET"])
def delete_all():
    delete_message()
    delete_file()
    flash("All the files and messages are deleted!")
    return redirect("/")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
