#!/bin/bash
# Read the IAM principal allowlist that gates access to the app through the auth sidecar.
#
#   sudo sh get-allowlist.sh users   # -> comma-separated IAM user names   (jd users list)
#   sudo sh get-allowlist.sh teams   # -> comma-separated IAM role names   (jd teams list)
#
# `teams` maps to the [roles] section (IAM roles), `users` to the [users] section (IAM users).
# The source of truth is /etc/AUTH_ALLOWLIST (see update-allowlist.sh). This is a query command:
# retrieving an empty list still exits 0.
set -e

LOG_FILE="/var/log/jupyter-deploy/get-allowlist.log"
touch "$LOG_FILE"
exec 2> >(tee -a "$LOG_FILE" >&2)

ALLOWLIST_FILE="/etc/AUTH_ALLOWLIST"
CATEGORY=$1

log_message() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] $*" >> "$LOG_FILE"
}

get_section_content() {
  local section=$1
  sed -n "/^\[$section\]$/,/^\[/p" "$ALLOWLIST_FILE" 2>/dev/null | grep -v "^\[$section\]$" | grep -v "^\[" | tr -d '\n' | tr -d ' '
}

case "$CATEGORY" in
  users) SECTION="users" ;;
  teams) SECTION="roles" ;;
  *)
    echo "Error: invalid category '$CATEGORY'. Use 'users' or 'teams'."
    exit 1
    ;;
esac

CONTENT=$(get_section_content "$SECTION")
log_message "Response [$SECTION]: $CONTENT"
echo "$CONTENT"
