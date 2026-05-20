import numpy as np
import matplotlib.pyplot as plt

# Parameter
mid_x, amp_x, f_x = 0, 1, 2.0
mid_y, amp_y, f_y = 0, 1, 4.0   # Das starre Verhältnis der Frequenzen bleibt erhalten
dt = 0.005
n_steps = 2000

# Speicher-Arrays
t_values = np.zeros(n_steps)
tau_values = np.zeros(n_steps)
y_values = np.zeros(n_steps)

t_actual = 0.0

for i in range(n_steps):
    # 1. Berechne die Werte basierend auf der aktuellen verbogenen Zeit
    tau_current = mid_x - amp_x * np.sin(f_x * t_actual)
    y_current = mid_y - amp_y * np.sin(f_y * t_actual)
    
    tau_values[i] = tau_current
    y_values[i] = y_current
    t_values[i] = t_actual
    
    # 2. DER ZEIT-TRICK FÜR DAS KONSTANTE VERHÄLTNIS:
    # Wenn tau_current groß (positiv) ist, erhöhen wir das Tempo (Frequenz hoch).
    # Wenn tau_current klein (negativ) ist, drosseln wir das Tempo.
    # Wir verschieben tau_current, damit der Faktor immer positiv bleibt.
    tau_minimal = mid_x - amp_x
    faktor = 0.1 + (tau_current - tau_minimal) * 2.0  # Die '2.0' steuert die Intensität
    
    # 3. Zeit dynamisch fortschreiben
    t_actual += dt * faktor

# Plot zur Kontrolle
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5))
ax1.plot(tau_values, label=r"$\tau$ (Schnell bei hohen Werten)")
ax1.legend()
ax2.plot(y_values, color="orange", label="y (Läuft absolut synchron mit)")
ax2.legend()
plt.show()
