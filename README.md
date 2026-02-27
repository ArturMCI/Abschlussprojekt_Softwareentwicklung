# Abschlussprojekt -- 2D-Federstruktur mit Topologieoptimierung

Dieses Projekt implementiert eine 2D-Federstruktur (Massenpunkte + lineare Federn) mit numerischer Lösung des Gleichungssystems **K · u = F** sowie einer schrittweisen Topologieoptimierung.  
Die Anwendung wird als interaktive Web-App mit **Streamlit** bereitgestellt.

Neben den Minimalanforderungen wurden mehrere Erweiterungen implementiert.

---

# Installation

## 1. Repository klonen

```bash
git clone <REPOSITORY-URL>
cd <REPOSITORY-ORDNER>
```

## 2. Virtuelle Umgebung erstellen

```bash
python -m venv .venv
```

## 3. Virtuelle Umgebung aktivieren

**Windows (PowerShell):**

```bash
.venv\Scripts\activate
```

**Mac / Linux:**

```bash
source .venv/bin/activate
```

## 4. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

## 5. Anwendung starten

```bash
streamlit run app.py
```

---

# Projektstruktur

```
abschlussprojekt/
│
├── .venv/
├── src/
│   ├── model.py
│   ├── solver.py
│   ├── viz.py
│   ├── optimizer.py
│   └── __init__.py
│
├── images/
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Verwendete Technologien

- Python  
- NumPy  
- SciPy  
- Matplotlib  
- Streamlit  
- TinyDB  
- ImageIO  

---

# Funktionsweise des Optimizers

1. Modell initialisieren  
2. Gleichungssystem **K · u = F** lösen  
3. Verformungsenergie berechnen  
4. Wichtigkeit der Knoten bestimmen  
5. Schwächste Knoten entfernen  
6. Neue Masse berechnen  
7. Wiederholen bis Zielmasse erreicht ist oder Struktur instabil wird  

---

# Erweiterungen

## Auswahl der Lagerung

In der Sidebar kann eingestellt werden, wie die Struktur gelagert werden soll.

- Lager links unten
- Lager rechts unten
- Auswahl zwischen **Loslager** und **Festlager**
- Loslager blockieren nur die Bewegung in z-Richtung

![Auswahl der Lagerung](images/Auswahl_der_Lagerung.png)

---

## Auswahl des Kraftangriffspunkts

Die Kraft wirkt ausschließlich in z-Richtung.

- Auswahl des Kraft-Knotens (x-index)
- Auswahl des Kraft-Knotens (z-index)
- Einstellbarer Kraftbetrag Fz

![Auswahl des Kraftangriffspunkts](images/Auswahl_des_Kraftangriffspunktes.png)

---

## Optimierungsziel

Die Stärke der Optimierung wird über einen Zielmassen-Faktor (0–1) eingestellt.

Die Optimierung läuft, bis:
- Zielmasse erreicht wird  
- oder die Struktur instabil wird  

![Optimierungsziel](images/Optimierungsziel.png)

---

## Fortschrittsanzeige der Optimierung

Während der Optimierung wird eine Fortschrittsleiste angezeigt mit:

- Aktueller Iteration  
- Aktueller Masse  
- Zielmasse  
- Fortschritt in Prozent  
- Anzahl verbleibender Knoten  

![Fortschrittsanzeige](images/Fortschrittsanzeige_der_Optimierung.png)

---

## Plot-Modi

### Nodes only

Nur die Knoten werden dargestellt.  
Ideal für große Strukturen.

![Optimized Nodes Only](images/optimized_(nodes_only).png)

---

### Lines (Federn)

Knoten und Federn werden dargestellt.  
Geeignet für kleinere Strukturen.

![Optimized Lines](images/optimized.png)

---

### Plot-Modus Auswahl (Auto / Nodes only / Lines)

Je nach Strukturgröße kann automatisch umgeschaltet werden.

![Plot Modus](images/Plot_Modus.png)

---

## Plot als Heatmap

Optional kann die Verformungsenergie farblich dargestellt werden.

![Heatmap Option](images/Plot_als_Heatmap.png)

---

### Heatmap – Nodes only

![Heatmap Nodes](images/Energie_Heatmap_(Deformed).png)

---

### Heatmap – Lines (Federn)

![Heatmap Lines](images/Energie_Heatmap_(Deformed_2).png)

---

## Erweitertes Speichersystem

- Speicherung beliebig vieler Strukturen in TinyDB  
- Speicherung nur der optimierten Struktur  
- Überschreiben bei gleichem Namen  
- Laden und Löschen gespeicherter Strukturen  

![Speichersystem](images/Erweitertes_Speicherungssystem.png)

---

# Darstellung der Optimierung als GIF

Wenn die Option vor Start der Optimierung aktiviert wird,  
wird jede Iteration gespeichert und am Ende als GIF zusammengefügt.

Das GIF kann ebenfalls heruntergeladen werden.

![Optimierung GIF](images/optimization.gif)

---

# Autor:innen

Artur Surberg  
Julian Köll  

Projekt im Rahmen des Moduls **Softwaredesign**
