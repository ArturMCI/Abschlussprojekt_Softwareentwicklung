import streamlit as st
import numpy as np

from src.model import Node, Spring, Structure
from src.solver import solve_displacements
from src.viz import plot_structure
from src.optimizer import Optimizer

# Session State initialisieren
if "struct" not in st.session_state:
    st.session_state.struct = None

if "disp" not in st.session_state:
    st.session_state.disp = None

if "u" not in st.session_state:
    st.session_state.u = None

def build_grid_structure(width: float, height: float, nx: int, ny: int, k: float,
                         diag: bool) -> Structure:
    nodes: dict[int, Node] = {}
    springs: list[Spring] = []

    # Create nodes on grid
    node_id = 0
    for j in range(ny):
        y = (height * j) / (ny - 1) if ny > 1 else 0.0
        for i in range(nx):
            x = (width * i) / (nx - 1) if nx > 1 else 0.0
            nodes[node_id] = Node(id=node_id, x=float(x), y=float(y))
            node_id += 1

    def nid(i, j):  # grid index -> node id
        return j * nx + i

    # Add springs: horiz + vert
    for j in range(ny):
        for i in range(nx):
            if i + 1 < nx:
                springs.append(Spring(i=nid(i, j), j=nid(i+1, j), k=k))
            if j + 1 < ny:
                springs.append(Spring(i=nid(i, j), j=nid(i, j+1), k=k))

            if diag:
                if i + 1 < nx and j + 1 < ny:
                    springs.append(Spring(i=nid(i, j), j=nid(i+1, j+1), k=k))
                if i - 1 >= 0 and j + 1 < ny:
                    springs.append(Spring(i=nid(i, j), j=nid(i-1, j+1), k=k))

    return Structure(nodes=nodes, springs=springs)

def apply_left_edge_fixed(struct: Structure, nx: int, ny: int):
    # fix all nodes with i=0 in x and y
    for j in range(ny):
        nid = j * nx + 0
        struct.nodes[nid].fixed_x = True
        struct.nodes[nid].fixed_y = True

def apply_force_at(struct: Structure, nx: int, i: int, j: int, fx: float, fy: float):
    nid = j * nx + i
    struct.nodes[nid].fx += fx
    struct.nodes[nid].fy += fy

st.set_page_config(page_title="Federstruktur (Grid) – Solver", layout="wide")
st.title("2D-Federstruktur (Grid) – Minimal-Solver")

with st.sidebar:
    st.header("Grid")
    width = st.number_input("Breite", value=10.0, min_value=0.1)
    height = st.number_input("Höhe", value=5.0, min_value=0.1)
    nx = st.slider("nx (Knoten in x)", 2, 40, 12)
    ny = st.slider("ny (Knoten in y)", 2, 40, 6)
    k = st.number_input("Federsteifigkeit k", value=100.0, min_value=0.0001)
    diag = st.checkbox("Diagonalen", value=True)

    st.header("Randbedingungen (Start: links fix)")
    fix_left = st.checkbox("Linke Kante fixieren", value=True)

    st.header("Kraft")
    fi = st.slider("Kraft-Knoten i (x-index)", 0, nx-1, nx-1)
    fj = st.slider("Kraft-Knoten j (y-index)", 0, ny-1, 0)
    fx = st.number_input("Fx", value=0.0)
    fy = st.number_input("Fy", value= -10.0)

    st.header("Plot")
    scale = st.number_input("Deformations-Skalierung", value=1.0, min_value=0.0)

    solve_btn = st.button("Generate + Solve")

col1, col2 = st.columns([1, 1])

if solve_btn:
    struct = build_grid_structure(width, height, nx, ny, k, diag)

    if fix_left:
        apply_left_edge_fixed(struct, nx, ny)

    apply_force_at(struct, nx, fi, fj, fx, fy)

    try:
        u, disp = solve_displacements(struct)

        # In Session speichern
        st.session_state.struct = struct
        st.session_state.disp = disp
        st.session_state.u = u

    except Exception as e:
        st.error(str(e))

# Optimizer (nur wenn Struktur existiert)
if st.session_state.struct is not None:
    optimizer = Optimizer(percent_remove=20)

    if st.button("Optimize once"):
        struct = st.session_state.struct

        # Backup komplette Struktur
        old_springs = struct.springs.copy()

        try:
            removed = optimizer.step(struct, st.session_state.disp)

            # Solver testen
            u, disp = solve_displacements(struct)

            # nur wenn Solver ok → speichern
            st.session_state.u = u
            st.session_state.disp = disp
            st.success(f"Entfernte Federn: {removed}")

        except Exception as e:
            # alles rückgängig
            struct.springs = old_springs
            st.error(str(e))

# Anzeige, wenn Ergebnis vorhanden
if st.session_state.struct is not None and st.session_state.disp is not None:
    struct = st.session_state.struct
    disp = st.session_state.disp
    u = st.session_state.u

    max_u = float(np.max(np.abs(u))) if u.size else 0.0

    with col1:
        st.subheader("Visualisierung")
        fig = plot_structure(struct, disp, scale=scale, show_nodes=False)
        st.pyplot(fig, clear_figure=True)

    with col2:
        st.subheader("Kennzahlen")
        st.write(f"Knoten: {len(struct.nodes)}")
        st.write(f"Federn: {len(struct.springs)}")
        st.write(f"Max |u|: {max_u:.6g}")
        st.write("Hinweis: Bei Singularität fehlen Lager/Connectivity.")

if st.session_state.struct is None:
    st.info("Links Parameter setzen und **Generate + Solve** drücken.")