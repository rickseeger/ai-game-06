"""Emberglow Hollow -- fixed-isometric (2.5D) visual foundation.

Node 2 of G13: the reusable rendering foundation (palette, noise, geometry,
procedural sprites, scene graph, UI) plus one representative art-complete scene
(the Hollow Gate room). Owns rendering and artistic coherence -- not navigation
or quest logic.

Everything is code-driven and deterministic given the shared noise seed, so a
frame is byte-reproducible and verifiable by code-level pixel sampling (no vision).
"""
__version__ = "0.2.0"
