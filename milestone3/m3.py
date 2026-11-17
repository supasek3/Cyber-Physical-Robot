import pygame 
import sys
import random
import math
from functions import *

def dist(r, target):
    return math.sqrt((r[0]-target[0])**2 + (r[1]-target[1])**2)

# decide function 

# for robots in all state the robot decides for itself
# if the robot is on the target it checks if there are other robot at the same position
# if there is then the 2 robots with the smallest id dos the pickup and removes the job

# For SEARCHING robots
# if the robot sees a target ahead then move forward to the target
# elif the robot is on the target sends a "FOUND" message with sender_id and target position and add the target to it's job's list
    # then create create a wait_until duration before changing the robot to waiting stage
# elif the searching robot has a job go to the job with the lowest priority and it changes to GO_TO state
# else random movement

# For WAITING robots
# if the current turn is more than the wait_until value. Remove the job and goes back to searching. Move forward so the robot does not wait on the same target
# elif the waiting robot does not sense the target remove the target from job and goes back to searching
# elif the robot is on the target and it is not in the job list add it in the job list and broadcast a found message
# elif the lowest job position is not at the waiting robot location then goto the job at the lowest target(a job with lower priority exists elsewhere preventing deadlock)
# else do nothing

# For GO_TO robots
# if the robot reaches the target with the lowest priority and the target has oready been picked up, go back to searching
# if the robot steps on to the target and the target is not in the job list. It creates a new job, sends out a find message and waits at the target
# it checks the job logs and goes to the job with the lowest priorit
# else it becomes a searching robot

# For PICKING UP robots
# sends out a done message and goes back to searching

def decide(r,seen,turn):
    #robot senses itself that there are other robot at the target position
    if seen["on_target"] and (len(seen["robot_at_same_pos"]) >= 1): 
        robots_on_target = sorted(seen["robot_at_same_pos"] + [r["id"]])
        if r["id"] in robots_on_target[:2]:
            r["state"] = "PICKUP"
            r["jobs"].pop((r["x"], r["y"]), None)
            return "PICKUP"

    if r["state"] == "SEARCH":            
        if seen["target_ahead"]:
            return "FORWARD"
        elif seen["on_target"]:
            r["outbox"] = {"type": "FOUND", "from": r["id"], "tpos": (r["x"], r["y"]), "turn": turn}
            r["jobs"][(r["x"], r["y"])] = {"prio": r["id"], "found": turn}
            r["state"] = "WAIT"
            min_wait = 4 * MEAN_DELAY + GRID_COLS + GRID_ROWS + 2
            r["wait_until"] = turn + random.randint(min_wait, 2 * min_wait)
            return "NOTHING"
        elif r["jobs"]:
            r["state"] = "GO_TO"
            return drive_to(r, lowest_job(r))
        return random.choice(["FORWARD","FORWARD","LEFT","RIGHT"])  
    
    elif r["state"] == "WAIT": 
        if turn > r["wait_until"]:
            r["jobs"].pop((r["x"], r["y"]), None)
            r["state"] = "SEARCH"
            return "FORWARD" 
        # the robot waiting on a target that has oready been picked up
        if not seen["on_target"]: 
            r["jobs"].pop((r["x"], r["y"]), None)
            r["state"] = "SEARCH"
            return random.choice(["FORWARD", "LEFT", "RIGHT"])
        # if the robot senses a target and it is not in the job
        elif (seen["on_target"]) and ((r["x"], r["y"]) not in r["jobs"]):
            r["jobs"][(r["x"], r["y"])] = {"prio": r["id"], "found": turn}
            r["outbox"] = {"type": "FOUND", "from": r["id"], "tpos": (r["x"], r["y"]), "turn": turn}
            return "NOTHING"
        # if the robot is not waiting on the lowest priority target there won't be any help
        if lowest_job(r) != (r["x"], r["y"]):
            r["state"] = "GO_TO"
            return drive_to(r, lowest_job(r))
        else:
            return "NOTHING"

    elif r["state"] == "GO_TO":
        # goes back to search if it went to an empty target
        if (r["x"],r["y"]) == lowest_job(r) and (not seen["on_target"]):
            r["jobs"].pop((r["x"], r["y"]), None)
            r["state"] = "SEARCH"
            return random.choice(["FORWARD","LEFT","RIGHT"])  
        # the robot senses a new target when it is on the way
        elif seen["on_target"]:
            if (r["x"],r["y"]) not in r["jobs"]:
                r["outbox"] = {"type": "FOUND", "from": r["id"], "tpos": (r["x"], r["y"]), "turn": turn}
                r["jobs"][(r["x"], r["y"])] = {"prio": r["id"], "found": turn}
            r["state"] = "WAIT"
            min_wait = 4 * MEAN_DELAY + GRID_COLS + GRID_ROWS + 2
            r["wait_until"] = turn + random.randint(min_wait, 2 * min_wait)
            return "NOTHING"
        # always drive to the target with lowest known priority
        elif r["jobs"]:
            return drive_to(r, lowest_job(r))
        else:
            r["state"] = "SEARCH"
            return random.choice(["FORWARD","LEFT","RIGHT"])  

    elif r["state"] == "PICKUP":
        r["outbox"] = {"type": "DONE", "from": r["id"], "tpos": (r["x"], r["y"]), "turn": turn}
        r["state"]= "SEARCH"
        return random.choice(["FORWARD","LEFT","RIGHT"])  


NUM_ROBOTS = 5
robots = []
for i in range(NUM_ROBOTS):
    robots.append(robot(i, random.randint(0, GRID_COLS - 1), random.randint(0, GRID_ROWS - 1)))

NUM_TARGETS = 30
targets = set() 

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((600, 600))
    pygame.display.set_caption("My First Pygame App")
    # 3. Create a clock object to control the frame rate
    status = "ACTIVE"         # Can be: "ACTIVE", "CAPTURED", "FAILED"
    status_timer = 0 
    clock = pygame.time.Clock()

    # Game Loop
    paused = False
    running = True
    turn = 0
    captures = 0
    STATE_COLORS = {"SEARCH": (0, 120, 255), "GO_TO": (255, 210, 0),
                    "WAIT": (255, 140, 0), "PICKUP": (0, 220, 120)}
    font = pygame.font.SysFont(None, 32)
    small = pygame.font.SysFont(None, 18)
    timer = 0
    max_turn = 1000
    targets = spawn_targets(NUM_TARGETS)
    while running and turn < max_turn:
        clock.tick(30)                       # ONE tick: 10 turns per second (smaller = slower)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                paused = not paused

        if not paused:
            turn += 1
            if not targets:
                targets = spawn_targets(NUM_TARGETS)

            # read input messages (only the ones whose delay has run out)
            for r in robots:
                read_messages(r)

            # sense + decide
            for r in robots:
                seen = sense(r, targets, robots)
                r["perform_action"] = decide(r, seen,turn)

            # test for illegal behaviour
            n_before = len(targets)
            targets = check_pickup(robots, targets, turn)
            captures += n_before - len(targets)

            # perform actions
            for r in robots:
                action(r, r["perform_action"])

            # send output messages (each receiver gets its own random delay)
            send_messages(robots)

        # DRAW every frame, after the robots have moved (also works while paused)
        screen.fill((30, 30, 45))
        display_grid_and_target(screen, targets)
        for r in robots:
            pygame.draw.polygon(screen, STATE_COLORS.get(r["state"], (0, 120, 255)), robot_triangle(r))

        by_cell = {}
        for r in robots:
            by_cell.setdefault((r["x"], r["y"]), []).append(r["id"])
        for cell, ids in by_cell.items():
            if len(ids) <= 3:
                text = ",".join(str(i) for i in sorted(ids))
            else:
                text = f"{len(ids)} robots"
            label = small.render(text, True, (255, 255, 255))
            cx, cy = x_cell_to_pixel(cell[0]), y_cell_to_pixel(cell[1])
            screen.blit(font.render(f"Turn {turn}   mean delay {MEAN_DELAY}", True, (255, 255, 255)), (10, 10))
            screen.blit(label, (cx - label.get_width() // 2, cy - CELL_SIZE // 2 - 1))
        screen.blit(small.render(f"captures {captures}   illegal pickups 0", True, (255, 255, 255)), (10, 40))
        x = 10
        for name, color in STATE_COLORS.items():
            pygame.draw.rect(screen, color, (x, 572, 14, 14))
            screen.blit(small.render(name, True, (255, 255, 255)), (x + 18, 572))
            x += 95
        if paused:
            screen.blit(font.render("PAUSED", True, (255, 0, 0)), (480, 10))

        pygame.display.flip()

    pygame.quit()
    sys.exit()  