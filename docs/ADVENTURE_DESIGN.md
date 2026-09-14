# G13 — Bounded Adventure Design: "Emberglow Hollow"

Status: DESIGN (this node). This is the bounded, implementation-ready adventure
design for G13, consistent with the approved art direction and the approved
implementation approach. It re-themes the proven 5-room / 11-action progression
skeleton (node 1) into the Emberglow Hollow world and fixes every strategic choice
a later node would otherwise re-derive. The machine-readable form of this design
(rooms, gates, actions, item/flag chain) is docs/world.json; the no-softlock proof
lives in tools/validate_design.py and evidence/progression-validation.json.

## 1. Approved art direction (named — not re-decided)

Emberglow Hollow — direction B. Selected by Rick; the full candidate spec is in
docs/ART_DIRECTIONS.md. A cozy autumnal hollow at dusk, storybook-warm and honeyed,
lit as if by lanterns. Everything below uses its locked named-hex palette:

  Hearth Amber     #F5A623   primary warm light
  Honey Gold       #F7C948   highlights, glow, lantern light
  Pumpkin          #E87A3E   roofs, harvest accents
  Russet           #C96F4A   wood, soil, brick
  Moss Green       #6B9E4A   foliage mid
  Fern Deep        #3F6F3A   foliage shadow
  Cream Parchment  #FBEFD8   paper, walls, paths
  Bark Brown       #6B4A32   trunks, dark wood
  Firefly Glow     #D9F26A   accent glow, fireflies
  Twilight Violet  #5B4A78   the single cool shadow / ambient

One optional cool accent is permitted by cohesion rule 1 ("a single named 'brook'
accent if desired"); we use it for the mill-water only:

  Brook            #6FA8B8   mill-water + greenhouse irrigation ONLY (cool accent)

Cohesion rules honored throughout: warm lit surfaces (R >= G >= B and R-B >= 15);
Twilight Violet is the only cool color on lit/shadow surfaces and is used only for
shadow/ambient; shadows and ambient are violet, never black; soft edges only (no
1px outlines); interactables are marked by a Firefly-Glow halo, not a contour; and
all painterly texture comes from one shared world-space noise seed so the brush is
continuous across the whole hollow.

## 2. Approved implementation approach (named — not re-decided)

Python 3.14 + pygame-ce 2.5.x (SDL2 software compositor); fixed 2:1 isometric
projection (64x32 diamond tiles, world unit 64 px, no rotation, no zoom);
painter's-algorithm depth sort with tile elevation (ELEV 16 px/unit) for the 2.5D
read; procedural painterly tiles from one shared value-noise seed; a warm/cool
two-light model (warm lit surfaces vs a single Twilight-Violet ambient + vignette,
additive Honey-Gold lantern glow and Firefly-Glow accents). Renders and frame-dumps
headlessly (SDL dummy driver); proven in node 11 (DECISION.md + spike/). All art is
code-driven — no image-generation and no hand-drawn asset pipeline. This design
authors content for that pipeline and adds no new engine or system requirements.

## 3. Story — "The Long Dusk"

Emberglow Hollow keeps its seasons warm with the Heart-Lantern, the great
lantern-crown tree on the hilltop, tended for generations by the Ember-Keepers.
One dusk the last Keeper grew too old to climb, and the Heart-Lantern guttered
out. Since then dusk has stretched into a Long Dusk: the hollow cools, the forge
burns low, the mill-wheel jams, and the fireflies — the hollow's warmth made
visible — have begun drifting away over the ridge.

You are a young ember-keeper who arrives at the Hollow Gate at dusk, sent to
relight the Heart-Lantern before the first frost. If it is not relit, the hollow
sleeps through a long grey winter and the fireflies are lost for good.

Relighting the tree needs three things gathered across the hollow: the Ember-Seed
(a live spark), the Dew-Cooled Lens (to focus the light), and the turning of the
mill-water (which wakes the seed and tempers the lens). The final note: when the
lantern relights and the old hollow bell rings, the fireflies — and Mallow's
long-lost companion — come home.

## 4. Experience and quality bar (specific)

What it must feel like:
  - The art is the centerpiece. Every screen reads as "lit by lanterns": warm
    honeyed surfaces against one cool violet dusk. Moving through the hollow should
    feel like wandering a picture book at golden hour — pleasurable even standing
    still, with no screen that looks unfinished or flat.
  - Gentle and frictionless. No combat, no death, no fail states, no time pressure.
    The "first frost" is atmospheric tension only — there is no timer and no way to
    lose or get stuck permanently.
  - Discovery is rewarded. A painted mural tells the hollow's founding and hints
    the three-part recipe. Ambient fireflies thicken as you progress. Each
    completed step visibly warms and brightens the world, so progress is felt, not
    merely logged.
  - Classic verbs, minimal UI. Examine, Talk, Take, and "Use X on Y" (plus walk).
    A single modal text panel and a simple inventory strip, both in-palette.

Quality bar (concrete and testable):
  1. Palette discipline — every sampled fill within dE <= 50 of a named swatch
     (painterly jitter allowed: +/-8% value, +/-6% saturation); soft edges only;
     no pure black; no hard outlines.
  2. Lighting correctness — warm lit surfaces (R>=G>=B, R-B>=15); shadows violet
     (B>=R); never a cool highlight.
  3. Readability — every interactable object/character shows a Firefly-Glow halo;
     walkable path tiles are clearly distinct from blocking props; the player reads
     clearly on any backdrop.
  4. Determinism — seed-fixed procedural tiles; a scene reproduces byte-identically
     so pixel-sampling checks are stable.
  5. Completeness — the full progression completes end-to-end with zero softlocks,
     zero unreachable items, zero circular dependencies (proven by
     tools/validate_design.py).
  6. Reactivity — each of the four big beats (water flows, lens cooled, seed taken,
     lantern lit) produces a distinct, legible world change; the lantern-lighting is
     the visual climax and the firefly return is the emotional one.
  7. Performance — steady 60 fps on Rick's Pop!_OS laptop (painterly tiles
     pre-rendered and cached once at boot; steady-state is blits — per node 11's
     spike note).
  8. Feel — "cozy at a glance." No pop-in, no jitter, no reading the UI to know
     where to go next.

## 5. World / locations (5 rooms)

The hollow is five connected rooms (fixed 2:1 isometric, 9x9 coarse grid each, world
unit 64 px). Rooms connect through edge portals on their borders; two edges are
gated by progression flags (see section 8). Coordinates and ports are fixed in
docs/world.json.

  1. Hollow Gate (id: gate) — the village entry, mushroom-roof cottages around a
     cobbled common. Palette anchor: Cream Parchment paths, Moss Green banks,
     Hearth Amber gate lantern, Pumpkin cottage roofs, Twilight Violet dusk.
     Props: Mallow (character), the Hollow Bell (terminal object), the Hill Stair
     (a moss-choked stair up to the crown, closed until stair_open). This is the
     home room you return to twice: to collect the crank, and to open the stair.
  2. Forge Market (id: market) — a warm kiln/forge under a canvas awning.
     Palette anchor: Hearth Amber + Honey Gold forge glow, Russet brick, Pumpkin
     awnings. Props: Bramble (character), the Forge (lens-quenching). Feels
     busiest and warmest early on.
  3. Mill Court (id: mill) — the wooden waterwheel at the hollow's edge.
     Palette anchor: Russet + Bark Brown wheel, Moss Green banks, Brook water
     (cool accent) when flowing. Props: the Crank Socket (accepts the crank), the
     Water Spout (fills the flask once water_flowing). Gated entry to the
     greenhouse sits across from it.
  4. Firefly Greenhouse (id: greenhouse) — a glass greenhouse glowing with
     drifting fireflies; vines over the door. Palette anchor: Moss Green + Fern
     Deep foliage, Firefly Glow dots, Cream Parchment glass panes. Props: the
     Ember-Seed (the live spark, liftable once watered), the Mural (a painted
     founding story — a discoverable hint, optional to read). Entered only after
     water_flowing (the mill-water feeds its irrigation).
  5. Lantern Crown (id: crown) — the hilltop with the great lantern-crown tree,
     now dark. Palette anchor: Bark Brown trunk, Fern Deep + Moss Green crown,
     dormant Hearth Amber lantern. Props: the Seed Cradle (plant the ember-seed),
     the Lens Mount (mount the lens), the Focus Wheel (kindle). Entered only after
     stair_open. This is the climax room where the final three actions occur.

## 6. Characters and interactions

Two speaking characters; the fireflies are a non-speaking ambient presence.

  - Mallow — the old gatekeeper and lantern-tender (a gentle, patient, wistful
    figure). First meeting: explains the Long Dusk and the quest, and hands over
    the Crank Handle ("the wheel's gone stiff; this ought to free it"). Later,
    once you return with the Dew-Cooled Lens and the Ember-Seed, Mallow clears the
    moss from the Hill Stair so you can climb. Mallow's long-lost companion — a
    little migrating firefly-moth — is what the ending returns home.
  - Bramble — the forge-smith, bluff and warm, keeps the Forge Market. First
    meeting: gives you the Glass Flask. Later, given a full flask, re-grinds and
    quenches the lantern's old lens into the Dew-Cooled Lens ("the glass must cool
    slow, in mill-water, or it'll crack").

Interaction model (classic, minimal): walk to an adjacent tile and press the
interact key. The verb set is Examine, Talk, Take, and Use-item-on-target; the
inventory is a horizontal strip. Talk opens a short text panel (Cream Parchment
panel, Bark Brown text); each line is 1-2 cozy sentences, no walls of text.

## 7. Items and their uses

  1. Crank Handle (id: crank_handle) — the mill-wheel's missing handle. Use on the
     Crank Socket to unjam the wheel (consumed). Source: Mallow.
  2. Glass Flask (id: glass_flask) — an empty glass flask. Use on the Water Spout
     (once water_flowing) to fill it (consumed). Source: Bramble.
  3. Glass Flask, full (id: full_flask) — brimming with cool mill-water. Give to
     Bramble to quench the lens (consumed). Source: filling the flask.
  4. Ember-Seed (id: ember_seed) — a warm, pulsing seed; the live spark. Take from
     the greenhouse once water_flowing revives the seed-bed. Plant in the Seed
     Cradle on the crown (consumed). Source: the greenhouse.
  5. Dew-Cooled Lens (id: lens) — the lantern's old glass lens, re-ground and
     quenched. Mount on the Lens Mount (consumed). Source: Bramble, from the full
     flask.

## 8. Puzzle/quest progression (start -> ending)

Eleven one-shot actions, same proven dependency topology as node 1 (re-themed
names only). Each action grants a persistent flag, so it fires exactly once.

  1. meet_mallow      (gate, Mallow)        -> Crank Handle, flag met_mallow
  2. request_flask    (market, Bramble)     -> Glass Flask, flag flask_received
  3. turn_wheel       (mill, Crank Socket)  needs Crank Handle -> water_flowing
  4. fill_flask       (mill, Water Spout)   needs Glass Flask, requires water_flowing -> full_flask
  5. take_seed        (greenhouse, Ember-Seed) requires water_flowing -> Ember-Seed
  6. cool_lens        (market, Bramble)     needs full_flask -> Dew-Cooled Lens
  7. open_stair       (gate, Mallow)        requires lens_ready + seed_taken -> stair_open
  8. mount_lens       (crown, Lens Mount)   needs lens, requires stair_open -> lens_mounted
  9. plant_seed       (crown, Seed Cradle)  needs Ember-Seed, requires stair_open -> seed_planted
  10. kindle_lantern  (crown, Focus Wheel)  requires lens_mounted + seed_planted -> lantern_lit
  11. ring_bell       (gate, Hollow Bell)   requires lantern_lit -> ended (terminal)

Room gates: gate <-> market and market <-> mill are always open; mill <->
greenhouse opens once water_flowing (the wheel feeds the greenhouse irrigation);
gate <-> crown opens once stair_open.

Start: gate at the common, empty-handed. Ending: after relighting the tree, return
to the gate and ring the Hollow Bell — the lantern's light spills down the hollow,
the fireflies pour home over the ridge, and Mallow's companion returns.

Completeness proof: tools/validate_design.py exhaustively searches all reachable
(room, flags, inventory) states and asserts (a) the ending is reachable, (b) every
action is reachable, (c) no circular dependencies, (d) zero softlocked states, and
(e) every room's floor is connected and every required interaction has a reachable
standing tile. It passes against this design (evidence/progression-validation.json).

## 9. World reactivity map (each beat visibly changes the world)

  - water_flowing: the wheel turns; Brook water pours at the spout; a soft water
    sound (if audio); the greenhouse door vines recede.
  - flask_filled: the flask in hand shows full.
  - lens_ready: the forge flashes warm; the lens glints with a cool sheen in your
    inventory.
  - seed_taken: the greenhouse seed-bed dims; the Ember-Seed glows warm in hand.
  - stair_open: the moss clears from the Hill Stair; a ribbon of warm light marks
    the way up.
  - lens_mounted: the lantern's empty socket now holds a glinting lens.
  - seed_planted: the cradle holds a warm, pulsing seed.
  - lantern_lit (climax): the Heart-Lantern ignites — warm Hearth Amber + Honey Gold
    light floods the hilltop and spills down the hollow; the violet dusk recedes.
  - ended (payoff): fireflies pour back over the ridge in a golden river; the hollow
    is bathed in warm light; Mallow's companion returns; a gentle homecoming note;
    end title over the glowing tree.

## 10. Ending

The Heart-Lantern relit and the bell rung, the hollow's long dusk ends. Fireflies
return in a golden stream, the hollow warms and brightens, and Mallow's companion
settles back into the lantern-crown tree. The final frame is the glowing tree over
the snug hollow, with a one-line title — "the fireflies came home." The player can
keep wandering the lit hollow afterward (no forced exit).

## 11. Bounded scope (deliverable set + suggested node map)

Deliverable set (the whole game, nothing more): 5 rooms, 11 actions, 5 items,
2 speaking characters + the Mural + ambient fireflies, 1 player, one ending,
a simple inventory strip, a short dialogue panel, one shared save flag (optional:
persist flags+inventory to a small JSON so a session can be resumed).

Suggested split across the remaining implementation nodes (guidance for the
controller — the controller owns actual node assignment):

  - Node 2: world data + scene graph + camera/movement. Load docs/world.json, render
    the 5 rooms with painterly tiles + 2.5D elevation, walk input, room portals.
    Deliverable: walk through all 5 rooms.
  - Node 3: props + characters + lighting art. Mushroom cottages, waterwheel,
    greenhouse, lantern tree, forge; Mallow/Bramble cards; fireflies; glow halos;
    warm/cool light + vignette. Deliverable: all 5 rooms read Emberglow; fireflies
    ambient.
  - Node 4: interaction + inventory + dialogue. Examine/Talk/Take/Use hooks; item
    sprites; inventory strip; dialogue panel. Deliverable: talk, take, use all work.
  - Node 5: progression + world reactivity. Wire the 11-action flag/item chain; the
    four big beats' world reactions; the ending sequence. Deliverable: full
    playthrough gate -> bell.
  - Node 6: polish + verification + packaging. Pixel-sampling checks; README
    single-command install/run; headless verification; optional soft audio.
    Deliverable: Rick clones + runs in one command, verified headless, ending lands.

## 12. Non-goals (explicit)

  - No combat, no enemies, no health/death/fail states.
  - No real-time pressure or timer (the frost is narrative only).
  - No procedural world generation — the world is hand-authored; procedural is only
    the painterly tile texture, seed-fixed and deterministic.
  - No image-generation or hand-drawn asset pipeline (all art is code-driven).
  - No multiplayer; no save system beyond optional flag+inventory persistence.
  - No Windows build this pass (Linux-first; Windows later for Andrew).
  - No voice acting (text dialogue only); audio is optional soft ambience, deferred
    behind visuals.
  - No engine swap (pygame-ce is decided; Godot 4 is the recorded fallback only).

## 13. Verification plan (automated, no vision)

  1. Progression: run tools/validate_design.py against docs/world.json — asserts
     ending reachable, all actions reachable, no circular deps, zero softlocks,
     connected floors, reachable interaction standpoints. (Run this session; output
     in evidence/progression-validation.json.)
  2. Rendering, per milestone (extend node 11's pixel-sampling checks): after
     water_flowing, Brook cool pixels appear at the spout; after lantern_lit,
     strong Hearth Amber/Honey Gold warm coverage floods the hilltop and the
     violet ambient recedes; after ended, the Firefly-Glow pixel count spikes.
  3. Palette/lighting invariants (from the art direction): warm lit surfaces
     R>=G>=B and R-B>=15; shadows violet B>=R; every fill within dE<=50 of the
     palette; no pure black; no hard outlines.
  4. Human playtest: final aesthetic judgment (painterly feel, glow subtlety,
     composition, the ending's emotional landing) is Rick's, on Pop!_OS — not
     verifiable here without vision; noted explicitly as unverified in this session.

## 14. Data contract

docs/world.json is the single machine-readable source of truth for rooms, gates,
objects, items, flags, and the 11-action chain (schemaVersion 1, the same shape
node 1 authored and validated). It also carries the art-direction name, per-room
palette anchors, an item catalog (id -> display name + one-line use), and a
character catalog, so nodes 2-6 implement directly from it without re-deriving
anything strategic. The narrative and quality bar in this document are the
human-readable companion to that data.
