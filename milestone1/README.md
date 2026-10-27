# Cyber Physical Robotics - Milestone 1

Python 3.10+ simulation that shows every illegal pick-up condition is detected.

- `milestone1.py` - standalone, beginner-style version built from your state machine and flowchart (plain functions, lists and dicts; no other files needed).
- `sim.py` - the engine: 10x10 grid, robots, random targets, broadcast channel with
  per-receiver exponential delay (mean set to 0 for milestone 1), and the illegal-behaviour test.
- `scenarios.py` - scripted scenarios S1-S5 plus a random stress test S6 with an independent checker.
- `visualize.py` - animated map: robots moving turn by turn, illegal pick-ups highlighted.
- `output.txt` - the log from the last run.
- `figures/` - grid snapshots used in the report; `figures/animations/` has a GIF per scenario.

Run:

    pip install matplotlib   # only needed for the figures
    python3 scenarios.py

It prints PASS/FAIL per scenario and ends with "ALL SCENARIOS PASS".

Watch the simulation (needs matplotlib):

    python3 visualize.py s1        # s1 to s6, or "random"
    python3 visualize.py random --robots 12 --turns 150 --seed 7
    python3 visualize.py all --save   # rewrite the GIFs

Space pauses and resumes the animation.

Your state machine + flowchart version:

    python3 milestone1.py                 # 4 robots, 1 target, N = 10 random moves, then pick up
    python3 milestone1.py --n 15 --seed 3 # change N, repeat a run with a seed
    python3 milestone1.py --robots 8 --vary-n
    python3 milestone1.py --demo          # hand-placed robots: every flowchart message appears
    python3 milestone1.py --show          # add this to any run to watch it as an animation
