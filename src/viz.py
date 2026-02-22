import numpy as np
import matplotlib.pyplot as plt
from src.model import Structure

def plot_structure(struct: Structure, disp: dict[int, tuple[float,float]] | None, scale: float, show_nodes: bool = True):
    fig, ax = plt.subplots()

    # Original springs
    for sp in struct.springs:
        ni = struct.nodes[sp.i]
        nj = struct.nodes[sp.j]
        ax.plot([ni.x, nj.x], [ni.y, nj.y])

    if show_nodes:
        xs = [n.x for n in struct.nodes.values()]
        ys = [n.y for n in struct.nodes.values()]
        ax.scatter(xs, ys)

    # Deformed overlay
    if disp is not None:
        for sp in struct.springs:
            ni = struct.nodes[sp.i]
            nj = struct.nodes[sp.j]
            uix, uiy = disp[sp.i]
            ujx, ujy = disp[sp.j]
            ax.plot([ni.x + scale*uix, nj.x + scale*ujx],
                    [ni.y + scale*uiy, nj.y + scale*ujy])

        if show_nodes:
            dxs = [n.x + scale*disp[n.id][0] for n in struct.nodes.values()]
            dys = [n.y + scale*disp[n.id][1] for n in struct.nodes.values()]
            ax.scatter(dxs, dys)

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()  # matches "origin top-left" convention
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("Structure (original + deformed overlay)")
    return fig