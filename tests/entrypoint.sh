#!/usr/bin/env bash
set -euo pipefail

# Keep task-level become_user active so pnpm runs as the service user, not root.
PLAYBOOK_ARGS=(-e ci_test=true --connection=local)

# --- Step 1: Convergence ---
echo "===> Step 1: Convergence test"
ansible-playbook playbook.yml "${PLAYBOOK_ARGS[@]}"
echo "===> Convergence: PASSED"

# --- Step 2: Verification ---
echo "===> Step 2: Verification"
ansible-playbook tests/verify.yml "${PLAYBOOK_ARGS[@]}"
echo "===> Verification: PASSED"

# --- Step 3: Idempotency ---
echo "===> Step 3: Idempotency test"
IDEMPOTENCY_OUT=$(ansible-playbook playbook.yml "${PLAYBOOK_ARGS[@]}" 2>&1)
echo "$IDEMPOTENCY_OUT"

CHANGED=$(echo "$IDEMPOTENCY_OUT" | tail -n 5 | grep -oP 'changed=\K[0-9]+' | head -1)
if [ "${CHANGED:-1}" -eq 0 ]; then
  echo "===> Idempotency: PASSED (0 changed)"
else
  echo "===> Idempotency: FAILED (changed=$CHANGED)"
  exit 1
fi

echo ""
echo "===> All tests passed"
