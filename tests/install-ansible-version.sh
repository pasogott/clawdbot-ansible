#!/usr/bin/env bash
# Drive install.sh with a mocked ansible-playbook so old controllers fail
# closed and ansible-core 2.14+ is accepted.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SH="${ROOT}/install.sh"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/openclaw-ansible-ver.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

BIN="${WORKDIR}/bin"
mkdir -p "$BIN"

failures=0

write_exec() {
    local path="$1"
    cat >"$path"
    chmod +x "$path"
}

write_ansible_playbook() {
    local version_banner="$1"
    write_exec "${BIN}/ansible-playbook" <<EOF
#!/usr/bin/env bash
if [[ " \$* " == *" --version "* ]] || [[ "\$1" == "--version" ]]; then
    printf '%s\n' $(printf '%q' "$version_banner")
    printf '  config file = None\n'
    exit 0
fi
printf 'playbook invoked: %s\n' "\$*"
exit 0
EOF
}

write_support_bins() {
    write_exec "${BIN}/apt-get" <<'EOF'
#!/usr/bin/env bash
printf 'unexpected apt-get: %s\n' "$*" >&2
exit 42
EOF
    write_exec "${BIN}/sudo" <<'EOF'
#!/usr/bin/env bash
exec "$@"
EOF
    write_exec "${BIN}/ansible-galaxy" <<'EOF'
#!/usr/bin/env bash
printf 'galaxy mocked: %s\n' "$*"
exit 0
EOF
}

run_install() {
    local banner="$1"
    write_support_bins
    write_ansible_playbook "$banner"
    env -u ANSIBLE_EXTRA_VARS \
        PATH="${BIN}:${PATH}" \
        bash "$INSTALL_SH" 2>&1
}

expect_reject() {
    local name="$1"
    local banner="$2"
    local out rc
    set +e
    out="$(run_install "$banner")"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        printf 'FAIL %s: expected install.sh to reject %s (exit 0)\n' "$name" "$banner" >&2
        printf '%s\n' "$out" >&2
        failures=$((failures + 1))
        return
    fi
    if ! printf '%s\n' "$out" | grep -q 'ansible-core 2.14'; then
        printf 'FAIL %s: missing ansible-core 2.14 error\n' "$name" >&2
        printf '%s\n' "$out" >&2
        failures=$((failures + 1))
        return
    fi
    if printf '%s\n' "$out" | grep -q 'playbook invoked:'; then
        printf 'FAIL %s: playbook ran after version reject\n' "$name" >&2
        printf '%s\n' "$out" >&2
        failures=$((failures + 1))
        return
    fi
    printf 'OK   %s (exit %s)\n' "$name" "$rc"
}

expect_accept() {
    local name="$1"
    local banner="$2"
    local out rc
    set +e
    out="$(run_install "$banner")"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        printf 'FAIL %s: expected install.sh to accept %s (exit %s)\n' "$name" "$banner" "$rc" >&2
        printf '%s\n' "$out" >&2
        failures=$((failures + 1))
        return
    fi
    if ! printf '%s\n' "$out" | grep -q 'playbook invoked:'; then
        printf 'FAIL %s: playbook did not run after version accept\n' "$name" >&2
        printf '%s\n' "$out" >&2
        failures=$((failures + 1))
        return
    fi
    printf 'OK   %s (exit %s)\n' "$name" "$rc"
}

expect_reject "ubuntu-2204-ansible-2.10" "ansible-playbook 2.10.8"
expect_reject "ubuntu-2204-core-2.12" "ansible-playbook [core 2.12.0]"
expect_reject "debian-11-ansible-2.10" "ansible-playbook 2.10.17"
expect_reject "unparseable-banner" "ansible-playbook (devel build)"
expect_accept "exact-core-2.14.0" "ansible-playbook [core 2.14.0]"
expect_accept "ubuntu-2404-core-2.16" "ansible-playbook [core 2.16.3]"

if [ "$failures" -ne 0 ]; then
    printf '\n%s check(s) failed\n' "$failures" >&2
    exit 1
fi

printf '\nAll ansible-playbook version checks passed\n'
