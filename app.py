import streamlit as st

from src.model import Node, Spring, Structure
from src.solver import solve_displacements
from src.viz import plot_original, plot_deformed, plot_optimized
from src.optimizer import optimize_until_target


def build_grid_structure(width: float, height: float, nx: int, nz: int, k: float) -> Structure:
    nodes: dict[int, Node] = {}
    springs: list[Spring] = []

    node_id = 0
    for j in range(nz):
        z = (height * j) / (nz - 1) if nz > 1 else 0.0
        for i in range(nx):
            x = (width * i) / (nx - 1) if nx > 1 else 0.0
            nodes[node_id] = Node(id=node_id, x=float(x), z=float(z))
            node_id += 1

    def nid(i, j):
        return j * nx + i

    for j in range(nz):
        for i in range(nx):
            # horizontal + vertical
            if i + 1 < nx:
                springs.append(Spring(i=nid(i, j), j=nid(i + 1, j), k=k))
            if j + 1 < nz:
                springs.append(Spring(i=nid(i, j), j=nid(i, j + 1), k=k))

            # diagonals ALWAYS
            if i + 1 < nx and j + 1 < nz:
                springs.append(Spring(i=nid(i, j), j=nid(i + 1, j + 1), k=k))
            if i - 1 >= 0 and j + 1 < nz:
                springs.append(Spring(i=nid(i, j), j=nid(i - 1, j + 1), k=k))

    return Structure(nodes=nodes, springs=springs)


def apply_left_edge_fixed(struct: Structure, nx: int, nz: int):
    for j in range(nz):
        n = j * nx + 0
        struct.nodes[n].fixed_x = True
        struct.nodes[n].fixed_z = True


def apply_force_at(struct: Structure, nx: int, i: int, j: int, fz: float) -> int:
    n = j * nx + i
    struct.nodes[n].fz += fz
    return n


st.set_page_config(page_title="Federstruktur (x-z)", layout="wide")
st.title("2D-Federstruktur (x-z) – Solver & Optimize-until-target")

SCALE = 1.0  # no UI control

if "struct" not in st.session_state:
    st.session_state.struct = None
if "disp" not in st.session_state:
    st.session_state.disp = None
if "optimized_struct" not in st.session_state:
    st.session_state.optimized_struct = None
if "force_node_id" not in st.session_state:
    st.session_state.force_node_id = None


with st.sidebar:
    st.header("Grid (x-z)")
    width = st.number_input("Breite (x)", value=10.0, min_value=0.1)
    height = st.number_input("Höhe (z)", value=5.0, min_value=0.1)
    nx = st.slider("nx (Knoten in x)", 2, 40, 12)
    nz = st.slider("nz (Knoten in z)", 2, 40, 6)
    k = st.number_input("Federsteifigkeit k", value=100.0, min_value=0.0001)

    st.header("Randbedingungen")
    fix_left = st.checkbox("Linke Kante fixieren", value=True)

    st.header("Kraft (nur z-Richtung)")
    fi = st.slider("Kraft-Knoten i (x-index)", 0, nx - 1, nx - 1)
    fj = st.slider("Kraft-Knoten j (z-index)", 0, nz - 1, 0)
    fz = st.number_input("Fz", value=-10.0)

    st.header("Optimierung")
    target_factor = st.slider("Mass reduction factor (Zielmasse)", 0.1, 1.0, 0.5, 0.05)

    colb1, colb2 = st.columns(2)
    with colb1:
        btn_solve = st.button("Generate + Solve")
    with colb2:
        btn_opt = st.button("Optimize")


if btn_solve:
    struct = build_grid_structure(width, height, nx, nz, k)

    if fix_left:
        apply_left_edge_fixed(struct, nx, nz)

    force_nid = apply_force_at(struct, nx, fi, fj, fz)

    try:
        _, disp = solve_displacements(struct)
        st.session_state.struct = struct
        st.session_state.disp = disp
        st.session_state.optimized_struct = None
        st.session_state.force_node_id = force_nid
        st.success("Solved successfully.")
    except Exception as e:
        st.session_state.struct = None
        st.session_state.disp = None
        st.session_state.optimized_struct = None
        st.session_state.force_node_id = None
        st.error(str(e))


if btn_opt:
    if st.session_state.struct is None:
        st.warning("Please run 'Generate + Solve' first.")
    else:
        struct = st.session_state.struct

        protected = set()
        for nid, n in struct.nodes.items():
            if n.fixed_x or n.fixed_z:
                protected.add(nid)
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
        st.markdown("---")
        st.subheader("Optimierte Struktur (bis Zielmasse)")
        st.pyplot(plot_optimized(st.session_state.optimized_struct, show_nodes=False), clear_figure=True)