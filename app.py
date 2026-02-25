import numpy as np
import streamlit as st

from src.model import Node, Spring, Structure
from src.solver import solve_displacements
from src.viz import plot_original, plot_deformed, plot_optimized
from src.optimizer import optimize_until_target


def build_grid_structure(nx: int, nz: int, k: float) -> Structure:
    """
    Grid über Knotenzahl generieren.
    Knoten liegen bei ganzzahligen Koordinaten:
    x = 0 ... nx-1
    z = 0 ... nz-1
    """
    nodes: dict[int, Node] = {}
    springs: list[Spring] = []

    node_id = 0
    for j in range(nz):
        for i in range(nx):
            nodes[node_id] = Node(
                id=node_id,
                x=float(i),   # nur Index!
                z=float(j)
            )
            node_id += 1

    def nid(i, j):
        return j * nx + i

    k_diag = float(k) / np.sqrt(2.0)

    for j in range(nz):
        for i in range(nx):

            # horizontal
            if i + 1 < nx:
                springs.append(Spring(nid(i, j), nid(i + 1, j), k))

            # vertical
            if j + 1 < nz:
                springs.append(Spring(nid(i, j), nid(i, j + 1), k))

            # diagonals
            if i + 1 < nx and j + 1 < nz:
                springs.append(Spring(nid(i, j), nid(i + 1, j + 1), k_diag))

            if i - 1 >= 0 and j + 1 < nz:
                springs.append(Spring(nid(i, j), nid(i - 1, j + 1), k_diag))

    return Structure(nodes=nodes, springs=springs)


def apply_mbb_supports(struct: Structure, nx: int, nz: int, left_type: str, right_type: str) -> tuple[int, int]:
    """
    MBB-Setup: Auflager nur unten links & unten rechts.
    - Festlager: fixed_x=True, fixed_z=True
    - Loslager: fixed_x=False, fixed_z=True
    """
    # unten links / unten rechts
    n_left = (nz - 1) * nx + 0
    n_right = (nz - 1) * nx + (nx - 1)

    # reset supports (wichtig, wenn mehrfach gelöst wird)
    for n in struct.nodes.values():
        n.fixed_x = False
        n.fixed_z = False

    def set_support(nid: int, typ: str):
        if typ == "Festlager":
            struct.nodes[nid].fixed_x = True
            struct.nodes[nid].fixed_z = True
        elif typ == "Loslager":
            struct.nodes[nid].fixed_x = False
            struct.nodes[nid].fixed_z = True
        else:
            raise ValueError(f"Unbekannter Lagertyp: {typ}")

    set_support(n_left, left_type)
    set_support(n_right, right_type)

    return n_left, n_right


def apply_force_at(struct: Structure, nx: int, i: int, j: int, fz: float) -> int:
    """
    Kraft nur in z-Richtung am Knoten (i,j).
    """
    n = j * nx + i
    struct.nodes[n].fz += float(fz)
    return n


st.set_page_config(page_title="Federstruktur (x-z)", layout="wide")
st.title("2D-Federstruktur (x-z) – Solver & MBB-Optimizer")

SCALE = 1.0  # keine UI-Kontrolle

if "struct" not in st.session_state:
    st.session_state.struct = None
if "disp" not in st.session_state:
    st.session_state.disp = None
if "optimized_struct" not in st.session_state:
    st.session_state.optimized_struct = None
if "force_node_id" not in st.session_state:
    st.session_state.force_node_id = None
if "support_nodes" not in st.session_state:
    st.session_state.support_nodes = None  # (left_id, right_id)


with st.sidebar:
    st.header("Grid (x-z)")
    st.write("Anzahl der Knoten: ")
    nx = st.number_input("Breite (x)", value=30, min_value=1)
    nz = st.number_input("Höhe (z)", value=15, min_value=1)
    #k = st.number_input("Federsteifigkeit k (h/v)", value=100.0, min_value=0.0001)

    st.header("Randbedingungen (MBB)")
    support_left = st.selectbox("Lager links unten", ["Festlager", "Loslager"], index=1)   # default: Loslager
    support_right = st.selectbox("Lager rechts unten", ["Festlager", "Loslager"], index=0) # default: Festlager

    st.header("Kraft (nur z-Richtung)")
    # MBB-typisch: oben Mitte
    fi = st.slider("Kraft-Knoten i (x-index)", 0, nx - 1, nx // 2)
    fj = st.slider("Kraft-Knoten j (z-index)", 0, nz - 1, 0)
    fz = st.number_input("Fz (z nach unten → nach unten meist +)", value=10.0)

    st.header("Optimierung")
    target_factor = st.slider("Mass reduction factor (Zielmasse)", 0.1, 1.0, 0.5, 0.05)

    colb1, colb2 = st.columns(2)
    with colb1:
        btn_solve = st.button("Generate + Solve")
    with colb2:
        btn_opt = st.button("Optimize")


if btn_solve:
    struct = build_grid_structure(nx, nz, 100)

    # MBB supports (nur unten links / unten rechts)
    left_id, right_id = apply_mbb_supports(struct, nx, nz, support_left, support_right)

    # Force
    force_nid = apply_force_at(struct, nx, fi, fj, fz)

    try:
        _, disp = solve_displacements(struct)
        st.session_state.struct = struct
        st.session_state.disp = disp
        st.session_state.optimized_struct = None
        st.session_state.force_node_id = force_nid
        st.session_state.support_nodes = (left_id, right_id)
        st.success("Solved successfully.")
    except Exception as e:
        st.session_state.struct = None
        st.session_state.disp = None
        st.session_state.optimized_struct = None
        st.session_state.force_node_id = None
        st.session_state.support_nodes = None
        st.error(str(e))


if btn_opt:
    if st.session_state.struct is None:
        st.warning("Please run 'Generate + Solve' first.")
    else:
        struct = st.session_state.struct

        protected = set()

        # supports schützen
        if st.session_state.support_nodes is not None:
            protected.update(st.session_state.support_nodes)

        # force node schützen
        if st.session_state.force_node_id is not None:
            protected.add(st.session_state.force_node_id)

        target_mass = target_factor * struct.total_mass()

        with st.spinner("Optimizing until target mass..."):
            opt_struct, steps, msg = optimize_until_target(
                struct=struct,
                protected=protected,
                target_mass=target_mass,
                max_steps=10_000,
            )

        if opt_struct is None:
            st.error(msg)
        else:
            st.session_state.optimized_struct = opt_struct
            st.success(f"{msg} (Steps: {steps})")


struct = st.session_state.struct
disp = st.session_state.disp

if struct is None:
    st.info("Links Parameter setzen und **Generate + Solve** drücken.")
else:
    if disp is None:
        try:
            _, disp = solve_displacements(struct)
            st.session_state.disp = disp
        except Exception as e:
            st.error(f"Solver failed: {e}")
            disp = None

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Originale Struktur")
        st.pyplot(plot_original(struct, show_nodes=False), clear_figure=True)

    with c2:
        st.subheader("Deformierte Struktur (Skalierung = 1)")
        if disp is not None:
            st.pyplot(plot_deformed(struct, disp, scale=SCALE, show_nodes=False), clear_figure=True)
        else:
            st.warning("No displacement solution available for deformed plot.")

    st.markdown("---")
    st.subheader("Kennzahlen")
    st.write(f"Knoten: {len(struct.nodes)}")
    st.write(f"Federn: {len(struct.springs)}")
    st.write(f"Masse (einfach): {struct.total_mass():.2f}")

    if st.session_state.optimized_struct is not None:
        opt_struct = st.session_state.optimized_struct

        st.markdown("---")
        st.subheader("Optimierte Struktur (bis Zielmasse)")

        c3, c4 = st.columns(2)

        # Plot optimized geometry
        with c3:
            st.pyplot(plot_optimized(opt_struct, show_nodes=False), clear_figure=True)

        # Solve and plot deformation of optimized structure
        with c4:
            st.subheader("Deformation (optimiert, Skalierung = 1)")
            try:
                _, opt_disp = solve_displacements(opt_struct)
                st.pyplot(
                    plot_deformed(opt_struct, opt_disp, scale=SCALE, show_nodes=False),
                    clear_figure=True
                )
            except Exception as e:
                st.warning(f"Optimized structure could not be solved: {e}")


