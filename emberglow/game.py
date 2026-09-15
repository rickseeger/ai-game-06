"""Game controller: real input -> movement, verbs, inventory, dialogue, feedback.

Owns the live session. Held directional keys (WASD / arrows) drive discrete grid
movement onto the 9x9 traversal in emberglow.world; facing follows the most recent
directional press; the context-sensitive target is the object in the cell the player
faces. The four explicit classic verbs (examine / talk / take / use-item-on-target,
from emberglow.verbs) act on the faced target, resolved by emberglow.verbs.resolve
into an Outcome that carries the dialogue lines, the success/failure/locked tone,
and the exact flag/inventory change (which is the only state the game mutates, per
docs/world.json). The E key is a contextual convenience that picks the obvious verb.
Inventory selection cycles with Tab/[. Dialogue is a multi-line Conversation
advanced with the interact key; escape dismisses. Success vs failure is made
visible in both the dialogue panel accent and the target-marker/prompt feedback.

All simulation is keyed on logical actions from emberglow.inputmap and never calls
World.move / verbs.resolve state-mutators directly from the trace driver -- the
runtime trace drives this controller through the real event queue
(pygame.event.post -> pygame.event.get -> Game.handle_event), the same application
input path a real keyboard feeds.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from . import inputmap, ui, verbs, worldreact
from .animation import idle_bob
from .geometry import prop_anchor
from .scene import render_room, layout
from .sprites import get_sprite
from .world import World, State, BlockedError

# Seconds between grid steps while a directional key is held.
MOVE_INTERVAL = 0.15

# Re-exported for callers (tools/tests) that imported them from game.py before.
OBJECT_NAMES = verbs.OBJECT_NAMES
OBJECT_VERBS = verbs.OBJECT_VERBS


class Game:
    """The live, input-driven session controller."""

    def __init__(self, world: Optional[World] = None):
        self.world = world or World()
        self.state: State = self.world.initial_state()
        self.facing: Tuple[int, int] = inputmap.direction_for(inputmap.MOVE_SOUTH)
        self._held: List[str] = []      # ordered move actions, most-recent first
        self._move_acc = 0.0
        self.move_interval = MOVE_INTERVAL
        self.dialogue: Optional[verbs.Conversation] = None
        self.target: Optional[str] = None
        self.selected_index: int = 0
        self.feedback: Optional[dict] = None    # {"tone", "text"} | None
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
            # modal dialogue: only interact advances; movement/verbs are ignored
            if action == inputmap.INTERACT:
                self._advance_dialogue()
            return
        if action == inputmap.INTERACT:
            self._verb(verbs.INTERACT)
            return
        if action == inputmap.EXAMINE:
            self._verb(verbs.EXAMINE)
            return
        if action == inputmap.TALK:
            self._verb(verbs.TALK)
            return
        if action == inputmap.TAKE:
            self._verb(verbs.TAKE)
            return
        if action == inputmap.USE:
            self._verb(verbs.USE)
            return
        if action == inputmap.NEXT_ITEM:
            self._cycle_item(1)
            return
        if action == inputmap.PREV_ITEM:
            self._cycle_item(-1)
            return
        if inputmap.is_move(action):
            self._press_move(action)

    def _on_release(self, action: str) -> None:
        if inputmap.is_move(action) and action in self._held:
            self._held.remove(action)

    def _press_move(self, action: str) -> None:
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

    # -- inventory selection -------------------------------------------------
    def _items(self) -> List[str]:
        return sorted(self.state.inventory)

    def selected_item(self) -> Optional[str]:
        items = self._items()
        if not items:
            return None
        return items[min(self.selected_index, len(items) - 1)]

    def _sync_selection(self, previous: Optional[str]) -> None:
        items = self._items()
        if previous is not None and previous in items:
            self.selected_index = items.index(previous)
        elif not items:
            self.selected_index = 0
        else:
            self.selected_index = min(self.selected_index, len(items) - 1)

    def _cycle_item(self, delta: int) -> None:
        items = self._items()
        if not items:
            self.selected_index = 0
            self._log("item", selected=None)
            return
        self.selected_index = (self.selected_index + delta) % len(items)
        self.feedback = None
        self._log("item", selected=self.selected_item())

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
            self._move_acc = 0.0
            break

    def _try_move(self, d: Tuple[int, int]) -> bool:
        try:
            new_state = self.world.move(self.state, d)
        except BlockedError:
            self._set_facing(d)
            self._log("blocked", dir=list(d), pos=list(self.state.pos))
            return False
        self.state = new_state
        self._set_facing(d)
        self.feedback = None
        self._log("move", dir=list(d), pos=list(self.state.pos), room=self.state.room)
        return True

    # -- verbs ---------------------------------------------------------------
    def _verb(self, verb: str) -> None:
        target = self._resolve_target()
        if target is None:
            self.feedback = {"tone": verbs.FAILURE, "text": "There's nothing there."}
            self._log("interact", verb=verb, result="nothing_here")
            return
        outcome = verbs.resolve(self.world, self.state, self.state.room, target,
                                verb, self.selected_item())
        self._apply_outcome(outcome)

    def _apply_outcome(self, outcome: verbs.Outcome) -> None:
        previous = self.selected_item()
        if outcome.kind == verbs.SUCCESS and outcome.action_id is not None:
            self.state = outcome.apply(self.state)
        self._sync_selection(previous)

        tone = outcome.kind
        if outcome.kind == verbs.LOCKED:
            tone = verbs.FAILURE        # locked renders as a failure (distinct text)

        if outcome.lines:
            self.dialogue = verbs.Conversation(outcome.lines, tone=tone)
            self._log("dialogue", open=True, speaker=self.dialogue.speaker,
                      tone=tone, lines=len(outcome.lines))
        self.feedback = {"tone": tone, "text": outcome.detail}
        self._log("interact", target=self.target, verb="verb", result=outcome.kind,
                  action=outcome.action_id, detail=outcome.detail,
                  flags=sorted(outcome.flags), grant=sorted(outcome.grant),
                  consume=sorted(outcome.consume))

    # -- dialogue ------------------------------------------------------------
    def _open_dialogue(self, lines, tone: str = verbs.INFO) -> None:
        self.dialogue = verbs.Conversation(list(lines), tone=tone)
        self._log("dialogue", open=True, speaker=self.dialogue.speaker, tone=tone)

    def _advance_dialogue(self) -> None:
        if self.dialogue is None:
            return
        if self.dialogue.advance():
            self._log("dialogue", open=True, speaker=self.dialogue.speaker,
                      index=self.dialogue.index)
        else:
            self.dialogue = None
            self.feedback = None
            self._log("dialogue", open=False)

    def _dismiss(self) -> None:
        if self.dialogue is not None:
            self.dialogue = None
            self.feedback = None
            self._log("dialogue", open=False)

    def _log(self, kind: str, **fields) -> None:
        self.trace.append({"frame": self.frame, "kind": kind, **fields})

    # -- rendering -----------------------------------------------------------
    def scene_room(self):
        return worldreact.build_scene_room(self.world, self.state.room, self.state.flags)

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
        tone = self.feedback["tone"] if self.feedback else None
        ui.draw_target_marker(surface, cx, cy, target is not None, tone=tone)
        if target is not None:
            name = verbs.OBJECT_NAMES.get(target, target)
            ui.draw_label_chip(surface, cx, cy, name)

        ui.draw_controls_hint(surface)
        if self.feedback is not None:
            ui.draw_prompt(surface, self.feedback["text"], tone=self.feedback["tone"])
        else:
            ui.draw_prompt(surface, self._prompt())

        ui.draw_room_chip(surface, room.title, room.subtitle)
        if self.dialogue is not None:
            ui.draw_dialogue(surface, self.dialogue.speaker, self.dialogue.text,
                             h - 250, tone=self.dialogue.tone)
        items = self._items()
        ui.draw_inventory(surface, items or [""],
                          self.selected_index if items else 0, h - 100)
        return surface, ox, oy

    def _prompt(self) -> str:
        target = self.target
        sel = self.selected_item()
        sel_name = verbs.item_name(self.world, sel) if sel else "item"
        if target is None:
            return "X: examine  T: talk  G: take  U: use  (walk to a person or object)"
        name = verbs.OBJECT_NAMES.get(target, target)
        if target in self.world.data.get("characters", {}):
            return f"T: talk to {name}   X: examine   U: use {sel_name}"
        if sel:
            return f"U: use {sel_name} on {name}   X: examine   G: take"
        return f"X: examine {name}   U: use   G: take"

    def _draw_player(self, surface, ox, oy, t: float) -> None:
        gx, gy = self.state.pos
        fx, fy = prop_anchor(gx, gy, 0, ox, oy)
        spr = get_sprite("player", gx, gy)
        dy = int(round(idle_bob(t))) if not self._held else 0
        surface.blit(spr, (fx - spr.get_width() // 2, fy - spr.get_height() + 2 + dy))
