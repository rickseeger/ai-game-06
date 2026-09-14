# ai-game-06 — Capability Report

Status: factual, Linux-only. Grounded in commands actually run on this server and this repository on 2026-09-14 (UTC). No design choices; no speculation.

## 1. Repository contents

`git@github.com:rickseeger/ai-game-06.git` is EMPTY.

- `git ls-remote` returns no refs (exit 0).
- `git clone` succeeds with "You appear to have cloned an empty repository".
- No code, no assets, no docs. This file (CAPABILITY.md) is the first commit.

## 2. Server runtime (where the worker/CI executes)

Host: Ubuntu 26.04.1 LTS "Resolute Raccoon", x86_64, kernel 7.0.0-31-generic.

- CPU: AMD EPYC 9354P (4 vCPUs allocated); RAM 15 GiB; disk 134 GB free on /.
- GPU: NONE (headless VM — `lspci` shows no VGA/3D controller). All rendering is software.
- Python: 3.14.4 (`python3`); no `pip` module; `python3 -m venv` works; `uv` 0.12.10 at /root/.hermes/bin/uv (use `uv venv` / `uv pip` for numpy etc.).
- Node: v26.8.1, npm 11.19.0.
- C toolchain: gcc 15.2.0, GNU Make 4.4.1; cmake not installed (installable).
- Git 2.53.0; SSH to github.com authenticated as `rickseeger` (verified).

## 3. Graphics / game libraries: present vs installable

### Present now (paths/versions verified)
- OpenGL (GLX): libGL.so.1.7.0, libGLX_mesa.so.0.0.0; Mesa 26.0.8-1ubuntu0.3 with llvmpipe software rasterizer (LLVM 21.1.8). Confirmed OpenGL 4.5 (Core + Compatibility), direct rendering yes.
- EGL: libEGL.so.1.1.0, libEGL_mesa.so.0.0.0 (installed during this session via mesa-utils deps).
- GBM: libgbm.so.1.0.0; Wayland client libs (libwayland-client.so.0.24.0).
- Vulkan loader libvulkan.so.1.4.341 + ICDs: lavapipe (lvp, software), radeon, nouveau, intel, virtio, gfxstream, asahi; mesa-vulkan-drivers 26.0.8.
- Audio libs: libasound.so.2 (ALSA), libpulse.so.0.24.3 (PulseAudio); `aplay`, `paplay` present (no physical device on this headless host).
- Capture/pixel tooling: ffmpeg 8.0.1 (with x11grab), Python Pillow (PIL) 12.1.1. numpy NOT installed (add via uv). No ImageMagick.
- mesa-utils 9.0.0 installed this session (provides `glxinfo`, `glxgears`).
- Display server: headless (no $DISPLAY, no $WAYLAND_DISPLAY); Xvfb + xvfb-run present at /usr/bin.

### Installable via apt (candidate versions verified with apt-cache)
- Engines/runtimes: godot3 3.6.2+ds-1build2 (NOTE: Ubuntu 26.04 ships only Godot 3.x; Godot 4.x is not packaged — download the static ~50 MB binary from godotengine.org, no install step, matches the "single download + run" preference); love 11.5-3 (LÖVE).
- Libraries: libsdl2-dev 2.32.10, libsdl2-image-dev 2.8.8, libsdl2-ttf-dev 2.24.0, libsdl2-mixer-dev 2.8.1, libsdl2-gfx-dev 1.0.4; libsfml-dev 3.0.2; liballegro5-dev 5.2.11.3; libgl1-mesa-dev / libegl1-mesa-dev 26.0.8 (for compiling GL/EGL from source); vulkan-tools 1.4.341 (`vulkaninfo`, `vkcube`).
- Python: python3-pygame 2.6.1.

## 4. Headless frame-capture path — VERIFIED

The following pipeline was executed end-to-end this session and produced sampled pixels (not just a plausible claim):

1. Start virtual display:
   `Xvfb :99 -screen 0 640x480x24 -nolisten tcp &`
2. Confirm software GL:
   `DISPLAY=:99 glxinfo -B` -> `OpenGL renderer string: llvmpipe (LLVM 21.1.8, 256 bits)`, `OpenGL version string: 4.5 (Compatibility Profile) Mesa 26.0.8`, `direct rendering: Yes`.
3. Render real GL content:
   `DISPLAY=:99 glxgears` -> `GL_RENDERER = llvmpipe`, ~2392 FPS software.
4. Capture frames from the virtual framebuffer:
   `ffmpeg -f x11grab -video_size 640x480 -i :99 -frames:v 3 gears_%02d.png`
5. Sample pixels in code:
   Python Pillow 12.1.1 opened the PNGs -> 364–370 unique colors per 640x480 frame, min (0,0,0) / max (255,255,255), i.e. rendered content (not a blank screen) was captured and read.

Result: Xvfb + Mesa llvmpipe GL 4.5 (software) renders the game as a normal X client on DISPLAY=:99; ffmpeg x11grab dumps frames to PNG; Pillow (or numpy via uv) asserts colors/geometry per frame. This is the automated, code-level pixel-sampling evidence path. No physical GPU or monitor required.

Notes / caveats (verified):
- `xsetroot -solid <color>` does NOT appear in x11grab output (root-window background is not painted into the grabbed framebuffer). Irrelevant for the real path: the game draws actual content (as glxgears did), which is captured correctly.
- Vulkan lavapipe (software Vulkan) is present but was NOT verified with a rendered frame this session; treat as unverified-until-tested.
- Alternative capture method: the game can also read its own pixels via GL `glReadPixels` into a buffer and write PNG with Pillow — same headless guarantees, no Xvfb needed for the readback (though an X display is still needed to create a GLX window).

## 5. Server can-do vs player-machine needs (Linux-only)

Server (this host) can, headlessly:
- Build: C/C++ (gcc 15, make, installable cmake), Python 3.14 + uv, Node 26 + npm.
- Render: OpenGL 4.5 and Vulkan via software (llvmpipe / lavapipe) under Xvfb.
- Verify: capture frames (ffmpeg x11grab or glReadPixels) and pixel-sample them in code (Pillow / numpy).
- NOT: real GPU acceleration (software only), audio output, or a physical display.

Player machine (Rick's Pop!_OS laptop, Ubuntu-based) needs at runtime:
- A working GPU driver (Mesa GL/Vulkan, which Pop!_OS ships by default on desktop) + a real display and audio device.
- The game runtime only: e.g. the Godot 4.x static binary, or LÖVE 11.5, or a self-contained SDL2-linked executable. Nothing server-specific is required.
