# Dependencies & asset-license inventory (G13 node 7)

Emberglow Hollow is Linux-first and dependency-minimal. This file is the
complete inventory of runtime dependencies and asset licenses for the
distributed game.

## Runtime dependencies

| Package          | Version | License                   | Purpose                 |
|------------------|---------|---------------------------|-------------------------|
| pygame-ce        | 2.5.8   | LGPL-2.1 (or later)       | Rendering, input, audio |
| CPython (Python) | 3.10+   | PSF-2.0                   | Language runtime        |

pygame-ce 2.5.8 ships prebuilt manylinux wheels for CPython 3.10 through 3.15
on x86_64 (and aarch64); it is the only third-party package, and it is the only
line in requirements.txt. No other pip dependency is declared.

## Asset inventory (all code-driven, no asset files)

There are no image, audio, or font files in this distribution. Every sprite,
tile, prop, character, lighting effect, and interface element is generated
deterministically in code at runtime:

- Sprites / tiles / props / characters: emberglow/sprites.py
- Locked palette + cohesion rules:      emberglow/palette.py
- Shared value-noise seed:              emberglow/noise.py
- Scene composition:                    emberglow/scene.py
- Interface treatment:                  emberglow/ui.py
- Animation:                            emberglow/animation.py

Because there are no third-party asset files, the asset-license surface is
empty: nothing is redistributed from an external source, so no asset license
applies. Text rendering uses pygame's bundled default font (part of pygame-ce,
covered by its license).

## Third-party licenses

- pygame-ce is distributed under the GNU Lesser General Public License v2.1 or
  later (LGPL-2.1+). Source: https://github.com/pygame-community/pygame-ce
- CPython is distributed under the Python Software Foundation License v2
  (PSF-2.0). Source: https://www.python.org/psf/license/

The game's own code (emberglow/, tests/, tools/, docs/) is original work of the
G13 project; a project license has not yet been chosen (pending Rick's
decision).

## Verified clean-room install (node 7)

A fresh disposable clone was installed and verified end-to-end:

    git clone git@github.com:rickseeger/ai-game-06.git
    cd ai-game-06
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python -m emberglow.main --headless     # writes evidence/scene_gate.png
    .venv/bin/python -m unittest discover -s tests    # 144 tests, OK
    .venv/bin/python -m emberglow.main --check        # all render checks ok=true

Verified on CPython 3.14.4 and 3.12.14 (both have pygame-ce 2.5.8 wheels).
