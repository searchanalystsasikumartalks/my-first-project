"""Private fixed-public-repository object refresh; never check out fetched code.

The caller must hold the Studio cooperative lock. Repository/configuration changes
by uncooperative concurrent writers are unsupported. FETCH_HEAD and object storage
may change, including on refusal; worktree, HEAD, and branch refs are not updated.
"""
import configparser
from dataclasses import dataclass
import os
import re
import selectors
import signal
import stat
import subprocess
import time

from intake import BRANCH, REMOTE, REF

REPO = "/home/dzfbipjkvhxg/repositories/github-transfer-test-20261108"
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


class RefreshError(ValueError):
    pass


@dataclass(frozen=True)
class RefreshReceipt:
    branch_tip: str
    source_commit: str
    previous_tip: str | None
    worktree_head: str
    fetched: bool = True
    checked_out: bool = False
    deployed: bool = False


def _commit(value):
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        raise RefreshError("full lowercase pinned commit required")
    return value


def _validate_config(raw):
    """Deliberately accept only a small ordinary-clone configuration subset."""
    try:
        config = configparser.ConfigParser(interpolation=None, strict=True,
                                          inline_comment_prefixes=None)
        config.read_string(raw.decode("utf-8"))
    except (UnicodeError, configparser.Error) as exc:
        raise RefreshError("unsupported local Git configuration") from exc
    if config.defaults():
        raise RefreshError("default config values unsupported")
    allowed = {"core": {"repositoryformatversion", "filemode", "bare", "logallrefupdates",
                        "ignorecase", "precomposeunicode"},
               'remote "origin"': {"url", "fetch"},
               'branch "' + BRANCH + '"': {"remote", "merge"}}
    for section in config.sections():
        if section not in allowed or not set(config[section]) <= allowed[section]:
            raise RefreshError("local Git configuration outside safe allowlist")
    if (config.get("core", "repositoryformatversion", fallback=None) != "0"
            or config.get("core", "bare", fallback=None) != "false"
            or config.get('remote "origin"', "url", fallback=None) != REMOTE):
        raise RefreshError("unsupported repository format, bare repository or origin")
    fetch = config.get('remote "origin"', "fetch", fallback=None)
    if fetch not in (None, "+refs/heads/*:refs/remotes/origin/*",
                     "+" + REF + ":refs/remotes/origin/" + BRANCH):
        raise RefreshError("unexpected configured fetch refspec")
    branch = 'branch "' + BRANCH + '"'
    if config.has_section(branch) and (
            config.get(branch, "remote", fallback=None) != "origin"
            or config.get(branch, "merge", fallback=None) != REF):
        raise RefreshError("unexpected configured branch tracking")


def _validate_repository():
    """No-follow fixed directory walk, bounded config and no alternate object DB."""
    fd = os.open("/", _DIR)
    gitfd = None
    try:
        parts = REPO.split("/")[1:]
        if not REPO.startswith("/") or any(part in ("", ".", "..") for part in parts):
            raise RefreshError("noncanonical fixed repository path")
        for part in parts:
            child = os.open(part, _DIR, dir_fd=fd)
            os.close(fd)
            fd = child
        gitfd = os.open(".git", _DIR, dir_fd=fd)
        for folder in (fd, gitfd):
            if os.fstat(folder).st_mode & 0o022:
                raise RefreshError("repository directories must not be writable by other users")
        for name in ("HEAD", "FETCH_HEAD", "packed-refs"):
            try:
                metadata = os.stat(name, dir_fd=gitfd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_mode & 0o022:
                raise RefreshError("unsafe Git ref metadata")
        configfd = os.open("config", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=gitfd)
        try:
            before = os.fstat(configfd)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or before.st_size > 65536 or before.st_mode & 0o022):
                raise RefreshError("unsafe or oversized Git config")
            raw = bytearray()
            while len(raw) <= 65536:
                chunk = os.read(configfd, min(8192, 65537 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
            after = os.fstat(configfd)
            fingerprint = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if len(raw) > 65536 or fingerprint(before) != fingerprint(after):
                raise RefreshError("Git config changed or exceeded limit")
            _validate_config(bytes(raw))
        finally:
            os.close(configfd)
        for name in ("shallow", "commondir", "config.worktree"):
            try:
                os.stat(name, dir_fd=gitfd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise RefreshError("shallow, alternate worktree or worktree config unsupported")
        # Walk potentially absent paths using no-follow directory handles.
        for directories, names in ((("objects", "info"), ("alternates", "http-alternates")),
                                   (("info",), ("grafts",)), (("refs",), ("replace",))):
            checkfd = os.dup(gitfd)
            try:
                for component in directories:
                    try:
                        child = os.open(component, _DIR, dir_fd=checkfd)
                    except FileNotFoundError:
                        break
                    os.close(checkfd)
                    checkfd = child
                else:
                    for name in names:
                        try:
                            os.stat(name, dir_fd=checkfd, follow_symlinks=False)
                        except FileNotFoundError:
                            continue
                        raise RefreshError("alternate or replaced object histories unsupported")
            finally:
                os.close(checkfd)
        return (os.fstat(fd).st_dev, os.fstat(fd).st_ino, bytes(raw))
    except OSError as exc:
        raise RefreshError("fixed repository or metadata is missing or unsafe") from exc
    finally:
        if gitfd is not None:
            os.close(gitfd)
        os.close(fd)


def _git(args, limit=65536, timeout=20):
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "HOME": "/nonexistent",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false",
           "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"}
    settings = ("core.hooksPath=/dev/null", "core.fsmonitor=false", "submodule.recurse=false",
                "credential.helper=", "http.proxy=", "http.followRedirects=false",
                "http.sslVerify=true", "protocol.allow=never", "protocol.https.allow=always",
                "maintenance.auto=false", "gc.auto=0", "fetch.writeCommitGraph=false")
    cmd = ["/usr/bin/git", "--no-replace-objects", "--no-optional-locks"]
    for setting in settings:
        cmd.extend(("-c", setting))
    cmd.extend(("-C", REPO))
    cmd.extend(args)
    try:
        with subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=env, start_new_session=True) as proc:
            data = bytearray()
            errors = 0
            deadline = time.monotonic() + timeout
            finished = False
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(proc.stdout, selectors.EVENT_READ, True)
                    selector.register(proc.stderr, selectors.EVENT_READ, False)
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise RefreshError("Git operation timed out")
                        for key, _ in selector.select(remaining):
                            chunk = os.read(key.fileobj.fileno(), 8192)
                            if not chunk:
                                selector.unregister(key.fileobj)
                            elif key.data:
                                data.extend(chunk)
                                if len(data) > limit:
                                    raise RefreshError("Git output exceeds bound")
                            else:
                                errors += len(chunk)
                                if errors > 65536:
                                    raise RefreshError("Git error output exceeds bound")
                remaining = deadline - time.monotonic()
                if remaining <= 0 or proc.wait(timeout=remaining) != 0:
                    raise RefreshError("Git operation failed")
                finished = True
                return bytes(data)
            finally:
                # Kill the process group on failure, including Git's HTTPS child.
                if not finished:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                proc.wait()
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RefreshError("Git operation failed or timed out") from exc


def _text(args):
    try:
        return _git(args, 4096).decode("ascii").strip()
    except UnicodeError as exc:
        raise RefreshError("unexpected Git response") from exc


def _worktree():
    if _text(["remote", "get-url", "origin"]) != REMOTE:
        raise RefreshError("fixed repository origin mismatch")
    if _text(["branch", "--show-current"]) != BRANCH:
        raise RefreshError("wrong checked-out branch")
    if _git(["status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"]):
        raise RefreshError("working tree must be clean")
    return _commit(_text(["rev-parse", "--verify", "HEAD"]))


def ensure_objects(branch_tip, source_commit, previous_tip=None):
    """Fetch fixed branch objects, verify exact tip/ancestry, leave checkout alone."""
    _commit(branch_tip)
    _commit(source_commit)
    if previous_tip is not None:
        _commit(previous_tip)
    before_config = _validate_repository()
    head = _worktree()
    _git(["fetch", "--no-tags", "--no-recurse-submodules", "--no-auto-maintenance",
          "--no-write-commit-graph", "--refmap=", REMOTE, REF])
    if _text(["rev-parse", "--verify", "FETCH_HEAD"]) != branch_tip:
        raise RefreshError("branch moved since polling; repoll required")
    for commit in dict.fromkeys((head, branch_tip, source_commit, previous_tip)):
        if commit is not None and _text(["cat-file", "-t", commit]) != "commit":
            raise RefreshError("pinned object is not a commit")
    _git(["merge-base", "--is-ancestor", head, branch_tip], 128)
    if previous_tip is not None:
        _git(["merge-base", "--is-ancestor", previous_tip, branch_tip], 128)
    _git(["merge-base", "--is-ancestor", source_commit, branch_tip], 128)
    if _validate_repository() != before_config or _worktree() != head:
        raise RefreshError("repository changed during object fetch")
    return RefreshReceipt(branch_tip, source_commit, previous_tip, head)
