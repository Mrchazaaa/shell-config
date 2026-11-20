"""Cross-platform project sessions using tmux (Linux/Android) or psmux (Windows)."""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class Session:
    name: str
    directory: Path


def expand_directory(value):
    # Expand only home prefixes, never shell expressions or arbitrary variables.
    if value in ("~", "$HOME"):
        return Path.home()
    for prefix in ("~/", "~\\", "$HOME/", "$HOME\\"):
        if value.startswith(prefix):
            return Path.home() / value[len(prefix):]
    return Path(value)


def read_sessions(config):
    # utf-8-sig also accepts JSON saved with a BOM by Windows editors.
    with config.open(encoding="utf-8-sig") as stream:
        data = json.load(stream)
    if not isinstance(data, list) or not data:
        raise ValueError("Expected a nonempty array of sessions")
    sessions = []
    names = set()
    for index, entry in enumerate(data, 1):
        if not isinstance(entry, dict):
            raise ValueError(f"Session {index} must be an object")
        name, directory = entry.get("name"), entry.get("directory")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError(f"Session {index}: name must contain only letters, numbers, underscores, or hyphens")
        if name in names:
            raise ValueError(f"Duplicate session name: {name}")
        if not isinstance(directory, str) or not directory or any(c in directory for c in "\r\n\0"):
            raise ValueError(f"Session {name}: directory must be a nonempty, single-line path")
        names.add(name)
        sessions.append(Session(name, expand_directory(directory)))
    return sessions


class TmuxBackend:
    command = "tmux"

    def __init__(self):
        self.executable = shutil.which(self.command)
        if self.executable is None:
            raise ValueError(f"{self.command} is required; install it and add it to PATH")

    def validate_session(self, session):
        pass

    def session_exists(self, name):
        result = subprocess.run(
            [self.executable, "has-session", "-t", f"={name}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, errors="replace",
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(f"{self.command} has-session failed: {result.stderr.strip()}")
        return result.returncode == 0

    def create_session(self, session):
        subprocess.run(
            [self.executable, "new-session", "-d", "-s", session.name,
             "-c", str(session.directory.resolve())],
            check=True,
        )

    def attach_session(self, name):
        # Both tmux and psmux set TMUX in their panes. Inherit terminal streams
        # for interactive attachment; do not capture output or impose a timeout.
        command = "switch-client" if os.environ.get("TMUX") else "attach-session"
        subprocess.run([self.executable, command, "-t", f"={name}"], check=True)


class PsmuxBackend(TmuxBackend):
    command = "psmux"

    def validate_session(self, session):
        # psmux reserves this separator for server namespaces on disk.
        if "__" in session.name:
            raise ValueError(f"psmux session names cannot contain '__': {session.name}")


def get_backend():
    if sys.platform == "win32":
        return PsmuxBackend()
    if sys.platform.startswith("linux") or sys.platform == "android":
        return TmuxBackend()
    raise ValueError(f"Unsupported platform: {sys.platform}")


def start_sessions(sessions, backend, preferred=None):
    # Preflight every new session before creating any of them. Existing sessions
    # remain usable even if their original starting directory has been removed.
    for session in sessions:
        backend.validate_session(session)
    missing = [s for s in sessions if not backend.session_exists(s.name)]
    for session in missing:
        if not session.directory.is_dir():
            raise ValueError(f"Session {session.name}: directory does not exist: {session.directory}")
    for session in missing:
        backend.create_session(session)
    target = sessions[0].name
    if preferred and backend.session_exists(preferred):
        target = preferred
    backend.attach_session(target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", nargs="?", help="preferred existing session (exact name)")
    parser.add_argument(
        "--config", type=Path,
        default=Path(os.environ.get("STARTTMUX_CONFIG") or Path(__file__).resolve().parent.parent / "sessions.json"),
        help="sessions JSON file (default: STARTTMUX_CONFIG or repository-root sessions.json)",
    )
    args = parser.parse_args(argv)
    try:
        sessions = read_sessions(args.config.expanduser())
        start_sessions(sessions, get_backend(), args.session)
    except subprocess.CalledProcessError as error:
        print(f"starttmux: {Path(error.cmd[0]).name} {error.cmd[1]} failed (exit {error.returncode})", file=sys.stderr)
        return error.returncode if error.returncode > 0 else 128 - error.returncode
    except (OSError, ValueError, RuntimeError) as error:
        print(f"starttmux: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
