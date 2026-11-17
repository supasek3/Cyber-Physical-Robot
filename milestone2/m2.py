import pygame 
import sys
import random
import math
from functions import * 

NUM_TARGETS = 3   # targets per wave; a new wave spawns when all are captured

def robot(rid, x, y):
    return {"id":rid,
            "x":x,
            "y":y,
            "dir": random.choice(DIRS),
            "state":"SEARCH",
            "job":{"finder":None,"helper":None},
            "input":[],
            "last_input":[],
            "output":{"from":None,"type":None,"pos":None,"helper":None, "tpos":None},
            "tpos":None,
            "perform_action":None
            }


#input messages: FOUND, ARRIVED, DONE, CLAIM, ASSIGN, CLAIMING
#output messages: FOUND, ARRIVED, DONE, CLAIM, ASSIGN,CLAIMING

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

def dist(r, target):
    return math.sqrt((r[0]-target[0])**2 + (r[1]-target[1])**2)

def action(r,action):
    if action == "FORWARD":
        move_forward(r)
    elif action == "LEFT":
        turn_left(r)
    elif action == "RIGHT":
        turn_right(r)
    elif action == "PICKUP":
        return 

def sense(r,targets,robots):
    return {"target_ahead": ahead(r) in targets,
            "on_target": (r["x"],r["y"]) in targets,
            "robot_ahead":robot_ahead(r,robots),
            "robot_at_same_pos":robot_at_same_pos(r,robots)}

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


#ROBOT STATE
#finder
#SEARCH -> WAIT_HELPER -> WAIT_ARRIVAL -> PICKUP -> SEARCH

#helper
#SEARCH -> GO_TO -> HELPER_READY -> PICKUP -> SEARCH      

def check_pickup(robots,targets,turn):
    pickers = {}                                  # (x, y) -> [robot ids]
    for r in robots:
        if r["perform_action"] == "PICKUP":
            pos = (r["x"],r["y"])
            if pos not in pickers:
                pickers[pos] = []
            pickers[pos].append(r["id"])
    for pos, ids in pickers.items():
        if pos not in targets:
            print(f"[turn {turn}] ERROR Robots {ids} attempted pickup at {pos}, but NO target is there")
        elif len(ids) == 1:
            print(f"[turn {turn}] ERROR Robot {ids[0]} attempted pickup at {pos} ALONE")
        elif len(ids) > 2:
            print(f"[turn {turn}] ERROR {len(ids)} robots {ids} attempted pickup at {pos}")
        else:
            print(f"[turn {turn}] CAPTURE robots {ids} picked up target at {pos}")
            targets.discard(pos)
    return targets

def decide(r,seen):
    s = r["state"]
    if s == "SEARCH": 
        for messages in r["input"]:
            if messages["type"] == "FOUND" and (r["id"] != r["job"]["finder"]):#if message is FOUND
                    r["job"]["finder"] = messages["from"]#add the finder to robot's job
                    r["output"] = {"from":r["id"],"type":"CLAIM","pos":(r["x"],r["y"]),"tpos":messages["tpos"]}#send a claim message saying that the robot is avalable
                    r["tpos"] = messages["tpos"]#save the target position
                    r["state"] = "WAIT_ASSIGN"
                    return "NOTHING"  
            elif messages["type"] == "DONE" and messages["pos"] == r["tpos"]:   # only my target's DONE
                    r["job"] = {"finder":None,"helper":None}
                    r["tpos"] = None

        if (seen["target_ahead"]) and (r["job"]["finder"] is None):
            r["output"] = {"from": r["id"], "type": "FOUND", "pos": (r["x"],r["y"]), "tpos":ahead(r)}
            goal = ahead(r)
            r["tpos"] = goal
            r["job"]["finder"] = r["id"]
            r["state"] = "WAIT_HELPER"
            return "FORWARD" #if seen target ahead move forward and robot is the finder
        return random.choice(["FORWARD","LEFT","RIGHT"])       
    
    elif s == "WAIT_ASSIGN":
        for messages in r["input"]:
            if messages["type"] == "ASSIGN" and (r["id"] == messages["helper"]) and messages["tpos"] == r["tpos"]:#if the searching robot sees an assign message and check if the robot id is equal to the helper_id in the message
                    r["job"]["helper"] = r["id"] # in the job set the robot to be the helper
                    helper_id = r["id"]
                    r["output"] = {"from":r["id"],"type":"ASSIGNED","helper":helper_id}
                    r["state"] = "GO_TO" # change the robot state to goto
                    return drive_to(r,r["tpos"])
            elif messages["type"] == "ASSIGN" and (r["id"] != messages["helper"]) and messages["tpos"] == r["tpos"]:
                #helper_id = r["id"]
                r["job"]["helper"] = messages["helper"]
                r["state"] = "SEARCH"
                return random.choice(["FORWARD","LEFT","RIGHT"]) 
            elif messages["type"] == "DONE" and messages["pos"] == r["tpos"]:
                r["job"] = {"finder":None,"helper":None}
                r["state"] = "SEARCH"
                return random.choice(["FORWARD","LEFT","RIGHT"]) 
        return "NOTHING"
            
    elif s == "WAIT_HELPER": #waiting for helper to be chosen
        distance =[];rid = [];finder_ids = []
        r["output"] = {"from": r["id"], "type": "FOUND", "pos": (r["x"],r["y"]), "tpos":(r["x"],r["y"])}
        for messages in r["input"]:#finder read inbox messages
            if messages["type"] == "CLAIM" and messages["tpos"] == r["tpos"]: #if the robot see a claim message for its target
                rid.append(messages["from"]) #save the claimer id
                distance.append(dist(messages["pos"], r["tpos"]))#save the distance of the helper from the target in a list

            elif messages["type"] == "FOUND" and messages["tpos"] == r["tpos"]:   # finders of MY target only
                finder_ids.append(messages["from"])

            elif messages["type"] == "DONE" and messages["pos"] == r["tpos"]:
                r["job"] = {"finder":None,"helper":None}
                r["state"] = "SEARCH"
                return random.choice(["FORWARD","LEFT","RIGHT"]) 

        if len(finder_ids) >= 2:
            first_two = finder_ids[:2]
            for a in first_two:
                if r["id"] == a:
                    r["state"] = "PICKUP"
                    return "PICKUP"

        if distance != []: # if the distance list is not empty
            helper_id = rid[distance.index(min(distance))] # find out the robot with the minimum distance
            r["job"]["helper"] = helper_id #make that robot the helper
            r["output"] = {"from":r["id"],"type":"ASSIGN","pos":(r["x"],r["y"]),"helper":helper_id, "tpos":r["tpos"]} #send out the helper assignment information
            r["state"] = "WAIT_ARRIVAL"
        return "NOTHING"

    elif s == "GO_TO":
        for messages in r["input"]:
            if messages["type"] == "DONE" and messages["pos"] == r["tpos"]:
                r["job"] = {"finder":None,"helper":None}
                r["state"] = "SEARCH"
                return random.choice(["FORWARD","LEFT","RIGHT"])
        if (r["x"],r["y"]) == r["tpos"]:
            r["output"] = {"from":r["id"],"type":"ARRIVED","pos":(r["x"],r["y"])}
            r["state"] = "HELPER_READY"
            return "NOTHING"
        else:
            return drive_to(r,r["tpos"])

    elif s == "WAIT_ARRIVAL":
        for messages in r["input"]:#finder read inbox messages
            if messages["type"] == "ARRIVED" and messages["pos"] == r["tpos"]:
                r["state"] = "PICKUP"
                return "PICKUP" 
            elif messages["type"] == "DONE" and messages["pos"] == r["tpos"]:
                r["job"] = {"finder":None,"helper":None}
                r["state"] = "SEARCH"
                return random.choice(["FORWARD","LEFT","RIGHT"]) 
        return "NOTHING"   

    elif s == "HELPER_READY":
        if seen["robot_at_same_pos"]:
            r["state"] = "PICKUP"
            return "PICKUP"
        for messages in r["input"]:   
            if messages["type"] == "DONE" and messages["pos"] == r["tpos"]:
                r["job"] = {"finder":None,"helper":None}
                r["state"] = "SEARCH"
                return random.choice(["FORWARD","LEFT","RIGHT"]) 
            
        return "NOTHING"

    elif s == "PICKUP":
        r["output"] = {"from":r["id"],"type":"DONE","pos":(r["x"],r["y"])}
        r["job"] = {"finder":None,"helper":None}
        r["input"] = []
        r["state"] = "SEARCH"
        return random.choice(["FORWARD","LEFT","RIGHT"]) 



grid_total_width = (CELL_SIZE + MARGIN) * GRID_COLS - MARGIN # square, margin, square, margin, square, ... 
grid_total_height = (CELL_SIZE + MARGIN) * GRID_ROWS - MARGIN

start_x = (600 - grid_total_width) // 2 # position of top right corner where the center of the grid is aligned with background size
start_y = (600 - grid_total_height) // 2

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
    robots = [robot(0, 1, 1), robot(1, 8, 8),robot(2,2,2),robot(3,3,3)]
    turn = 0
    timer = 0
    max_turn = 1000
    targets = spawn_targets(NUM_TARGETS)
    while running and turn < max_turn:
        dt = clock.tick(20)
        screen.fill((30, 30, 45))  # Fills the background with a dark blue color
        # 4. Event Handling (e.g., checking if the user closed the window)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                paused = not paused

        if not paused:
            turn += 1
        # 5. Game Logic goes here
            if not targets:                      # all captured -> new wave
                targets = spawn_targets(NUM_TARGETS)
            display_grid_and_target(screen, targets)
            for r in robots:
                #pygame.draw.polygon(screen, (0, 120, 255),((x_cell_to_pixel(r["x"])), (y_cell_to_pixel(r["y"]))), CELL_SIZE // 3) # generate robot
                pygame.draw.polygon(screen, (0, 120, 255), robot_triangle(r))

                        
            #for all robot read input
            for r in robots: #for all robot
                r["input"] = [] # a robot input is empty
                for m in robots: #for all robot
                    if m["output"] is not None:
                        r["input"].append(m["output"])
            for r in robots:
                r["output"] = None
            

            # for all robot
            for r in robots:
                #sense enviroment
                #decide action to perform
                seen = sense(r,targets,robots)
                r["perform_action"] = decide(r,seen)
            
            #Test for illegal behavior here
            print([r["job"] for r in robots])
            targets = check_pickup(robots,targets,turn)

            for r in robots:
                action(r,r["perform_action"])
            send = []
            for r in robots:
                if r["output"] is not None:
                    send.append(r["output"])
        else:
            font = pygame.font.SysFont(None, 48)
            screen.blit(font.render("PAUSED", True, (255, 0, 0)), (10, 10))

        print(turn)
        print([(r["x"],r["y"]) for r in robots])
        print("targets:", targets)
        print([r["state"] for r in robots])
        print([r["state"] for r in robots])
        print([r["input"] for r in robots])
        print([r["output"] for r in robots])
        # 7. Update the screen
        pygame.display.flip()

    # Clean up and exit cleanly
    pygame.quit()
    sys.exit()  