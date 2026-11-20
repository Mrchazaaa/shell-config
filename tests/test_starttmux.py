import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import starttmux


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / "sessions.json"

    def write(self, value):
        self.config.write_text(json.dumps(value), encoding="utf-8-sig")

    def test_home_prefixes_and_windows_drive_are_not_split(self):
        for value in ("~", "$HOME", "~/my projects", "$HOME/my projects"):
            with self.subTest(value=value):
                self.write([{"name": "dev", "directory": value}])
                expected = Path.home() / "my projects" if "/" in value else Path.home()
                self.assertEqual(starttmux.read_sessions(self.config)[0].directory, expected)
        self.write([{"name": "dev", "directory": "C:/Users/Alex/my projects"}])
        self.assertEqual(starttmux.read_sessions(self.config)[0].directory,
                         Path("C:/Users/Alex/my projects"))

    def test_invalid_configuration_is_rejected(self):
        good = {"name": "dev", "directory": "."}
        for value in ([], {}, [None], [good, good],
                      [{"name": "bad.name", "directory": "."}],
                      [{"name": "dev", "directory": "bad\npath"}],
                      [{"name": "dev", "directory": "bad\0path"}],
                      [{"name": "dev", "directory": 123}]):
            with self.subTest(value=value):
                self.write(value)
                with self.assertRaises(ValueError):
                    starttmux.read_sessions(self.config)

    def test_bad_json_reports_error_without_starting_backend(self):
        self.config.write_text("{broken", encoding="utf-8")
        with patch("starttmux.get_backend") as backend, contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(starttmux.main(["--config", str(self.config)]), 1)
        backend.assert_not_called()
        self.assertIn("starttmux:", error.getvalue())

    def test_config_option_overrides_environment(self):
        self.write([{"name": "dev", "directory": "."}])
        with patch.dict(os.environ, {"STARTTMUX_CONFIG": "missing.json"}), \
                patch("starttmux.get_backend"), patch("starttmux.start_sessions") as start:
            self.assertEqual(starttmux.main(["--config", str(self.config), "preferred"]), 0)
        self.assertEqual(start.call_args.args[0][0].name, "dev")
        self.assertEqual(start.call_args.args[2], "preferred")


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.sessions = [starttmux.Session("first", self.directory),
                         starttmux.Session("second", self.directory)]
        self.backend = Mock()

    def test_reuses_existing_and_creates_missing_before_attach(self):
        self.backend.session_exists.side_effect = lambda name: name == "first"
        starttmux.start_sessions(self.sessions, self.backend)
        self.backend.create_session.assert_called_once_with(self.sessions[1])
        self.backend.attach_session.assert_called_once_with("first")

    def test_preferred_external_session_and_missing_fallback(self):
        for preferred, exists, target in (("external", True, "external"),
                                           ("missing", False, "first")):
            with self.subTest(preferred=preferred):
                backend = Mock()
                backend.session_exists.side_effect = lambda name: exists if name == preferred else True
                starttmux.start_sessions(self.sessions, backend, preferred)
                backend.attach_session.assert_called_once_with(target)

    def test_missing_directory_prevents_partial_creation(self):
        self.backend.session_exists.return_value = False
        sessions = self.sessions + [starttmux.Session("bad", self.directory / "missing")]
        with self.assertRaisesRegex(ValueError, "directory does not exist"):
            starttmux.start_sessions(sessions, self.backend)
        self.backend.create_session.assert_not_called()
        self.backend.attach_session.assert_not_called()

    def test_existing_session_does_not_require_original_directory(self):
        self.backend.session_exists.return_value = True
        starttmux.start_sessions([starttmux.Session("existing", self.directory / "gone")], self.backend)
        self.backend.create_session.assert_not_called()
        self.backend.attach_session.assert_called_once_with("existing")

    def test_creation_failure_prevents_attach(self):
        self.backend.session_exists.return_value = False
        self.backend.create_session.side_effect = subprocess.CalledProcessError(2, ["tmux", "new-session"])
        with self.assertRaises(subprocess.CalledProcessError):
            starttmux.start_sessions(self.sessions, self.backend)
        self.backend.attach_session.assert_not_called()


class BackendTests(unittest.TestCase):
    def test_platform_selection_and_missing_dependency(self):
        for platform, command in (("linux", "tmux"), ("android", "tmux"), ("win32", "psmux")):
            with self.subTest(platform=platform), patch("starttmux.sys.platform", platform), \
                    patch("starttmux.shutil.which", return_value=command) as which:
                self.assertEqual(starttmux.get_backend().command, command)
                which.assert_called_once_with(command)
        with patch("starttmux.shutil.which", return_value=None):
            with self.assertRaisesRegex(ValueError, "install it"):
                starttmux.TmuxBackend()

    def test_backend_arguments_and_interactive_streams(self):
        for cls in (starttmux.TmuxBackend, starttmux.PsmuxBackend):
            with self.subTest(backend=cls.command), \
                    patch("starttmux.shutil.which", return_value=cls.command), \
                    patch("starttmux.subprocess.run") as run:
                backend = cls()
                run.return_value.returncode = 0
                self.assertTrue(backend.session_exists("work"))
                self.assertEqual(run.call_args.args[0], [cls.command, "has-session", "-t", "=work"])
                session = starttmux.Session("work", Path("project with spaces"))
                backend.create_session(session)
                run.assert_called_with([cls.command, "new-session", "-d", "-s", "work",
                                        "-c", str(session.directory.resolve())], check=True)
                for inside, command in (("", "attach-session"), ("socket,123,0", "switch-client")):
                    with patch.dict(os.environ, {"TMUX": inside}):
                        backend.attach_session("work")
                    run.assert_called_with([cls.command, command, "-t", "=work"], check=True)

    def test_query_failure_is_not_treated_as_absent_session(self):
        with patch("starttmux.shutil.which", return_value="tmux"), \
                patch("starttmux.subprocess.run") as run:
            backend = starttmux.TmuxBackend()
            run.return_value.returncode = 1
            self.assertFalse(backend.session_exists("work"))
            run.return_value.returncode = 2
            run.return_value.stderr = "invalid option"
            with self.assertRaisesRegex(RuntimeError, "invalid option"):
                backend.session_exists("work")

    def test_psmux_namespace_separator_is_rejected(self):
        with patch("starttmux.shutil.which", return_value="psmux"):
            with self.assertRaisesRegex(ValueError, "cannot contain"):
                starttmux.PsmuxBackend().validate_session(starttmux.Session("a__b", Path(".")))


if __name__ == "__main__":
    unittest.main()
