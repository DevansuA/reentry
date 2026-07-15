# ReEntry zsh shell hook
#
# Opt-in capture of command, exit code, and duration. Full output capture is
# NOT done by default; contents of stdout/stderr are never recorded here.
# Redaction runs before the spool write (inside the Python helper).
#
# Install: add to ~/.zshrc
#   source /path/to/reentry/hooks/reentry.zsh
#
# Or use the managed install:
#   reentry hook install --shell zsh
#
# Uninstall: remove the source line from ~/.zshrc.

_reentry_preexec() {
    # $1 is the command string as typed.
    _REENTRY_CMD="$1"
    _REENTRY_CMD_START="${EPOCHSECONDS:-$SECONDS}"
}

_reentry_precmd() {
    local exit_code=$?
    if [[ -n "${_REENTRY_CMD:-}" ]]; then
        local now="${EPOCHSECONDS:-$SECONDS}"
        local dur=$(( now - ${_REENTRY_CMD_START:-$now} ))
        # Run the spool write silently; if Python is unavailable, skip.
        command python3 -m reentry.connectors.terminal spool-write \
            "$_REENTRY_CMD" "$exit_code" "$dur" 2>/dev/null || true
        unset _REENTRY_CMD _REENTRY_CMD_START
    fi
}

autoload -Uz add-zsh-hook
add-zsh-hook preexec _reentry_preexec
add-zsh-hook precmd _reentry_precmd
