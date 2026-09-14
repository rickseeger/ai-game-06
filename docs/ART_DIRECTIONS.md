# G13 — Candidate Art Directions

Status: PROPOSAL — awaiting human selection. This document presents three distinct,
fully-specified art directions for G13. The final direction is chosen by Rick (the
human), not by the worker; Rick's pick is recorded in the final section below as
G13's approved art direction.

## Purpose and constraints

G13 is an art-first, fixed-isometric (2.5D) adventure game. Node 0 sets the
centerpiece: vibrant, colorful, cohesive, visually appealing, and charming — with
classic adventure mechanics (exploration, items, interaction, progression).

Each candidate below is written so it can be implemented procedurally / code-driven
and later verified by code-level pixel sampling (workers have no reliable vision).
Every candidate therefore specifies:

  (a) a setting / world premise
  (b) a concrete visual language — exactly how a fixed-isometric scene is rendered
  (c) an explicit cohesive palette (named hex swatches + rationale)
  (d) cohesion rules (testable invariants)
  (e) 1-2 named reference touchstones

Common ground fixed by node 0 / node 1 (not re-decided here):

  - Fixed 2:1 isometric projection (diamond tiles), one camera, no rotation, no zoom.
  - Linux-only. Rendered on Mesa GL 4.5 (llvmpipe software rasterizer on the build
    server; a real GPU on Rick's Pop!_OS laptop). No image-generation or hand-drawn
    asset pipeline — all art is procedural/code-driven.
  - The existing progression skeleton (5 connected rooms, 11 actions, an item chain
    ending in lighting a beacon and calling a ferry — see node 1's world.json) is
    setting-agnostic and can be re-themed to any of the three worlds. Only room and
    object names and narrative dressing change.

## Summary table

  |              | A. Coralbright Atoll        | B. Emberglow Hollow          | C. Prismgrove                  |
  |--------------|-----------------------------|------------------------------|--------------------------------|
  | Setting      | tropical island harbor      | cozy autumnal hollow         | toybox candy-pixel grove       |
  | Visual lang. | flat-shaded low-poly vector | hand-painted painterly tiles | pixel-art sprite-stacked voxels|
  | Palette mood | bright pastel + turquoise   | warm amber + violet shadow   | 16-color toybox                |
  | Render cost  | lowest                      | medium (noise/brush)         | low (nearest-neighbor)         |
  | Skeleton fit | drop-in (maritime)          | re-theme only                | re-theme only                  |

---

## Candidate A — "Coralbright Atoll"

### (a) Setting / world premise

A sun-washed island harbor: turquoise lagoons and coral reefs, driftwood docks, a
white lighthouse "crown" on the headland, a kiln market under palm shade, a tide-pool
pump, and a floating glasshouse over a bright cove. The story of "one last departure"
plays out in a place that reads like a postcard come to life — cheerful, breezy, and
a little wistful.

### (b) Visual language

Flat-shaded, low-poly vector isometric. Each tile and prop is built from 2-3 flat
faces filled with a single solid color: the top face is the lightest tint of its hue,
the left/right faces the darker shade (fixed light from the north-west). No gradients
except a soft sky band and a translucent water shimmer. Crisp silhouettes, generous
negative space, and a thin (1px) dark-navy contour applied only to interactive objects
so they read instantly. This is the cheapest to render and the most tolerant of
software rasterization.

Concrete rules:

  - Projection: 2:1 isometric; a floor tile is a 64x32 px diamond (world unit 64 px).
  - Floor: flat solid tiles; water tiles add a two-frame sine ripple highlight at 12%
    opacity.
  - Props: extruded diamonds — draw a top face plus two side faces; side faces are the
    base hue darkened by a fixed 22% value step, the top face is the base hue.
  - Character: a small round flat-shaded "bean" with one accent color.
  - Outlines: 1px Ink Navy on interactable props and the character only.

### (c) Palette — named hex swatches

  - Lagoon Turquoise  #38C6B6  — primary shallow water
  - Deep Lagoon       #1E8F8A  — water depth / side faces
  - Sand Cream        #F7E6C0  — beaches, docks, paths
  - Coral Pink        #FF8A7A  — accent: flowers, roofs, awnings
  - Frond Green       #47B96B  — foliage mid
  - Palm Shadow       #1F7A4E  — foliage dark / side faces
  - Sun Yellow        #FFD23F  — highlights, fruit, lantern glow
  - Cloud White       #FFF7E8  — buildings, sails, clouds
  - Sky Blue          #A8E6F0  — sky band, glass
  - Ink Navy          #123A5A  — outlines, deep shadow, UI text

Rationale: high-key pastels with two saturated anchors (turquoise water, coral pink)
keep it vibrant without clashing; cool water against warm land gives instant
figure/ground; Ink Navy is the single neutral that ties outlines and UI together.

### (d) Cohesion rules

  1. Only the 10 swatches (plus pure white and pure black at <=1% of pixels for
     antialiasing) may appear; every sampled fill must be within dE <= 6 of one swatch.
  2. Lighting is a fixed 2-stop rule: an object's side faces are its hue darkened by
     exactly 22% value, the top face is the hue itself; never a third shade per object.
  3. Shadows: one global cool multiply (Ink Navy at 18% alpha) cast along the NW
     diagonal; never pure black.
  4. Water uses only the two turquoise swatches; land uses only warm swatches — no
     warm/cool mixing within a single object.
  5. At most four distinct hues visible in any one screen region (everything else is
     tint/shade), keeping it cohesive rather than noisy.

### (e) Reference touchstones

  - Monument Valley (flat-geometry discipline + restrained palette)
  - The Witness (color-graded, sunlit environment)

Verifiability: sample the top face and a side face of any object — assert top
luminance > side luminance and both within dE of palette; assert no fill outside the
palette; assert outline pixels are exactly Ink Navy.

---

## Candidate B — "Emberglow Hollow"

### (a) Setting / world premise

A cozy autumnal hollow at dusk: mushroom-roof cottages, a warm kiln/forge market, a
wooden waterwheel where the tide pump once stood, a glass greenhouse glowing with
fireflies, and a great lantern-crown tree on the hilltop. Storybook-warm, honeyed, and
snug — the whole world lit as if by lanterns.

### (b) Visual language

Hand-painted painterly tiles, produced procedurally. Every isometric floor tile gets a
flat base color plus a low-frequency "brush" overlay (Perlin noise jittering value by
+/-8% and saturation by +/-6%) to fake paint strokes. Props are painted "cards"
(billboarded sprites) composited onto the diamond floor with soft edges and a warm rim
light; no hard outlines — form is read by value contrast. Depth comes from warm/cool
contrast: warm light from lanterns/hearth against a single cool violet ambient shadow.

Concrete rules:

  - Projection: 2:1 isometric, 64x32 diamond floor tiles.
  - Brush: one shared Perlin seed/scale across the whole scene so texture stays
    consistent (no per-object noise soup).
  - Props: 2D painted cards sorted back-to-front; soft 1px alpha feather on edges.
  - Light: warm (honey-gold) highlights, cool (twilight violet) shadows; a soft radial
    vignette.

### (c) Palette — named hex swatches

  - Hearth Amber     #F5A623  — primary warm light
  - Honey Gold       #F7C948  — highlights, glow, lantern light
  - Pumpkin          #E87A3E  — roofs, harvest accents
  - Russet           #C96F4A  — wood, soil, brick
  - Moss Green       #6B9E4A  — foliage mid
  - Fern Deep        #3F6F3A  — foliage shadow
  - Cream Parchment  #FBEFD8  — paper, walls, paths
  - Bark Brown       #6B4A32  — trunks, dark wood
  - Firefly Glow     #D9F26A  — accent glow, fireflies
  - Twilight Violet  #5B4A78  — the single cool shadow / ambient

Rationale: a warm analogous range (amber -> pumpkin -> russet -> moss) anchored by one
cool violet shadow creates the "cozy dusk" glow; one cool accent (firefly green-yellow)
adds a gentle pop without breaking the warmth.

### (d) Cohesion rules

  1. Warm palette for lit surfaces; Twilight Violet is the only cool color allowed,
     used exclusively for shadows/ambient (never a lit surface). No blue/teal except a
     single named "brook" accent if desired.
  2. All brush noise shares one seed/scale; value jitter <= +/-8%, saturation jitter
     <= +/-6%, so palette identity survives the painterly texture.
  3. Light is warm and low: highlights pull toward Honey Gold, shadows toward Twilight
     Violet; never a cool highlight.
  4. Soft edges only — no 1px outlines; interactable props are distinguished by a
     Firefly Glow halo, not a contour.
  5. The shadow layer is a single translucent Twilight Violet multiply, never black.

### (e) Reference touchstones

  - A Short Hike (cozy painterly nature)
  - Spiritfarer (hand-painted warmth and softness)

Verifiability: sample lit vs shadow regions — assert lit pixels are warm (R >= G >= B
and R-B >= 15) and shadow pixels are violet-ish (B >= R) and within dE of Twilight
Violet; assert every sampled fill within dE of the palette (with the stated value
tolerance).

---

## Candidate C — "Prismgrove"

### (a) Setting / world premise

A miniature toy world: a magical grove where cottages are chunky candy-colored blocks,
berry bushes dot a stitched meadow, a winding stream is a ribbon of blue tiles, and the
"lantern crown" is a stack of glowing toy blocks. Everything reads as a diorama of
colored blocks — playful, saturated, and immediately charming.

### (b) Visual language

Pixel-art sprite stacking (voxel-in-2D). Each tile and object is a vertical stack of 2D
pixel sprites that together read as a 3D volume from the fixed iso camera. Chunky pixels
(16 px per iso unit face), crisp nearest-neighbor edges, no antialiasing, no gradients —
shading is two-tone with ordered dithering (Bayer/checkerboard). This is the most
distinctive, retro-charming option and renders cheaply.

Concrete rules:

  - Projection: 2:1 isometric; a tile face is a 16x16 px pixel block; the camera
    upscales by integer factors with nearest-neighbor only.
  - Volume: objects are sprite stacks — N horizontal slices, each a 16x16 (or 32x32) px
    sprite, composited bottom-to-top.
  - Shading: top face = pure lit color; NE-facing side face = the darker of the hue's
    two values applied as ordered dither; SE face = the darker value solid.
  - Outline: 1px Charcoal on interactable props and the character only.

### (c) Palette — 16 colors (closed)

Lit (top faces)  ->  Shadow (NE face dithered / SE face solid):

  - Cream        #FFF1D0  ->  Peach        #FFD1A9
  - Butter Yellow#FFD23F  ->  Apricot      #FFA74F
  - Leaf Green   #58C25C  ->  Deep Grass   #2E8B57
  - Sky Blue     #63B8FF  ->  Cobalt       #2E5FA3
  - Rose         #F58BB0  ->  Cherry Red   #E64545
  - Lilac        #C6A7E8  ->  Plum         #8A4F9E
  - Aqua         #6FE0D0  ->  Teal         #2E8F8A

Neutrals:

  - Charcoal     #3A3A3A  — 1px outline on interactables + text only
  - Cloud        #FFFFFF  — sparkle / glint only

Rationale: a toybox palette — each hue exists at exactly one "lit" and one "shadow"
value and ordered dithering bridges the two; the small closed set is what keeps it
cohesive and readable at chunky scale.

### (d) Cohesion rules

  1. The 16-color palette is closed: every rendered pixel is snapped to the nearest
     palette color in code (no off-palette output, ever).
  2. Shading is strictly two-tone per hue — a "lit" and a "shadow" value, blended only
     by ordered dithering (Bayer 4x4), never by alpha or gradients.
  3. Charcoal appears only as 1px outlines on interactables and text; Cloud only as
     sparkle/light glints.
  4. Pixel grid is locked: all geometry snaps to a 2px grid and upscales by integer
     factors (nearest-neighbor) — no sub-pixel, no rotation.
  5. Each screen region uses <= 4 hues plus their shadow values.

### (e) Reference touchstones

  - Stardew Valley (warmth, palette charm, cohesion)
  - Fae Farm (vibrant toybox diorama)
  - Octopath Traveler "HD-2D" (sprite-stacked diorama depth)

Verifiability: assert every sampled pixel is exactly one of the 16 palette colors (the
strongest automated guarantee of all three candidates); assert top faces are the lit
value and dithered faces contain only the hue's two values.

---

## How to choose (tradeoffs, not a decision)

All three satisfy node 0's centerpiece — vibrant, colorful, cohesive, visually
appealing, charming. They differ in texture and mood:

  - A (Coralbright Atoll) is the most clean and modern, and a drop-in for the existing
    maritime skeleton — lowest risk, fastest to a good-looking result.
  - B (Emberglow Hollow) is the most cozy and storybook, and emotionally warmest, but
    its painterly layer needs the most tuning to stay cohesive.
  - C (Prismgrove) is the most playful and distinctive, with the strongest automated
    verifiability (closed palette), at the cost of a retro look some may find less
    "visually rich".

The worker does not make this call. The final direction is Rick's.

## Approved art direction (record)

Status: PENDING — awaiting Rick's selection.

Once Rick chooses, record here (this is what promotes node 10 to "human-approved"):

  - Selected direction (A / B / C) and its name
  - Any palette or cohesion amendments Rick requests
  - Date, and (optionally) Rick's one-line rationale

