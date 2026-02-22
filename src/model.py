from dataclasses import dataclass
import numpy as np

@dataclass
class Node:
    id: int
    x: float
    y: float
    fixed_x: bool = False
    fixed_y: bool = False
    fx: float = 0.0
    fy: float = 0.0
    mass: float = 1.0  # simple: 1 per node

@dataclass
class Spring:
    i: int  # node id
    j: int  # node id
    k: float

class Structure:
    def __init__(self, nodes: dict[int, Node], springs: list[Spring]):
        self.nodes = nodes
        self.springs = springs

    def node_ids_sorted(self) -> list[int]:
        return sorted(self.nodes.keys())

    def id_to_pos(self) -> dict[int, int]:
        # maps node_id -> 0..N-1
        ids = self.node_ids_sorted()
        return {nid: idx for idx, nid in enumerate(ids)}

    def ndofs(self) -> int:
        return 2 * len(self.nodes)

    def total_mass(self) -> float:
        return sum(n.mass for n in self.nodes.values())