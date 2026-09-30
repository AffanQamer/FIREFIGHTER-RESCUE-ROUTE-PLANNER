
import tkinter as tk
from tkinter import ttk, messagebox
import heapq
import math
import random
import time

ROWS, COLS = 18, 28
CELL = 30

# Cell types
EMPTY = 0
WALL = 1
FIRE = 2
DANGER = 3
DOOR = 4
STAIRS = 5
FIREFIGHTER = 6
VICTIM = 7

NAMES = {
    EMPTY: "Empty",
    WALL: "Wall",
    FIRE: "Fire",
    DANGER: "Dangerous Area",
    DOOR: "Blocked Door",
    STAIRS: "Stairs",
    FIREFIGHTER: "Firefighter",
    VICTIM: "Victim",
}

# Visual appearance
FILL = {
    EMPTY: "#f7f7f7",
    WALL: "#333333",
    FIRE: "#e74c3c",
    DANGER: "#f39c12",
    DOOR: "#8e44ad",
    STAIRS: "#3498db",
    FIREFIGHTER: "#2ecc71",
    VICTIM: "#e91e63",
}

SYMBOL = {
    FIRE: "🔥",
    DANGER: "!",
    DOOR: "X",
    STAIRS: "S",
    FIREFIGHTER: "F",
    VICTIM: "V",
}

# A* movement costs.
# Fire is treated as extremely expensive rather than completely forbidden,
# so the algorithm can still report a route if no safer alternative exists.
MOVE_COST = {
    EMPTY: 1.0,
    STAIRS: 1.4,
    DANGER: 5.0,
    DOOR: 100.0,
    FIRE: 50.0,
    FIREFIGHTER: 1.0,
    VICTIM: 1.0,
}

class RescuePlanner:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 Firefighter Rescue Route Planner - A* Search")
        self.root.resizable(False, False)

        self.grid = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        self.start = (1, 1)
        self.goal = (ROWS - 2, COLS - 2)
        self.grid[self.start[0]][self.start[1]] = FIREFIGHTER
        self.grid[self.goal[0]][self.goal[1]] = VICTIM

        self.tool = tk.StringVar(value="Wall")
        self.status = tk.StringVar(value="Ready. Select a tool and edit the building.")
        self.stats = tk.StringVar(value="Nodes: 0   Cost: 0   Time: 0 ms")
        self.heuristic = tk.StringVar(value="Manhattan")
        self.allow_diagonal = tk.BooleanVar(value=False)

        self.path = []
        self.visited = []
        self.frontier = []
        self.animating = False

        self.build_ui()
        self.draw_grid()

    def build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0)

        title = ttk.Label(
            main,
            text="🔥 Firefighter Rescue Route Planner",
            font=("Segoe UI", 18, "bold")
        )
        title.grid(row=0, column=0, columnspan=2, pady=(0, 3))

        subtitle = ttk.Label(
            main,
            text="A* finds an efficient rescue route while considering fire, danger, doors and stairs.",
            font=("Segoe UI", 9)
        )
        subtitle.grid(row=1, column=0, columnspan=2, pady=(0, 10))

        left = ttk.Frame(main)
        left.grid(row=2, column=0, sticky="n")

        self.canvas = tk.Canvas(
            left,
            width=COLS * CELL,
            height=ROWS * CELL,
            bg="white",
            highlightthickness=1
        )
        self.canvas.grid(row=0, column=0)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)

        right = ttk.Frame(main, padding=(12, 0, 0, 0))
        right.grid(row=2, column=1, sticky="ns")

        ttk.Label(right, text="MAP TOOLS", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        tools = [
            ("Wall", WALL),
            ("Fire 🔥", FIRE),
            ("Dangerous Area", DANGER),
            ("Blocked Door", DOOR),
            ("Stairs", STAIRS),
            ("Erase", EMPTY),
            ("Set Firefighter", FIREFIGHTER),
            ("Set Victim", VICTIM),
        ]

        for label, value in tools:
            ttk.Radiobutton(
                right, text=label, value=label, variable=self.tool
            ).pack(anchor="w", pady=2)

        ttk.Separator(right).pack(fill="x", pady=8)

        ttk.Label(right, text="A* SETTINGS", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        ttk.Label(right, text="Heuristic:").pack(anchor="w", pady=(4, 0))
        ttk.Combobox(
            right, textvariable=self.heuristic,
            values=["Manhattan", "Euclidean"],
            state="readonly", width=15
        ).pack(anchor="w")

        ttk.Checkbutton(
            right, text="Allow diagonal movement",
            variable=self.allow_diagonal
        ).pack(anchor="w", pady=5)

        ttk.Separator(right).pack(fill="x", pady=8)

        self.solve_btn = ttk.Button(
            right, text="🔥 FIND RESCUE ROUTE", command=self.solve
        )
        self.solve_btn.pack(fill="x", pady=3)

        ttk.Button(
            right, text="Animate A* Search", command=self.animate_solve
        ).pack(fill="x", pady=3)

        ttk.Button(
            right, text="Generate Sample Building", command=self.sample_building
        ).pack(fill="x", pady=3)

        ttk.Button(
            right, text="Clear Map", command=self.clear_map
        ).pack(fill="x", pady=3)

        ttk.Separator(right).pack(fill="x", pady=8)

        ttk.Label(right, text="RESULTS", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(
            right, textvariable=self.stats,
            wraplength=210, justify="left"
        ).pack(anchor="w", pady=4)

        ttk.Label(
            right, textvariable=self.status,
            wraplength=210, justify="left"
        ).pack(anchor="w", pady=4)

        legend = ttk.LabelFrame(right, text="Legend", padding=6)
        legend.pack(fill="x", pady=8)

        for cell_type in [EMPTY, WALL, FIRE, DANGER, DOOR, STAIRS, FIREFIGHTER, VICTIM]:
            row = ttk.Frame(legend)
            row.pack(fill="x")
            swatch = tk.Canvas(row, width=18, height=18, highlightthickness=0)
            swatch.create_rectangle(1, 1, 17, 17, fill=FILL[cell_type], outline="")
            swatch.pack(side="left")
            ttk.Label(row, text="  " + NAMES[cell_type]).pack(side="left")

    def draw_grid(self, visited=None, frontier=None, path=None):
        self.canvas.delete("all")
        visited = set(visited or [])
        frontier = set(frontier or [])
        path = set(path or [])

        for r in range(ROWS):
            for c in range(COLS):
                x1, y1 = c * CELL, r * CELL
                x2, y2 = x1 + CELL, y1 + CELL
                cell_type = self.grid[r][c]

                fill = FILL.get(cell_type, FILL[EMPTY])

                if (r, c) in visited and cell_type == EMPTY:
                    fill = "#d6eaf8"
                if (r, c) in frontier and cell_type == EMPTY:
                    fill = "#fcf3cf"
                if (r, c) in path:
                    fill = "#58d68d"

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fill, outline="#bbbbbb"
                )

                symbol = SYMBOL.get(cell_type, "")
                if symbol:
                    self.canvas.create_text(
                        x1 + CELL / 2, y1 + CELL / 2,
                        text=symbol, font=("Segoe UI Emoji", 14, "bold")
                    )

        # Draw route as a simple center-to-center line
        if len(path) > 1:
            ordered = self.path
            points = []
            for r, c in ordered:
                points.extend([c * CELL + CELL / 2, r * CELL + CELL / 2])
            self.canvas.create_line(
                *points, fill="#145a32", width=4,
                capstyle=tk.ROUND, joinstyle=tk.ROUND
            )

        # Repaint F and V above route
        for r, c, label in [
            (self.start[0], self.start[1], "F"),
            (self.goal[0], self.goal[1], "V")
        ]:
            x = c * CELL + CELL / 2
            y = r * CELL + CELL / 2
            self.canvas.create_oval(
                x - 10, y - 10, x + 10, y + 10,
                fill=FILL[FIREFIGHTER if label == "F" else VICTIM],
                outline="white", width=2
            )
            self.canvas.create_text(
                x, y, text=label, fill="white",
                font=("Segoe UI", 10, "bold")
            )

    def on_canvas_click(self, event):
        self.paint(event.x, event.y)

    def on_canvas_drag(self, event):
        self.paint(event.x, event.y)

    def paint(self, x, y):
        if self.animating:
            return

        c = int(x // CELL)
        r = int(y // CELL)

        if not (0 <= r < ROWS and 0 <= c < COLS):
            return

        selected = self.tool.get()

        # Remove old start/goal marker when moving them.
        if selected == "Set Firefighter":
            old = self.start
            self.grid[old[0]][old[1]] = EMPTY
            self.start = (r, c)
            if self.start == self.goal:
                self.goal = (max(0, r - 1), c)
            self.grid[r][c] = FIREFIGHTER
        elif selected == "Set Victim":
            old = self.goal
            self.grid[old[0]][old[1]] = EMPTY
            self.goal = (r, c)
            if self.goal == self.start:
                self.start = (min(ROWS - 1, r + 1), c)
            self.grid[r][c] = VICTIM
        else:
            if (r, c) == self.start or (r, c) == self.goal:
                return

            mapping = {
                "Wall": WALL,
                "Fire 🔥": FIRE,
                "Dangerous Area": DANGER,
                "Blocked Door": DOOR,
                "Stairs": STAIRS,
                "Erase": EMPTY,
            }
            self.grid[r][c] = mapping[selected]

        self.path = []
        self.visited = []
        self.frontier = []
        self.stats.set("Nodes: 0   Cost: 0   Time: 0 ms")
        self.status.set("Map edited.")
        self.draw_grid()

    def neighbors(self, node):
        r, c = node
        if self.allow_diagonal.get():
            directions = [
                (-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (-1, 1), (1, -1), (1, 1)
            ]
        else:
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                yield (nr, nc)

    def heuristic_value(self, a, b):
        dr = abs(a[0] - b[0])
        dc = abs(a[1] - b[1])
        if self.heuristic.get() == "Euclidean":
            return math.sqrt(dr * dr + dc * dc)
        return dr + dc

    def astar(self):
        start_time = time.perf_counter()

        open_heap = []
        counter = 0
        g_score = {self.start: 0.0}
        parent = {}
        closed = set()
        discovered_frontier = set([self.start])

        f0 = self.heuristic_value(self.start, self.goal)
        heapq.heappush(open_heap, (f0, counter, self.start))

        visit_order = []
        max_frontier = 1

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue

            closed.add(current)
            visit_order.append(current)
            discovered_frontier.discard(current)

            if current == self.goal:
                path = []
                node = current
                while node != self.start:
                    path.append(node)
                    node = parent[node]
                path.append(self.start)
                path.reverse()

                elapsed = (time.perf_counter() - start_time) * 1000
                return path, visit_order, discovered_frontier, g_score[current], elapsed

            for nb in self.neighbors(current):
                if self.grid[nb[0]][nb[1]] == WALL:
                    continue

                # Penalize diagonal moves slightly more.
                step = MOVE_COST.get(self.grid[nb[0]][nb[1]], 1.0)
                if nb[0] != current[0] and nb[1] != current[1]:
                    step *= math.sqrt(2)

                tentative = g_score[current] + step

                if tentative < g_score.get(nb, float("inf")):
                    parent[nb] = current
                    g_score[nb] = tentative
                    counter += 1
                    f = tentative + self.heuristic_value(nb, self.goal)
                    heapq.heappush(open_heap, (f, counter, nb))
                    discovered_frontier.add(nb)

            max_frontier = max(max_frontier, len(discovered_frontier))

        elapsed = (time.perf_counter() - start_time) * 1000
        return None, visit_order, discovered_frontier, None, elapsed

    def solve(self):
        if self.animating:
            return

        self.status.set("Running A*...")
        self.root.update_idletasks()

        path, visited, frontier, cost, elapsed = self.astar()

        self.path = path or []
        self.visited = visited
        self.frontier = frontier

        if path:
            self.stats.set(
                f"Nodes explored: {len(visited)}\n"
                f"Route steps: {len(path) - 1}\n"
                f"Route cost: {cost:.1f}\n"
                f"Search time: {elapsed:.2f} ms"
            )
            self.status.set(
                "Route found. Green cells show the safest/lowest-cost route."
            )
        else:
            self.stats.set(
                f"Nodes explored: {len(visited)}\n"
                f"Route: Not found\n"
                f"Search time: {elapsed:.2f} ms"
            )
            self.status.set(
                "No route exists. Remove some walls or blocked areas."
            )

        self.draw_grid(visited=visited, frontier=frontier, path=self.path)

    def animate_solve(self):
        if self.animating:
            return

        self.animating = True
        self.solve_btn.configure(state="disabled")
        self.status.set("Animating A* search...")
        self.path = []

        # Run the algorithm first to get its visit order.
        path, visited, frontier, cost, elapsed = self.astar()

        self.visited = []
        self.frontier = []
        self._animation_data = (path, visited, cost, elapsed)
        self._animate_step(0)

    def _animate_step(self, i):
        path, visited, cost, elapsed = self._animation_data

        if i < len(visited):
            self.visited.append(visited[i])
            self.draw_grid(
                visited=self.visited,
                frontier=visited[i + 1:i + 30],
                path=[]
            )
            self.status.set(
                f"A* exploring node {i + 1} of {len(visited)}..."
            )
            self.root.after(25, lambda: self._animate_step(i + 1))
            return

        self.path = path or []
        self.animating = False
        self.solve_btn.configure(state="normal")

        if path:
            self.stats.set(
                f"Nodes explored: {len(visited)}\n"
                f"Route steps: {len(path) - 1}\n"
                f"Route cost: {cost:.1f}\n"
                f"Search time: {elapsed:.2f} ms"
            )
            self.status.set("A* finished: rescue route found.")
        else:
            self.stats.set(
                f"Nodes explored: {len(visited)}\n"
                f"Route: Not found\n"
                f"Search time: {elapsed:.2f} ms"
            )
            self.status.set("A* finished: no route was found.")

        self.draw_grid(
            visited=visited,
            frontier=[],
            path=self.path
        )

    def clear_map(self):
        if self.animating:
            return

        self.grid = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        self.start = (1, 1)
        self.goal = (ROWS - 2, COLS - 2)
        self.grid[self.start[0]][self.start[1]] = FIREFIGHTER
        self.grid[self.goal[0]][self.goal[1]] = VICTIM
        self.path = []
        self.visited = []
        self.frontier = []
        self.stats.set("Nodes: 0   Cost: 0   Time: 0 ms")
        self.status.set("Map cleared.")
        self.draw_grid()

    def sample_building(self):
        if self.animating:
            return

        self.clear_map()

        # Outer walls
        for r in range(ROWS):
            self.grid[r][0] = WALL
            self.grid[r][COLS - 1] = WALL
        for c in range(COLS):
            self.grid[0][c] = WALL
            self.grid[ROWS - 1][c] = WALL

        # Internal walls / rooms
        for r in range(2, 15):
            if r not in (6, 11):
                self.grid[r][7] = WALL

        for r in range(3, 16):
            if r not in (4, 13):
                self.grid[r][17] = WALL

        for c in range(4, 25):
            if c not in (9, 21):
                self.grid[8][c] = WALL

        for c in range(3, 14):
            if c not in (5, 11):
                self.grid[13][c] = WALL

        # Stairs
        for r, c in [(3, 4), (4, 4), (5, 4), (11, 12), (12, 12), (14, 22)]:
            self.grid[r][c] = STAIRS

        # Dangerous zones
        danger_cells = [
            (4, 10), (4, 11), (5, 10), (5, 11),
            (10, 20), (10, 21), (11, 20),
            (14, 19), (15, 19), (15, 20)
        ]
        for r, c in danger_cells:
            self.grid[r][c] = DANGER

        # Fire zones
        fire_cells = [
            (3, 21), (3, 22), (4, 21),
            (10, 10), (10, 11), (11, 10),
            (15, 5), (15, 6)
        ]
        for r, c in fire_cells:
            self.grid[r][c] = FIRE

        # Blocked doors
        for r, c in [(6, 7), (11, 7), (4, 17), (13, 17), (8, 9), (8, 21)]:
            self.grid[r][c] = DOOR

        # Restore endpoints
        self.start = (1, 1)
        self.goal = (16, 25)
        self.grid[self.start[0]][self.start[1]] = FIREFIGHTER
        self.grid[self.goal[0]][self.goal[1]] = VICTIM

        self.path = []
        self.visited = []
        self.frontier = []
        self.stats.set("Nodes: 0   Cost: 0   Time: 0 ms")
        self.status.set("Sample building generated. Click 'Find Rescue Route'.")
        self.draw_grid()


if __name__ == "__main__":
    root = tk.Tk()
    app = RescuePlanner(root)
    root.mainloop()
