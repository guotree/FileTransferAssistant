"""Smoke test for the bug fixes. Uses an isolated temp DB + upload folder."""
import io
import os
import re
import shutil
import tempfile

TEST_ROOT = tempfile.mkdtemp(prefix='easysync_smoke_')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(TEST_ROOT, 'test.db')
os.environ['UPLOAD_FOLDER'] = os.path.join(TEST_ROOT, 'uploads')

from app import app, db, File, Message, User  # noqa: E402  (needs env above)

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
TEST_UPLOADS = os.environ['UPLOAD_FOLDER']

results = []


def check(name, cond, extra=''):
    results.append((name, bool(cond), extra))


with app.app_context():
    db.create_all()

client = app.test_client()

# --- auth / route-method fixes -------------------------------------------
r = client.get('/')
check('GET / unauthenticated redirects to login',
      r.status_code == 302 and '/login' in r.headers.get('Location', ''), str(r.status_code))

r = client.post('/delete_all')
check('POST /delete_all unauthenticated redirects (was 500)',
      r.status_code == 302 and '/login' in r.headers.get('Location', ''), str(r.status_code))

r = client.get('/delete_all')
check('GET /delete_all now 405', r.status_code == 405, str(r.status_code))

r = client.get('/logout')
check('GET /logout now 405', r.status_code == 405, str(r.status_code))

# --- register / login -----------------------------------------------------
r = client.post('/register', data={'username': 'alice', 'password': 'pw123456',
                                   'confirm_password': 'pw123456'})
check('register alice', r.status_code == 302, str(r.status_code))

# --- register: short password rejected -------------------------------------
r = client.post('/register', data={'username': 'tiny', 'password': 'a',
                                   'confirm_password': 'a'},
                follow_redirects=True)
check('short password rejected',
      r.status_code == 200 and b'at least 6 characters' in r.data, str(r.status_code))

# --- register: duplicate username (was IntegrityError 500) -----------------
r = client.post('/register', data={'username': 'alice', 'password': 'pw123456',
                                   'confirm_password': 'pw123456'},
                follow_redirects=True)
check('duplicate username refused with flash (was 500)',
      r.status_code == 200 and b'already exists' in r.data, str(r.status_code))

r = client.post('/login', data={'username': 'alice', 'password': 'pw123456'}, follow_redirects=True)
check('login alice', b'Welcome, alice' in r.data)

# --- upload: success ------------------------------------------------------
r = client.post('/upload', data={'file': (io.BytesIO(b'hello world'), 'hello.txt')},
                content_type='multipart/form-data', follow_redirects=True)
check('upload success flash', b'File uploaded successfully' in r.data)

with app.app_context():
    f = File.query.filter_by(filename='hello.txt').first()
    check('stored in per-user dir',
          f is not None and os.path.isfile(f.filepath)
          and os.path.dirname(f.filepath) == os.path.join(TEST_UPLOADS, '1'),
          getattr(f, 'filepath', 'missing'))

# --- upload: duplicate refused (was IntegrityError 500) -------------------
r = client.post('/upload', data={'file': (io.BytesIO(b'again'), 'hello.txt')},
                content_type='multipart/form-data', follow_redirects=True)
check('duplicate name refused with flash',
      b'same name already exists' in r.data and r.status_code == 200, str(r.status_code))
with app.app_context():
    check('duplicate did not overwrite / no extra row',
          File.query.filter_by(filename='hello.txt').count() == 1)

# --- upload: path traversal ----------------------------------------------
client.post('/upload', data={'file': (io.BytesIO(b'evil'), '../../evil.txt')},
            content_type='multipart/form-data', follow_redirects=True)
with app.app_context():
    f = File.query.filter_by(filename='evil.txt').first()
    check('traversal name confined to user dir',
          f is not None and os.path.dirname(f.filepath) == os.path.join(TEST_UPLOADS, '1'),
          getattr(f, 'filepath', 'missing'))
check('no file escaped the upload root',
      not os.path.isfile(os.path.join(TEST_ROOT, 'evil.txt')))

# --- upload: non-ASCII name preserved -------------------------------------
client.post('/upload', data={'file': (io.BytesIO(b'cn'), '报告.txt')},
            content_type='multipart/form-data', follow_redirects=True)
with app.app_context():
    check('unicode filename kept',
          File.query.filter_by(filename='报告.txt').first() is not None)

# --- upload: empty submit no longer silent --------------------------------
r = client.post('/upload', data={}, follow_redirects=True)
check('empty upload flashes an error',
      b'This field is required' in r.data or b'File required' in r.data,
      r.data[:200].decode('utf-8', 'replace'))

# --- message --------------------------------------------------------------
r = client.post('/send_message', data={'content': 'hi from smoke test'}, follow_redirects=True)
check('message sent', b'Message sent' in r.data)

r = client.post('/send_message', data={'content': 'x' * 10001}, follow_redirects=True)
check('oversized message rejected', b'Message too long' in r.data)

r = client.get('/')
check('messages render copy buttons',
      b'copy-btn' in r.data and b'clipboard' in r.data)

# --- download ownership ---------------------------------------------------
with app.app_context():
    alice_file_id = File.query.filter_by(filename='hello.txt').first().id

client.post('/logout')
client.post('/register', data={'username': 'bob', 'password': 'pw456789', 'confirm_password': 'pw456789'})
client.post('/login', data={'username': 'bob', 'password': 'pw456789'})

client.post('/send_message', data={'content': 'bob message'})
r = client.get('/')
check('dashboard renders separate clear controls',
      b'Clear Files' in r.data and b'Clear Messages' in r.data)
r = client.post('/delete_file', follow_redirects=True)
check('clear files flash', b'All files are deleted' in r.data)
with app.app_context():
    check('clear files keeps messages',
          File.query.filter_by(user_id=2).count() == 0
          and Message.query.filter_by(user_id=2).count() == 1)
r = client.post('/upload', data={'file': (io.BytesIO(b'bob again'), 'hello.txt')},
                content_type='multipart/form-data', follow_redirects=True)
check("bob can reuse alice's filename", b'File uploaded successfully' in r.data)
r = client.post('/delete_message', follow_redirects=True)
check('clear messages flash', b'All messages are deleted' in r.data)
with app.app_context():
    check('clear messages keeps files',
          Message.query.filter_by(user_id=2).count() == 0
          and File.query.filter_by(user_id=2).count() == 1)
client.post('/send_message', data={'content': 'bob message restored'})

r = client.get('/download/%d' % alice_file_id, follow_redirects=True)
check("other user's download blocked", b'permission' in r.data, str(r.status_code))

r = client.post('/upload', data={'file': (io.BytesIO(b'bob'), 'hello.txt')},
                content_type='multipart/form-data', follow_redirects=True)
check('duplicate name refused after initial upload', b'same name already exists' in r.data)

# --- logout via POST ------------------------------------------------------
r = client.post('/logout')
check('POST /logout works', r.status_code == 302 and '/login' in r.headers.get('Location', ''),
      str(r.status_code))

# --- delete_all for alice -------------------------------------------------
client.post('/login', data={'username': 'alice', 'password': 'pw123456'})
r = client.post('/delete_all', follow_redirects=True)
check('delete_all flash', b'All the files and messages are deleted' in r.data)
with app.app_context():
    check('alice files/messages gone',
          File.query.filter_by(user_id=1).count() == 0
          and Message.query.filter_by(user_id=1).count() == 0)
    check("bob's file survives", File.query.filter_by(user_id=2).count() == 1)
check('alice upload dir removed', not os.path.isdir(os.path.join(TEST_UPLOADS, '1')))
check('bob upload dir kept', os.path.isdir(os.path.join(TEST_UPLOADS, '2')))

# --- CSRF end-to-end ------------------------------------------------------
app.config['WTF_CSRF_ENABLED'] = True
r = client.get('/', follow_redirects=True)
m = re.search(rb'name="csrf_token" value="([^"]+)"', r.data)
check('dashboard renders a CSRF token (csrf_token() resolves)', m is not None)
token = m.group(1).decode() if m else ''

r = client.post('/send_message', data={'content': 'csrf ok', 'csrf_token': token},
                follow_redirects=True)
check('POST with valid CSRF token accepted',
      r.status_code == 200 and b'Message sent' in r.data, str(r.status_code))

r = client.post('/send_message', data={'content': 'no token'}, follow_redirects=True)
check('POST with missing CSRF token rejected',
      b'The form has expired' in r.data, str(r.status_code))

# --- request size limit ---------------------------------------------------
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
r = client.post('/upload', data={'file': (io.BytesIO(b'x' * (1024 * 1024 + 1)), 'big.bin')},
                content_type='multipart/form-data', follow_redirects=True)
check('oversized upload rejected', b'too large' in r.data.lower(), str(r.status_code))

# --- report ---------------------------------------------------------------
failed = [x for x in results if not x[1]]
for name, ok, extra in results:
    print(('PASS  ' if ok else 'FAIL  ') + name + (('  <- ' + extra) if (not ok and extra) else ''))
print('\n%d/%d passed' % (len(results) - len(failed), len(results)))
shutil.rmtree(TEST_ROOT, ignore_errors=True)
raise SystemExit(1 if failed else 0)
