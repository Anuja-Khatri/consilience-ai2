"""Download, copy-in and verify pinned sources; unzip safely.

Integrity rules
- A file source is accepted only if its SHA-256 and size equal the pinned values. A
  download is written to ``<path>.part`` while it is hashed, and renamed into place only
  after it verifies; a mismatch deletes the partial file and raises ``FetchError``.
- A git source is accepted only if ``git rev-parse HEAD`` equals the pinned commit.
- A file that verified is stamped with ``<path>.verified.json`` (hash, size, mtime), so
  later calls do not re-hash hundreds of MB; ``verify=True`` re-hashes anyway.
- Zips are extracted member by member; absolute paths, ``..`` and symlinks are refused.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections.abc import Iterable, Sequence
from pathlib import Path

from consilience_ai2 import __version__
from consilience_ai2.core.hashing import sha256_file
from consilience_ai2.fetch.sources import Source, cache_root, get_source

USER_AGENT = f"consilience-ai2/{__version__} (data fetch)"
CHUNK = 1 << 20
MARKER = ".consilience-ai2-extracted.json"
_DRIVE_UUID = re.compile(r'name="uuid"\s+value="([^"]+)"')


class FetchError(RuntimeError):
    """A source could not be fetched or did not verify."""


# --------------------------------------------------------------------------- files


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".verified.json")


def _stamp(path: Path, src: Source) -> None:
    st = path.stat()
    _sidecar(path).write_text(json.dumps(
        {"name": src.name, "sha256": src.sha256, "size": st.st_size, "mtime_ns": st.st_mtime_ns},
        sort_keys=True) + "\n")


def _stamp_ok(path: Path, src: Source) -> bool:
    side = _sidecar(path)
    if not (path.is_file() and side.is_file()):
        return False
    try:
        d = json.loads(side.read_text())
    except ValueError:
        return False
    st = path.stat()
    return (d.get("sha256") == src.sha256 and d.get("size") == st.st_size
            and d.get("mtime_ns") == st.st_mtime_ns)


def _check_file(path: Path, src: Source) -> None:
    size = path.stat().st_size
    if src.size is not None and size != src.size:
        raise FetchError(f"{src.name}: size {size} != pinned {src.size}")
    digest = sha256_file(path)
    if digest != src.sha256:
        raise FetchError(f"{src.name}: sha256 {digest} != pinned {src.sha256}")


def _find_local(src: Source, from_dirs: Iterable[Path], want_dir: bool) -> Path | None:
    names = src.local_candidates()
    for base in from_dirs:
        base = Path(base).expanduser()
        if not base.is_dir():
            continue
        for name in names:
            direct = base / name
            if (direct.is_dir() if want_dir else direct.is_file()):
                return direct
        # shallow recursive search (depth <= 4), deterministic order
        for depth in range(1, 5):
            pattern = "/".join(["*"] * depth)
            for cand in sorted(base.glob(pattern)):
                if cand.name in names and (cand.is_dir() if want_dir else cand.is_file()):
                    if want_dir and not (cand / ".git").exists():
                        continue
                    return cand
    return None


def _download(src: Source, dest: Path, quiet: bool) -> None:
    url = src.url
    for attempt in range(2):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if "text/html" in ctype and "drive" in url and attempt == 0:
                # Google Drive virus-scan interstitial: retry with its confirmation uuid
                page = resp.read(1 << 16).decode("utf-8", "replace")
                m = _DRIVE_UUID.search(page)
                if not m:
                    raise FetchError(f"{src.name}: Drive returned an HTML page, not the file. "
                                     f"Manual step: {src.manual or src.page}")
                url = f"{src.url}&uuid={m.group(1)}"
                continue
            if "text/html" in ctype:
                raise FetchError(f"{src.name}: server returned HTML, not the file. "
                                 f"Manual step: {src.manual or src.page}")
            done = 0
            next_report = 50 * CHUNK
            with open(dest, "wb") as fh:
                while True:
                    block = resp.read(CHUNK)
                    if not block:
                        break
                    fh.write(block)
                    done += len(block)
                    if not quiet and done >= next_report:
                        total = f"/{src.size}" if src.size else ""
                        print(f"  {src.name}: {done}{total} bytes", file=sys.stderr)
                        next_report += 50 * CHUNK
        return
    raise FetchError(f"{src.name}: Drive confirmation failed. Manual step: {src.manual}")


def _fetch_file(src: Source, root: Path, from_dirs: Sequence[Path], verify: bool,
                quiet: bool, offline: bool) -> Path:
    if src.is_todo:
        raise FetchError(f"{src.name}: sha256 not pinned yet ({src.sha256}); refusing to fetch")
    target = root / src.path
    if target.exists():
        if not verify and _stamp_ok(target, src):
            return target
        try:
            _check_file(target, src)
        except FetchError as exc:
            raise FetchError(f"{exc}. The cached file {target} does not match its pin; "
                             "delete it and fetch again.") from exc
        _stamp(target, src)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    part.unlink(missing_ok=True)
    local = _find_local(src, from_dirs, want_dir=False) if from_dirs else None
    try:
        if local is not None:
            if not quiet:
                print(f"  {src.name}: copying from {local}", file=sys.stderr)
            shutil.copyfile(local, part)
        elif offline:
            where = ", ".join(map(str, from_dirs)) or "no --from-dir given"
            raise FetchError(f"{src.name}: offline and not found locally ({where})")
        else:
            if not quiet:
                print(f"  {src.name}: downloading {src.url}", file=sys.stderr)
            _download(src, part, quiet)
        _check_file(part, src)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    os.replace(part, target)
    _stamp(target, src)
    return target


# --------------------------------------------------------------------------- zips


def _safe_extract(zpath: Path, dest: Path) -> int:
    count = 0
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            name = info.filename
            parts = Path(name).parts
            if name.startswith(("/", "\\")) or ".." in parts or (parts and ":" in parts[0]):
                raise FetchError(f"{zpath.name}: unsafe member path {name!r}")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise FetchError(f"{zpath.name}: symlink member refused: {name!r}")
            out = dest / name
            if info.is_dir():
                out.mkdir(parents=True, exist_ok=True)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as srcf, open(out, "wb") as dstf:
                shutil.copyfileobj(srcf, dstf, CHUNK)
            count += 1
    return count


def extract(src: Source, root: Path, quiet: bool = False) -> Path:
    """Unzip a verified file source next to it; idempotent (checks a marker)."""
    zpath = root / src.path
    dest = src.extract_dir(root)
    if dest is None:
        raise FetchError(f"{src.name}: not a zip source")
    marker = dest / MARKER
    if marker.is_file():
        try:
            if json.loads(marker.read_text()).get("sha256") == src.sha256:
                return dest
        except ValueError:
            pass
        raise FetchError(f"{src.name}: {dest} holds a different extraction; delete it first")
    if dest.exists():
        raise FetchError(f"{src.name}: {dest} exists without a marker; delete it first")
    tmp = dest.with_name(dest.name + ".extracting")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        if not quiet:
            print(f"  {src.name}: extracting to {dest}", file=sys.stderr)
        n = _safe_extract(zpath, tmp)
        (tmp / MARKER).write_text(json.dumps(
            {"name": src.name, "sha256": src.sha256, "files": n}, sort_keys=True) + "\n")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    os.replace(tmp, dest)
    return dest


# --------------------------------------------------------------------------- git


def _git(*args: str, cwd: Path | None = None) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise FetchError(f"git {' '.join(args)} failed: {res.stderr.strip()[:400]}")
    return res.stdout.strip()


def _git_head(path: Path) -> str | None:
    try:
        return _git("rev-parse", "HEAD", cwd=path)
    except FetchError:
        return None


def _fetch_git(src: Source, root: Path, from_dirs: Sequence[Path], quiet: bool,
               offline: bool) -> Path:
    target = root / src.path
    if target.exists():
        head = _git_head(target)
        if head == src.commit:
            return target
        raise FetchError(f"{src.name}: {target} is at {head}, pinned {src.commit}; "
                         "delete it and fetch again")
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    if part.exists():
        shutil.rmtree(part)
    local = _find_local(src, from_dirs, want_dir=True) if from_dirs else None
    try:
        if local is not None:
            if not quiet:
                print(f"  {src.name}: cloning from {local}", file=sys.stderr)
            _git("clone", "--quiet", "--no-checkout", str(local), str(part))
            _git("checkout", "--quiet", "--detach", src.commit, cwd=part)
        elif offline:
            where = ", ".join(map(str, from_dirs)) or "no --from-dir given"
            raise FetchError(f"{src.name}: offline and not found locally ({where})")
        else:
            if not quiet:
                print(f"  {src.name}: fetching {src.url} @ {src.commit[:12]}", file=sys.stderr)
            part.mkdir(parents=True)
            _git("init", "--quiet", cwd=part)
            _git("remote", "add", "origin", src.url, cwd=part)
            _git("fetch", "--quiet", "--depth", "1", "origin", src.commit, cwd=part)
            _git("checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=part)
        head = _git_head(part)
        if head != src.commit:
            raise FetchError(f"{src.name}: checked out {head}, pinned {src.commit}")
    except BaseException:
        shutil.rmtree(part, ignore_errors=True)
        raise
    os.replace(part, target)
    return target


# --------------------------------------------------------------------------- API


def fetch_source(src: Source, root: str | Path | None = None,
                 from_dirs: Sequence[str | Path] = (), verify: bool = False,
                 extract_zip: bool | None = None, quiet: bool = False,
                 offline: bool = False) -> Path:
    """Fetch (or copy in) and verify one source; return its path in the cache.

    ``from_dirs`` are searched first (the file by name, or a git clone by repo name, up
    to four levels deep); what is found there is verified exactly like a download. With
    ``offline=True`` nothing is downloaded: a source not found locally is an error.
    """
    base = cache_root(root)
    dirs = [Path(d) for d in from_dirs]
    if src.kind == "git":
        return _fetch_git(src, base, dirs, quiet, offline)
    path = _fetch_file(src, base, dirs, verify, quiet, offline)
    if src.extract if extract_zip is None else extract_zip:
        extract(src, base, quiet)
    return path


def ensure(name: str, root: str | Path | None = None,
           from_dirs: Sequence[str | Path] = (), quiet: bool = True) -> Path:
    """The verified local path of source ``name``, fetching it first if needed."""
    return fetch_source(get_source(name), root, from_dirs, quiet=quiet)


def ensure_extracted(name: str, root: str | Path | None = None,
                     from_dirs: Sequence[str | Path] = (), quiet: bool = True) -> Path:
    """The extracted directory of zip source ``name`` (fetching and extracting if needed)."""
    src = get_source(name)
    fetch_source(src, root, from_dirs, extract_zip=False, quiet=quiet)
    return extract(src, cache_root(root), quiet)


def require(name: str, root: str | Path | None = None) -> Path:
    """The verified local path of source ``name`` WITHOUT any network access.

    Raises ``FetchError`` naming the command to run when the source is not present.
    Analyses call this, so they never download anything implicitly.
    """
    src = get_source(name)
    base = cache_root(root)
    target = base / src.path
    if not target.exists():
        raise FetchError(f"{name}: not in the cache ({target}). Run: consilience-ai2 fetch {name}")
    if src.kind == "git":
        head = _git_head(target)
        if head != src.commit:
            raise FetchError(f"{name}: {target} is at {head}, pinned {src.commit}")
        return target
    if not _stamp_ok(target, src):
        _check_file(target, src)
        _stamp(target, src)
    return target


def status(src: Source, root: str | Path | None = None) -> str:
    """``ok``, ``missing``, ``mismatch`` or ``unverified`` (present but never verified)."""
    base = cache_root(root)
    target = base / src.path
    if not target.exists():
        return "missing"
    if src.kind == "git":
        return "ok" if _git_head(target) == src.commit else "mismatch"
    return "ok" if _stamp_ok(target, src) else "unverified"
