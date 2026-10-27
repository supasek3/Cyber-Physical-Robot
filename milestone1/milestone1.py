# Milestone 1: robots follow the state machine, the flowchart checks pick-ups.
# Run:  python3 milestone1.py         (4 robots, 1 target, N = 10)
#       python3 milestone1.py demo    (robots placed by hand: all 4 messages)
import random
import sys

SIZE = 10
N = 10
DIRS = ["N", "E", "S", "W"]


def move_forward(r):
    x, y = r["x"], r["y"]
    if r["dir"] == "N": y -= 1
    if r["dir"] == "S": y += 1
    if r["dir"] == "E": x += 1
    if r["dir"] == "W": x -= 1
    if 0 <= x < SIZE and 0 <= y < SIZE:  # blocked at the edge
        r["x"], r["y"] = x, y


# State machine: MOVE for N turns -> PICKUP once -> DONE
def decide(r):
    if r["state"] == "MOVE":
        r["moves"] += 1
        if r["moves"] >= r["N"]:
            r["state"] = "PICKUP"
        return random.choice(["LEFT", "RIGHT", "FORWARD"])
    if r["state"] == "PICKUP":
        r["state"] = "DONE"
        return "PICKUP"
    return "NOTHING"


# Flowchart: for each cell where robots try to pick up
def check_pickups(turn, attempts, targets):
    for pos, ids in attempts.items():
        if pos in targets and len(ids) == 2:
            print(f"[turn {turn}] SUCCESS")
            targets.remove(pos)
        elif pos not in targets:
            print(f"[turn {turn}] ERROR Robots {ids} attempted pickup at {pos}, but NO target is there")
        elif len(ids) > 2:
            print(f"[turn {turn}] ERROR {len(ids)} robots {ids} attempted pickup at {pos}")
        elif len(ids) == 1:
            print(f"[turn {turn}] ERROR Robot {ids[0]} attempted pickup at {pos} ALONE")


def run(robots, targets):
    for turn in range(max(r["N"] for r in robots) + 1):
        actions = {r["id"]: decide(r) for r in robots}

        attempts = {}
        for r in robots:
            if actions[r["id"]] == "PICKUP":
                attempts.setdefault((r["x"], r["y"]), []).append(r["id"])
        check_pickups(turn, attempts, targets)  # check before anyone acts

        for r in robots:
            i = DIRS.index(r["dir"])
            if actions[r["id"]] == "LEFT": r["dir"] = DIRS[(i - 1) % 4]
            if actions[r["id"]] == "RIGHT": r["dir"] = DIRS[(i + 1) % 4]
            if actions[r["id"]] == "FORWARD": move_forward(r)


def robot(rid, x, y, n):
    return {"id": rid, "x": x, "y": y, "dir": random.choice(DIRS),
            "state": "MOVE" if n > 0 else "PICKUP", "moves": 0, "N": n}


if len(sys.argv) > 1 and sys.argv[1] == "demo":
    # N = 0 so all pick up on turn 0: SUCCESS, NO target, more than two, ALONE
    robots = [robot(1, 1, 1, 0), robot(2, 1, 1, 0), robot(3, 8, 1, 0),
              robot(4, 5, 5, 0), robot(5, 5, 5, 0), robot(6, 5, 5, 0), robot(7, 8, 8, 0)]
    run(robots, [(1, 1), (5, 5), (8, 8)])
else:
    robots = [robot(i, random.randint(0, SIZE - 1), random.randint(0, SIZE - 1), N) for i in range(1, 5)]
    target = (random.randint(0, SIZE - 1), random.randint(0, SIZE - 1))
    print("Target at", target)
    for r in robots:
        print(f"Robot {r['id']} starts at ({r['x']}, {r['y']}) facing {r['dir']}")
    run(robots, [target])
