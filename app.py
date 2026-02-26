import numpy as np
import streamlit as st

from src.model import Node, Spring, Structure
from src.solver import solve_displacements
from src.viz import (
    plot_original,
    plot_deformed,
    plot_optimized,
    save_plot,
    plot_original_fast_nodes,
    plot_deformed_fast_nodes,
    plot_optimized_fast_nodes,
)
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

    k = float(k)
    k_diag = k / np.sqrt(2.0)

    for j in range(nz):
        for i in range(nx):

            # horizontal
            if i + 1 < nx:
                springs.append(Spring(nid(i, j), nid(i + 1, j), k))

            # vertical
            if j + 1 < nz:
                springs.append(Spring(nid(i, j), nid(i, j + 1), k))

            # diagonals (immer)
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
    n_left = (nz - 1) * nx + 0
    n_right = (nz - 1) * nx + (nx - 1)

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
    n = j * nx + i
    struct.nodes[n].fz += float(fz)
    return n


st.set_page_config(page_title="Federstruktur (x-z)", layout="wide")
st.title("2D-Federstruktur (x-z) – Solver & MBB-Optimizer")

SCALE = 1.0  # keine UI-Kontrolle


def _should_fast_plot_auto(struct: Structure) -> bool:
    """Auto-Schwellwert: ab hier ist Linien-Plot (Federn) in Streamlit oft zu langsam."""
    return (len(struct.springs) > 6000) or (len(struct.nodes) > 1500)


def _use_nodes_only(struct: Structure, plot_mode: str) -> bool:
    """
    plot_mode:
      - "Auto" -> threshold-based
      - "Nodes only" -> always nodes
      - "Lines (Federn)" -> always lines
    """
    if plot_mode == "Nodes only":
        return True
    if plot_mode == "Lines (Federn)":
        return False
    return _should_fast_plot_auto(struct)


# Session state
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
if "plot_mode" not in st.session_state:
    st.session_state.plot_mode = "Auto"


with st.sidebar:
    st.header("Grid (x-z)")
    st.write("Anzahl der Knoten: ")
    nx = st.number_input("Breite (x)", value=20, min_value=2)
    nz = st.number_input("Höhe (z)", value=10, min_value=2)

    k = 100.0
    st.caption("Federsteifigkeit k ist fix: 100")

    st.header("Randbedingungen (MBB)")
    support_left = st.selectbox("Lager links unten", ["Festlager", "Loslager"], index=1)
    support_right = st.selectbox("Lager rechts unten", ["Festlager", "Loslager"], index=0)

    st.header("Kraft (nur z-Richtung)")
    fi = st.slider("Kraft-Knoten i (x-index)", 0, nx - 1, nx // 2)
    fj = st.slider("Kraft-Knoten j (z-index)", 0, nz - 1, 0)
    fz = st.number_input("Fz (z nach unten → nach unten meist +)", value=10.0)

    st.header("Darstellung")
    plot_mode = st.selectbox(
        "Plot-Modus",
        ["Auto", "Nodes only", "Lines (Federn)"],
        index=["Auto", "Nodes only", "Lines (Federn)"].index(st.session_state.plot_mode),
        help="Auto schaltet bei großen Strukturen automatisch auf Nodes only um.",
    )
    st.session_state.plot_mode = plot_mode

    st.header("Optimierung")
    target_factor = st.slider("Mass reduction factor (Zielmasse)", 0.1, 1.0, 0.5, 0.05)

    colb1, colb2 = st.columns(2)
    with colb1:
        btn_solve = st.button("Generate + Solve")
    with colb2:
        btn_opt = st.button("Optimize")


if btn_solve:
    struct = build_grid_structure(int(nx), int(nz), float(k))

    left_id, right_id = apply_mbb_supports(struct, int(nx), int(nz), support_left, support_right)
    force_nid = apply_force_at(struct, int(nx), int(fi), int(fj), float(fz))

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
        if st.session_state.support_nodes is not None:
            protected.update(st.session_state.support_nodes)
        if st.session_state.force_node_id is not None:
            protected.add(st.session_state.force_node_id)

        target_mass = target_factor * struct.total_mass()

        progress_bar = st.progress(0)
        progress_text = st.empty()

        start_mass = struct.total_mass()
        denom = max(start_mass - target_mass, 1e-12)

        def progress_callback(step, cur_mass, tgt_mass, n_nodes):
            frac = (start_mass - float(cur_mass)) / denom
            frac = max(0.0, min(1.0, frac))
            progress_bar.progress(int(frac * 100))
            progress_text.write(
                f"Step: {step} | Masse: {cur_mass:.2f} | Ziel: {tgt_mass:.2f} | "
                f"Fortschritt: {frac*100:.1f}% | Knoten: {n_nodes}"
            )

        with st.spinner("Optimizing until target mass..."):
            try:
                opt_struct, steps, msg = optimize_until_target(
                    struct=struct,
                    protected=protected,
                    target_mass=target_mass,
                    max_steps=10_000,
                    progress_callback=progress_callback,
                )
            except TypeError:
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
            progress_bar.progress(100)
            st.success(f"{msg} (Steps: {steps})")


struct = st.session_state.struct
disp = st.session_state.disp

supports = st.session_state.support_nodes
load = st.session_state.force_node_id
plot_mode = st.session_state.plot_mode

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

    st.subheader("Originale Struktur:")
    if _use_nodes_only(struct, plot_mode):
        if plot_mode == "Auto" and _should_fast_plot_auto(struct):
            st.caption("Auto: großes Grid erkannt → Nodes only aktiviert.")
        st.pyplot(plot_original_fast_nodes(struct, supports=supports, load=load), clear_figure=True)
    else:
        st.pyplot(plot_original(struct, show_nodes=False), clear_figure=True)

    st.subheader("Deformierte Struktur:")
    if disp is not None:
        if _use_nodes_only(struct, plot_mode):
            st.pyplot(plot_deformed_fast_nodes(struct, disp, scale=SCALE, supports=supports, load=load), clear_figure=True)
        else:
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
        st.subheader("Optimierte Struktur:")

        if _use_nodes_only(opt_struct, plot_mode):
            opt_plot = plot_optimized_fast_nodes(opt_struct, supports=supports, load=load)
        else:
            opt_plot = plot_optimized(opt_struct, show_nodes=False)

        st.pyplot(opt_plot, clear_figure=False)

        opt_png = save_plot(opt_plot)
        st.download_button(
            label="Geometrie herunterladen (.png)",
            data=opt_png,
            file_name="optimized_geometry.png",
            mime="image/png"
        )

        st.subheader("Deformierte optimierte Struktur:")
        try:
            _, opt_disp = solve_displacements(opt_struct)
            if _use_nodes_only(opt_struct, plot_mode):
                st.pyplot(plot_deformed_fast_nodes(opt_struct, opt_disp, scale=SCALE, supports=supports, load=load), clear_figure=True)
            else:
                st.pyplot(plot_deformed(opt_struct, opt_disp, scale=SCALE, show_nodes=False), clear_figure=True)
        except Exception as e:
            st.warning(f"Optimized structure could not be solved: {e}")

        st.markdown("---")
        st.subheader("Kennzahlen")
        st.write(f"Knoten: {len(opt_struct.nodes)}")
        st.write(f"Federn: {len(opt_struct.springs)}")
        st.write(f"Masse (einfach): {opt_struct.total_mass():.2f}")