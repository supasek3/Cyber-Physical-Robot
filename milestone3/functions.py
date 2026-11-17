import pygame
import sys
import random
#import variables
# from m1 import GRID_ROWS,GRID_COLS,CELL_SIZE,MARGIN,CELL_COLOR,TARGET_COLOR,DIRS
#import functions
# from m1 import ahead,move_forward,turn_left,turn_right

CELL_SIZE = 40 # the px size of each cell
MARGIN = 2 # Gap between cells making grid line
BACKGROUND_COLOR = (255, 255, 255) #set background color to black
CELL_COLOR = (0, 0, 0) # set cell color to white
TARGET_COLOR = (255, 50, 50) # set target color to red
DIRS = ["N","E","S","W"]
GRID_ROWS = 10 #set simulation to 10 rows
GRID_COLS = 10 #set simulation to 10 columns
MEAN_DELAY = 20   # mean of the exponential message delay in turns (0 = no delay)

grid_total_width = (CELL_SIZE + MARGIN) * GRID_COLS - MARGIN
grid_total_height = (CELL_SIZE + MARGIN) * GRID_ROWS - MARGIN
start_x = (600 - grid_total_width) // 2
start_y = (600 - grid_total_height) // 2

def spawn_targets(n):
    targets = set()
    while len(targets) < n:
        x = random.randint(0, GRID_COLS - 1)
        y = random.randint(0, GRID_ROWS - 1)
        targets.add((x, y))   # a set ignores duplicates, so the loop just tries again
    return targets

# ------------------------------------------------------------ robot
def robot(rid, x, y):
    return {"id":rid, "x":x, "y":y, "dir": random.choice(DIRS), "state":"SEARCH",
            "jobs": {},          # tpos -> {"prio": lowest finder id, "found": turn found}
            "queue": [],         # waiting messages: [msg, countdown]
            "inbox": [],         # messages delivered this turn
            "outbox": None,      # at most one broadcast per turn
            "perform_action": None,
            "wait_until": 0
            }

# jobs are collected by target position as a target my only have one jobs, and for each target there are the priority of the find

def ahead(r):
    x, y = r["x"], r["y"] # robot x and y coordinate
    if r["dir"] == "N": y -= 1
    if r["dir"] == "S": y += 1
    if r["dir"] == "E": x += 1
    if r["dir"] == "W": x -= 1
    return (x, y)

def move_forward(r):
    x, y = ahead(r)
    if 0 <= x < GRID_ROWS and 0 <= y < GRID_COLS:  # blocked at the edge
        r["x"], r["y"] = x, y 

def turn_left(r):
    r["dir"] = DIRS[(DIRS.index(r["dir"]) - 1) % 4]

def turn_right(r):
    r["dir"] = DIRS[(DIRS.index(r["dir"]) + 1) % 4]

def x_cell_to_pixel(x):
    return start_x + x * (CELL_SIZE + MARGIN) + CELL_SIZE // 2 # convert input cell number into pixel

def y_cell_to_pixel(y):
    return start_y + y * (CELL_SIZE + MARGIN) + CELL_SIZE // 2

def robot_triangle(r):
    cx, cy = x_cell_to_pixel(r["x"]), y_cell_to_pixel(r["y"])
    s = CELL_SIZE // 3                       # half-size of the triangle
    if r["dir"] == "N": return [(cx, cy - s), (cx - s, cy + s), (cx + s, cy + s)]
    if r["dir"] == "S": return [(cx, cy + s), (cx - s, cy - s), (cx + s, cy - s)]
    if r["dir"] == "E": return [(cx + s, cy), (cx - s, cy - s), (cx - s, cy + s)]
    return                     [(cx - s, cy), (cx + s, cy - s), (cx + s, cy + s)]

# ------------------------------------------------------------ communication
#random delay generates a random number depending on the set mean delay
#send message adds the outbox messages from the sender to the recieving robot's queue excluding the sender. Each robot gets a different amount of message delay
#read message goes through the robot's queue, if it reaches 0(counting down by 1 each turn) the robot adds the message to it's inbox and "process_message"
#the proccess_message function does 2 things
    #1.) if the message type is "FOUND" and the job oready existed, the job priority = lower(sender_id,prio)
        #if the job isn't created then the sender becomes the job's priority, turn = current turn
    #2.) elif the message type is "DONE" it removes the target from the job's list. If the robot recieves a new "FOUND" message it re-adds the target to the job's list
        #and removes the target once it is on the target and senses that there is no target
def random_delay():
    if MEAN_DELAY <= 0:
        return 0
    return int(round(random.expovariate(1.0 / MEAN_DELAY)))

def send_messages(robots):
    # every OTHER robot gets the message with its own random delay
    for sender in robots:
        if sender["outbox"] is not None:
            for rcv in robots:
                if rcv is sender:
                    continue
                rcv["queue"].append([sender["outbox"], random_delay()])
            sender["outbox"] = None

def read_messages(r):
    # deliver messages whose countdown is 0, count the rest down
    inbox, waiting = [], []
    for msg, d in r["queue"]:
        if d == 0:
            inbox.append(msg)
        else:
            waiting.append([msg, d - 1])
    r["inbox"] = inbox
    r["queue"] = waiting
    for msg in inbox:
        process_message(r, msg)

#{"type": "FOUND", "from": 2, "tpos": (4, 7), "fid": 2, "turn": 15}
# tpos -> {"prio": lowest finder id, "found": turn found}

def process_message(r, msg):
    # FOUND -> add/merge job (keep lowest finder id), DONE -> remove job
    if msg is not None:
        if msg["type"] is not None:
            if msg["type"] == "FOUND" and msg["tpos"] in r["jobs"]:
                if msg["from"] < r["jobs"][msg["tpos"]]["prio"]:
                    r["jobs"][msg["tpos"]]["prio"] = msg["from"]
                else:
                    pass
            elif msg["type"] == "FOUND" and msg["tpos"] not in r["jobs"]:
                r["jobs"][msg["tpos"]] = {"prio" : msg["from"],"found" : msg["turn"]}
            elif msg["type"] == "DONE":
                r["jobs"].pop(msg["tpos"],None)
    


# ------------------------------------------------------------ sensing
def robot_ahead(r,robots):
    robot_id = []
    for m in robots:
        if ahead(r) == (m["x"],m["y"]):
            robot_id.append(m["id"])
    return robot_id

def robot_at_same_pos(r,robots):
    robot_id = []
    for m in robots:
        if (r["x"],r["y"]) == (m["x"],m["y"]) and (r["id"] != m["id"]):
            robot_id.append(m["id"])
    return robot_id

def sense(r,targets,robots):
    return {"target_ahead": ahead(r) in targets,
            "on_target": (r["x"],r["y"]) in targets,
            "robot_ahead": robot_ahead(r,robots),
            "robot_at_same_pos": robot_at_same_pos(r,robots)}


# ------------------------------------------------------------ movement
def drive_to(r, goal):
    gx, gy = goal
    if r["x"] < gx:   want = "E"
    elif r["x"] > gx: want = "W"
    elif r["y"] < gy: want = "S"
    elif r["y"] > gy: want = "N"
    else:
        return "NOTHING"                  # already at the goal
    if r["dir"] == want:
        return "FORWARD"
    i, j = DIRS.index(r["dir"]), DIRS.index(want)
    if (j - i) % 4 == 1:                  # wanted direction is one turn to the right
        return "RIGHT"
    return "LEFT"                         # left, or (two left turns)

# the lower job function output the target position with the lowest known job priority
# if there are several job with the same priority, the function outputs the one with the minimun target position
# a robot can have multiple job with the same priority as it may sense a target during GO_TO state. 
# for example, if robot 1 found a target and sends "found". robot 0 also finds a target and send "found". Once robot 1 recieve found it goes to robot 0. On the way to picking up target 0 if it finds another target and send another "found" and adds the target with priority 1. After picking up the target there will me multiple target with finder_id 1.
# This sorting method ensures that the robot go minimum position of the target with priority 1.
# Without the tie-break the robots can learn about the target in different order. By sorting it makes sure that the robots are always updated and will eventually go to the same target.

def lowest_job(r):
    priority = []
    for job in r["jobs"].values():
        priority.append(job["prio"])
    if priority != []:
        candidates = []
        for tpos, job in r["jobs"].items():
            if job["prio"] == min(priority):
                candidates.append(tpos)
        return min(candidates)
    return None

def action(r,act):
    if act == "FORWARD":
        move_forward(r)
    elif act == "LEFT":
        turn_left(r)
    elif act == "RIGHT":
        turn_right(r)

def check_pickup(robots, targets, turn):
    pickers = {} # (x, y) -> [robot ids]
    for r in robots:
        if r["perform_action"] == "PICKUP":
            pos = (r["x"], r["y"])
            if pos not in pickers:
                pickers[pos] = []
            pickers[pos].append(r["id"])

    for pos, ids in pickers.items():
        if pos not in targets:
            pygame.quit()
            sys.exit(f"[turn {turn}] ERROR Robots {ids} attempted pickup at {pos}, but NO target is there")
        elif len(ids) == 1:
            pygame.quit()
            sys.exit(f"[turn {turn}] ERROR Robot {ids[0]} attempted pickup at {pos} ALONE")
        elif len(ids) > 2:
            pygame.quit()
            sys.exit(f"[turn {turn}] ERROR {len(ids)} robots {ids} attempted pickup at {pos}")
        else:   # exactly 2
            print(f"[turn {turn}] CAPTURE robots {ids} picked up target at {pos}")
            targets.discard(pos)

    return targets

def display_grid_and_target(screen, targets):
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            x = start_x + col * (CELL_SIZE + MARGIN)
            y = start_y + row * (CELL_SIZE + MARGIN)
            cell_rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            if (col,row) in targets:
                pygame.draw.rect(screen, TARGET_COLOR, cell_rect)
            else:
                pygame.draw.rect(screen, CELL_COLOR, cell_rect)