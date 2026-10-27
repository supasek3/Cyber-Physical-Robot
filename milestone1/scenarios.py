"""
Milestone 1 scenarios: show that the simulation detects every illegal
pick-up condition, and that a legal pick-up (exactly two robots on a
target at the same time) is accepted.

Run:  python3 scenarios.py            (prints logs, writes figures/ if matplotlib is installed)
"""

from __future__ import annotations

import os
import random
import sys
from collections import Counter

from sim import (GRID_SIZE, Action, Heading, Robot, Violation, World)

F, L, R, P = Action.FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT, Action.PICK_UP


def scripted(actions: list[Action], announce: bool = True):
    """Controller that plays a fixed list of actions, then keeps turning
    right (a harmless 'wait'). Each turn it broadcasts its position and
    the action it chose, so message delivery can be checked as well."""
    def controller(robot: Robot, perception, it):
        for m in robot.inbox:
            robot.known.setdefault("heard", []).append((it, m.sender, m.payload["act"]))
        act = actions[it] if it < len(actions) else R
        payload = {"pos": robot.pos, "act": act.value} if announce else None
        return act, payload
    return controller


def random_controller(p_pick: float):
    """Uncoordinated 'greedy' robot: it wanders randomly, steps onto any
    target it sees ahead, then tries to pick it up whether or not a
    partner is there. It also sometimes picks up blindly. This is not the
    real behaviour (milestone 2), it is meant to provoke violations."""
    def controller(robot: Robot, perception, it):
        rng = robot.known.setdefault("rng", random.Random(robot.rid * 7919))
        if robot.known.get("on_target", 0) > 0:      # lingers on a target
            robot.known["on_target"] -= 1
            return (P, None) if rng.random() < 0.5 else (R, None)
        if perception.target_ahead:
            robot.known["on_target"] = 6
            return F, None
        if rng.random() < p_pick:
            return P, None
        return rng.choice([F, F, L, R]), None
    return controller


# --------------------------------------------------------------------------
# Scripted scenarios
# --------------------------------------------------------------------------

def scenario_no_target():
    """Robot 1 drives two squares and tries to pick up on an empty cell.
    Robots 2 and 3 do the same together on another empty cell (a pair is
    still illegal when there is no target)."""
    robots = [
        Robot(1, (1, 1), Heading.EAST, scripted([F, F, P])),
        Robot(2, (6, 6), Heading.NORTH, scripted([F, P])),
        Robot(3, (6, 8), Heading.SOUTH, scripted([F, P])),
    ]
    w = World(robots, targets={(8, 1)}, seed=1)
    w.run(4)
    return w, {Violation.NO_TARGET: 2}


def scenario_solo():
    """Robot 1 drives onto a target and tries to pick it up alone."""
    robots = [
        Robot(1, (2, 5), Heading.EAST, scripted([F, F, F, P])),
        Robot(2, (8, 8), Heading.WEST, scripted([L, L, L, L, L])),
    ]
    w = World(robots, targets={(5, 5)}, seed=2)
    w.run(5)
    return w, {Violation.SOLO_PICKUP: 1}


def scenario_crowd():
    """Three robots converge on one target and all try to pick it up."""
    robots = [
        Robot(1, (5, 3), Heading.EAST, scripted([F, F, P])),   # from the west
        Robot(2, (7, 5), Heading.SOUTH, scripted([F, F, P])),  # from the north
        Robot(3, (9, 3), Heading.WEST, scripted([F, F, P])),   # from the east
    ]
    w = World(robots, targets={(7, 3)}, seed=3)
    w.run(4)
    return w, {Violation.CROWD_PICKUP: 1}


def scenario_valid_pair():
    """Control case: exactly two robots pick up the same target in the
    same turn. This must NOT be flagged and the target must disappear."""
    robots = [
        Robot(1, (1, 4), Heading.EAST, scripted([F, F, P])),
        Robot(2, (3, 7), Heading.SOUTH, scripted([F, F, F, P])),
    ]
    # robot 2 needs one more step, so robot 1 waits by turning twice
    robots[0].controller = scripted([F, F, R, L, P])
    robots[1].controller = scripted([F, F, F, R, P])
    w = World(robots, targets={(3, 4), (8, 8)}, seed=4)
    w.run(6)
    return w, {}


def scenario_all_at_once():
    """All three illegal conditions, plus one legal pair, in the SAME turn
    at four different cells. Checks that detection is per cell and that
    one turn can raise several violations."""
    robots = [
        Robot(1, (0, 0), Heading.NORTH, scripted([P])),        # empty cell
        Robot(2, (2, 2), Heading.NORTH, scripted([P])),        # solo on target
        Robot(3, (5, 5), Heading.NORTH, scripted([P])),        # crowd of 3
        Robot(4, (5, 5), Heading.EAST, scripted([P])),
        Robot(5, (5, 5), Heading.SOUTH, scripted([P])),
        Robot(6, (8, 8), Heading.NORTH, scripted([P])),        # legal pair
        Robot(7, (8, 8), Heading.WEST, scripted([P])),
    ]
    w = World(robots, targets={(2, 2), (5, 5), (8, 8)}, seed=5)
    w.run(1)
    return w, {Violation.NO_TARGET: 1, Violation.SOLO_PICKUP: 1,
               Violation.CROWD_PICKUP: 1}


# --------------------------------------------------------------------------
# Random stress test with an independent checker
# --------------------------------------------------------------------------

def brute_force_count(snapshots):
    """Re-classify every recorded decision phase from scratch, without
    using World.check_illegal, to cross-check the detector."""
    counts = Counter()
    for s in snapshots:
        cells = {}
        for rid, pos, _, act in s["robots"]:
            if act is P:
                cells.setdefault(pos, 0)
                cells[pos] += 1
        for pos, n in cells.items():
            if pos not in s["targets"]:
                counts[Violation.NO_TARGET] += 1
            elif n == 1:
                counts[Violation.SOLO_PICKUP] += 1
            elif n > 2:
                counts[Violation.CROWD_PICKUP] += 1
            else:
                counts["valid"] += 1
    return counts


def scenario_random(n_robots=10, iterations=300, p_pick=0.05, seed=42):
    rng = random.Random(seed)
    robots = [Robot(i, (rng.randrange(GRID_SIZE), rng.randrange(GRID_SIZE)),
                    rng.choice(list(Heading)), random_controller(p_pick))
              for i in range(1, n_robots + 1)]
    w = World(robots, n_random_targets=6, seed=seed)
    w.run(iterations)
    return w


# --------------------------------------------------------------------------
# Figures (optional)
# --------------------------------------------------------------------------

def render(ax, world: World, s: dict):
    """Draw one recorded decision phase (snapshot) of the world onto ax."""
    from matplotlib.patches import Rectangle

    bad = {v.position: v for v in world.violations if v.iteration == s["iteration"]}
    good = {c.position for c in world.captures if c.iteration == s["iteration"]}

    ax.set_xlim(-0.5, GRID_SIZE - 0.5)
    ax.set_ylim(-0.5, GRID_SIZE - 0.5)
    ax.set_xticks(range(GRID_SIZE))
    ax.set_yticks(range(GRID_SIZE))
    ax.set_xticks([x - 0.5 for x in range(GRID_SIZE + 1)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(GRID_SIZE + 1)], minor=True)
    ax.grid(which="minor", color="#cccccc")
    ax.tick_params(which="minor", length=0)
    ax.set_aspect("equal")

    for pos, v in bad.items():
        ax.add_patch(Rectangle((pos[0] - .5, pos[1] - .5), 1, 1, color="#f4a6a6", zorder=0))
        label = {Violation.NO_TARGET: "NO TARGET", Violation.SOLO_PICKUP: "SOLO",
                 Violation.CROWD_PICKUP: "CROWD"}[v.kind]
        ly, va = (pos[1] + 0.55, "bottom") if pos[1] < GRID_SIZE - 1 else (pos[1] - 0.55, "top")
        ax.text(pos[0], ly, label, ha="center", va=va, fontsize=6.5,
                color="#b00000", weight="bold", zorder=5)
    for pos in good:
        ax.add_patch(Rectangle((pos[0] - .5, pos[1] - .5), 1, 1, color="#b5e3b5", zorder=0))
        ly, va = (pos[1] + 0.55, "bottom") if pos[1] < GRID_SIZE - 1 else (pos[1] - 0.55, "top")
        ax.text(pos[0], ly, "VALID", ha="center", va=va, fontsize=6.5,
                color="#1b6e1b", weight="bold", zorder=5)

    for t in s["targets"]:
        ax.plot(t[0], t[1], marker="*", markersize=20, color="#e0a800", zorder=1)

    by_cell = {}
    for rid, pos, hd, act in s["robots"]:
        by_cell.setdefault(pos, []).append((rid, hd, act))
    marker = {Heading.NORTH: "^", Heading.EAST: ">", Heading.SOUTH: "v", Heading.WEST: "<"}
    slots = [(-.22, .22), (.22, .22), (-.22, -.22), (.22, -.22)]
    for pos, rs in by_cell.items():
        for k, (rid, hd, act) in enumerate(rs):
            ox, oy = (0, 0) if len(rs) == 1 else slots[k % 4]
            x, y = pos[0] + ox, pos[1] + oy
            ax.plot(x, y, marker[hd], markersize=15 if len(rs) == 1 else 12,
                    color="#1f4e9c" if act is not P else "#7a1fa2",
                    markeredgecolor="white", zorder=4)
            ax.text(x, y, str(rid), ha="center", va="center", color="white",
                    fontsize=6.5, weight="bold", zorder=6)


LEGEND = ("star = target   triangle = robot (points where it faces)   "
          "purple = robot choosing PICK UP   red = illegal   green = legal")


def draw(world: World, snap_index: int, title: str, path: str):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    s = world.snapshots[snap_index]
    fig, ax = plt.subplots(figsize=(5.2, 5.6))
    render(ax, world, s)
    ax.set_title(f"{title}\n(iteration {s['iteration']}, decision phase)", fontsize=10)
    fig.text(0.5, 0.015, LEGEND, ha="center", fontsize=7, color="#555")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return True


# --------------------------------------------------------------------------

def main():
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
    os.makedirs(outdir, exist_ok=True)

    scripted_cases = [
        ("S1 Pick-up with no target", scenario_no_target),
        ("S2 Single robot pick-up", scenario_solo),
        ("S3 Three robots pick-up", scenario_crowd),
        ("S4 Legal pair (control)", scenario_valid_pair),
        ("S5 All conditions in one turn", scenario_all_at_once),
    ]
    all_ok = True
    for name, fn in scripted_cases:
        w, expected = fn()
        got = Counter(v.kind for v in w.violations)
        ok = got == Counter(expected)
        if name.startswith("S4"):
            ok = ok and len(w.captures) == 1
        all_ok &= ok
        print("=" * 72)
        print(f"{name}   ->   {'PASS' if ok else 'FAIL'}")
        print("-" * 72)
        for line in w.log:
            print("  " + line)
        print(f"  robots: {len(w.robots)}, iterations: {w.iteration}, "
              f"violations: {len(w.violations)}, valid captures: {len(w.captures)}")
        heard = {r.rid: len(r.known.get('heard', [])) for r in w.robots}
        print(f"  messages received per robot (zero delay): {heard}")
        key = (w.violations[0].iteration if w.violations
               else w.captures[0].iteration if w.captures else 0)
        draw(w, key, name, os.path.join(outdir, name.split()[0] + ".png"))

    print("=" * 72)
    print("S6 Random stress test (10 robots, 300 iterations, greedy uncoordinated robots)")
    print("-" * 72)
    w = scenario_random()
    detected = Counter(v.kind for v in w.violations)
    oracle = brute_force_count(w.snapshots)
    match = all(detected[k] == oracle[k] for k in Violation) and \
        oracle["valid"] == len(w.captures)
    all_ok &= match
    for k in Violation:
        print(f"  {k.value:<55} detector={detected[k]:>4}  checker={oracle[k]:>4}")
    print(f"  {'valid captures':<55} detector={len(w.captures):>4}  checker={oracle['valid']:>4}")
    print(f"  -> {'PASS' if match else 'FAIL'} (detector agrees with independent checker)")
    first = {}
    for v in w.violations:
        first.setdefault(v.kind, v.iteration)
    for k, it in first.items():
        draw(w, it, f"S6 Random run: first {k.name.replace('_', ' ').lower()}",
             os.path.join(outdir, f"S6_{k.name.lower()}.png"))

    print("=" * 72)
    print("ALL SCENARIOS PASS" if all_ok else "SOME SCENARIOS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
