import matplotlib.pyplot as plt
from src.model import Structure


def plot_original(struct: Structure, show_nodes: bool = False):
    fig, ax = plt.subplots()

    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        ax.plot([ni.x, nj.x], [ni.z, nj.z])

    if show_nodes:
        xs = [n.x for n in struct.nodes.values()]
        zs = [n.z for n in struct.nodes.values()]
        ax.scatter(xs, zs)

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()  # Ursprung links oben, z nach unten
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Original")
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


def plot_optimized(struct: Structure, show_nodes: bool = False):
    fig, ax = plt.subplots()

    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        ax.plot([ni.x, nj.x], [ni.z, nj.z])

    if show_nodes:
        xs = [n.x for n in struct.nodes.values()]
        zs = [n.z for n in struct.nodes.values()]
        ax.scatter(xs, zs)

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Optimized")
    return fig