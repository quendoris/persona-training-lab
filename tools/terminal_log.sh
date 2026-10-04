#!/usr/bin/env bash
set -u

if ! command -v script >/dev/null 2>&1; then
  printf '%s\n' "terminal_log: util-linux 'script' command is required." >&2
  exit 127
fi

repo_root="$(
  git rev-parse --show-toplevel 2>/dev/null || pwd
)"
head_sha="$(
  git -C "$repo_root" rev-parse HEAD 2>/dev/null || printf 'no-git-head'
)"
branch="$(
  git -C "$repo_root" branch --show-current 2>/dev/null || true
)"
if [[ -z "$branch" ]]; then
  branch="DETACHED"
fi

log_dir="${PTL_TERMINAL_LOG_DIR:-${TMPDIR:-/tmp}/persona-training-lab-terminal}"
mkdir -p "$log_dir"
log_file="$log_dir/$head_sha.log"
export PTL_TERMINAL_LOG_FILE="$log_file"

started_at="$(
  date -u '+%Y-%m-%dT%H:%M:%SZ'
)"

{
  printf '\n===== PTL TERMINAL SESSION START =====\n'
  printf 'started_at_utc=%s\n' "$started_at"
  printf 'repo_root=%s\n' "$repo_root"
  printf 'head=%s\n' "$head_sha"
  printf 'branch=%s\n' "$branch"
  printf 'cwd=%s\n' "$PWD"
  if (($# > 0)); then
    printf 'mode=command\n'
    printf 'argv='
    printf '%q ' "$@"
    printf '\n'
  else
    printf 'mode=interactive_shell\n'
  fi
  printf '======================================\n'
} >> "$log_file"

printf '[ptl-terminal-log] appending to %s\n' "$log_file" >&2
printf '[ptl-terminal-log] HEAD %s (%s)\n' "$head_sha" "$branch" >&2
if (($# == 0)); then
  printf '[ptl-terminal-log] interactive shell started; exit to stop capture.\n' >&2
fi

status=0
if (($# > 0)); then
  printf -v command_string '%q ' "$@"
  script --quiet --append --flush --return \
    --command "$command_string" "$log_file"
  status=$?
else
  script --quiet --append --flush --return "$log_file"
  status=$?
fi

finished_at="$(
  date -u '+%Y-%m-%dT%H:%M:%SZ'
)"
{
  printf '\n===== PTL TERMINAL SESSION END =====\n'
  printf 'finished_at_utc=%s\n' "$finished_at"
  printf 'exit_code=%s\n' "$status"
  printf '====================================\n'
} >> "$log_file"

printf '[ptl-terminal-log] capture ended with exit code %s\n' "$status" >&2
printf '[ptl-terminal-log] log: %s\n' "$log_file" >&2
exit "$status"
