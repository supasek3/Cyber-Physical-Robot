"""
Cyber Physical Robotics project - core simulation engine.

10x10 grid, a configurable number of robots, randomly appearing targets.
Implements the simulation loop exactly as given in the project brief:

    while iterations < max_iterations:
        if no more targets: generate random targets
        for all robots: read input messages
        for all robots: sense environment, decide action
        test for illegal behaviour
        for all robots: perform action
        for all robots: send output messages

Milestone 1: communication delay is switched off (delay = 0), and robot
behaviour is supplied by pluggable controllers, so that the illegal
pick-up conditions can be provoked on purpose and shown to be detected.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

GRID_SIZE = 10


# --------------------------------------------------------------------------
# Basic types
# --------------------------------------------------------------------------

class Heading(Enum):
    NORTH = (0, 1)
    EAST = (1, 0)
    SOUTH = (0, -1)
    WEST = (-1, 0)

    def left(self) -> "Heading":
        order = [Heading.NORTH, Heading.WEST, Heading.SOUTH, Heading.EAST]
        return order[(order.index(self) + 1) % 4]

    def right(self) -> "Heading":
        order = [Heading.NORTH, Heading.EAST, Heading.SOUTH, Heading.WEST]
        return order[(order.index(self) + 1) % 4]


class Action(Enum):
    FORWARD = "forward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    PICK_UP = "pick_up"


class Violation(Enum):
    NO_TARGET = "pick-up attempted where there is no target"
    SOLO_PICKUP = "exactly one robot attempted to pick up a target"
    CROWD_PICKUP = "more than two robots attempted to pick up a target"


Pos = tuple[int, int]


@dataclass
class Message:
    sender: int
    payload: dict


@dataclass
class Perception:
    """What a robot can sense in one turn (brief section 2.1)."""
    target_ahead: bool
    robots_ahead: list[int]
    robots_here: list[int]


@dataclass
class ViolationEvent:
    iteration: int
    kind: Violation
    position: Pos
    robot_ids: list[int]

    def __str__(self) -> str:
        return (f"[iter {self.iteration:>3}] ILLEGAL: {self.kind.value} "
                f"at {self.position} by robot(s) {self.robot_ids}")


@dataclass
class CaptureEvent:
    iteration: int
    position: Pos
    robot_ids: list[int]

    def __str__(self) -> str:
        return (f"[iter {self.iteration:>3}] VALID capture at {self.position} "
                f"by robots {self.robot_ids}")


# --------------------------------------------------------------------------
# Communication
# --------------------------------------------------------------------------

class MessageBus:
    """Broadcast channel with per-receiver delay.

    Each queued entry is [message, remaining_delay]. The delay is drawn
    separately for every receiver (brief section 2.3). With mean_delay = 0
    (milestone 1 and 2) every message is delivered on the next read.
    """

    def __init__(self, robot_ids: list[int], mean_delay: float, rng: random.Random):
        self.mean_delay = mean_delay
        self.rng = rng
        self.queues: dict[int, list[list]] = {rid: [] for rid in robot_ids}

    def _draw_delay(self) -> int:
        if self.mean_delay <= 0:
            return 0
        return int(round(self.rng.expovariate(1.0 / self.mean_delay)))

    def send(self, msg: Message) -> None:
        for rid, queue in self.queues.items():
            if rid != msg.sender:
                queue.append([msg, self._draw_delay()])

    def read(self, rid: int) -> list[Message]:
        delivered, waiting = [], []
        for entry in self.queues[rid]:
            if entry[1] == 0:
                delivered.append(entry[0])
            else:
                entry[1] -= 1
                waiting.append(entry)
        self.queues[rid] = waiting
        return delivered


# --------------------------------------------------------------------------
# Robots
# --------------------------------------------------------------------------

# A controller decides the robot's action from its perception and the
# messages it has received. It may also return a payload to broadcast.
Controller = Callable[["Robot", Perception, int], tuple[Action, Optional[dict]]]


@dataclass
class Robot:
    rid: int
    pos: Pos
    heading: Heading
    controller: Controller
    inbox: list[Message] = field(default_factory=list)
    pending_action: Optional[Action] = None
    outbox: Optional[dict] = None
    known: dict = field(default_factory=dict)  # free memory for controllers

    def ahead(self) -> Pos:
        dx, dy = self.heading.value
        return (self.pos[0] + dx, self.pos[1] + dy)


# --------------------------------------------------------------------------
# World
# --------------------------------------------------------------------------

def in_bounds(p: Pos) -> bool:
    return 0 <= p[0] < GRID_SIZE and 0 <= p[1] < GRID_SIZE


class World:
    def __init__(self, robots: list[Robot], *, targets: Optional[set[Pos]] = None,
                 n_random_targets: int = 3, mean_delay: float = 0.0,
                 seed: int = 0, auto_spawn: bool = True):
        self.rng = random.Random(seed)
        self.robots = robots
        ids = [r.rid for r in robots]
        if len(set(ids)) != len(ids):
            raise ValueError("robot IDs must be unique")
        self.targets: set[Pos] = set(targets or ())
        self.n_random_targets = n_random_targets
        self.auto_spawn = auto_spawn
        self.bus = MessageBus(ids, mean_delay, self.rng)
        self.iteration = 0
        self.violations: list[ViolationEvent] = []
        self.captures: list[CaptureEvent] = []
        self.log: list[str] = []
        self.snapshots: list[dict] = []

    # --- helpers ---------------------------------------------------------
    def robots_at(self, p: Pos) -> list[int]:
        return sorted(r.rid for r in self.robots if r.pos == p)

    def spawn_targets(self) -> None:
        free = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE)
                if (x, y) not in self.targets]
        for p in self.rng.sample(free, self.n_random_targets):
            self.targets.add(p)
        self.log.append(f"[iter {self.iteration:>3}] spawned targets "
                        f"{sorted(self.targets)}")

    def sense(self, r: Robot) -> Perception:
        a = r.ahead()
        return Perception(
            target_ahead=a in self.targets,
            robots_ahead=self.robots_at(a) if in_bounds(a) else [],
            robots_here=[i for i in self.robots_at(r.pos) if i != r.rid],
        )

    def snapshot(self, note: str = "") -> dict:
        return {
            "iteration": self.iteration,
            "targets": set(self.targets),
            "robots": [(r.rid, r.pos, r.heading, r.pending_action) for r in self.robots],
            "note": note,
        }

    # --- illegal-behaviour test -----------------------------------------
    def check_illegal(self) -> list[ViolationEvent]:
        """Group all PICK_UP intentions by cell and classify each group.

        A group is legal only if the cell holds a target and exactly two
        robots attempt the pick-up in the same turn.
        """
        attempts: dict[Pos, list[int]] = {}
        for r in self.robots:
            if r.pending_action is Action.PICK_UP:
                attempts.setdefault(r.pos, []).append(r.rid)

        found = []
        for pos, ids in sorted(attempts.items()):
            ids = sorted(ids)
            if pos not in self.targets:
                kind = Violation.NO_TARGET
            elif len(ids) == 1:
                kind = Violation.SOLO_PICKUP
            elif len(ids) > 2:
                kind = Violation.CROWD_PICKUP
            else:
                continue
            found.append(ViolationEvent(self.iteration, kind, pos, ids))
        return found

    # --- one iteration of the brief's loop -------------------------------
    def step(self) -> None:
        if not self.targets and self.auto_spawn:
            self.spawn_targets()

        for r in self.robots:
            r.inbox = self.bus.read(r.rid)

        for r in self.robots:
            perception = self.sense(r)
            r.pending_action, r.outbox = r.controller(r, perception, self.iteration)

        new_violations = self.check_illegal()
        self.violations.extend(new_violations)
        self.log.extend(str(v) for v in new_violations)
        self.snapshots.append(self.snapshot())

        self.perform_actions(illegal={(v.position) for v in new_violations})

        for r in self.robots:
            if r.outbox is not None:
                self.bus.send(Message(r.rid, r.outbox))
                r.outbox = None

        self.iteration += 1

    def perform_actions(self, illegal: set[Pos]) -> None:
        pickers: dict[Pos, list[int]] = {}
        for r in self.robots:
            a = r.pending_action
            if a is Action.FORWARD:
                nxt = r.ahead()
                if in_bounds(nxt):
                    r.pos = nxt  # walls block; robots may share a cell
            elif a is Action.TURN_LEFT:
                r.heading = r.heading.left()
            elif a is Action.TURN_RIGHT:
                r.heading = r.heading.right()
            elif a is Action.PICK_UP:
                pickers.setdefault(r.pos, []).append(r.rid)

        # Only legal pairs remove a target; illegal attempts change nothing.
        for pos, ids in pickers.items():
            if pos not in illegal and pos in self.targets and len(ids) == 2:
                self.targets.discard(pos)
                ev = CaptureEvent(self.iteration, pos, sorted(ids))
                self.captures.append(ev)
                self.log.append(str(ev))

    def run(self, max_iterations: int) -> None:
        while self.iteration < max_iterations:
            self.step()
