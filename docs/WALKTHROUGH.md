# Emberglow Hollow — explicit step-by-step walkthrough

A human-readable route from the Hollow Gate to the ending, matching docs/world.json
exactly. This is the canonical 11-action chain: no developer knowledge required,
every step is reachable through the normal playable interface (walk, Examine,
Talk, Take, Use-item-on-target, and the contextual interact key).

Controls (the on-screen hint always shows them):
  WASD / arrows  walk (hold to move)
  X              examine
  T              talk
  G              take
  U              use the selected item on the object you face
  Tab / [        cycle the selected inventory item
  E / Space / Enter  contextual "do the obvious thing"
  Escape         dismiss dialogue

The four big world-change beats to watch for as you play:
  1. water flows      — the mill-wheel turns and Brook water pours at the spout
  2. lens cooled      — the forge flashes warm as the lens is quenched
  3. seed taken       — the greenhouse seed-bed dims as you lift the Ember-Seed
  4. lantern lit      — the Heart-Lantern floods the crown in warm light (climax)
...then the ending: the bell rings, the fireflies pour home, and Mallow's little
firefly-moth companion drifts back to the gatekeeper.

## The walk

1.  MEET MALLOW — you start in the Hollow Gate. Walk to Mallow (the hooded
    gatekeeper by the common) and press T (Talk). He explains the Long Dusk and
    hands you the Crank Handle. (flag met_mallow; +crank_handle)

2.  REQUEST THE FLASK — cross the east portal (the path on the right edge) into
    the Forge Market. Walk to Bramble the forge-smith and press T (Talk). He
    gives you the Glass Flask. (flag flask_received; +glass_flask)

3.  TURN THE WHEEL — go north from the market into the Mill Court. Face the Crank
    Socket (on the waterwheel), select the Crank Handle (Tab), and press U (Use).
    The wheel turns and water begins to flow. (flag water_flowing; -crank_handle)

4.  FILL THE FLASK — still in the Mill Court, face the Water Spout, select the
    Glass Flask, and press U. The flask fills with cool mill-water.
    (flag flask_filled; -glass_flask, +full_flask)

5.  TAKE THE SEED — cross the east portal (now open because water is flowing) into
    the Firefly Greenhouse. Face the pulsing Ember-Seed and press G (Take).
    (flag seed_taken; +ember_seed)

6.  COOL THE LENS — return to the Forge Market. Face Bramble, select the full
    Flask, and press U. He re-grinds and quenches the old lens.
    (flag lens_ready; -full_flask, +lens)

7.  OPEN THE STAIR — return to the Hollow Gate and Talk to Mallow. He clears the
    moss from the Hill Stair. (flag stair_open)

8.  MOUNT THE LENS — climb the now-open Hill Stair (north portal) to the Lantern
    Crown. Face the Lens Mount, select the Lens, press U. (flag lens_mounted; -lens)

9.  PLANT THE SEED — still on the crown, face the Seed Cradle, select the
    Ember-Seed, press U. (flag seed_planted; -ember_seed)

10. KINDLE THE LANTERN — face the Focus Wheel and press U (no item needed). The
    Heart-Lantern ignites and warm light floods the hilltop. (flag lantern_lit)

11. RING THE BELL — climb back down to the Hollow Gate, face the Hollow Bell, and
    press U. The bell rings; the fireflies pour home in a golden river and
    Mallow's companion drifts back to him. The title "the fireflies came home."
    appears. (flag ended — terminal)

## Why this order (the dependency chain)

  - meet_mallow and request_flask are the two free entry actions.
  - turn_wheel needs the Crank Handle; fill_flask needs the Glass Flask AND
    water_flowing; take_seed needs water_flowing (the greenhouse irrigation).
  - cool_lens needs the full Flask; open_stair needs lens_ready AND seed_taken.
  - mount_lens and plant_seed need stair_open (plus their items); kindle_lantern
    needs lens_mounted AND seed_planted; ring_bell needs lantern_lit.

Every action is one-shot (a persistent flag), every item is granted once and
consumed once, and the two room gates (water_flowing for the greenhouse,
stair_open for the crown) prevent reaching the later rooms before their beats.
There is no way to softlock: every reachable state can still reach the ending
(proven exhaustively by tests/test_progression.py and tools/validate_design.py).

## Verification (headless, no vision)

    python3 -m unittest tests.test_progression   # chain / out-of-order / softlocks
    python3 tools/validate_design.py             # design-level no-softlock proof
    python3 tools/demo_progression.py            # full playthrough trace + captures
    python3 -m emberglow.main --check            # beats + ending (companion + title)
