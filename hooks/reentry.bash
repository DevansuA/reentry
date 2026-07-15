# ReEntry bash shell hook
#
# Opt-in capture of command, exit code, and duration. No output is captured
# by default. Redaction runs inside the Python helper before the spool write.
#
# Install: add to ~/.bashrc or ~/.bash_profile
#   source /path/to/reentry/hooks/reentry.bash
#
# Or use:
#   reentry hook install --shell bash
#
# Uninstall: remove the source line.

_reentry_prompt_command() {
    local exit_code=$?
    if [[ -n "${_REENTRY_CMD:-}" ]]; then
        local dur=$(( SECONDS - ${_REENTRY_CMD_START:-$SECONDS} ))
        python3 -m reentry.connectors.terminal spool-write \
            "$_REENTRY_CMD" "$exit_code" "$dur" 2>/dev/null || true
        unset _REENTRY_CMD _REENTRY_CMD_START
    fi
}

_reentry_debug_trap() {
    # Avoid recording our own PROMPT_COMMAND invocation.
    if [[ "${BASH_COMMAND}" != "_reentry_prompt_command"* ]] && \
       [[ "${BASH_COMMAND}" != "_reentry_debug_trap"* ]]; then
        _REENTRY_CMD="${BASH_COMMAND}"
        _REENTRY_CMD_START=$SECONDS
    fi
}

trap '_reentry_debug_trap' DEBUG

# Prepend to PROMPT_COMMAND to run before any user-defined prompt hooks.
if [[ "${PROMPT_COMMAND}" != *"_reentry_prompt_command"* ]]; then
    PROMPT_COMMAND="_reentry_prompt_command${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi
