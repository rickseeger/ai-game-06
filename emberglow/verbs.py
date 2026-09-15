"""Explicit verb model + interaction resolution for Emberglow Hollow.

This is the missing explicit-verb layer from node 4's partial stub. It owns:

  - the four classic verbs (examine / talk / take / use-item-on-target, plus walk
    which is movement's concern), and the contextual "interact" convenience verb;
  - the human-readable content (examine lines, cozy multi-line conversations for
    Mallow and Bramble, success/failure/locked lines, object display names);
  - a pure resolver that maps (verb, faced target, selected item) onto an Outcome:
    a success/failure/info/locked result, the dialogue lines to show, and the exact
    flag/inventory change to apply.

It is pure: no pygame, no rendering. All PROGRESSION state is expressed solely as
docs/world.json's actions (flags/requires/needs/consume/grant); this module never
invents a flag or item. The content (prose) is authored here exactly as the design
document authored dialogue content, but the one-shot chain and the item economy
always come from world.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

from .world import State

# -- verbs --------------------------------------------------------------------
EXAMINE = "examine"
TALK = "talk"
TAKE = "take"
USE = "use"
INTERACT = "interact"          # the E key: contextual "do the obvious thing"

VERBS: Tuple[str, ...] = (EXAMINE, TALK, TAKE, USE)

# -- outcome kinds ------------------------------------------------------------
SUCCESS = "success"
FAILURE = "failure"
INFO = "info"          # examine / neutral narration / hint conversation
LOCKED = "locked"      # a gated action whose world-state prerequisite is unmet

# -- object display names / verbs (target feedback) ---------------------------
OBJECT_NAMES: Dict[str, str] = {
    "mallow": "Mallow", "hollow_bell": "Hollow Bell", "hill_stair": "Hill Stair",
    "bramble": "Bramble", "forge": "Forge", "crank_socket": "Crank Socket",
    "water_spout": "Water Spout", "ember_seed": "Ember-Seed", "mural": "Mural",
    "seed_cradle": "Seed Cradle", "lens_mount": "Lens Mount",
    "focus_wheel": "Focus Wheel",
}

OBJECT_VERBS: Dict[str, str] = {
    "mallow": "talk to", "bramble": "talk to", "hollow_bell": "ring",
    "hill_stair": "climb", "forge": "use", "crank_socket": "use",
    "water_spout": "fill", "ember_seed": "take", "mural": "read",
    "seed_cradle": "plant", "lens_mount": "mount", "focus_wheel": "turn",
}


def item_name(world, item_id: str) -> str:
    return world.data.get("items", {}).get(item_id, {}).get("name", item_id)


def display_name(world, target: str) -> str:
    return OBJECT_NAMES.get(target, target)


# -- examine lines (every prop + both characters) -----------------------------
EXAMINE_LINES: Dict[str, str] = {
    "mallow": "Mallow, the old gatekeeper and lantern-tender, waits by the common "
              "with a patient, wistful look.",
    "bramble": "Bramble the forge-smith stands by the low-burning forge, bluff and warm.",
    "hollow_bell": "The Hollow Bell hangs in its wooden frame, waiting to ring the hollow home.",
    "hill_stair": "The Hill Stair climbs toward the Lantern Crown, its stone steps "
                  "choked with moss.",
    "forge": "The forge burns low, still hot enough to work glass.",
    "crank_socket": "An empty socket on the waterwheel where a handle once fit.",
    "water_spout": "The Water Spout stands dry, waiting for the mill-water to flow.",
    "ember_seed": "A warm, pulsing ember-seed rests in the greenhouse bed -- a live "
                  "spark of the hollow.",
    "mural": "The mural tells the founding: light, water, and a seed, kept in trust "
             "through the long dusk.",
    "seed_cradle": "The Seed Cradle waits beneath the dark lantern-crown, ready to "
                   "hold the spark.",
    "lens_mount": "The Lens Mount sits empty on the great lantern, waiting for its glass.",
    "focus_wheel": "The Focus Wheel will kindle the lantern, once the seed and the "
                   "lens are set.",
}

# -- success conversations (multi-line for talk actions, short for use/take) ---
ACTION_LINES: Dict[str, List[Tuple[str, str]]] = {
    "meet_mallow": [
        ("Mallow", "Ah -- the young ember-keeper. You've come at the worst of the Long Dusk."),
        ("Mallow", "The Heart-Lantern has gone out, and the hollow grows cold."),
        ("Mallow", "Take this crank -- it ought to free the stiff mill-wheel."),
        ("Mallow", "Water first, then the seed and the glass. Bring both back, and I'll clear the stair."),
    ],
    "request_flask": [
        ("Bramble", "Ember-keeper! The forge burns low, but it'll do the job."),
        ("Bramble", "You'll need mill-water for the old lens. Here, take this glass flask."),
        ("Bramble", "Fill it at the spout once the wheel turns, and bring it back full."),
    ],
    "turn_wheel": [
        ("Mallow", "The crank bites, and the great wheel turns."),
        ("Mallow", "Mill-water pours into the greenhouse at last."),
    ],
    "fill_flask": [
        ("Bramble", "Cool mill-water, just what the glass needs. Bring it back when you're ready."),
    ],
    "take_seed": [
        ("Mallow", "A live ember-seed. It pulses warm in your hand -- the heart of the hollow."),
    ],
    "cool_lens": [
        ("Bramble", "The glass must cool slow, in mill-water, or it'll crack."),
        ("Bramble", "There -- a dew-cooled lens, fit to focus the light."),
    ],
    "open_stair": [
        ("Mallow", "You found the dew-cooled lens and the ember-seed -- the hollow's hope, gathered."),
        ("Mallow", "The stair is clear. Climb, and kindle the lantern when the hollow is ready."),
    ],
    "mount_lens": [
        ("Mallow", "The lens sits in the lantern's socket, catching the last of the dusk."),
    ],
    "plant_seed": [
        ("Mallow", "The seed is planted in the cradle. Now only the kindling remains."),
    ],
    "kindle_lantern": [
        ("Mallow", "The Heart-Lantern ignites, and warm light spills down the whole hollow."),
    ],
    "ring_bell": [
        ("Mallow", "The bell rings, and the fireflies come home."),
    ],
}

SUCCESS_BLURB: Dict[str, str] = {
    "meet_mallow": "Mallow gives you the crank",
    "request_flask": "Bramble gives you the flask",
    "turn_wheel": "the wheel turns",
    "fill_flask": "the flask is full",
    "take_seed": "you take the ember-seed",
    "cool_lens": "you get the dew-cooled lens",
    "open_stair": "the stair is open",
    "mount_lens": "the lens is mounted",
    "plant_seed": "the seed is planted",
    "kindle_lantern": "the lantern is lit",
    "ring_bell": "the bell rings",
}

# -- locked lines (world-state prerequisite unmet) ----------------------------
LOCKED_LINES: Dict[str, str] = {
    "fill_flask": "The spout is dry -- the mill-water isn't flowing yet.",
    "take_seed": "The seed-bed is parched and hard -- it needs the mill-water first.",
    "open_stair": "Not yet. Bring me the dew-cooled lens and the ember-seed, and I'll clear the stair.",
    "kindle_lantern": "The lantern waits -- set the lens and plant the seed first.",
    "mount_lens": "The stair to the crown is still closed.",
    "plant_seed": "The stair to the crown is still closed.",
}

DONE_LINES: Dict[str, str] = {
    "ring_bell": "The bell has already rung -- the fireflies are home.",
}


# -- hint conversations (fallback talk to a character, no pending action) -----
def hint_lines(state: State, target: str) -> List[Tuple[str, str]]:
    F = state.flags
    I = state.inventory
    if target == "mallow":
        if "ended" in F:
            return [("Mallow", "They came home -- every last firefly, and my little companion too."),
                    ("Mallow", "The hollow will sleep warm tonight, thanks to you.")]
        if "lantern_lit" in F:
            return [("Mallow", "The lantern burns again. Ring the Hollow Bell, and the fireflies will come home.")]
        if "stair_open" in F:
            return [("Mallow", "The stair is open. Climb to the crown, set the seed and the lens, and kindle the light.")]
        if "met_mallow" in F:
            return [("Mallow", "The wheel first. Mill-water wakes the seed and cools the glass."),
                    ("Mallow", "Bring me the dew-cooled lens and the ember-seed, and I'll clear the stair.")]
        return [("Mallow", "Hm?")]
    if target == "bramble":
        if "lens_ready" in F:
            return [("Bramble", "Set the lens and the seed on the crown, then turn the focus wheel.")]
        if "flask_received" in F:
            if "full_flask" in I:
                return [("Bramble", "A full flask! Use it here, and I'll re-grind and quench the old lens.")]
            return [("Bramble", "Fill that flask at the mill spout once the wheel turns."),
                    ("Bramble", "Bring it back full, and I'll re-grind the old lens.")]
        return [("Bramble", "Hm?")]
    return []


# -- outcome ------------------------------------------------------------------
@dataclass
class Outcome:
    kind: str                                   # SUCCESS | FAILURE | INFO | LOCKED
    lines: List[Tuple[str, str]] = field(default_factory=list)
    flags: FrozenSet[str] = frozenset()
    grant: FrozenSet[str] = frozenset()
    consume: FrozenSet[str] = frozenset()
    action_id: Optional[str] = None
    detail: str = ""                            # short phrase for the UI feedback chip

    def apply(self, state: State) -> State:
        """Return the state this outcome produces (flags/inventory only)."""
        return State(
            state.room, state.pos,
            flags=state.flags | self.flags,
            inventory=(state.inventory - self.consume) | self.grant,
        )


@dataclass
class Conversation:
    """A modal, multi-line dialogue; advance with the interact key."""
    lines: List[Tuple[str, str]]
    tone: str = INFO
    index: int = 0

    @property
    def speaker(self) -> str:
        return self.lines[self.index][0] if self.index < len(self.lines) else ""

    @property
    def text(self) -> str:
        return self.lines[self.index][1] if self.index < len(self.lines) else ""

    @property
    def done(self) -> bool:
        return self.index >= len(self.lines)

    def advance(self) -> bool:
        """Advance one line; return True if more lines remain."""
        self.index += 1
        return not self.done

    def __getitem__(self, key: str):
        if key == "speaker":
            return self.speaker
        if key == "text":
            return self.text
        raise KeyError(key)


# -- action matching ----------------------------------------------------------
def _actions_for(world, room: str, target: str) -> List[dict]:
    return [a for a in world.actions if a["room"] == room and a["target"] == target]


def _pending(action: dict, state: State) -> bool:
    """True if the action has not yet been performed (its one-shot flag is unset)."""
    return not (set(action["flags"]) <= state.flags)


def _requires_met(action: dict, state: State) -> bool:
    return set(action["requires"]) <= state.flags


def _missing_needs(world, action: dict, state: State) -> List[str]:
    return [n for n in action["needs"] if n not in state.inventory]


def _locked_text(world, action: dict) -> str:
    return LOCKED_LINES.get(action["id"],
                            "Not yet -- the world isn't ready for that.")


def _done_text(world, action: dict) -> str:
    return DONE_LINES.get(action["id"], "That's already taken care of.")


# -- the resolver -------------------------------------------------------------
def resolve(world, state: State, room: str, target: str, verb: str,
            selected_item: Optional[str]) -> Outcome:
    """Resolve `verb` applied to the faced `target` into an Outcome.

    `selected_item` is the currently selected inventory item (or None). The
    contextual INTERACT verb delegates to the obvious specific verb.
    """
    if verb == INTERACT:
        if target in world.data.get("characters", {}):
            verb = TALK
        elif _has_take_action(world, state, room, target):
            verb = TAKE
        else:
            verb = USE

    if verb == EXAMINE:
        return Outcome(INFO, [("", EXAMINE_LINES.get(target, display_name(world, target)))],
                       detail="you look at the " + display_name(world, target))

    if verb == TALK:
        return _resolve_talk(world, state, room, target)

    if verb == TAKE:
        return _resolve_take(world, state, room, target)

    if verb == USE:
        return _resolve_use(world, state, room, target, selected_item)

    return Outcome(FAILURE, [("", "That can't be done.")])


def _has_take_action(world, state: State, room: str, target: str) -> bool:
    if target in world.data.get("characters", {}):
        return False
    for a in _actions_for(world, room, target):
        if not a["needs"] and _pending(a, state) and _requires_met(a, state):
            return True
    return False


def _resolve_talk(world, state: State, room: str, target: str) -> Outcome:
    name = display_name(world, target)
    if target not in world.data.get("characters", {}):
        return Outcome(FAILURE, [("", f"The {name} doesn't answer.")],
                       detail="nobody to talk to")
    for a in _actions_for(world, room, target):
        if a["needs"]:
            continue                       # a use-action, not a talk-action
        if _pending(a, state):
            if not _requires_met(a, state):
                return Outcome(LOCKED, [("", _locked_text(world, a))],
                               detail="not ready")
            return _success_outcome(world, a)
    return Outcome(INFO, hint_lines(state, target), detail=f"you talk to {name}")


def _resolve_take(world, state: State, room: str, target: str) -> Outcome:
    name = display_name(world, target)
    if target in world.data.get("characters", {}):
        return Outcome(FAILURE, [("", f"You can't take {name}.")],
                       detail=f"can't take {name}")
    for a in _actions_for(world, room, target):
        if a["needs"]:
            continue
        if _pending(a, state):
            if not _requires_met(a, state):
                return Outcome(LOCKED, [("", _locked_text(world, a))],
                               detail="not ready")
            return _success_outcome(world, a)
        return Outcome(FAILURE, [("", _done_text(world, a))],
                       detail="nothing left to take")
    return Outcome(FAILURE, [("", f"You can't take the {name}.")],
                   detail=f"can't take the {name}")


def _resolve_use(world, state: State, room: str, target: str,
                 selected_item: Optional[str]) -> Outcome:
    name = display_name(world, target)
    actions = _actions_for(world, room, target)

    # 1. an item is selected: look for the action that needs exactly it
    if selected_item is not None:
        for a in actions:
            if selected_item in a["needs"]:
                if not _pending(a, state):
                    return Outcome(FAILURE, [("", _done_text(world, a))],
                                   detail="already done")
                if not _requires_met(a, state):
                    return Outcome(LOCKED, [("", _locked_text(world, a))],
                                   detail="not ready")
                return _success_outcome(world, a)
        # no action needs the selected item here
        if any(a["needs"] for a in actions):
            return Outcome(FAILURE,
                           [("", f"The {item_name(world, selected_item)} doesn't do anything there.")],
                           detail="wrong item")
        return Outcome(FAILURE, [("", f"There's nothing to use the {item_name(world, selected_item)} on here.")],
                       detail="nothing to use it on")

    # 2. no item selected: bare "operate" actions (needs empty, e.g. focus wheel)
    for a in actions:
        if not a["needs"]:
            if not _pending(a, state):
                return Outcome(FAILURE, [("", _done_text(world, a))],
                               detail="already done")
            if not _requires_met(a, state):
                return Outcome(LOCKED, [("", _locked_text(world, a))],
                               detail="not ready")
            return _success_outcome(world, a)
    if any(a["needs"] for a in actions):
        need = actions[0]["needs"][0]
        return Outcome(FAILURE,
                       [("", f"You'll need the {item_name(world, need)} to use the {name}.")],
                       detail="need an item")
    return Outcome(FAILURE, [("", f"There's nothing to use the {name} on.")],
                   detail="nothing to use")


def _success_outcome(world, action: dict) -> Outcome:
    return Outcome(
        SUCCESS,
        ACTION_LINES.get(action["id"], [("", "")]),
        flags=frozenset(action["flags"]),
        grant=frozenset(action["grant"]),
        consume=frozenset(action["consume"]),
        action_id=action["id"],
        detail=SUCCESS_BLURB.get(action["id"], action["id"]),
    )
