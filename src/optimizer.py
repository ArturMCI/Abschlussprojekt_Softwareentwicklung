import copy
import numpy as np

from src.model import Structure
from src.solver import solve_displacements


def spring_energy(struct: Structure, disp: dict[int, tuple[float, float]]) -> dict[tuple[int, int], float]:
    energies: dict[tuple[int, int], float] = {}

    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]

        dx = nj.x - ni.x
        dz = nj.z - ni.z
        L = float(np.hypot(dx, dz))
        if L == 0.0:
            continue

        c = dx / L
        s = dz / L

        uix, uiz = disp[sp.i]
        ujx, ujz = disp[sp.j]

        delta = c * (ujx - uix) + s * (ujz - uiz)  # along spring axis
        E = 0.5 * sp.k * (delta ** 2)

        key = (min(sp.i, sp.j), max(sp.i, sp.j))
        energies[key] = energies.get(key, 0.0) + float(E)

    return energies


def node_scores_from_energies(struct: Structure, energies: dict[tuple[int, int], float]) -> dict[int, float]:
    scores = {nid: 0.0 for nid in struct.nodes.keys()}
    for (i, j), E in energies.items():
        if i in scores:
            scores[i] += 0.5 * E
        if j in scores:
            scores[j] += 0.5 * E
    return scores


def reachable_from_fixed(struct: Structure) -> set[int]:
    fixed_nodes = [nid for nid, n in struct.nodes.items() if n.fixed_x or n.fixed_z]
    if not fixed_nodes:
        return set()

    adj = struct.adjacency()
    seen: set[int] = set()
    stack = list(fixed_nodes)

    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nb in adj.get(cur, []):
            if nb not in seen:
                stack.append(nb)

    return seen


def is_connectivity_ok(struct: Structure, protected: set[int]) -> bool:
    reachable = reachable_from_fixed(struct)
    for p in protected:
        if p in struct.nodes and p not in reachable:
            return False
    return True


# FIX 1
def min_degree_ok(struct: Structure, protected: set[int], min_deg: int = 2) -> bool:
    adj = struct.adjacency()
    for nid in struct.nodes.keys():
        if nid in protected:
            continue
        if len(adj.get(nid, set())) < min_deg:
            return False
    return True


def try_remove_one_node(struct: Structure, disp: dict[int, tuple[float, float]], protected: set[int]) -> Structure | None:
    energies = spring_energy(struct, disp)
    scores = node_scores_from_energies(struct, energies)

    candidates = sorted(
        [nid for nid in struct.nodes.keys() if nid not in protected],
        key=lambda nid: scores.get(nid, 0.0)
    )

    for nid in candidates:
        trial = copy.deepcopy(struct)
        trial.remove_node(nid)

        # FIX 1: reject too-sparse structures
        if not min_degree_ok(trial, protected=protected, min_deg=2):
            continue

        # connectivity check
        if not is_connectivity_ok(trial, protected):
            continue

        # FIX 2: must be mechanically solvable (K not singular)
        try:
            solve_displacements(trial)
        except Exception:
            continue

        return trial

    return None


def optimize_until_target(
    struct: Structure,
    protected: set[int],
    target_mass: float,
    max_steps: int = 10_000,
) -> tuple[Structure | None, int, str]:

    if struct.total_mass() <= target_mass:
        return struct, 0, "Already at or below target mass."

    current = copy.deepcopy(struct)

    if not is_connectivity_ok(current, protected):
        return None, 0, "Initial structure fails connectivity check."

    steps = 0
    while current.total_mass() > target_mass and steps < max_steps:
        try:
            _, disp = solve_displacements(current)
        except Exception as e:
            return None, steps, f"Solver failed during optimization: {e}"

        nxt = try_remove_one_node(current, disp, protected)
        if nxt is None:
            return current, steps, "No more safe removable nodes found."

        current = nxt
        steps += 1

    if current.total_mass() > target_mass:
        return current, steps, "Reached max_steps before target mass."

    return current, steps, "Optimization finished (target mass reached)."