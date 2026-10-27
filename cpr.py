import random

def make_grid():
    grid = []
    for i in range(10):
        row = []
        for j in range(10):
            row.append(".")
        grid.append(row)
    return grid

def print_grid(g):
    for row in g:
        print(" ".join(row))

class Robot:
    def __init__(self, robot_id, x, y, direction="N"):
        self.id = robot_id
        self.x = x
        self.y = y
        self.direction = direction 
        self.message_queue = []

    def turn_left(self):
        directions = ["N", "S", "E", "W"]
        idx = directions.index(self.direction)
        self.direction = directions[(idx + 1) % 4]

    def turn_right(self):
        directions = ["N", "E", "S", "W"]
        idx = directions.index(self.direction)
        self.direction = directions[(idx + 1) % 4]

    def move_forward(self, grid_size=10):
        new_x, new_y = self.x, self.y
        if self.direction == "N":
            new_y -= 1
        elif self.direction == "S":
            new_y += 1
        elif self.direction == "E":
            new_x += 1
        elif self.direction == "W":
            new_x -= 1

        if 0 <= new_x < grid_size and 0 <= new_y < grid_size:
            self.x = new_x
            self.y = new_y

    def get_front_cell_coordinates(self):
        """Returns the (x, y) coordinate directly in front of the robot."""
        dx, dy = 0, 0
        if self.direction == "N":
            dy = -1
        elif self.direction == "S":
            dy = 1
        elif self.direction == "E":
            dx = 1
        elif self.direction == "W":
            dx = -1
            
        front_x = self.x + dx
        front_y = self.y + dy
        return front_x, front_y

def validate_and_execute_pickups(robot_actions, targets):
    """
    robot_actions: List or dict of robot actions for the turn, e.g.:
                   [
                       {"robot_id": "A", "action": "PICKUP", "pos": (3, 5)},
                       {"robot_id": "B", "action": "PICKUP", "pos": (3, 5)}
                   ]
    targets: List or set of target coordinates [(x, y)]
    """
    pickup_attempts = {}

    for act in robot_actions:
        if act["action"] == "PICKUP":
            pos = act["pos"]
            if pos not in pickup_attempts:
                pickup_attempts[pos] = []
            pickup_attempts[pos].append(act["robot_id"])

    for pos, robots in pickup_attempts.items():
        count = len(robots)
        target_exists = pos in targets

        if not target_exists:
            print(f"ERROR Robots {robots} attempted pickup at {pos}, but NO target is there")

        elif count == 1:
            print(f"ERROR Robot {robots[0]} attempted pickup at {pos} ALONE")

        elif count > 2:
            print(f"ERROR {count} robots {robots} attempted pickup at {pos}")

        elif count == 2:
            print(f"SUCCESS")
            targets.remove(pos)  

grid = make_grid()


target_x = random.randint(0, 9)
target_y = random.randint(0, 9)
grid[target_y][target_x] = "T"

robot_id = ['a','b','c','d']
for r_id in robot_id:
    rx = random.randint(0, 9)
    ry = random.randint(0, 9)
    while grid[rx][ry] != '.':
            rx,ry = random.randint(0, 9),random.randint(0, 9)
    grid[rx][ry] = r_id

print_grid(grid)