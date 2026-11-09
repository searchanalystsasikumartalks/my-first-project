"""Linux no-follow manifest and atomic-rename primitives."""
import ctypes, errno, fcntl, hashlib, json, os, re, stat
from pathlib import Path

FILES = ('app.js', 'data.js', 'index.html', 'style.css')
FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
libc = ctypes.CDLL(None, use_errno=True)
renameat2 = getattr(libc, 'renameat2', None)
if renameat2:
    renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    renameat2.restype = ctypes.c_int

class Refused(RuntimeError): pass

def rename(srcfd, src, dstfd, dst, flag):
    if renameat2 is None: raise Refused('renameat2 unavailable; no fallback')
    if renameat2(srcfd, src.encode(), dstfd, dst.encode(), flag):
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e))

def identity(fd):
    s = os.fstat(fd)
    return [s.st_dev, s.st_ino]

def open_dir(parent, name):
    if not isinstance(name,str) or not re.fullmatch(r'[a-z0-9-]+',name): raise Refused('single safe directory name required')
    return os.open(name, FLAGS, dir_fd=parent)

def manifest(fd):
    if sorted(os.listdir(fd)) != list(FILES): raise Refused('exact four files required')
    result = {}
    for name in FILES:
        f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            before = os.fstat(f)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 1048576:
                raise Refused('bounded ordinary singly-linked file required')
            data = b''
            while len(data) <= 1048576:
                part = os.read(f, 65536)
                if not part: break
                data += part
            if len(data) > 1048576 or b'\0' in data: raise Refused('invalid file content')
            data.decode('utf-8')
            after = os.fstat(f)
            if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns): raise Refused('file changed while reading')
            named = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if (named.st_dev,named.st_ino) != (after.st_dev,after.st_ino): raise Refused('file replaced while reading')
            result[name] = hashlib.sha256(data).hexdigest()
        finally: os.close(f)
    return result

