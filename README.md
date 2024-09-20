# File Transfer Assistant
#### Video Demo:  <URL [HERE](https://youtu.be/ppaG9ubJrHU)>
#### Description:
##### Background
The motivation behind developing this web app is that I frequently need to send a text snippet or a small file from my phone to someone's computer, without wanting to log into my regular messaging accounts (e.g., Telegram, WeChat) on their device. Sometimes, the direction is reversed, so I require a medium for file transfer independent of messaging apps.

This is a web application that allows users to send and receive files and messages across different devices, which I call the **EasySync**.

##### User Manual

I designed a login page for users who explore my web page `127.0.0.1:5000/login`.  You will first see a pop-up at the top of the page that says "Please log in to access this page." It will disappear after two seconds, but you can also click the close button in the top-right corner to dismiss it. Below the pop-up element, there is a form for user login. You should input your correct username and password. If not, a notification will pop-up at the top of the page that says "Invalid username or password".

When you click the button *Click to Register*, the web application will redirect to `127.0.0.1:5000/register`. You need to submit your username and password, with the password being entered a second time for confirmation.

If you successfully log in, you will see the dashboard of my web application. The page is divided into two sections, with the left side being the file management area and the right side being the message center. 

In the file management area, you can browse for local files, select them, and click Upload. Then you will see a notification "File uploaded successfully", and the uploaded file appears in the *Your Files* area with a timestamp. If you click the file name, you can download it to your local. The server will refuse the file with the same name.

In the Message Center, you can type your message and click send. Then you will see a notification "Message sent", and the message will appear in the *Your Messages* area with a timestamp. And you can copy the text.

There is also a button to delete all the files and messages for the current account on the server. I recommend you delete all the files and messages if you finish your file transfer for data security.

Of course, there is a button for logout. If you click it, the server will redirect you to `127.0.0.1:5000/login`

##### Project Structure

The technical architecture of my web application is mainly Flask. To avoid redundant work, I used the following packages to build the application: 

1. **Flask**: It's a lightweight web framework in Python that makes it easy to build web applications.
2. **Flask-SQLAlchemy**: This adds database support to Flask, making it simpler to work with databases using Python code.
3. **Flask-Login**: It helps manage user logins in Flask apps, handling things like remembering users and logging them in or out.
4. **Flask-WTF**: This makes it easier to create and handle forms in Flask, including adding security features like CSRF protection.

Here is the structure of my final project.


```
project
├── README.md
├── app.db
├── app.py
├── config.py
├── forms.py
├── models.py
├── requirements.txt
├── static
│   ├── main.js
│   ├── styles.css
│   └── uploads
│       └── Welcome.md
├── templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   └── register.html
└── utils.py

```


 The root folder is `project` which contains python scripts, database files, html files, css files, upload files and pip requirements files.

1. `./app.py` is the main function of this project. 
2. `./app.db` are the database files which contain three tables: `user`, `message`, `file`
   -  `user`: this table contains user IDs, usernames, and hashed passwords. Usernames are unique.
   -  `message`: this table contains message IDs, message contents, timestamps, user IDs.
   -  `file`: this table contains file IDs, file names, file paths, user IDs, upload times and the file names are unique.
3. `./config.py` stores the path of the database and the path of upload files
4. `./forms.py` it defines four different forms for a Flask web application using Flask-WTF. Here's a brief explanation of each form:
   1. **LoginForm**: This form is used for logging in. 
   2. **RegistrationForm**: This form is used for user registration.
   3. **UploadForm**: This form is for file uploads.
   4. **MessageForm**: This form is for sending messages. 
4. `./models.py` it sets up a basic model structure for a Flask application using Flask-SQLAlchemy for database interactions and Flask-Login for user authentication. User Model, File Model and Message Model are connected to user table, file table and message table.
5. `./utils.py` contains some tools for `./app.py`
6. `./requirements.txt` it lists the python packages we need to use.
7. `./static/uploads/` stores uploaded files for each user.
8. `./static/style.css` is the style file.
9. `./templates/` are html files