import copy
import numpy as np

from src.model import Structure
from src.solver import solve_displacements


def _spring_element_matrix(struct: Structure, sp) -> np.ndarray:
    """
    Build 4x4 element stiffness matrix K_e for one spring (i,j) in global coords:
        K_e = (k * [[1,-1],[-1,1]]) ⊗ (e ⊗ e)
    where e is the unit direction vector of the spring.
    """
    ni = struct.nodes[sp.i]
    nj = struct.nodes[sp.j]

    dx = nj.x - ni.x
    dz = nj.z - ni.z
    L = float(np.hypot(dx, dz))
    if L == 0.0:
        return np.zeros((4, 4), dtype=float)

    e = np.array([dx / L, dz / L], dtype=float)  # unit direction (nx, nz)
    O = np.outer(e, e)  # 2x2

    K2 = float(sp.k) * np.array([[1.0, -1.0], [-1.0, 1.0]], dtype=float)  # 2x2
    Ke = np.kron(K2, O)  # 4x4

    return Ke


def spring_energies_from_Ke(struct: Structure, disp: dict[int, tuple[float, float]]) -> dict[tuple[int, int], float]:
    """
    Step (4) from screenshot:
      For each spring e:
        u_e from global u
        E_e = 1/2 * u_e^T * K_e * u_e

    Returns energies per undirected spring key (min(i,j), max(i,j)).
    """
    energies: dict[tuple[int, int], float] = {}

    for sp in struct.springs:
        # build element displacement vector u_e = [uix, uiz, ujx, ujz]^T
        uix, uiz = disp[sp.i]
        ujx, ujz = disp[sp.j]
        ue = np.array([uix, uiz, ujx, ujz], dtype=float)

        Ke = _spring_element_matrix(struct, sp)
        if Ke.size == 0:
            continue

        E = 0.5 * float(ue.T @ Ke @ ue)

        key = (min(sp.i, sp.j), max(sp.i, sp.j))
        energies[key] = energies.get(key, 0.0) + E

    return energies


def node_scores_from_energies(struct: Structure, energies: dict[tuple[int, int], float]) -> dict[int, float]:
    """
    Step (5) from screenshot:
      S_p = Σ 1/2 * E_e over adjacent springs
    """
    scores = {nid: 0.0 for nid in struct.nodes.keys()}

    for (i, j), E in energies.items():
        if i in scores:
            scores[i] += 0.5 * E
        if j in scores:
            scores[j] += 0.5 * E

    return scores


def is_connectivity_ok(struct: Structure, protected: set[int]) -> bool:
    """
    Alle 'protected' Knoten müssen in derselben zusammenhängenden Komponente liegen.
    (Damit zerfällt die Struktur nicht in Inseln.)
    """
    prot = [p for p in protected if p in struct.nodes]
    if not prot:
        return True

    anchor = prot[0]
    adj = struct.adjacency()

    seen: set[int] = set()
    stack = [anchor]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nb in adj.get(cur, []):
            if nb not in seen:
                stack.append(nb)

    return all(p in seen for p in prot)


def min_degree_ok(struct: Structure, protected: set[int], min_deg: int = 2) -> bool:
    """
    Optional extra guard: reject too-sparse graphs (can help avoid trivial singularities).
    If you don't want it, set min_deg_guard=None in optimize.
    """
    adj = struct.adjacency()
    for nid in struct.nodes.keys():
        if nid in protected:
            continue
        if len(adj.get(nid, set())) < min_deg:
            return False
    return True


def _try_remove_candidate(
    struct: Structure,
    nid: int,
    protected: set[int],
    min_deg_guard: int | None,
) -> Structure | None:
    """
    Removes exactly one node (trial) and applies the Step (8) checks.
    """
    if nid in protected:
        return None
    if nid not in struct.nodes:
        return None

    trial = copy.deepcopy(struct)
    trial.remove_node(nid)

    if min_deg_guard is not None:
        if not min_degree_ok(trial, protected=protected, min_deg=min_deg_guard):
            return None

    if not is_connectivity_ok(trial, protected):
        return None

    try:
        solve_displacements(trial)
    except Exception:
        return None

    return trial


def _compute_k_to_remove(current: Structure, target_mass: float, removal_fraction: float, min_remove: int = 1) -> int:
    """
    Step (6): determine removal count k for this iteration.
    """
    cur_mass = current.total_mass()
    if cur_mass <= target_mass:
        return 0

    n_nodes = len(current.nodes)
    if n_nodes <= 0:
        return 0

    node_mass = cur_mass / float(n_nodes)
    if node_mass <= 0:
        return 0

    max_removable = int(np.floor((cur_mass - target_mass) / node_mass))
    if max_removable <= 0:
        return 0

    k = int(np.floor(removal_fraction * n_nodes))
    k = max(min_remove, k)
    k = min(k, max_removable)
    return k


def optimize_until_target(
    struct: Structure,
    protected: set[int],
    target_mass: float,
    max_steps: int = 10_000,
    removal_fraction: float = 0.02,
    min_deg_guard: int | None = 2,
) -> tuple[Structure | None, int, str]:
    """
    Workflow (screenshot):
      1) assemble Kg (inside solve_displacements)
      2) apply BC (inside solve_displacements)
      3) solve u (inside solve_displacements)
      4) compute spring energies E_e = 1/2 u_e^T K_e u_e
      5) compute node scores S_p = Σ 1/2 E_e
      6) determine k nodes to remove this iteration
      7) choose nodes with smallest S_p (excluding protected)
      8) for each candidate: connectivity + solvable checks, then remove
      9) stop when target mass reached
    """
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

        energies = spring_energies_from_Ke(current, disp)
        scores = node_scores_from_energies(current, energies)

        k = _compute_k_to_remove(current, target_mass, removal_fraction=removal_fraction, min_remove=1)
        if k <= 0:
            return current, steps, "Target mass cannot be reached further (k=0)."

        candidates = [nid for nid in current.nodes.keys() if nid not in protected]
        if not candidates:
            return current, steps, "No removable nodes (all nodes are protected)."

        candidates.sort(key=lambda nid: scores.get(nid, 0.0))

        removed_this_iter = 0

        for nid in candidates:
            if removed_this_iter >= k:
                break

            trial = _try_remove_candidate(current, nid, protected, min_deg_guard=min_deg_guard)
            if trial is None:
                continue

            current = trial
            removed_this_iter += 1

            if current.total_mass() <= target_mass:
                break

        if removed_this_iter == 0:
            return current, steps, "No more safe removable nodes found."

        steps += 1

    if current.total_mass() > target_mass:
        return current, steps, "Reached max_steps before target mass."

    return current, steps, "Optimization finished (target mass reached)."