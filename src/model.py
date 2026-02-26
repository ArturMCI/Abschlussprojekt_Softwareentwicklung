from dataclasses import dataclass, asdict
from tinydb import TinyDB
import os

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

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)



@dataclass
class Spring:
    i: int  # node id
    j: int  # node id
    k: float

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class Structure:

    db = TinyDB(os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")).table("structures")

    def __init__(self, nodes: dict[int, Node], springs: list[Spring], name: str = "Unnamed"):
        self.nodes = nodes
        self.springs = springs
        self.name = name
        self.id = None

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
    
    def to_dict(self):
        return {
            "name": self.name,
            "nodes": {nid: node.__dict__ for nid, node in self.nodes.items()},
            "springs": [spring.__dict__ for spring in self.springs],
        }

    @classmethod
    def from_dict(cls, data):
        nodes = {int(nid): Node(**nd) for nid, nd in data["nodes"].items()}
        springs = [Spring(**sd) for sd in data["springs"]]
        return cls(nodes, springs, name=data.get("name", "Unnamed"))
    
    @classmethod
    def list_all(cls):
        return [(doc.doc_id, doc["name"]) for doc in cls.db.all()]


    def save(self):
        if self.id is None:
            self.id = self.db.insert(self.to_dict())
        else:
            self.db.update(self.to_dict(), doc_ids=[self.id])
        return self.id


    @classmethod
    def load(cls, id: int):
        data = cls.db.get(doc_id=id)
        if data is None:
            raise ValueError(f"Keine Structure mit id {id} gefunden.")

        structure = cls.from_dict(data)
        structure.id = id
        return structure
    
    @classmethod
    def delete(cls, id: int):
        cls.db.remove(doc_ids=[id])