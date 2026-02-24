import numpy as np
from src.model import Structure


def _spring_element_matrix(xi: float, zi: float, xj: float, zj: float, k: float) -> np.ndarray:
    dx = xj - xi
    dz = zj - zi
    L = float(np.hypot(dx, dz))
    if L == 0.0:
        raise ValueError("Zero-length spring detected.")
    c = dx / L
    s = dz / L

    # 2D axial spring (x-z), 4x4
    ke = k * np.array([
        [ c*c,  c*s, -c*c, -c*s],
        [ c*s,  s*s, -c*s, -s*s],
        [-c*c, -c*s,  c*c,  c*s],
        [-c*s, -s*s,  c*s,  s*s],
    ], dtype=float)
    return ke


def assemble_K_F(struct: Structure) -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    id2pos = struct.id_to_pos()
    N = len(id2pos)
    ndofs = 2 * N

    K = np.zeros((ndofs, ndofs), dtype=float)
    F = np.zeros(ndofs, dtype=float)

    # forces
    for nid, node in struct.nodes.items():
        p = id2pos[nid]
        F[2 * p] += node.fx
        F[2 * p + 1] += node.fz

    # springs
    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        ke = _spring_element_matrix(ni.x, ni.z, nj.x, nj.z, sp.k)

        pi = id2pos[sp.i]
        pj = id2pos[sp.j]
        dofs = [2 * pi, 2 * pi + 1, 2 * pj, 2 * pj + 1]

        for a in range(4):
            for b in range(4):
                K[dofs[a], dofs[b]] += ke[a, b]

    return K, F, id2pos


def apply_dirichlet_bc(K: np.ndarray, F: np.ndarray, fixed_dofs: list[int]) -> tuple[np.ndarray, np.ndarray]:
    K2 = K.copy()
    F2 = F.copy()
    for dof in fixed_dofs:
        K2[dof, :] = 0.0
        K2[:, dof] = 0.0
        K2[dof, dof] = 1.0
        F2[dof] = 0.0
    return K2, F2


def solve_displacements(struct: Structure) -> tuple[np.ndarray, dict[int, tuple[float, float]]]:
    K, F, id2pos = assemble_K_F(struct)

    fixed: list[int] = []
    for nid, node in struct.nodes.items():
        p = id2pos[nid]
        if node.fixed_x:
            fixed.append(2 * p)
        if node.fixed_z:
            fixed.append(2 * p + 1)

    Kb, Fb = apply_dirichlet_bc(K, F, fixed)

    try:
        u = np.linalg.solve(Kb, Fb)
    except np.linalg.LinAlgError as e:
        raise np.linalg.LinAlgError("System not solvable (singular). Check supports/connectivity.") from e

    disp: dict[int, tuple[float, float]] = {}
    for nid, p in id2pos.items():
        disp[nid] = (float(u[2 * p]), float(u[2 * p + 1]))
    return u, disp