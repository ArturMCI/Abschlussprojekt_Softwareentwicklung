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
    
    def _is_connected(self, struct) -> bool:
        """
        Prüft, ob alle Knoten über Federn erreichbar sind (Graph-Connectivity).
        """
        if len(struct.nodes) == 0:
            return True

        # Adjazenzliste aufbauen
        adj = {nid: set() for nid in struct.nodes.keys()}

        for s in struct.springs:
            if s.i in adj and s.j in adj:
                adj[s.i].add(s.j)
                adj[s.j].add(s.i)

        # BFS
        start = next(iter(struct.nodes.keys()))
        visited = set()
        stack = [start]

        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            stack.extend(adj[nid] - visited)

        return len(visited) == len(struct.nodes)

    def step(self, struct, disp):
        """
        Führt einen Optimierungsschritt aus:
        - Energie berechnen
        - Kandidaten entfernen
        - Connectivity prüfen
        - Nur übernehmen, wenn gültig
        """

        if len(struct.springs) == 0:
            return 0

        energies = self.compute_spring_energies(struct, disp)
        threshold = np.percentile(energies, self.percent_remove)

        # Kandidat erzeugen (noch NICHT übernehmen)
        candidate_springs = [
            s for s, e in zip(struct.springs, energies)
            if e > threshold
        ]

        removed = len(struct.springs) - len(candidate_springs)

        # Backup
        original_springs = struct.springs.copy()

        # Testweise setzen
        struct.springs = candidate_springs

        # Connectivity prüfen
        if not self._is_connected(struct):
            # zurücksetzen
            struct.springs = original_springs
            raise ValueError(
                "Optimierung abgebrochen: Struktur würde auseinanderfallen."
            )

        # Alles ok → Änderung bleibt
        return removed