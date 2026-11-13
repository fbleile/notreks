#!/usr/bin/env bash
set -euo pipefail

# Build the NOTREKS-enabled FLOP extension shipped with this repository. This
# is separate from `pip install flopsearch`: the public wheel currently
# contains vanilla FLOP but not the proposal-level NOTREKS API.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
SOURCE_DIR="$ROOT_DIR/vendor/flopsearch/flop_python"
MATURIN_BIN="${MATURIN_BIN:-}"
CARGO_BIN="${CARGO_BIN:-$(command -v cargo || true)}"

if [[ -z "$MATURIN_BIN" ]]; then
  MATURIN_BIN="$($PYTHON_BIN - <<'PY'
import shutil
print(shutil.which("maturin") or "")
PY
)"
fi

[[ -f "$SOURCE_DIR/pyproject.toml" ]] || {
  echo "missing vendored FLOP source: $SOURCE_DIR" >&2
  exit 2
}
[[ -n "$MATURIN_BIN" && -x "$MATURIN_BIN" ]] || {
  echo "maturin is required; install it with: $PYTHON_BIN -m pip install maturin" >&2
  exit 2
}
[[ -n "$CARGO_BIN" && -x "$CARGO_BIN" ]] || {
  echo "cargo is required to build the vendored FLOP extension" >&2
  exit 2
}

export PATH="$(dirname "$CARGO_BIN"):$PATH"
wheel_dir="$(mktemp -d)"
trap 'rm -rf "$wheel_dir"' EXIT

"$MATURIN_BIN" build --manifest-path "$SOURCE_DIR/Cargo.toml" \
  --interpreter "$PYTHON_BIN" --release --out "$wheel_dir"
"$PYTHON_BIN" -m pip install --no-deps "$wheel_dir"/*.whl

"$PYTHON_BIN" - <<'PY'
import flopsearch
if not callable(getattr(flopsearch, "flop_notreks", None)):
    raise SystemExit("built flopsearch does not expose flop_notreks")
print("FLOP+NOTREKS backend ready:", flopsearch.__file__)
PY
