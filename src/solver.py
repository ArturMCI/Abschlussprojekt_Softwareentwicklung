import numpy as np
from src.model import Structure

try:
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve, MatrixRankWarning
    import warnings
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


def _spring_element_matrix(xi: float, zi: float, xj: float, zj: float, k: float) -> np.ndarray:
    dx = xj - xi
    dz = zj - zi
    L = float(np.hypot(dx, dz))
    if L <= 0.0:
        raise ValueError("Zero-length spring detected.")
    c = dx / L
    s = dz / L
    return float(k) * np.array(
        [
            [ c*c,  c*s, -c*c, -c*s],
            [ c*s,  s*s, -c*s, -s*s],
            [-c*c, -c*s,  c*c,  c*s],
            [-c*s, -s*s,  c*s,  s*s],
        ],
        dtype=float,
    )


def assemble_K_F_sparse(struct: Structure):
    id2pos = struct.id_to_pos()
    N = len(id2pos)
    ndofs = 2 * N

    F = np.zeros(ndofs, dtype=float)
    for nid, node in struct.nodes.items():
        p = id2pos[nid]
        F[2 * p] += float(node.fx)
        F[2 * p + 1] += float(node.fz)

    rows, cols, data = [], [], []
    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        ke = _spring_element_matrix(ni.x, ni.z, nj.x, nj.z, float(sp.k))

        pi = id2pos[sp.i]
        pj = id2pos[sp.j]
        dofs = [2 * pi, 2 * pi + 1, 2 * pj, 2 * pj + 1]

        for a in range(4):
            ra = dofs[a]
            for b in range(4):
                rows.append(ra)
                cols.append(dofs[b])
                data.append(float(ke[a, b]))

    K = coo_matrix((data, (rows, cols)), shape=(ndofs, ndofs)).tocsr()
    return K, F, id2pos


def assemble_K_F_dense(struct: Structure):
    id2pos = struct.id_to_pos()
    N = len(id2pos)
    ndofs = 2 * N

    K = np.zeros((ndofs, ndofs), dtype=float)
    F = np.zeros(ndofs, dtype=float)

    for nid, node in struct.nodes.items():
        p = id2pos[nid]
        F[2 * p] += float(node.fx)
        F[2 * p + 1] += float(node.fz)

    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        ke = _spring_element_matrix(ni.x, ni.z, nj.x, nj.z, float(sp.k))

        pi = id2pos[sp.i]
        pj = id2pos[sp.j]
        dofs = [2 * pi, 2 * pi + 1, 2 * pj, 2 * pj + 1]

        for a in range(4):
            for b in range(4):
                K[dofs[a], dofs[b]] += ke[a, b]

    return K, F, id2pos


def solve_displacements(struct: Structure):
    id2pos = struct.id_to_pos()
    fixed = []
    for nid, node in struct.nodes.items():
        p = id2pos[nid]
        if node.fixed_x:
            fixed.append(2 * p)
        if node.fixed_z:
            fixed.append(2 * p + 1)

    # ---------- Sparse ----------
    if _HAS_SCIPY:
        K, F, _ = assemble_K_F_sparse(struct)
        ndofs = K.shape[0]
        fixed_set = set(fixed)
        free = np.array([i for i in range(ndofs) if i not in fixed_set], dtype=int)

        u = np.zeros(ndofs, dtype=float)
        if free.size == 0:
            disp = {nid: (0.0, 0.0) for nid in id2pos.keys()}
            return u, disp

        K_ff = K[free][:, free]
        F_f = F[free]

        # Turn "Matrix is exactly singular" into a hard error
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            try:
                u_f = spsolve(K_ff, F_f)
            except MatrixRankWarning as e:
                raise np.linalg.LinAlgError("System not solvable (exactly singular).") from e
            except Exception as e:
                raise np.linalg.LinAlgError("System not solvable (solver error).") from e

        u_f = np.asarray(u_f, dtype=float)
        if not np.all(np.isfinite(u_f)):
            raise np.linalg.LinAlgError("System not solvable (NaN/Inf in solution).")

        u[free] = u_f
        disp = {nid: (float(u[2 * p]), float(u[2 * p + 1])) for nid, p in id2pos.items()}
        return u, disp

    # ---------- Dense fallback ----------
    K, F, _ = assemble_K_F_dense(struct)
    Kb = K.copy()
    Fb = F.copy()
    for dof in fixed:
        Kb[dof, :] = 0.0
        Kb[:, dof] = 0.0
        Kb[dof, dof] = 1.0
        Fb[dof] = 0.0

    try:
        u = np.linalg.solve(Kb, Fb)
    except np.linalg.LinAlgError as e:
        raise np.linalg.LinAlgError("System not solvable (singular).") from e

    if not np.all(np.isfinite(u)):
        raise np.linalg.LinAlgError("System not solvable (NaN/Inf in solution).")

    disp = {nid: (float(u[2 * p]), float(u[2 * p + 1])) for nid, p in id2pos.items()}
    return u, disp