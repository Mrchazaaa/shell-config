# Cross-platform shell configuration

Personal shell configuration for Linux/Termux (Bash) and native Windows
(PowerShell). Session management lives in `starttmux.py`, using Python's standard
library to invoke tmux on Linux and psmux on Windows. No WSL or pip dependencies
are required. Shell loaders also provide Neovim profile shortcuts.

## Requirements

- Python 3.8 or newer (`python3` or `python` on Linux; `py -3` or `python` on Windows).
- tmux on Linux/Termux, or a current [psmux](https://github.com/psmux/psmux)
  installation on Windows, available on `PATH`.
- Git for installation; curl for the Bash download command.
- Neovim 0.9+ for the profile shortcuts, with your profile configurations installed
  separately. Native Windows Neovim normally uses `%LOCALAPPDATA%/nvim` instead
  of `~/.config/nvim`.

`jq` is no longer required. The installer sets up the loader; install dependencies
separately.

## Starting tmux

Run `starttmux` to create any missing sessions from `sessions.json` and focus the
first configured session. Pass an optional session name, such as
`starttmux "my-session"`, to focus that exact session if it exists after setup.
This also works for existing sessions outside the configuration. If no matching
session exists, the first configured session is focused as usual. Inside tmux,
the command switches the current client to the selected session. The same behavior
applies inside psmux, which also sets the `TMUX` environment variable.

```text
starttmux
starttmux personal-site
starttmux --config /path/to/sessions.json personal-site
```

You can also invoke the Python CLI directly, without loading shell configuration:

```bash
python3 ~/.config/bash-config/starttmux.py --help
```

```powershell
py -3 "$HOME/.config/bash-config/starttmux.py" --help
```

### Session configuration

Edit `sessions.json` to match your machine, or select another file with `--config`
or `STARTTMUX_CONFIG` (`--config` takes precedence):

```bash
export STARTTMUX_CONFIG="$HOME/.config/my-sessions.json"
```

```powershell
$env:STARTTMUX_CONFIG = "$HOME/.config/my-sessions.json"
```

The file is a nonempty JSON array:

```json
[
  { "name": "project", "directory": "~/projects/project" },
  { "name": "notes", "directory": "~/notes" }
]
```

Windows absolute paths can use forward slashes, such as `C:/Users/Alex/projects`,
or escaped backslashes (`C:\\Users\\Alex\\projects`). Leading `~` and `$HOME`
prefixes are expanded without evaluating shell code. Relative directories resolve
against the directory from which you run the command.

Names must be unique and contain only letters, numbers, underscores, or hyphens.
psmux additionally reserves `__` for namespaces. Configuration and directories
needed for new sessions are checked before any sessions are created. Existing
sessions are reused even if their original directory no longer exists.

The backends use `has-session`, `new-session -d -s ... -c ...`, `attach-session`,
and `switch-client`, with `=name` exact targets. Install a current psmux release
supporting these tmux-compatible commands.

## Installation

### Linux / Termux

For example, on Debian/Ubuntu:

```bash
sudo apt install python3 tmux git curl neovim
```

On Termux:

```bash
pkg install python tmux git curl neovim
```

Run the installer with Bash (requires `curl` and `git`):

```bash
curl -fsSL https://raw.githubusercontent.com/Mrchazaaa/bash-config/master/install.sh | bash
```

This clones the repository into `~/.config/bash-config` and adds its loader to
`~/.bashrc`. Re-running the installer reuses an existing checkout without updating
it and avoids adding the same loader line twice. An unrelated directory at the
installation path is left untouched and causes the installer to stop.

Open a new Bash shell or run `source ~/.bashrc` to load the configuration.

You can also run `bash install.sh` from a local copy of the repository.

### Windows (native PowerShell)

Install Python 3.8+, Git, and psmux, and optionally Neovim. For example, psmux is
available through WinGet:

```powershell
winget install psmux
```

Clone the repository, then run its PowerShell installer:

```powershell
git clone https://github.com/Mrchazaaa/bash-config.git "$HOME/.config/bash-config"
& "$HOME/.config/bash-config/install.ps1"
. $PROFILE
```

For an existing checkout, run `install.ps1` directly. It adds a loader to the
current PowerShell host's `$PROFILE`, creates the profile directory if necessary,
and avoids duplicate loader lines. Like the Bash installer, it reuses an existing
checkout without updating it and rejects an unrelated installation directory.

If local scripts are blocked by your execution policy, enable local scripts for
your user where permitted (for example, `Set-ExecutionPolicy -Scope CurrentUser
RemoteSigned`).

For manual loading, add this to `$PROFILE`:

```powershell
. (Join-Path $HOME '.config/bash-config/init.ps1')
```

Then use `starttmux`, `nvim-code`, `nvim-hemingway`, or `nvim-clean` directly in
PowerShell. Set `STARTTMUX_CONFIG` to a Windows-specific file if your project
directories differ between machines.

### Manual Bash installation

1. Clone this repository into `~/.config/bash-config`:

   ```bash
   mkdir -p ~/.config
   git clone https://github.com/Mrchazaaa/bash-config.git ~/.config/bash-config
   ```

2. Open `~/.bashrc` in your preferred editor and add the following line at the end:

   ```bash
   source "$HOME/.config/bash-config/init.sh"
   ```

   Or append it with this one-liner:

   ```bash
   printf '\n%s\n' 'source "$HOME/.config/bash-config/init.sh"' >> ~/.bashrc
   ```

3. Reload your Bash configuration to apply the changes to your current shell:

   ```bash
   source ~/.bashrc
   ```

   New interactive Bash shells will load the configuration automatically.

## Development

### Project layout

The root `init.sh` and `init.ps1` loaders source shell-specific modules:

```text
shell/
  bash/
    tmux.sh
    neovim.sh
  powershell/
    tmux.ps1
    neovim.ps1
```

Add shell helpers to the appropriate directory and source them from its root
loader. Both shells share the root `starttmux.py` CLI and `sessions.json`
configuration. Installers remain at the root alongside the loaders.

### Tests

Run the standard-library tests from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

On Windows, use `py -3 -m unittest discover -s tests -v`. Tests cover shared
session behavior and subprocess arguments for both backends; interactive
attachment should also be checked with the actual multiplexer on each platform.
