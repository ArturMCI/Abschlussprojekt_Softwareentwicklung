import numpy as np
import copy
from src.model import Structure
from src.solver import solve_displacements

# --- Performance & Geometry Helpers ---

def _get_vectorized_data(struct: Structure, id2pos: dict):
    nodes = struct.nodes
    springs = struct.springs
    idx_i = np.array([id2pos[sp.i] for sp in springs])
    idx_j = np.array([id2pos[sp.j] for sp in springs])
    ks = np.array([float(sp.k) for sp in springs])
    pos_i = np.array([[nodes[sp.i].x, nodes[sp.i].z] for sp in springs])
    pos_j = np.array([[nodes[sp.j].x, nodes[sp.j].z] for sp in springs])
    d_vec = pos_j - pos_i
    lengths = np.linalg.norm(d_vec, axis=1)
    dirs = d_vec / np.where(lengths[:, None] == 0, 1, lengths[:, None])
    return idx_i, idx_j, ks, dirs

def _spring_energies_vec(u_vec, idx_i, idx_j, ks, dirs, springs):
    u_i = np.stack([u_vec[2*idx_i], u_vec[2*idx_i + 1]], axis=1)
    u_j = np.stack([u_vec[2*idx_j], u_vec[2*idx_j + 1]], axis=1)
    du = u_j - u_i
    du_proj = np.einsum('ij,ij->i', du, dirs)
    energies_val = 0.5 * ks * (du_proj ** 2)
    
    energies_dict = {}
    for idx, sp in enumerate(springs):
        key = (min(sp.i, sp.j), max(sp.i, sp.j))
        energies_dict[key] = energies_dict.get(key, 0.0) + energies_val[idx]
    return energies_dict

def _fast_snapshot(struct: Structure):
    new_struct = copy.copy(struct) 
    new_struct.nodes = struct.nodes.copy()
    new_struct.springs = list(struct.springs)
    return new_struct

# --- Logik-Verbesserungen ---

def _prune_dead_ends(struct: Structure, protected: set[int]):
    """Entfernt Knoten, die statisch nichts beitragen (Grad 0 oder 1)."""
    while True:
        adj = struct.adjacency()
        to_remove = [nid for nid, neighbors in adj.items() 
                     if len(neighbors) <= 1 and nid not in protected]
        if not to_remove:
            break
        for nid in to_remove:
            struct.remove_node(nid)

def _node_scores_pro(struct: Structure, energies: dict, alpha: float = 0.5) -> dict[int, float]:
    """Berechnet Scores mit Fokus auf Lastpfad-Erhaltung."""
    scores = {nid: 0.0 for nid in struct.nodes.keys()}
    for (i, j), E in energies.items():
        if i in scores: scores[i] += 0.5 * E
        if j in scores: scores[j] += 0.5 * E
    
    # Smoothing & Grad-Penalty
    adj = struct.adjacency()
    refined_scores = {}
    for nid, s in scores.items():
        neighbors = adj.get(nid, set())
        if not neighbors:
            refined_scores[nid] = 0.0
            continue
        # Mittelwert der Umgebung einbeziehen (verhindert Checkerboard)
        m = np.mean([scores.get(nb, 0.0) for nb in neighbors])
        # Bestrafung für "dünne" Stellen: Wenig Nachbarn = geringerer Score = eher weg
        degree_weight = (len(neighbors) / 4.0) ** 0.5 
        refined_scores[nid] = (alpha * s + (1.0 - alpha) * m) * degree_weight
        
    return refined_scores

def _dfs_check(adj, starts, targets):
    seen = set()
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if cur in seen: continue
        seen.add(cur)
        for nb in adj.get(cur, ()):
            if nb not in seen: stack.append(nb)
    return all(t in seen for t in targets)

def is_connectivity_ok(struct: Structure, protected: set[int]) -> bool:
    """Prüft, ob alle geschützten Punkte (Last + Lager) noch verbunden sind."""
    prot_list = [p for p in protected if p in struct.nodes]
    if len(prot_list) <= 1: return True
    adj = struct.adjacency()
    return _dfs_check(adj, [prot_list[0]], prot_list[1:])

# --- Haupt-Optimizer ---

def optimize_until_target(
    struct: Structure,
    protected: set[int],
    target_mass: float,
    max_steps: int = 10_000,
    progress_callback=None,
) -> tuple[Structure | None, int, str]:

    current = _fast_snapshot(struct)
    start_mass = float(current.total_mass())
    
    try:
        u_vec, _ = solve_displacements(current)
    except:
        return None, 0, "Struktur initial nicht lösbar."

    steps = 0
    stalled_count = 0

    while current.total_mass() > target_mass and steps < max_steps:
        id2pos = current.id_to_pos()
        idx_i, idx_j, ks, dirs = _get_vectorized_data(current, id2pos)
        energies = _spring_energies_vec(u_vec, idx_i, idx_j, ks, dirs, current.springs)
        
        # Scoring mit Sensitivitäts-Filter
        scores = _node_scores_pro(current, energies, alpha=0.4)
        
        removable = [nid for nid in current.nodes if nid not in protected]
        # Nach Score aufsteigend sortieren (kleinste Energie zuerst)
        removable.sort(key=lambda nid: scores.get(nid, 0.0))
        
        # Adaptive Batch-Größe & Suchfenster
        # Wenn wir "stallen", suchen wir in einem größeren Pool (top_n)
        search_pool_size = 500 + stalled_count * 500 
        candidates = removable[:search_pool_size]
        
        success = False
        # Wir versuchen erst große Batches, dann kleinere
        batch_sizes = [max(1, int(len(current.nodes) * 0.02)), 5, 1]
        
        for b_size in batch_sizes:
            snapshot = _fast_snapshot(current)
            
            # Wir nehmen die absolut schwächsten Kandidaten aus dem Pool
            to_remove = candidates[:b_size]
            for nid in to_remove:
                current.remove_node(nid)
            
            # WICHTIG: Sofort tote Enden wegschneiden
            _prune_dead_ends(current, protected)
            
            if is_connectivity_ok(current, protected):
                try:
                    u_vec_new, _ = solve_displacements(current)
                    u_vec = u_vec_new
                    success = True
                    stalled_count = 0
                    steps += 1
                    break
                except:
                    pass
            
            current = snapshot

        if not success:
            stalled_count += 1
            if stalled_count > 5: # Wenn auch mit großem Pool nichts geht
                break
        
        if progress_callback:
            progress_callback(steps, current.total_mass(), target_mass, len(current.nodes))

    # Finale Säuberung
    _prune_dead_ends(current, protected)
    return current, steps, f"Ziel erreicht oder stabilisiert bei {current.total_mass():.1f}"