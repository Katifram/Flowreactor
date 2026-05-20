import os
import sys
import time
import csv
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, CheckButtons
import seabreeze
# Erzwinge PyUSB-Backend für korrekte WinUSB/libusb-Kommunikation
seabreeze.use("pyseabreeze")
import seabreeze.spectrometers as sb

# ==============================================================================
# KONFIGURATION
# ==============================================================================
INTEGRATION_TIME_US = 150_000   # Integrationszeit in Mikrosekunden
UPDATE_PAUSE_SECONDS = 0.05     # Pause zwischen den Updates im Live-Plot
NUM_CYCLES = 0                  # Anzahl der Messzyklen (0 = unendlich)

# Achsen-Einschränkung für den Plot (Sinnvoller Bereich für Maya 2000 Pro)
X_MIN_NM = 200.0
X_MAX_NM = 1100.0

# ==============================================================================

def find_spectrometer():
    devices = sb.list_devices()
    if not devices:
        raise RuntimeError("No Ocean Optics spectrometer found.")
    return devices[0]  # <-- WICHTIG: Holt das erste Gerät aus der Liste


def initialize_csv(csv_file, wavelengths, baseline=None):
    """Erstellt die CSV-Datei mit Header und schreibt die Baseline in die erste Zeile."""
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["Timestamp"] + [f"WL_{wl:.1f}nm" for wl in wavelengths]
        writer.writerow(header)
        
        if baseline is not None:
            writer.writerow(["background"] + list(baseline))
            print(f"✓ Baseline in erste Zeile von {csv_file} geschrieben.")

def append_spectrum_to_csv(csv_file, intensities, timestamp=None):
    """Hängt eine normale Messung an die CSV-Datei an."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    with open(csv_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp] + list(intensities))
    return timestamp

def plot_spectrum_continuous(integration_time_us, update_pause_s, num_cycles, x_min, x_max):
    device = find_spectrometer()
    spec = sb.Spectrometer(device)
    spec.integration_time_micros(integration_time_us)
    
    plt.ion()
    fig = plt.figure(figsize=(14, 6))
    ax_plot = plt.subplot2grid((1, 4), (0, 0), colspan=3)
    
    # Verwende ein Dictionary in einer Liste, um Referenzänderungen im Scope der Buttons zu erlauben
    context = {
        'csv_file': None
    }
    
    state = {
        'baseline': None,
        'subtract_baseline': False,
        'recording_active': False,
        'current_intensities': None,
        'current_wavelengths': None
    }

    # Positionierung der GUI-Elemente im rechten Viertel
    ax_btn_baseline = plt.axes([0.78, 0.6, 0.15, 0.06])
    btn_baseline = Button(ax_btn_baseline, "Save Baseline", color="lightblue", hovercolor="skyblue")
    
    ax_checkbox = plt.axes([0.78, 0.7, 0.15, 0.08])
    checkbox = CheckButtons(ax_checkbox, ["Subtract Baseline"], [False])
    
    # Toggle-Button für den Aufzeichnungsstart / Stopp
    ax_btn_trigger = plt.axes([0.78, 0.45, 0.15, 0.06])
    btn_trigger = Button(ax_btn_trigger, "Start Recording", color="lightgreen", hovercolor="limegreen")

    def on_save_baseline(event):
        if state['current_intensities'] is not None:
            state['baseline'] = state['current_intensities'].copy()
            print(f"✓ Baseline im Speicher aktualisiert (Max: {state['baseline'].max():.0f} Counts)")
        else:
            print("Keine Daten für Baseline verfügbar.")

    def on_toggle_baseline(label):
        state['subtract_baseline'] = checkbox.get_status()[0]

    def on_toggle_recording(event):
        if not state['recording_active']:
            # STARTEN
            state['recording_active'] = True
            context['csv_file'] = f"spectrum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            initialize_csv(context['csv_file'], state['current_wavelengths'], state['baseline'])
            
            # Button visuell auf Stopp umstellen
            btn_trigger.color = "tomato"
            btn_trigger.hovercolor = "crimson"
            btn_trigger.label.set_text("Stop Recording")
            print(f"▶️ Aufzeichnung GESTARTET: {context['csv_file']}")
        else:
            # STOPPEN
            state['recording_active'] = False
            print(f"⏹️ Aufzeichnung GESTOPPT: {context['csv_file']}")
            context['csv_file'] = None
            
            # Button visuell auf Start zurücksetzen
            btn_trigger.color = "lightgreen"
            btn_trigger.hovercolor = "limegreen"
            btn_trigger.label.set_text("Start Recording")

    btn_baseline.on_clicked(on_save_baseline)
    checkbox.on_clicked(on_toggle_baseline)
    btn_trigger.on_clicked(on_toggle_recording)

    # Initialer Datenabruf für Linien-Setup
    wl, ints = spec.wavelengths(), spec.intensities()
    line, = ax_plot.plot(wl, ints, color="tab:blue", linewidth=1)
    
    sat_text = ax_plot.text(0.5, 0.9, "⚠️ SENSOR SATURATED (REDUCE INTEGRATION TIME)", 
                            color="red", transform=ax_plot.transAxes, ha="center", 
                            weight="bold", visible=False)

    ax_plot.set_xlim(x_min, x_max)
    ax_plot.set_xlabel("Wavelength (nm)")
    ax_plot.set_ylabel("Intensity (Counts)")
    ax_plot.grid(alpha=0.3)
    fig.tight_layout(rect=[0, 0, 0.75, 1])

    cycle = 0
    try:
        while num_cycles == 0 or cycle < num_cycles:
            if not plt.fignum_exists(fig.number):
                break
                
            state['current_wavelengths'] = np.array(spec.wavelengths())
            state['current_intensities'] = np.array(spec.intensities())
            
            raw_ints = state['current_intensities']
            wl_data = state['current_wavelengths']

            # CSV-Aufzeichnung läuft nur, wenn getoggelt
            if state['recording_active'] and context['csv_file'] is not None:
                timestamp = append_spectrum_to_csv(context['csv_file'], raw_ints)

            # Baseline-Subtraktion für das Live-Bild
            display_ints = raw_ints.copy()
            if state['subtract_baseline'] and state['baseline'] is not None:
                display_ints = np.maximum(raw_ints - state['baseline'], 0)

            line.set_ydata(display_ints)
            
            visible_mask = (wl_data >= x_min) & (wl_data <= x_max)
            if np.any(visible_mask):
                y_max = display_ints[visible_mask].max()
                ax_plot.set_ylim(0, max(y_max * 1.1, 100))

            title = f"Ocean Optics Maya 2000 Pro (Cycle {cycle + 1})"
            if state['subtract_baseline'] and state['baseline'] is not None:
                title += " [Baseline Subtracted]"
            ax_plot.set_title(title)

            sat_text.set_visible(raw_ints.max() >= 63000)

            fig.canvas.draw_idle()
            fig.canvas.flush_events()
            time.sleep(update_pause_s)
            cycle += 1
            
    except KeyboardInterrupt:
        print("\nGestoppt durch Benutzer.")
    finally:
        spec.close()
        plt.close(fig)

def main():
    try:
        plot_spectrum_continuous(INTEGRATION_TIME_US, UPDATE_PAUSE_SECONDS, NUM_CYCLES, X_MIN_NM, X_MAX_NM)
    except Exception as error:
        print("Error:", error)
        sys.exit(1)

if __name__ == "__main__":
    main()
