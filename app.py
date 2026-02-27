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
    plot_heatmap,
    create_gif_from_figures,
)
from src.optimizer import optimize_until_target, get_energy_data


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
if "show_heatmap" not in st.session_state:
    st.session_state.show_heatmap = False
if "optimization_frames" not in st.session_state:
    st.session_state.optimization_frames = None


with st.sidebar:
    #gespeicherte laden
    st.header("Gespeicherte Strukturen")

    saved_structs = Structure.list_all()

    if saved_structs:
        options = {name: doc_id for doc_id, name in saved_structs}

        selected_name = st.selectbox(
            "Struktur auswählen",
            list(options.keys())
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Laden"):
                try:
                    loaded = Structure.load(options[selected_name])
                    st.session_state.struct = loaded
                    st.session_state.disp = None
                    st.session_state.optimized_struct = None
                    st.success(f"Struktur '{selected_name}' geladen.")
                except Exception as e:
                    st.error(f"Laden fehlgeschlagen: {e}")

        with col2:
            if st.button("Löschen"):
                try:
                    Structure.delete(options[selected_name])

                    # Falls gerade geladene Struktur gelöscht wird → zurücksetzen
                    if (
                        st.session_state.struct is not None
                        and st.session_state.struct.id == options[selected_name]
                    ):
                        st.session_state.struct = None
                        st.session_state.disp = None
                        st.session_state.optimized_struct = None

                    st.success(f"Struktur '{selected_name}' gelöscht.")
                    st.rerun()  # wichtig → Dropdown aktualisieren

                except Exception as e:
                    st.error(f"Löschen fehlgeschlagen: {e}")

    else:
        st.info("Keine gespeicherten Strukturen vorhanden.")


    #neue erstellen
    st.markdown("---")
    st.header("Neue Struktur")
    st.write("Anzahl der Knoten (x-z): ")
    nx = st.number_input("Breite (x)", value=100, min_value=1)
    nz = st.number_input("Höhe (z)", value=30, min_value=1)
    k = 100.0
    st.caption("Federsteifigkeit k ist fix: 100")
    #k = st.number_input("Federsteifigkeit k (h/v)", value=100.0, min_value=0.0001)

    st.header("Randbedingungen (MBB)")
    support_left = st.selectbox("Lager links unten", ["Festlager", "Loslager"], index=1)
    support_right = st.selectbox("Lager rechts unten", ["Festlager", "Loslager"], index=0)

    st.header("Kraft (nur z-Richtung)")
    fi = st.slider("Kraft-Knoten i (x-index)", 0, nx - 1, nx // 2)
    fj = st.slider("Kraft-Knoten j (z-index)", 0, nz - 1, 0)
    fz = st.number_input("Fz (z nach unten → nach unten meist +)", value=50.0)

    st.header("Darstellung")
    plot_mode = st.selectbox(
        "Plot-Modus",
        ["Auto", "Nodes only", "Lines (Federn)"],
        index=["Auto", "Nodes only", "Lines (Federn)"].index(st.session_state.plot_mode),
        help="Auto schaltet bei großen Strukturen automatisch auf Nodes only um.",
    )
    st.session_state.plot_mode = plot_mode

    show_heatmap = st.checkbox("Energie-Heatmap anzeigen", value=st.session_state.show_heatmap)
    st.session_state.show_heatmap = show_heatmap
    

    st.header("Optimierung")
    target_factor = st.slider("Mass reduction factor (Zielmasse)", 0.1, 1.0, 0.5, 0.05)

    colb1, colb2 = st.columns(2)
    with colb1:
        btn_solve = st.button("Generate + Solve")
    with colb2:
        btn_opt = st.button("Optimize")
    
    create_gif = st.checkbox("Optimierungsverlauf als GIF erzeugen", value=False)

    st.markdown("---")
    st.header("Struktur speichern")

    save_name = st.text_input("Name der Struktur")

    # Struktur speichern
    if st.button("Optimierte Struktur speichern"):
        if st.session_state.optimized_struct is None:
            st.warning("Keine optimierte Struktur vorhanden.")
        elif not save_name.strip():
            st.warning("Bitte einen Namen vergeben.")
        else:
            try:
                opt_struct = st.session_state.optimized_struct
                opt_struct.name = save_name
                id = opt_struct.save()
                st.success(f"Struktur '{save_name}' gespeichert.")
                st.rerun()
            except Exception as e:
                st.error(f"Speichern fehlgeschlagen: {e}")


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

        def snapshot_callback(step, cur_struct):
            if frames is None:
                return

            supports = st.session_state.support_nodes
            load = st.session_state.force_node_id
            plot_mode_local = st.session_state.plot_mode

            if _use_nodes_only(cur_struct, plot_mode_local):
                fig = plot_optimized_fast_nodes(
                    cur_struct,
                    supports=supports,
                    load=load
                )
            else:
                fig = plot_optimized(cur_struct, show_nodes=False)

            frames.append(fig)

        # Liste von Frames für GIF
        frames = [] if create_gif else None

        with st.spinner("Optimizing until target mass..."):
            try:
                opt_struct, steps, msg = optimize_until_target(
                struct=struct,
                protected=protected,
                target_mass=target_mass,
                max_steps=10_000,
                progress_callback=progress_callback,
                snapshot_callback=snapshot_callback if create_gif else None,
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
            if create_gif and frames:
                gif_buffer = create_gif_from_figures(frames, duration=0.2)
                st.session_state.optimization_frames = gif_buffer
            else:
                st.session_state.optimization_frames = None
        


struct = st.session_state.struct
disp = st.session_state.disp

supports = st.session_state.support_nodes
load = st.session_state.force_node_id
plot_mode = st.session_state.plot_mode

if struct is None:
    st.info("Vorhandene Struktur laden oder neue Struktur generieren (Generate+Solve)")
else:
    if disp is None:
        try:
            _, disp = solve_displacements(struct)
            st.session_state.disp = disp
        except Exception as e:
            st.error(f"Solver failed: {e}")
            disp = None

    st.markdown("---")
    st.subheader("Originale Struktur:")
    if _use_nodes_only(struct, plot_mode):
        if plot_mode == "Auto" and _should_fast_plot_auto(struct):
            st.caption("Auto: großes Grid erkannt → Nodes only aktiviert.")
        struct_plot = plot_original_fast_nodes(struct, supports=supports, load=load)
    else:
        struct_plot = plot_original(struct, show_nodes=False)

    # plot originale Struktur
    st.pyplot(struct_plot, clear_figure=False)

    # Save Plot as PNG
    struct_png = save_plot(struct_plot)

    # Download File in Browser
    st.download_button(
        label="herunterladen (.png)",
        data=struct_png,
        file_name="original_geometry.png",
        mime="image/png" #File-Type
    )
    
    st.markdown("---")
    st.subheader("Deformierte Struktur:")

    if disp is not None:
        if show_heatmap:            
            # Berechnungen
            u_vec, _ = solve_displacements(struct) 
            s_es, n_es = get_energy_data(struct, u_vec)
            
            # Modus bestimmen
            nodes_only = _use_nodes_only(struct, plot_mode)
            
            # WICHTIG: disp und SCALE übergeben!
            def_plot = plot_heatmap(struct, disp, s_es, n_es, nodes_only, scale=SCALE)

        else:
            if _use_nodes_only(struct, plot_mode):
                def_plot = plot_deformed_fast_nodes(struct, disp, scale=SCALE, supports=supports, load=load)
            else:
                def_plot = plot_deformed(struct, disp, scale=SCALE, show_nodes=False)
       

        # plot deformed originale Struktur
        st.pyplot(def_plot, clear_figure=False)
        c1, c2 = st.columns(2)

        # Save Plot as PNG
        def_png = save_plot(def_plot)

        # Download File in Browser
        st.download_button(
            label="herunterladen (.png)",
            data=def_png,
            file_name="deformed_geometry.png",
            mime="image/png" #File-Type
        )
    else:
        st.warning("No displacement solution available for deformed plot.")

    st.markdown("---")
    st.subheader("Kennzahlen")
    st.write(f"Knoten: {len(struct.nodes)}")
    st.write(f"Federn: {len(struct.springs)}")
    st.write(f"Masse: {struct.total_mass():.2f}")

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
            label="herunterladen (.png)",
            data=opt_png,
            file_name="optimized_geometry.png",
            mime="image/png"
        )

         # Solve and plot deformation of optimized structure
        st.markdown("---")
        st.subheader("Deformierte optimierte Struktur:")
        try:
            _, opt_disp = solve_displacements(opt_struct)
            if show_heatmap:            
                # Berechnungen
                u_vec, _ = solve_displacements(opt_struct) 
                s_es, n_es = get_energy_data(opt_struct, u_vec)
                
                # Modus bestimmen
                nodes_only = _use_nodes_only(opt_struct, plot_mode)
                
                # WICHTIG: disp und SCALE übergeben!
                opt_def_plot = plot_heatmap(opt_struct, disp, s_es, n_es, nodes_only, scale=SCALE)           
            else:
                if _use_nodes_only(opt_struct, plot_mode):
                    opt_def_plot = plot_deformed_fast_nodes(opt_struct, opt_disp, scale=SCALE, supports=supports, load=load)
                else:
                    opt_def_plot = plot_deformed(opt_struct, opt_disp, scale=SCALE, show_nodes=False)
            
            st.pyplot(opt_def_plot, clear_figure=False)

            # Save Plot as PNG
            opt_def_png = save_plot(opt_def_plot)

            # Download File in Browser
            st.download_button(
                label="herunterladen (.png)",
                data=opt_def_png,
                file_name="optimized_deformed_geometry.png",
                mime="image/png" #File-Type
            )

        except Exception as e:
            st.error(f"Fehler bei der Berechnung der optimierten Verformung: {e}")
       
        st.markdown("---")
        st.subheader("Kennzahlen")
        st.write(f"Knoten: {len(opt_struct.nodes)}")
        st.write(f"Federn: {len(opt_struct.springs)}")
        st.write(f"Masse: {opt_struct.total_mass():.2f}")

        if st.session_state.optimization_frames is not None:
            st.markdown("---")
            st.subheader("Optimierungsverlauf (GIF)")

            st.image(st.session_state.optimization_frames)

            st.download_button(
                label="Optimierungs-GIF herunterladen",
                data=st.session_state.optimization_frames,
                file_name="optimization.gif",
                mime="image/gif"
            )


