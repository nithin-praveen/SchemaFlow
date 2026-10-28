"""Shared 2D character-grid canvas, box layout, and BFS connector routing.

Provides deterministic ASCII layout algorithms:
1. Box representation and port resolution.
2. Center-out grid positioning for connected schemas.
3. Orthogonal BFS pathfinding around obstacles with bend penalties.
4. Intelligent ASCII line and intersection character selection (─ │ ┌ ┐ └ ┘ ┼).
"""

from collections import deque
import heapq
from typing import Dict, List, Optional, Set, Tuple


class Box:
    """Represents a rendered ASCII box placed on the 2D grid canvas."""
    def __init__(self, name: str, lines: List[str], x: int = 0, y: int = 0):
        self.name = name
        self.lines = lines
        self.height = len(lines)
        self.width = max(len(line) for line in lines) if lines else 0
        self.x = x
        self.y = y

    def get_port(self, side: str) -> Tuple[int, int]:
        """Calculates connection port coordinates on the boundary of the box."""
        mid_x = self.x + (self.width // 2)
        mid_y = self.y + (self.height // 2)
        if side == "top":
            return (mid_x, self.y)
        if side == "bottom":
            return (mid_x, self.y + self.height - 1)
        if side == "left":
            return (self.x, mid_y)
        return (self.x + self.width - 1, mid_y)


class GridCanvas:
    """2D character canvas for layout and obstacle-avoiding line routing."""
    EMPTY = 0
    BOX_INTERIOR = 1
    BOX_BORDER = 2
    BUFFER = 3

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: List[List[str]] = [[" " for _ in range(width)] for _ in range(height)]
        self.mask: List[List[int]] = [[self.EMPTY for _ in range(width)] for _ in range(height)]
        self.boxes: Dict[str, Box] = {}

    def place_box(self, box: Box, x: int, y: int) -> None:
        """Paints a box onto the grid and registers collision obstacles."""
        box.x = x
        box.y = y
        self.boxes[box.name] = box

        # Mark 1-cell buffer around box so lines have clean clearance
        for r in range(max(0, y - 1), min(self.height, y + box.height + 1)):
            for c in range(max(0, x - 1), min(self.width, x + box.width + 1)):
                if self.mask[r][c] == self.EMPTY:
                    self.mask[r][c] = self.BUFFER

        # Blit box lines and mark interior/borders
        for r_idx, line in enumerate(box.lines):
            target_r = y + r_idx
            if target_r >= self.height:
                break
            for c_idx, char in enumerate(line):
                target_c = x + c_idx
                if target_c >= self.width:
                    break
                self.grid[target_r][target_c] = char
                if r_idx == 0 or r_idx == box.height - 1 or c_idx == 0 or c_idx == box.width - 1:
                    self.mask[target_r][target_c] = self.BOX_BORDER
                else:
                    self.mask[target_r][target_c] = self.BOX_INTERIOR

    def find_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Finds an orthogonal path between start and end avoiding box interiors/borders."""
        # Cost-penalized BFS/Dijkstra to favor straight lines with minimal turns
        pq: List[Tuple[int, int, int, int, int]] = [(0, start[0], start[1], 0, 0)]
        dist: Dict[Tuple[int, int, int, int], int] = {(start[0], start[1], 0, 0): 0}
        parent: Dict[Tuple[int, int, int, int], Tuple[int, int, int, int]] = {}
        best_end_state: Optional[Tuple[int, int, int, int]] = None

        while pq:
            cost, cx, cy, cdx, cdy = heapq.heappop(pq)
            if (cx, cy) == end:
                best_end_state = (cx, cy, cdx, cdy)
                break
            if cost > dist.get((cx, cy, cdx, cdy), float("inf")):
                continue

            for ndx, ndy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = cx + ndx, cy + ndy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue

                # Don't step into box interiors or borders unless it is the destination
                cell_type = self.mask[ny][nx]
                if (nx, ny) != end and (cell_type in (self.BOX_INTERIOR, self.BOX_BORDER)):
                    continue

                turn_cost = 0 if (cdx, cdy) in ((0, 0), (ndx, ndy)) else 6
                new_cost = cost + 1 + turn_cost
                state_key = (nx, ny, ndx, ndy)
                if new_cost < dist.get(state_key, float("inf")):
                    dist[state_key] = new_cost
                    parent[state_key] = (cx, cy, cdx, cdy)
                    heapq.heappush(pq, (new_cost, nx, ny, ndx, ndy))

        if not best_end_state:
            return None

        path: List[Tuple[int, int]] = []
        curr: Optional[Tuple[int, int, int, int]] = best_end_state
        while curr:
            path.append((curr[0], curr[1]))
            curr = parent.get(curr)
        path.reverse()
        return path

    def draw_connector(
        self,
        box_from: Box,
        box_to: Box,
        source_label: str = "1",
        target_label: str = "N",
        is_crow_foot: bool = True,
    ) -> None:
        """Routes and draws a connector line between two boxes with cardinality marks."""
        # Select best matching ports based on center offsets
        from_cx = box_from.x + box_from.width // 2
        from_cy = box_from.y + box_from.height // 2
        to_cx = box_to.x + box_to.width // 2
        to_cy = box_to.y + box_to.height // 2

        dx = to_cx - from_cx
        dy = to_cy - from_cy

        if abs(dx) > abs(dy):
            port_from = box_from.get_port("right" if dx > 0 else "left")
            port_to = box_to.get_port("left" if dx > 0 else "right")
        else:
            port_from = box_from.get_port("bottom" if dy > 0 else "top")
            port_to = box_to.get_port("top" if dy > 0 else "bottom")

        # Step 1 space outward from border ports to start navigation cleanly
        def step_out(pt: Tuple[int, int], b: Box) -> Tuple[int, int]:
            px, py = pt
            if px == b.x:
                return (max(0, px - 1), py)
            if px == b.x + b.width - 1:
                return (min(self.width - 1, px + 1), py)
            if py == b.y:
                return (px, max(0, py - 1))
            return (px, min(self.height - 1, py + 1))

        out_from = step_out(port_from, box_from)
        out_to = step_out(port_to, box_to)

        sub_path = self.find_path(out_from, out_to)
        if not sub_path:
            return

        full_path = [port_from] + sub_path + [port_to]

        # Draw the line segments on the grid
        for idx in range(1, len(full_path) - 1):
            x, y = full_path[idx]
            px, py = full_path[idx - 1]
            nx, ny = full_path[idx + 1]

            d_prev = (px - x, py - y)
            d_next = (nx - x, ny - y)
            dirs = {d_prev, d_next}

            char = "─"
            if dirs == {(0, -1), (0, 1)}:
                char = "│"
            elif dirs == {(-1, 0), (1, 0)}:
                char = "─"
            elif dirs == {(0, -1), (1, 0)}:
                char = "└"
            elif dirs == {(0, -1), (-1, 0)}:
                char = "┘"
            elif dirs == {(0, 1), (1, 0)}:
                char = "┌"
            elif dirs == {(0, 1), (-1, 0)}:
                char = "┐"

            existing = self.grid[y][x]
            if existing in ("─", "│", "┌", "┐", "└", "┘", "┼") and existing != char:
                char = "┼"

            self.grid[y][x] = char

        # Place source cardinality label near port_from
        sx, sy = out_from
        if 0 <= sy < self.height and 0 <= sx < self.width and source_label:
            # Place label slightly offset if on path
            self._place_label(sx, sy, source_label)

        # Place target cardinality / crow's foot near port_to
        tx, ty = out_to
        if 0 <= ty < self.height and 0 <= tx < self.width:
            arrow = "<" if is_crow_foot else ""
            label = f"{arrow}{target_label}" if arrow else target_label
            self._place_label(tx, ty, label)

    def _place_label(self, x: int, y: int, text: str) -> None:
        """Places a short label string adjacent to a coordinate without overwriting box borders."""
        start_x = max(0, min(self.width - len(text), x))
        for i, ch in enumerate(text):
            col = start_x + i
            if self.mask[y][col] not in (self.BOX_INTERIOR, self.BOX_BORDER):
                self.grid[y][col] = ch

    def render(self) -> str:
        """Renders the grid canvas into a clean, trimmed monochrome string."""
        lines = []
        for row in self.grid:
            line_str = "".join(row).rstrip()
            lines.append(line_str)
        # Remove trailing empty rows
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)
