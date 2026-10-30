#!/usr/bin/env sh

# TODO(XCPNG-3032): Delete this script and the compatibility archive once support for XCP-ng 8.3 has ended.

# Build `site36.tar.gz`: the Python 3.6 packages needed to run the tests on XCP-ng 8.3, whose Python 3.6 has no
# usable pytest, and a `cryptography` too old for the TLS tests.

set -eu

script_dir_path=$(cd "$(dirname "$0")" && pwd)
build_dir_path=$(mktemp -d)
trap 'rm -rf "$build_dir_path"' EXIT

# manylinux2014_x86_64 => https://peps.python.org/pep-0599/ (Base for CentOS 7)
pip install \
  --target "$build_dir_path/site36" \
  --python-version 3.6 \
  --implementation cp \
  --abi cp36m \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --no-compile \
  'pytest==7.0.1' \
  'importlib_metadata' \
  'cryptography==40.0.2'

# Always create the same archive if pip params are not modified.
tar \
  --sort=name \
  --mtime=@0 \
  --owner=0 \
  --group=0 \
  --numeric-owner \
  -C "$build_dir_path" \
  -cf - site36 | gzip -n > "$script_dir_path/site36.tar.gz"
