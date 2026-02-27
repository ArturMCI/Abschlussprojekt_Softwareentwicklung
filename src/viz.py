import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
import matplotlib.colors as colors
from src.model import Structure
from io import BytesIO
import imageio.v2 as imageio


def _scatter_nodes(ax, struct: Structure, *, label: str = "Nodes", size: int = 12):
    xs = [n.x for n in struct.nodes.values()]
    zs = [n.z for n in struct.nodes.values()]
    ax.scatter(xs, zs, s=size, label=label)


def _scatter_supports_and_load(ax, struct: Structure, supports=None, load=None):
    if supports:
        sx = [struct.nodes[i].x for i in supports if i in struct.nodes]
        sz = [struct.nodes[i].z for i in supports if i in struct.nodes]
        if sx:
            ax.scatter(sx, sz, s=60, marker="s", label="Support")
    if load is not None and load in struct.nodes:
        ax.scatter([struct.nodes[load].x], [struct.nodes[load].z], s=80, marker="x", label="Load")


def plot_original(struct: Structure, show_nodes: bool = False):
    fig, ax = plt.subplots()

    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        ax.plot([ni.x, nj.x], [ni.z, nj.z])

    if show_nodes:
        _scatter_nodes(ax, struct)

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Original")
    return fig


def plot_original_fast_nodes(struct: Structure, supports=None, load=None):
    """Fast plot: nodes only (for large grids)."""
    fig, ax = plt.subplots()
    _scatter_nodes(ax, struct, label="Nodes", size=10)
    _scatter_supports_and_load(ax, struct, supports, load)
    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Original (nodes only)")
    ax.legend(loc="best")
    return fig


def plot_deformed(struct: Structure, disp: dict[int, tuple[float, float]], scale: float = 1.0, show_nodes: bool = False):
    fig, ax = plt.subplots()

    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        uix, uiz = disp[sp.i]
        ujx, ujz = disp[sp.j]
        ax.plot(
            [ni.x + scale * uix, nj.x + scale * ujx],
            [ni.z + scale * uiz, nj.z + scale * ujz],
        )

    if show_nodes:
        xs = [n.x + scale * disp[n.id][0] for n in struct.nodes.values()]
        zs = [n.z + scale * disp[n.id][1] for n in struct.nodes.values()]
        ax.scatter(xs, zs)

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Deformed")
    return fig


def plot_deformed_fast_nodes(
    struct: Structure,
    disp: dict[int, tuple[float, float]],
    scale: float = 1.0,
    supports=None,
    load=None,
):
    """Fast plot: deformed node positions only (for large grids)."""
    fig, ax = plt.subplots()

    xs = [n.x + scale * disp[n.id][0] for n in struct.nodes.values()]
    zs = [n.z + scale * disp[n.id][1] for n in struct.nodes.values()]
    ax.scatter(xs, zs, s=10, label="Nodes (deformed)")

    if supports:
        sx = [struct.nodes[i].x + scale * disp[i][0] for i in supports if i in struct.nodes]
        sz = [struct.nodes[i].z + scale * disp[i][1] for i in supports if i in struct.nodes]
        if sx:
            ax.scatter(sx, sz, s=60, marker="s", label="Support")
    if load is not None and load in struct.nodes:
        ax.scatter(
            [struct.nodes[load].x + scale * disp[load][0]],
            [struct.nodes[load].z + scale * disp[load][1]],
            s=80,
            marker="x",
            label="Load",
        )

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Deformed (nodes only)")
    ax.legend(loc="best")
    return fig


def plot_optimized(struct: Structure, show_nodes: bool = False):
    fig, ax = plt.subplots()

    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        ax.plot([ni.x, nj.x], [ni.z, nj.z])

    if show_nodes:
        _scatter_nodes(ax, struct)

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Optimized")
    return fig


def plot_optimized_fast_nodes(struct: Structure, supports=None, load=None):
    """Fast plot: nodes only (for large optimized structures)."""
    fig, ax = plt.subplots()
    _scatter_nodes(ax, struct, label="Nodes", size=10)
    _scatter_supports_and_load(ax, struct, supports, load)
    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Optimized (nodes only)")
    ax.legend(loc="best")
    return fig

def save_plot(fig: Figure) -> BytesIO: 
    """ Zwischenspeicherung eines Plots im RAM um Datei danach zum Download bereitzustellen """
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=300)
    buf.seek(0)
    return buf

def plot_heatmap(struct: Structure, disp: dict, spring_es, node_es, use_nodes_only: bool, scale: float = 1.0):
    fig, ax = plt.subplots()
    cmap = 'jet' # Colormap
    
    # Energie-Werte normalisieren
    node_vals = np.array(list(node_es.values()))
    vmax_node = np.percentile(node_vals, 95) if len(node_vals) > 0 else 1.0
    
    if use_nodes_only:
        # deformierte Koordinaten für Knoten
        xs = [struct.nodes[nid].x + scale * disp[nid][0] for nid in node_es.keys()]
        zs = [struct.nodes[nid].z + scale * disp[nid][1] for nid in node_es.keys()]
        vals = list(node_es.values())
        
        sc = ax.scatter(xs, zs, c=vals, cmap=cmap, s=15, edgecolors='none', vmax=vmax_node)
        plt.colorbar(sc, ax=ax, label="Energie (deformiert)")
    else:
        # deformierte Koordinaten für Federn
        lines = []
        for sp in struct.springs:
            ni, nj = struct.nodes[sp.i], struct.nodes[sp.j]
            # Start- und Endpunkt deformieren
            p1 = (ni.x + scale * disp[sp.i][0], ni.z + scale * disp[sp.i][1])
            p2 = (nj.x + scale * disp[sp.j][0], nj.z + scale * disp[sp.j][1])
            lines.append([p1, p2])
        
        spring_vals = np.array(spring_es)
        vmax_spring = np.percentile(spring_vals, 95) if len(spring_vals) > 0 else 1.0
        
        lc = LineCollection(lines, cmap=cmap, linewidths=1.5)
        lc.set_array(spring_vals)
        lc.set_clim(0, vmax_spring) # Skala begrenzen
        ax.add_collection(lc)
        ax.autoscale()
        plt.colorbar(lc, ax=ax, label="Energie (deformiert)")

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_title("Energie-Heatmap (Deformiert)")
    return fig

def create_gif_from_figures(figures: list, duration: float = 0.3) -> BytesIO:
    """
    Erstellt ein GIF aus einer Liste von matplotlib-Figuren.
    duration = Zeit pro Frame in Sekunden.
    """
    images = []

    for fig in figures:
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        buf.seek(0)
        images.append(imageio.imread(buf))
        buf.close()
        plt.close(fig)

    gif_buffer = BytesIO()
    imageio.mimsave(gif_buffer, images, format="GIF", duration=duration)
    gif_buffer.seek(0)
    return gif_buffer