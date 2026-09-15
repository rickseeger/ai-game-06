"""Game controller: real input -> movement, facing, targeting, interaction, dialogue.

Owns the live session. Held directional keys (WASD / arrows) drive discrete grid
movement onto the 9x9 traversal in emberglow.world; facing follows the most recent
directional press; the context-sensitive target is the object in the cell the player
faces; the interact key performs that target's action (or advances an open
dialogue); escape dismisses dialogue/interface. Rendering draws the player at its
true world position plus a controls hint and readable target feedback.

All simulation is keyed on the logical actions from emberglow.inputmap and never
calls World.move / state mutators directly from the trace driver -- the runtime
trace drives this controller through the real event queue (pygame.event.post ->
pygame.event.get -> Game.handle_event), the same application input path a real
keyboard feeds.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from . import inputmap, ui
from .animation import idle_bob
from .geometry import prop_anchor
from .scene import Room as SceneRoom, Prop, build_room_gate, render_room, layout
from .sprites import get_sprite
from .world import World, State, BlockedError

# Seconds between grid steps while a directional key is held.
MOVE_INTERVAL = 0.15

# Object id -> human display name (target-feedback label).
OBJECT_NAMES: Dict[str, str] = {
    "mallow": "Mallow", "hollow_bell": "Hollow Bell", "hill_stair": "Hill Stair",
    "bramble": "Bramble", "forge": "Forge", "crank_socket": "Crank Socket",
    "water_spout": "Water Spout", "ember_seed": "Ember-Seed", "mural": "Mural",
    "seed_cradle": "Seed Cradle", "lens_mount": "Lens Mount",
    "focus_wheel": "Focus Wheel",
}

# Object id -> interaction verb (target-feedback prompt).
OBJECT_VERBS: Dict[str, str] = {
    "mallow": "talk to", "bramble": "talk to", "hollow_bell": "ring",
    "hill_stair": "climb", "forge": "use", "crank_socket": "use",
    "water_spout": "fill", "ember_seed": "take", "mural": "read",
    "seed_cradle": "plant", "lens_mount": "mount", "focus_wheel": "turn",
}

# Action id -> (speaker, text) success line (1-2 cozy sentences, per the design).
DIALOGUE: Dict[str, Tuple[str, str]] = {
    "meet_mallow": ("Mallow",
        "The Heart-Lantern has gone out and the hollow grows cold. "
        "Take this crank -- it ought to free the mill-wheel."),
    "request_flask": ("Bramble",
        "You'll need mill-water for the old lens. Here, take this glass flask."),
    "turn_wheel": ("Mallow",
        "The wheel turns! Mill-water flows into the greenhouse at last."),
    "fill_flask": ("Bramble",
        "Cool mill-water, just what the glass needs. Bring it here when you're ready."),
    "take_seed": ("Mallow",
        "A live ember-seed. It pulses warm in your hand -- the heart of the hollow."),
    "cool_lens": ("Bramble",
        "The glass must cool slow, in mill-water. There -- a dew-cooled lens, fit to focus the light."),
    "open_stair": ("Mallow",
        "You found the lens and the seed. The stair is clear -- climb when the hollow is ready."),
    "mount_lens": ("Mallow",
        "The lens sits in the lantern's socket, catching the last of the dusk."),
    "plant_seed": ("Mallow",
        "The seed is planted in the cradle. Now only the kindling remains."),
    "kindle_lantern": ("Mallow",
        "The Heart-Lantern ignites, and warm light spills down the whole hollow."),
    "ring_bell": ("Mallow",
        "The bell rings, and the fireflies come home."),
}

# Objects with no progression action (examine-only).
EXAMINE: Dict[str, Tuple[str, str]] = {
    "mural": ("Mallow",
        "The mural tells the founding: light, water, and a seed, kept in trust."),
}


class Game:
    """The live, input-driven session controller."""

    def __init__(self, world: Optional[World] = None):
        self.world = world or World()
        self.state: State = self.world.initial_state()
        self.facing: Tuple[int, int] = inputmap.direction_for(inputmap.MOVE_SOUTH)
        self._held: List[str] = []      # ordered move actions, most-recent first
        self._move_acc = 0.0
        self.move_interval = MOVE_INTERVAL
        self.dialogue: Optional[dict] = None
        self.target: Optional[str] = None
        self.quit = False
        self.frame = 0
        self.trace: List[dict] = []
        self._log("spawn", room=self.state.room, pos=list(self.state.pos))

    # -- event handling (the application input path) -------------------------
    def handle_event(self, event) -> None:
        if getattr(event, "type", None) == pygame.QUIT:
            self.quit = True
            self._log("quit_requested")
            return
        if not (inputmap.is_keydown(event) or inputmap.is_keyup(event)):
            return
        action = inputmap.action_for_key(getattr(event, "key", None))
        if action is None:
            return
        if inputmap.is_keydown(event):
            self._on_press(action)
        else:
            self._on_release(action)

    def _on_press(self, action: str) -> None:
        if action == inputmap.QUIT:
            self.quit = True
            self._log("quit_requested")
            return
        if action == inputmap.DISMISS:
            self._dismiss()
            return
        if self.dialogue is not None:
            # modal dialogue: only interact advances; movement is ignored
            if action == inputmap.INTERACT:
                self._dismiss()
            return
        if action == inputmap.INTERACT:
            self._interact()
            return
        if inputmap.is_move(action):
            self._press_move(action)

    def _on_release(self, action: str) -> None:
        if inputmap.is_move(action) and action in self._held:
            self._held.remove(action)

    def _press_move(self, action: str) -> None:
        # most-recent-pressed first (deterministic when two keys overlap)
        if action in self._held:
            self._held.remove(action)
        self._held.insert(0, action)
        self._set_facing(inputmap.direction_for(action))

    def _set_facing(self, d: Tuple[int, int]) -> None:
        if d != self.facing:
            self.facing = d
            self._log("facing", dir=list(d))
        self._resolve_target()

    def _resolve_target(self) -> Optional[str]:
        dx, dy = self.facing
        cell = (self.state.pos[0] + dx, self.state.pos[1] + dy)
        objs = self.world.objects_at(self.state.room, cell)
        new_target = objs[0] if objs else None
        if new_target != self.target:
            self.target = new_target
            self._log("target", target=new_target)
        return new_target

    # -- simulation ----------------------------------------------------------
    def tick(self, dt: float) -> None:
        self.frame += 1
        if self.dialogue is not None or not self._held:
            self._move_acc = 0.0
            return
        self._move_acc += dt
        while self._move_acc >= self.move_interval:
            self._move_acc -= self.move_interval
            d = inputmap.direction_for(self._held[0])
            if self._try_move(d):
                continue
            # blocked: don't buffer a burst against a wall
            self._move_acc = 0.0
            break

    def _try_move(self, d: Tuple[int, int]) -> bool:
        try:
            new_state = self.world.move(self.state, d)
        except BlockedError:
            self._set_facing(d)   # turning to face a wall/object is meaningful
            self._log("blocked", dir=list(d), pos=list(self.state.pos))
            return False
        self.state = new_state
        self._set_facing(d)
        self._log("move", dir=list(d), pos=list(self.state.pos), room=self.state.room)
        return True

    # -- interaction ---------------------------------------------------------
    def _interact(self) -> None:
        target = self._resolve_target()
        if target is None:
            self._log("interact", result="nothing_here")
            return
        action = self._available_action(self.state.room, target)
        if action is not None:
            self._perform(action)
        else:
            self._open_dialogue(*self._locked_line(target))
            self._log("interact", target=target, result="locked")

    def _available_action(self, room: str, target: str) -> Optional[dict]:
        for a in self.world.actions:
            if a["room"] == room and a["target"] == target:
                if set(a["requires"]) <= self.state.flags and \
                   set(a["needs"]) <= self.state.inventory:
                    return a
        return None

    def _perform(self, action: dict) -> None:
        flags = self.state.flags | frozenset(action["flags"])
        inventory = (self.state.inventory - frozenset(action["consume"])) \
                    | frozenset(action["grant"])
        self.state = State(self.state.room, self.state.pos, flags=flags,
                           inventory=inventory)
        speaker, text = DIALOGUE.get(
            action["id"], (self._speaker_for(action["target"]), ""))
        self._open_dialogue(speaker, text)
        self._log("interact", target=action["target"], result="performed",
                  action=action["id"], flags=sorted(action["flags"]),
                  grant=sorted(action["grant"]), consume=sorted(action["consume"]))

    def _locked_line(self, target: str) -> Tuple[str, str]:
        for a in self.world.actions:
            if a["room"] == self.state.room and a["target"] == target:
                missing_items = [n for n in a["needs"] if n not in self.state.inventory]
                parts = []
                if missing_items:
                    names = ", ".join(
                        self.world.data["items"].get(n, {}).get("name", n)
                        for n in missing_items)
                    parts.append("you need " + names)
                if set(a["requires"]) - self.state.flags:
                    parts.append("the world is not ready yet")
                text = "Not yet -- " + "; ".join(parts) + "." if parts else \
                       "Not yet."
                return (self._speaker_for(target), text)
        return EXAMINE.get(target, (self._speaker_for(target),
                                    "Nothing to do here just now."))

    def _speaker_for(self, target: str) -> str:
        chars = self.world.data.get("characters", {})
        if target in chars:
            return chars[target]["name"]
        return "Mallow"

    def _open_dialogue(self, speaker: str, text: str) -> None:
        self.dialogue = {"speaker": speaker, "text": text}
        self._log("dialogue", open=True, speaker=speaker)

    def _dismiss(self) -> None:
        if self.dialogue is not None:
            self.dialogue = None
            self._log("dialogue", open=False)

    def _log(self, kind: str, **fields) -> None:
        self.trace.append({"frame": self.frame, "kind": kind, **fields})

    # -- rendering -----------------------------------------------------------
    def scene_room(self) -> SceneRoom:
        rid = self.state.room
        if rid == "gate":
            room = build_room_gate()
            room.props = [p for p in room.props if p.kind != "player"]
            return room
        return self._generic_scene(rid)

    def _generic_scene(self, rid: str) -> SceneRoom:
        data = self.world.data["rooms"][rid]
        room = SceneRoom(9, data["title"], data.get("mood", ""))
        for cell in sorted(self.world.rooms[rid].obstacles):
            room.props.append(Prop("rock", cell[0], cell[1]))
        for name, cell in sorted(self.world.rooms[rid].objects.items()):
            room.props.append(Prop("marker", cell[0], cell[1], interactable=True))
        return room

    def render(self, w: int = 1280, h: int = 720, t: float = 0.0):
        room = self.scene_room()
        ox, oy = layout(room, w, h)
        surface = pygame.Surface((w, h))
        render_room(surface, room, t, ox, oy)
        self._draw_player(surface, ox, oy, t)

        # target feedback: mark + label the object the player faces
        dx, dy = self.facing
        cell = (self.state.pos[0] + dx, self.state.pos[1] + dy)
        cx, cy = ui.tile_top_center(cell[0], cell[1], ox, oy)
        target = self._resolve_target()
        ui.draw_target_marker(surface, cx, cy, target is not None)
        name = None
        if target is not None:
            name = OBJECT_NAMES.get(target, target)
            ui.draw_label_chip(surface, cx, cy, name)

        ui.draw_controls_hint(surface)
        if self.dialogue is None:
            if target is not None:
                verb = OBJECT_VERBS.get(target, "examine")
                prompt = f"E: {verb} {name}"
            else:
                prompt = "E: nothing here to interact with"
            ui.draw_prompt(surface, prompt)

        ui.draw_room_chip(surface, room.title, room.subtitle)
        if self.dialogue is not None:
            ui.draw_dialogue(surface, self.dialogue["speaker"],
                             self.dialogue["text"], h - 250)
        ui.draw_inventory(surface, sorted(self.state.inventory) or [""], 0, h - 100)
        return surface, ox, oy

    def _draw_player(self, surface, ox, oy, t: float) -> None:
        gx, gy = self.state.pos
        fx, fy = prop_anchor(gx, gy, 0, ox, oy)
        spr = get_sprite("player", gx, gy)
        dy = int(round(idle_bob(t))) if not self._held else 0
        surface.blit(spr, (fx - spr.get_width() // 2, fy - spr.get_height() + 2 + dy))
