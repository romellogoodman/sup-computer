#!/bin/sh
# Vercel build only (installCommand): drop the onnxruntime-node binaries for
# platforms the API functions never run on. The package ships every platform
# (258 MB); the function bundle limit is 250 MB, and the file tracer includes
# the whole package once it sees the native binding. Linux-only so a local
# `vercel build` on a Mac keeps its own binaries. See ADR-0036.
[ "$(uname)" = "Linux" ] || exit 0
for dir in node_modules/onnxruntime-node/bin/napi-v6/darwin node_modules/onnxruntime-node/bin/napi-v6/win32; do
  rm -rf "$dir"
done
du -sh node_modules/onnxruntime-node 2>/dev/null || true
