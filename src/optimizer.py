import copy
import numpy as np

from src.model import Structure
from src.solver import solve_displacements


def _make_ke_cache(initial_struct: Structure):
    coords = {nid: (float(n.x), float(n.z)) for nid, n in initial_struct.nodes.items()}
    cache: dict[tuple[int, int, float], np.ndarray] = {}

    def get_ke(sp) -> np.ndarray:
        i = int(sp.i)
        j = int(sp.j)
        a, b = (i, j) if i < j else (j, i)
        key = (a, b, float(sp.k))
        if key in cache:
            return cache[key]

        xi, zi = coords[i]
        xj, zj = coords[j]
        dx = xj - xi
        dz = zj - zi
        L = float(np.hypot(dx, dz))
        if L <= 0.0:
            Ke = np.zeros((4, 4), dtype=float)
            cache[key] = Ke
            return Ke

        e = np.array([dx / L, dz / L], dtype=float)
        O = np.outer(e, e)
        K2 = float(sp.k) * np.array([[1.0, -1.0],
                                     [-1.0, 1.0]], dtype=float)
        Ke = np.kron(K2, O)
        cache[key] = Ke
        return Ke

    return get_ke


def _spring_energies(struct: Structure, disp: dict[int, tuple[float, float]], get_ke) -> dict[tuple[int, int], float]:
    energies: dict[tuple[int, int], float] = {}
    for sp in struct.springs:
        uix, uiz = disp[sp.i]
        ujx, ujz = disp[sp.j]
        ue = np.array([uix, uiz, ujx, ujz], dtype=float)
        Ke = get_ke(sp)
        E = 0.5 * float(ue.T @ Ke @ ue)
        key = (min(sp.i, sp.j), max(sp.i, sp.j))
        energies[key] = energies.get(key, 0.0) + E
    return energies


def _node_scores(struct: Structure, energies: dict[tuple[int, int], float]) -> dict[int, float]:
    scores = {nid: 0.0 for nid in struct.nodes.keys()}
    for (i, j), E in energies.items():
        if i in scores:
            scores[i] += 0.5 * E
        if j in scores:
            scores[j] += 0.5 * E
    return scores


def _dfs(adj: dict[int, set[int]], starts: list[int]) -> set[int]:
    seen: set[int] = set()
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nb in adj.get(cur, ()):
            if nb not in seen:
                stack.append(nb)
    return seen


def is_connectivity_ok(struct: Structure, protected: set[int]) -> bool:
    prot = [p for p in protected if p in struct.nodes]
    if not prot:
        return True
    adj = struct.adjacency()
    seen = _dfs(adj, [prot[0]])
    return all(p in seen for p in prot)


def _split_supports_and_loads(struct: Structure, protected: set[int]) -> tuple[list[int], list[int]]:
    supports = []
    for nid in protected:
        if nid not in struct.nodes:
            continue
        n = struct.nodes[nid]
        if getattr(n, "fixed_x", False) or getattr(n, "fixed_z", False):
            supports.append(nid)
    loads = [nid for nid in protected if nid in struct.nodes and nid not in supports]
    return supports, loads


def _lastpath_mask(struct: Structure, protected: set[int]) -> set[int]:
    adj = struct.adjacency()
    supports, loads = _split_supports_and_loads(struct, protected)
    if not supports or not loads:
        return set(struct.nodes.keys())
    rs = _dfs(adj, supports)
    rl = _dfs(adj, loads)
    return rs.intersection(rl)


def _smooth_scores(struct: Structure, scores: dict[int, float], alpha: float = 0.6) -> dict[int, float]:
    adj = struct.adjacency()
    out: dict[int, float] = {}
    for nid in struct.nodes.keys():
        neigh = adj.get(nid, set())
        if not neigh:
            out[nid] = scores.get(nid, 0.0)
            continue
        m = float(np.mean([scores.get(nb, 0.0) for nb in neigh]))
        out[nid] = alpha * scores.get(nid, 0.0) + (1.0 - alpha) * m
    return out


def _bfs_distance_to_set(adj: dict[int, set[int]], targets: list[int]) -> dict[int, int]:
    """
    Multi-source BFS distances (unweighted graph).
    dist[n] = shortest number of edges to any target.
    """
    from collections import deque
    dist: dict[int, int] = {}
    dq = deque()
    for t in targets:
        dist[t] = 0
        dq.append(t)
    while dq:
        cur = dq.popleft()
        d = dist[cur]
        for nb in adj.get(cur, ()):
            if nb not in dist:
                dist[nb] = d + 1
                dq.append(nb)
    return dist


def _prune_degree0(struct: Structure, protected: set[int], rounds: int = 50) -> None:
    for _ in range(rounds):
        adj = struct.adjacency()
        to_remove = [nid for nid in struct.nodes.keys()
                     if nid not in protected and len(adj.get(nid, set())) == 0]
        if not to_remove:
            return
        for nid in to_remove:
            if nid in struct.nodes and nid not in protected:
                struct.remove_node(nid)


def _prune_degree01_final(struct: Structure, protected: set[int], rounds: int = 120) -> None:
    for _ in range(rounds):
        adj = struct.adjacency()
        to_remove = [nid for nid in struct.nodes.keys()
                     if nid not in protected and len(adj.get(nid, set())) <= 1]
        if not to_remove:
            return
        for nid in to_remove:
            if nid in struct.nodes and nid not in protected:
                struct.remove_node(nid)


def _is_solvable(struct: Structure):
    try:
        _, disp = solve_displacements(struct)
        return True, disp
    except Exception:
        return False, None


def optimize_until_target(
    struct: Structure,
    protected: set[int],
    target_mass: float,
    max_steps: int = 10_000,
    top_n_candidates: int = 400,
    min_deg_guard: int | None = None,
    stagnation_patience: int = 80,
    progress_callback=None,
) -> tuple[Structure | None, int, str]:

    start_mass = float(struct.total_mass())
    if start_mass <= target_mass:
        return struct, 0, "Already at or below target mass."

    current = copy.deepcopy(struct)
    get_ke = _make_ke_cache(struct)

    if not is_connectivity_ok(current, protected):
        return None, 0, "Initial structure fails connectivity (protected not connected)."

    ok, disp = _is_solvable(current)
    if not ok or disp is None:
        return None, 0, "Initial structure is not mechanically solvable."

    batch_fraction = 0.012
    batch_min = 8
    batch_max = 120
    rollback_halving = 8

    steps = 0
    stalled = 0
    rng = np.random.default_rng(0)

    def compute_k(cur_mass: float, n_nodes: int) -> int:
        mass_ratio = cur_mass / max(start_mass, 1e-12)
        remaining_ratio = (cur_mass - target_mass) / max(cur_mass, 1e-12)

        k = int(np.ceil(batch_fraction * n_nodes))
        k = max(batch_min, min(batch_max, k))

        if remaining_ratio < 0.20:
            k = min(k, 25)
        if remaining_ratio < 0.08:
            k = min(k, 8)
        if remaining_ratio < 0.03:
            k = 1

        if mass_ratio < 0.75:
            k = min(k, 10)
        if mass_ratio < 0.65:
            k = min(k, 5)
        if mass_ratio < 0.55:
            k = 1

        return max(1, k)

    while current.total_mass() > target_mass and steps < max_steps:
        cur_mass = float(current.total_mass())
        if progress_callback is not None:
            progress_callback(steps, cur_mass, target_mass, len(current.nodes))

        energies = _spring_energies(current, disp, get_ke)
        scores = _node_scores(current, energies)
        scores = _smooth_scores(current, scores, alpha=0.6)

        adj = current.adjacency()
        deg = {nid: len(adj.get(nid, set())) for nid in current.nodes.keys()}

        # distance to protected (supports+load)
        prot_existing = [p for p in protected if p in current.nodes]
        dist = _bfs_distance_to_set(adj, prot_existing) if prot_existing else {}

        # --- NEW: degree & distance penalty to break inner loops / grids ---
        # Higher degree -> cheaper to remove. Far from protected -> cheaper to remove.
        gamma = 1.6  # degree penalty strength (1.2-2.0 good)
        beta = 0.8   # distance penalty strength (0.5-1.2 good)
        eff = {}
        for nid in current.nodes.keys():
            s = scores.get(nid, 0.0)
            d = float(deg.get(nid, 0))
            di = float(dist.get(nid, 0))
            eff[nid] = s / ((d + 1.0) ** gamma) / ((di + 1.0) ** beta)

        mask = _lastpath_mask(current, protected)
        removable_all = [nid for nid in current.nodes.keys() if nid not in protected]
        removable_masked = [nid for nid in removable_all if nid in mask]
        removable = removable_masked if removable_masked else removable_all

        if not removable:
            return current, steps, "No removable nodes (all nodes are protected)."

        removable.sort(key=lambda nid: eff.get(nid, 0.0))

        base_pool = max(150, int(top_n_candidates))
        pool = removable[: min(len(removable), base_pool)]

        k = compute_k(cur_mass, len(current.nodes))
        attempt_k = k
        success = False

        for _ in range(rollback_halving + 1):
            snapshot = copy.deepcopy(current)
            removed = 0

            for nid in pool:
                if removed >= attempt_k:
                    break
                if nid not in current.nodes or nid in protected:
                    continue

                current.remove_node(nid)

                if not is_connectivity_ok(current, protected):
                    current = snapshot
                    removed = 0
                    break

                removed += 1

            if removed == 0:
                current = snapshot
                attempt_k = max(1, attempt_k // 2)
                continue

            _prune_degree0(current, protected, rounds=20)

            ok2, disp2 = _is_solvable(current)
            if ok2 and disp2 is not None:
                disp = disp2
                steps += 1
                stalled = 0
                success = True
                break

            current = snapshot
            attempt_k = max(1, attempt_k // 2)

        if success:
            continue

        stalled += 1
        if stalled >= stagnation_patience:
            expand_sorted = min(len(removable), 8000)
        else:
            expand_sorted = min(len(removable), max(2000, base_pool * 5))

        candidates = removable[:expand_sorted]

        if len(removable) > expand_sorted:
            tail = removable[expand_sorted:]
            sample_n = min(2000, len(tail))
            if sample_n > 0:
                rand_pick = rng.choice(tail, size=sample_n, replace=False).tolist()
                candidates = candidates + rand_pick

        removed_one = False
        for nid in candidates:
            if nid in protected or nid not in current.nodes:
                continue

            trial = copy.deepcopy(current)
            trial.remove_node(nid)

            if not is_connectivity_ok(trial, protected):
                continue

            _prune_degree0(trial, protected, rounds=30)

            ok3, disp3 = _is_solvable(trial)
            if ok3 and disp3 is not None:
                current = trial
                disp = disp3
                steps += 1
                stalled = 0
                removed_one = True
                break

        if not removed_one:
            return current, steps, "Stuck: no safe removable node found."

    if progress_callback is not None:
        progress_callback(steps, float(current.total_mass()), target_mass, len(current.nodes))

    if current.total_mass() <= target_mass:
        _prune_degree01_final(current, protected, rounds=120)
        return current, steps, f"Optimization finished (target mass reached). Steps: {steps}"

    return current, steps, "Reached max_steps before target mass."