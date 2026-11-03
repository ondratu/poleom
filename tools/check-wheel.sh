#!/bin/sh
# Check that the wheel contains everything the application needs to run and
# nothing it should not (editor backups).
set -eu

wheel=${1:?usage: check-wheel.sh WHEEL}
files=$(python3 -m zipfile -l "$wheel" | awk 'NR > 1 {print $1}')

rc=0
for required in \
    poleom/lib/core.py \
    poleom/templates/index.html \
    poleom/assets/css/poleom.css \
    poleom/mysql/init.sql \
    poleom/sqlite/init.sql \
    poleom/passwd_bcrypt.py \
    poleom/py.typed; do
  if ! echo "$files" | grep -qx "$required"; then
    echo "missing in the wheel: $required" >&2
    rc=1
  fi
done

if echo "$files" | grep -E '~$|\.orig$'; then
  echo "backup files in the wheel" >&2
  rc=1
fi

exit $rc
