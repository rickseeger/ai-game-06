"""G13 node 14 -- population / catalog-agreement contract (headless).

This is the mechanical proof of node 14's completion contract: every entity named
in docs/world.json (characters, items, discoverable props) exists at its designed
location, is inspectable through the interaction system, and is reachable from a
valid standing tile in normal play.

It drives straight from the world.json catalog (never from a hardcoded list of the
author's own expectations), and cross-checks the finished scene art
(emberglow.scene / worldreact) against that catalog via the single
OBJECT_PROP_KIND table in emberglow/worldreact.py. A divergence between the data
and the art therefore fails here, mechanically.

No vision tool is used: presence is asserted structurally (scene prop at the exact
grid cell + a non-empty sprite), inspectability through verbs.resolve(EXAMINE),
and reachability through World.interaction_tiles / World.find_path.
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from emberglow import verbs, worldreact
from emberglow.sprites import get_sprite, build_item_icon
from emberglow.world import World


class CatalogAgreementTests(unittest.TestCase):
    """Entity/catalog agreement: presence + inspectability + reachability."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()
        cls.un_gated_rooms = {
            r for r, _ in cls.w.reachable_state_space(
                cls.w.initial_room, cls.w.initial_pos, frozenset())
        }

    def setUp(self):
        pygame.init()

    def tearDown(self):
        pygame.quit()

    def _all_entities(self):
        """Yield (room_id, object_id, (gx, gy)) for every object in the catalog."""
        for rid, rdata in self.w.data["rooms"].items():
            for name, cell in rdata["objects"].items():
                yield rid, name, tuple(cell)

    def _all_characters(self):
        for cid in self.w.data.get("characters", {}):
            yield cid

    def test_every_catalog_object_is_placed_in_its_scene(self):
        """Each world.json object exists as its mapped prop, interactable, in the
        finished scene, at exactly the catalog grid cell."""
        w = self.w
        for rid, name, cell in self._all_entities():
            room = worldreact.build_scene_room(w, rid, frozenset())
            # the scene must place exactly the catalog's prop kind on that cell
            kind = worldreact.OBJECT_PROP_KIND[name]
            matches = [p for p in room.props
                       if (p.gx, p.gy) == cell and p.kind == kind]
            self.assertTrue(matches, f"{rid}.{name}: no {kind!r} prop at {cell}")
            # it must be interactable (Firefly-Glow halo + interaction target)
            self.assertTrue(all(p.interactable for p in matches),
                            f"{rid}.{name}: prop at {cell} not interactable")

    def test_every_catalog_object_has_a_sprite(self):
        """Each placed prop kind resolves to a real (non-empty) sprite."""
        for rid, name, cell in self._all_entities():
            kind = worldreact.OBJECT_PROP_KIND[name]
            spr = get_sprite(kind, cell[0], cell[1])
            self.assertGreater(spr.get_width(), 0, f"{rid}.{name} sprite width")
            self.assertGreater(spr.get_height(), 0, f"{rid}.{name} sprite height")

    def test_every_catalog_object_is_inspectable(self):
        """Each object has a display name + examine line and Examine returns INFO."""
        w = self.w
        for rid, name, cell in self._all_entities():
            self.assertIn(name, verbs.OBJECT_NAMES, f"{name}: no display name")
            self.assertIn(name, verbs.EXAMINE_LINES, f"{name}: no examine line")
            self.assertTrue(verbs.EXAMINE_LINES[name].strip(), f"{name}: empty examine")
            out = verbs.resolve(w, w.initial_state(), rid, name, verbs.EXAMINE, None)
            self.assertEqual(out.kind, verbs.INFO, f"{name}: examine not INFO")
            self.assertTrue(out.lines and out.lines[0][1], f"{name}: no examine text")

    def test_every_catalog_object_has_a_valid_standing_tile(self):
        """Each object has at least one walkable cell adjacent to it."""
        w = self.w
        for rid, name, cell in self._all_entities():
            tiles = w.interaction_tiles(rid, name)
            self.assertTrue(tiles, f"{rid}.{name}: no standing tile next to {cell}")

    def test_every_catalog_object_is_reachable_in_normal_play(self):
        """Each object is reachable on foot from the initial spawn: un-gated rooms
        immediately, gated rooms once their portal flags are granted."""
        w = self.w
        for rid, name, cell in self._all_entities():
            tiles = w.interaction_tiles(rid, name, w.all_flags)
            self.assertTrue(tiles, f"{rid}.{name}: no standing tile (all flags)")
            if rid in self.un_gated_rooms:
                path = w.find_path(w.initial_room, w.initial_pos, rid, tiles[0],
                                   frozenset())
                self.assertIsNotNone(path, f"{rid}.{name}: unreachable without flags")
            path = w.find_path(w.initial_room, w.initial_pos, rid, tiles[0],
                               w.all_flags)
            self.assertIsNotNone(path, f"{rid}.{name}: unreachable with all flags")


class CharacterHandoffTests(unittest.TestCase):
    """The two authored item handoffs fire from the catalog's first-talk actions."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def setUp(self):
        pygame.init()

    def tearDown(self):
        pygame.quit()

    def _walk_to(self, state, room, target):
        w = self.w
        tile = w.interaction_tiles(room, target, state.flags)[0]
        path = w.find_path(state.room, state.pos, room, tile, state.flags)
        self.assertIsNotNone(path, (room, target))
        for d in path:
            state = w.move(state, d)
        self.assertEqual((state.room, state.pos), (room, tile))
        return state

    def test_mallow_first_talk_hands_over_crank_handle(self):
        w = self.w
        state = self._walk_to(w.initial_state(), "gate", "mallow")
        out = verbs.resolve(w, state, "gate", "mallow", verbs.TALK, None)
        self.assertEqual(out.action_id, "meet_mallow")
        self.assertEqual(out.grant, frozenset({"crank_handle"}))
        self.assertIn("met_mallow", out.flags)
        # catalog agreement: the action really says the same thing
        action = next(a for a in w.actions if a["id"] == "meet_mallow")
        self.assertEqual(action["target"], "mallow")
        self.assertEqual(action["room"], "gate")
        self.assertEqual(action["grant"], ["crank_handle"])
        self.assertEqual(action["needs"], [])
        # the granted item is a real catalog item
        self.assertIn("crank_handle", w.data["items"])

    def test_bramble_first_talk_hands_over_glass_flask(self):
        w = self.w
        state = self._walk_to(w.initial_state(), "market", "bramble")
        out = verbs.resolve(w, state, "market", "bramble", verbs.TALK, None)
        self.assertEqual(out.action_id, "request_flask")
        self.assertEqual(out.grant, frozenset({"glass_flask"}))
        self.assertIn("flask_received", out.flags)
        action = next(a for a in w.actions if a["id"] == "request_flask")
        self.assertEqual(action["target"], "bramble")
        self.assertEqual(action["room"], "market")
        self.assertEqual(action["grant"], ["glass_flask"])
        self.assertEqual(action["needs"], [])
        self.assertIn("glass_flask", w.data["items"])

    def test_handoffs_are_one_shot(self):
        w = self.w
        state = self._walk_to(w.initial_state(), "gate", "mallow")
        first = verbs.resolve(w, state, "gate", "mallow", verbs.TALK, None)
        state = first.apply(state)
        again = verbs.resolve(w, state, "gate", "mallow", verbs.TALK, None)
        self.assertNotEqual(again.action_id, "meet_mallow")
        self.assertNotIn("crank_handle", again.grant)


class ItemCatalogTests(unittest.TestCase):
    """Every catalog item has a display name and a rendered inventory icon."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def setUp(self):
        pygame.init()

    def tearDown(self):
        pygame.quit()

    def test_every_catalog_item_has_name_and_icon(self):
        w = self.w
        for item_id, spec in w.data["items"].items():
            self.assertTrue(spec.get("name"), f"{item_id}: no display name")
            icon = build_item_icon(item_id)
            self.assertGreater(icon.get_width(), 0, f"{item_id}: icon width")
            self.assertGreater(icon.get_height(), 0, f"{item_id}: icon height")
            self.assertGreater(icon.get_width(), 0)


if __name__ == "__main__":
    unittest.main()
