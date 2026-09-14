# ai-game-06 -- G13 "Emberglow Hollow"

Fixed-isometric (2.5D) adventure game. Linux-only, art-direction-first.

## What is here

- DECISION.md -- implementation approach (engine/language + rendering pipeline + rationale)
- docs/ART_DIRECTIONS.md -- candidate art directions; "Emberglow Hollow" (option B) is locked
- CAPABILITY.md -- server runtime + graphics capability report
- spike/isometric_spike.py -- hello-world spike: renders an Emberglow Hollow isometric scene
- evidence/ -- captured frame (PNG) + automated verification output

## Install (one command)

    pip install -r spike/requirements.txt

## Run

    python3 spike/isometric_spike.py              # open a window (playtest)
    python3 spike/isometric_spike.py --headless   # save evidence/emberglow_spike.png
    python3 spike/isometric_spike.py --check      # render + run pixel-sampling assertions

Requires Python 3.10+ and pygame-ce 2.5.x. No other dependencies, no build step.
