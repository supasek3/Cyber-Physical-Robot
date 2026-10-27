"""
Animated view of the simulation: the 10x10 map, robots moving turn by turn,
targets, and every illegal pick-up highlighted as it is detected.

Run:
    python3 visualize.py s1            # open a window and play scenario S1
    python3 visualize.py s6 --speed 300
    python3 visualize.py random --robots 12 --turns 150 --seed 7
    python3 visualize.py all --save    # write a GIF per scenario to figures/animations/

Scenarios: s1 no target, s2 solo, s3 crowd, s4 legal pair, s5 all in one
turn, s6 random stress run, random (your own settings).
Keys in the window: space = pause/resume.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

import scenarios as sc
from sim import Action, Violation

SCENARIOS = {
    "s1": ("S1 Pick-up with no target", sc.scenario_no_target),
    "s2": ("S2 Single robot pick-up", sc.scenario_solo),
    "s3": ("S3 Three robots pick-up", sc.scenario_crowd),
    "s4": ("S4 Legal pair (control)", sc.scenario_valid_pair),
    "s5": ("S5 All conditions in one turn", sc.scenario_all_at_once),
    "s6": ("S6 Random stress run", sc.scenario_random),
}

ACTION_WORD = {Action.FORWARD: "forward", Action.TURN_LEFT: "turn left",
               Action.TURN_RIGHT: "turn right", Action.PICK_UP: "PICK UP", None: "-"}
SHORT = {Violation.NO_TARGET: "no target", Violation.SOLO_PICKUP: "solo",
         Violation.CROWD_PICKUP: "crowd"}


def build(name: str, args):
    if name == "random":
        w = sc.scenario_random(n_robots=args.robots, iterations=args.turns, seed=args.seed)
        title = f"Random run ({args.robots} robots, seed {args.seed})"
    else:
        title, fn = SCENARIOS[name]
        result = fn()
        w = result[0] if isinstance(result, tuple) else result
    # one extra frame showing the world after the last turn's actions
    final = {"iteration": w.iteration, "targets": set(w.targets),
             "robots": [(r.rid, r.pos, r.heading, None) for r in w.robots], "note": "end"}
    return title, w, w.snapshots + [final]


def side_text(world, frames, i):
    s = frames[i]
    it = s["iteration"]
    lines = [f"Turn {it}" + ("  (final state)" if s.get("note") == "end" else ""), ""]
    if s.get("note") != "end":
        lines.append("Chosen actions:")
        robots = sorted(s["robots"])
        for rid, pos, hd, act in robots[:12]:
            lines.append(f"  R{rid:<2} {str(pos):<7} {hd.name[0]}  {ACTION_WORD[act]}")
        if len(robots) > 12:
            lines.append(f"  ... and {len(robots) - 12} more")
        lines.append("")
    events = [v for v in world.violations if v.iteration == it]
    caps = [c for c in world.captures if c.iteration == it]
    lines.append("This turn:")
    if not events and not caps:
        lines.append("  nothing to report")
    for v in events:
        lines.append(f"  ILLEGAL {SHORT[v.kind]} at {v.position}")
        lines.append(f"     robots {v.robot_ids}")
    for c in caps:
        lines.append(f"  VALID capture at {c.position}")
        lines.append(f"     robots {c.robot_ids}")
    totals = Counter(v.kind for v in world.violations if v.iteration <= it)
    ncap = sum(1 for c in world.captures if c.iteration <= it)
    lines += ["", "Totals so far:",
              f"  no target  {totals[Violation.NO_TARGET]}",
              f"  solo       {totals[Violation.SOLO_PICKUP]}",
              f"  crowd      {totals[Violation.CROWD_PICKUP]}",
              f"  captures   {ncap}"]
    return "\n".join(lines)


def animate(name: str, args, save_path: str | None):
    import matplotlib
    if save_path:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter

    title, world, frames = build(name, args)
    fig = plt.figure(figsize=(9, 5.8))
    ax = fig.add_axes([0.05, 0.1, 0.55, 0.8])
    panel = fig.add_axes([0.63, 0.1, 0.35, 0.8])
    fig.text(0.5, 0.02, sc.LEGEND, ha="center", fontsize=7, color="#555")

    def update(i):
        ax.clear()
        panel.clear()
        panel.axis("off")
        sc.render(ax, world, frames[i])
        ax.set_title(title, fontsize=11)
        panel.text(0, 1, side_text(world, frames, i), va="top", ha="left",
                   family="monospace", fontsize=8)

    anim = FuncAnimation(fig, update, frames=len(frames), interval=args.speed, repeat=not save_path)

    if save_path:
        speed = min(args.speed, 200) if len(frames) > 60 else args.speed  # long runs play faster
        anim.save(save_path, writer=PillowWriter(fps=max(1, round(1000 / speed))))
        plt.close(fig)
        print(f"saved {save_path}")
        return

    paused = [False]

    def on_key(event):
        if event.key == " ":
            (anim.resume if paused[0] else anim.pause)()
            paused[0] = not paused[0]
    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scenario", choices=list(SCENARIOS) + ["random", "all"])
    p.add_argument("--speed", type=int, default=700, help="milliseconds per turn (default 700)")
    p.add_argument("--save", action="store_true", help="write a GIF instead of opening a window")
    p.add_argument("--robots", type=int, default=10, help="robots in a random run")
    p.add_argument("--turns", type=int, default=100, help="turns in a random run")
    p.add_argument("--seed", type=int, default=42, help="random seed for a random run")
    args = p.parse_args()

    try:
        import matplotlib  # noqa: F401
    except ImportError:
        sys.exit("matplotlib is needed: pip3 install matplotlib")

    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    if args.scenario == "all" and not args.save:
        sys.exit("use 'all' together with --save, or pick one scenario to watch")
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "animations")
    for n in names:
        path = None
        if args.save:
            os.makedirs(outdir, exist_ok=True)
            path = os.path.join(outdir, f"{n}.gif")
        animate(n, args, path)


if __name__ == "__main__":
    main()
