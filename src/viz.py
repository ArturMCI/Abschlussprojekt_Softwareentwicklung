import matplotlib.pyplot as plt
from src.model import Structure
from io import BytesIO


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
