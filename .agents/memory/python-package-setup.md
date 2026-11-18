---
name: Python package setup
description: Python runtime and dependency installation behavior in this Replit workspace.
---

Use a Replit Python Tools module before installing Python packages. The base-only Python 3.13 runtime had no usable pip and rejected package installation as externally managed; adding the Python Tools module enabled package-managed installs.

**Why:** Bypassing the system-managed Python environment risks modifying the immutable Nix store.

**How to apply:** For future Python dependencies here, use Replit's package-management flow and keep dependencies in `requirements.txt`; do not force pip into the base-only interpreter.
