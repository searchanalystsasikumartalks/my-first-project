"""Read-only intake of bounded static-app proposals from one public repository.

No fetched source is executed. Approval records must come from the caller's trusted
owner approval store, never from the repository. This module neither grants owner
authority nor dispatches/deploys a proposal.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import http.client
import json
import os
import re
import selectors
import ssl
import subprocess
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from uuid import UUID

REPOSITORY = "searchanalystsasikumartalks/my-first-project"
BRANCH = "test/under-construction-20261108"
REMOTE = "https://github.com/" + REPOSITORY + ".git"
REF = "refs/heads/" + BRANCH
MANIFEST_PATH = "deployment/appstudio-manifest.json"
MAX_MANIFEST_BYTES = 65536
MAX_APPS = 64
MAX_FILE_BYTES = 1024 * 1024
STATIC_FILES = frozenset(("app.js", "data.js", "index.html", "style.css"))
RESERVED_SLUGS = frozenset(("a", "admin", "master", "assets", "api", "static", "index", "deployment", "catalog-preview"))
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class IntakeError(ValueError):
    pass


class ManifestMissing(IntakeError):
    """The fixed manifest path returned HTTP 404 at the observed branch tip."""


@dataclass(frozen=True)
class AppProposal:
    app_id: str
    display_name: str
    slug: str
    operation: str
    source: str
    files: tuple  # sorted (filename, sha256) pairs
    expected_revision: str | None


@dataclass(frozen=True)
class Manifest:
    commit: str
    apps: tuple
    sha256: str  # exact uploaded manifest bytes, not a normalized reserialization


@dataclass(frozen=True)
class PollResult:
    commit: str
    changed: bool


@dataclass(frozen=True)
class IntakeResult:
    branch_tip: str
    source_commit: str | None
    changed: bool
    status: str
    manifest: Manifest | None


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirects are forbidden", headers, fp)


def fetch_manifest(branch_tip, timeout=15):
    """Read the fixed JSON path at a polled tip; never fetch/execute app source.

    The manifest's commit pins source files and need not equal branch_tip. Neither
    a valid manifest nor a branch change constitutes owner approval.
    """
    if not _matches(branch_tip, _COMMIT):
        raise IntakeError("a full lowercase branch-tip commit is required")
    if type(timeout) not in (int, float) or not 0 < timeout <= 30:
        raise IntakeError("timeout must be between zero and 30 seconds")
    url = "https://raw.githubusercontent.com/" + REPOSITORY + "/" + branch_tip + "/" + MANIFEST_PATH
    # No environment proxy, cookie jar, credential handler, or redirect follows.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()), _NoRedirects())
    request = urllib.request.Request(url, headers={"Accept": "application/json", "Accept-Encoding": "identity"}, method="GET")
    deadline = time.monotonic() + timeout
    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status == 404:
                raise ManifestMissing("manifest missing at observed branch tip")
            if response.status != 200 or response.geturl() != url:
                raise IntakeError("manifest response status or destination is invalid")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise IntakeError("encoded manifest bodies are not accepted")
            length = response.headers.get("Content-Length")
            if length is not None and (not re.fullmatch(r"[0-9]{1,6}", length) or int(length) > MAX_MANIFEST_BYTES):
                raise IntakeError("manifest response exceeds byte limit or has invalid length")
            content = bytearray()
            # read1 avoids a single read waiting for an entire slowly streamed body.
            # Each network read also has the transport timeout supplied above.
            while len(content) <= MAX_MANIFEST_BYTES:
                if time.monotonic() >= deadline:
                    raise IntakeError("manifest retrieval timed out")
                chunk = response.read1(min(8192, MAX_MANIFEST_BYTES + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
            if time.monotonic() >= deadline:
                raise IntakeError("manifest retrieval timed out")
            if len(content) > MAX_MANIFEST_BYTES:
                raise IntakeError("manifest response exceeds byte limit")
            return parse_manifest(bytes(content))
    except urllib.error.HTTPError as exc:
        exc.close()
        if exc.code == 404:
            raise ManifestMissing("manifest missing at observed branch tip") from exc
        raise IntakeError("manifest HTTP request failed; redirects are forbidden") from exc
    except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
        raise IntakeError("manifest retrieval failed or timed out") from exc


def poll_and_read(previous_commit=None, timeout=15):
    """Inspect a branch tip and its manifest. Never approve or dispatch proposals."""
    result = poll_branch(previous_commit=previous_commit, timeout=timeout)
    try:
        manifest = fetch_manifest(result.commit, timeout=timeout)
    except ManifestMissing:
        return IntakeResult(result.commit, None, result.changed, "missing_manifest", None)
    return IntakeResult(result.commit, manifest.commit, result.changed, "manifest_ready", manifest)


def _object(pairs):
    result = {}
    seen = set()
    for key, value in pairs:
        if key.casefold() in seen:
            raise IntakeError("duplicate or case-colliding JSON field")
        seen.add(key.casefold())
        result[key] = value
    return result


def _fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise IntakeError("unexpected or missing fields")


def _matches(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def parse_manifest(raw):
    """Validate untrusted UTF-8 JSON without reading files or contacting a service."""
    if isinstance(raw, str):
        try:
            raw = raw.encode("utf-8")
        except UnicodeError as exc:
            raise IntakeError("invalid UTF-8 manifest") from exc
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_MANIFEST_BYTES:
        raise IntakeError("manifest byte limit exceeded or invalid input")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(IntakeError("nonfinite JSON")))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise IntakeError("invalid manifest JSON") from exc
    _fields(value, ("version", "repository", "branch", "commit", "apps"))
    if type(value["version"]) is not int or value["version"] != 1:
        raise IntakeError("unsupported manifest version")
    if value["repository"] != REPOSITORY or value["branch"] != BRANCH:
        raise IntakeError("repository or branch is outside approved intake scope")
    if not _matches(value["commit"], _COMMIT):
        raise IntakeError("a full lowercase pinned commit is required")
    if not isinstance(value["apps"], list) or not 1 <= len(value["apps"]) <= MAX_APPS:
        raise IntakeError("invalid app count")
    ids, slugs, names, apps = set(), set(), set(), []
    for app in value["apps"]:
        _fields(app, ("app_id", "display_name", "slug", "operation", "source", "files", "expected_revision"))
        app_id = app["app_id"]
        try:
            parsed_id = UUID(app_id) if isinstance(app_id, str) else None
        except ValueError as exc:
            raise IntakeError("invalid app UUID") from exc
        if parsed_id is None or str(parsed_id) != app_id or parsed_id.int == 0 or app_id in ids:
            raise IntakeError("app UUID must be unique, nonzero and canonical")
        name = app["display_name"]
        if (not isinstance(name, str) or not 1 <= len(name) <= 80 or name != name.strip()
                or any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in name)):
            raise IntakeError("invalid display name")
        normalized_name = " ".join(unicodedata.normalize("NFKC", name).casefold().split())
        if normalized_name in names:
            raise IntakeError("duplicate normalized display name")
        slug = app["slug"]
        if (not _matches(slug, _SLUG) or len(slug) > 63
                or slug in RESERVED_SLUGS or slug in slugs):
            raise IntakeError("invalid, reserved or duplicate slug")
        if app["operation"] not in ("create", "update"):
            raise IntakeError("explicit create or update required")
        revision = app["expected_revision"]
        if ((app["operation"] == "create" and revision is not None)
                or (app["operation"] == "update" and not _matches(revision, _SHA256))):
            raise IntakeError("create requires null revision; update requires pinned previous revision")
        if app["source"] != "static-apps/" + app_id + "/":
            raise IntakeError("source must be the exact UUID static-app directory")
        _fields(app["files"], STATIC_FILES)
        if not all(_matches(digest, _SHA256) for digest in app["files"].values()):
            raise IntakeError("each file requires a lowercase SHA-256")
        ids.add(app_id)
        slugs.add(slug)
        names.add(normalized_name)
        apps.append(AppProposal(app_id, name, slug, app["operation"], app["source"],
                                tuple(sorted(app["files"].items())), revision))
    return Manifest(value["commit"], tuple(apps), hashlib.sha256(raw).hexdigest())


def approved_proposals(manifest, approval):
    """Return proposals only for an exact trusted owner approval record.

    Caller must authenticate/store owner approval separately and enforce registry
    create/update identity, slug uniqueness, and atomicity at dispatch time. A JSON
    record from GitHub is not an owner approval, regardless of its field values.
    """
    _fields(approval, ("decision", "approved_by", "approved_at", "commit", "manifest_sha256"))
    if (approval["decision"] != "approve" or approval["approved_by"] != "owner"
            or approval["commit"] != manifest.commit or approval["manifest_sha256"] != manifest.sha256):
        raise IntakeError("exact owner approval is required")
    try:
        stamp = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("timezone required")
    except (AttributeError, TypeError, ValueError) as exc:
        raise IntakeError("approval requires a timezone-aware timestamp") from exc
    return manifest.apps


def dispatch_proposal(manifest, app_id, approval):
    """Build a registry proposal, without dispatch, after trusted owner approval.

    Registry approval is independently required; its digest uses the exact returned
    dictionary serialized with sorted keys and compact comma/colon separators.
    """
    apps = approved_proposals(manifest, approval)
    for app in apps:
        if app.app_id == app_id:
            return {"app_id": app.app_id, "slug": app.slug, "display_name": app.display_name,
                    "operation": app.operation, "commit": manifest.commit,
                    "hashes": dict(app.files), "expected_revision": app.expected_revision}
    raise IntakeError("app is not in the approved manifest")


def verify_file_bytes(proposal, filename, content):
    """Validate bytes fetched at Manifest.commit before any caller stages them."""
    expected = dict(proposal.files).get(filename)
    if expected is None or not isinstance(content, bytes) or len(content) > MAX_FILE_BYTES:
        raise IntakeError("unexpected filename, type or file size")
    if hashlib.sha256(content).hexdigest() != expected:
        raise IntakeError("file does not match approved hash")
    return content


def poll_branch(previous_commit=None, timeout=15):
    """Read only the fixed public branch ref. Does not fetch or interpret source."""
    if previous_commit is not None and not _matches(previous_commit, _COMMIT):
        raise IntakeError("invalid previous commit")
    if type(timeout) not in (int, float) or not 0 < timeout <= 30:
        raise IntakeError("timeout must be between zero and 30 seconds")
    # Ignore inherited credential helpers, local Git config, proxies and git env.
    env = {"PATH": os.defpath, "LANG": "C", "GIT_TERMINAL_PROMPT": "0",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_ASKPASS": "/bin/false", "GIT_PROTOCOL_FROM_USER": "0"}
    cmd = ["git", "-c", "credential.helper=", "-c", "http.followRedirects=false",
           "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
           "ls-remote", "--exit-code", "--heads", REMOTE, REF]
    # Drain capped pipes, killing immediately on oversized output or timeout.
    with tempfile.TemporaryDirectory() as cwd:
        try:
            with subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
                buffers = {"out": bytearray(), "err": bytearray()}
                deadline = time.monotonic() + timeout
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(proc.stdout, selectors.EVENT_READ, ("out", 256))
                        selector.register(proc.stderr, selectors.EVENT_READ, ("err", 4096))
                        while selector.get_map():
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                raise IntakeError("public branch polling timed out")
                            for key, _ in selector.select(remaining):
                                label, limit = key.data
                                chunk = os.read(key.fileobj.fileno(), 1024)
                                if not chunk:
                                    selector.unregister(key.fileobj)
                                else:
                                    buffers[label].extend(chunk)
                                    if len(buffers[label]) > limit:
                                        raise IntakeError("public branch polling exceeded output limits")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or proc.wait(timeout=remaining) != 0:
                        raise IntakeError("public branch polling failed")
                finally:
                    if proc.poll() is None:
                        proc.kill()
                    proc.wait()
                raw = bytes(buffers["out"])
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IntakeError("public branch polling failed or timed out") from exc
    try:
        line = raw.decode("ascii")
    except UnicodeError as exc:
        raise IntakeError("invalid branch response") from exc
    match = re.fullmatch(r"([0-9a-f]{40})\t" + re.escape(REF) + r"\n?", line)
    if match is None:
        raise IntakeError("expected exactly the fixed branch ref")
    commit = match.group(1)
    return PollResult(commit, commit != previous_commit)
