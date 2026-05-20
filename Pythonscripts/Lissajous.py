import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

# ==========================================
# 0. EINSTELLUNG: Linear oder Verzerrt
# ==========================================
t_verzerrt_aktivieren = True  # True = verzerrt (Zeit-Trick aktiv), False = linear

# ==========================================
# 1. Parameter und Wertebereiche definieren
# ==========================================
x_min, x_max = 3, 30
y_min, y_max = 0.0004, 0.002

# Frequenzen exakt auf das gewünschte Verhältnis setzen
f_x = 3
f_y = 4

anzahl_punkte = 400
dt = 0.005  # Kleiner Zeitschritt für die numerische Integration

# Dynamische Puffer für die Achsenbegrenzung (10% des Bereichs)
pad_x = (x_max - x_min) * 0.1
pad_y = (y_max - y_min) * 0.1

# ==========================================
# 2. Mathematische Amplituden & Schleife
# ==========================================
amp_x = (x_max - x_min) / 2
mid_x = (x_max + x_min) / 2

amp_y = (y_max - y_min) / 2
mid_y = (y_max + y_min) / 2

# Arrays für die Ergebnisse vorbereiten
t_values = np.zeros(anzahl_punkte)
x_values = np.zeros(anzahl_punkte)
y_values = np.zeros(anzahl_punkte)

t_actual = 0.0

if t_verzerrt_aktivieren:
    # IHRE ORIGINAL-SCHLEIFE: Dynamische Zeitschritte integrieren
    for i in range(anzahl_punkte):
        tau_current = mid_x - amp_x * np.sin(f_x * t_actual)
        y_current = mid_y - amp_y * np.sin(f_y * t_actual)
        
        x_values[i] = tau_current
        y_values[i] = y_current
        t_values[i] = t_actual
        
        tau_minimal = mid_x - amp_x
        # Die '0.1' sichert Mindesttempo, die '0.2' steuert die Stärke der Beschleunigung
        faktor = 0.1 + (tau_current - tau_minimal) * 0.2  
        
        t_actual += dt * faktor
else:
    # Klassische lineare Zeitachse zum Vergleich
    t_values = np.linspace(0, 2 * np.pi, anzahl_punkte)
    x_values = mid_x - amp_x * np.sin(f_x * t_values)
    y_values = mid_y - amp_y * np.sin(f_y * t_values)

# Das maximale t ermitteln, da es bei Verzerrung nicht mehr exakt 2*pi ist
t_max_erreicht = t_values[-1]

# ==========================================
# 3. Layout und Diagramme initialisieren
# ==========================================
layout = [
    ["Links", "Main"],
    [".",     "Unten"]
]

fig, axes = plt.subplot_mosaic(layout, figsize=(9, 9), layout='constrained')

# Hauptplot: y(x)
axes["Main"].plot(x_values, y_values, color='tab:blue', alpha=0.7, lw=2)
axes["Main"].set_title(r"c($\tau$) [Lissajous 3:4, $\Delta\phi=0$]")
axes["Main"].set_xlabel(r"$\tau$") 
axes["Main"].set_ylabel("c")       
axes["Main"].set_xlim(x_min - pad_x, x_max + pad_x)
axes["Main"].set_ylim(y_min - pad_y, y_max + pad_y)
axes["Main"].grid(True)

# Linker Plot: y(t)
axes["Links"].plot(t_values, y_values, color='tab:orange', alpha=0.6)
axes["Links"].set_title("c(t)")
axes["Links"].set_xlabel("t")
axes["Links"].set_ylabel("c")
axes["Links"].set_xlim(0, t_max_erreicht)  # Dynamische Anpassung an t
axes["Links"].set_ylim(y_min - pad_y, y_max + pad_y)
axes["Links"].grid(True)

# Unterer Plot: t(x)
axes["Unten"].plot(x_values, t_values, color='tab:green', alpha=0.6)
axes["Unten"].set_title(r"Unten: $\tau$(t)")
axes["Unten"].set_xlabel(r"$\tau$") 
axes["Unten"].set_ylabel("t")
axes["Unten"].set_xlim(x_min - pad_x, x_max + pad_x)
axes["Unten"].set_ylim(0, t_max_erreicht)  # Dynamische Anpassung an t
axes["Unten"].grid(True)

# Animierte rote Punkte vorbereiten
dot_main, = axes["Main"].plot([], [], 'ro', markersize=8, zorder=5)
dot_links, = axes["Links"].plot([], [], 'ro', markersize=8, zorder=5)
dot_unten, = axes["Unten"].plot([], [], 'ro', markersize=8, zorder=5)

# ==========================================
# 4. Animations-Logik
# ==========================================
def update(frame):
    t_curr = t_values[frame]
    x_curr = x_values[frame]
    y_curr = y_values[frame]
    
    dot_main.set_data([x_curr], [y_curr])
    dot_links.set_data([t_curr], [y_curr])
    dot_unten.set_data([x_curr], [t_curr])
    
    return dot_main, dot_links, dot_unten

ani = FuncAnimation(
    fig, 
    update, 
    frames=len(t_values), 
    interval=15,    # Kleinerer Wert für höhere FPS und flüssigere Darstellung
    blit=True,      # Wieder auf True gesetzt für maximale Performance
    repeat=True
)

plt.show(block=True)
