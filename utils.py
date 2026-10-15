import os
import re


def safe_filename(filename, max_length=180):
    """Sanitize a client-supplied filename.

    Strips any directory components so a crafted name like ``../../x.txt``
    cannot escape the upload folder, and removes characters that are unsafe
    on disk. Unlike ``werkzeug.secure_filename`` it keeps non-ASCII (e.g.
    Chinese) characters instead of dropping them.
    """
    name = os.path.basename((filename or "").replace("\\", "/"))
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).lstrip(".").strip()
    if not name:
        name = "file"
    if len(name) > max_length:
        root, ext = os.path.splitext(name)
        name = root[: max_length - len(ext)] + ext
    return name
