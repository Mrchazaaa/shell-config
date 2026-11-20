# Resolve the Python entry point when sourced, not from the caller's directory.
_STARTTMUX_SCRIPT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)/starttmux.py"

starttmux() {
    local python
    if command -v python3 >/dev/null 2>&1; then
        python=python3
    elif command -v python >/dev/null 2>&1; then
        python=python
    else
        printf 'starttmux requires Python 3.8 or newer. Install Python and try again.\n' >&2
        return 1
    fi
    # Also support a non-exported shell variable, as the original function did.
    STARTTMUX_CONFIG="${STARTTMUX_CONFIG:-}" "$python" "$_STARTTMUX_SCRIPT" "$@"
}
