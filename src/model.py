from dataclasses import dataclass


@dataclass
class Node:
    id: int
    x: float
    z: float
    fixed_x: bool = False
    fixed_z: bool = False
    fx: float = 0.0
    fz: float = 0.0
    mass: float = 1.0


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
        ids = self.node_ids_sorted()
        return {nid: idx for idx, nid in enumerate(ids)}

    def ndofs(self) -> int:
        return 2 * len(self.nodes)

    def total_mass(self) -> float:
        return sum(n.mass for n in self.nodes.values())

    def remove_node(self, node_id: int) -> None:
        if node_id not in self.nodes:
            return
        del self.nodes[node_id]
        self.springs = [s for s in self.springs if s.i != node_id and s.j != node_id]

    def adjacency(self) -> dict[int, set[int]]:
        adj: dict[int, set[int]] = {nid: set() for nid in self.nodes.keys()}
        for s in self.springs:
            if s.i in adj and s.j in adj:
                adj[s.i].add(s.j)
                adj[s.j].add(s.i)
        return adj