import numpy as np


class Optimizer:
    """
    Entfernt iterativ Federn mit geringer Dehnenergie.
    Minimal-Variante für Topologieoptimierung.
    """

    def __init__(self, percent_remove: float = 20.0):
        """
        percent_remove: Prozentsatz der schwächsten Federn,
                        die pro Schritt entfernt werden.
        """
        self.percent_remove = percent_remove

    def compute_spring_energies(self, struct, disp):
        energies = []

        for s in struct.springs:
            n1 = struct.nodes[s.i]
            n2 = struct.nodes[s.j]

            # ursprüngliche Länge
            dx0 = n2.x - n1.x
            dy0 = n2.y - n1.y
            L0 = np.hypot(dx0, dy0)

            # deformierte Länge
            u1 = disp[s.i]
            u2 = disp[s.j]

            dx = (n2.x + u2[0]) - (n1.x + u1[0])
            dy = (n2.y + u2[1]) - (n1.y + u1[1])
            L = np.hypot(dx, dy)

            dL = L - L0
            energy = 0.5 * s.k * dL**2
            energies.append(energy)

        return np.array(energies)

    def step(self, struct, disp):
        """
        Führt einen Optimierungsschritt aus:
        - Energie berechnen
        - Schwächste Federn entfernen
        """

        if len(struct.springs) == 0:
            return 0

        energies = self.compute_spring_energies(struct, disp)

        threshold = np.percentile(energies, self.percent_remove)

        new_springs = [
            s for s, e in zip(struct.springs, energies)
            if e > threshold
        ]

        removed = len(struct.springs) - len(new_springs)
        struct.springs = new_springs

        return removed