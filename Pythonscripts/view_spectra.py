"""Viewer for saved spectrum CSV files with a matplotlib slider.

Usage:
    python view_spectra.py path/to/spectrum_YYYYMMDD_HHMMSS.csv

If you pass a directory instead of a file, the first CSV found will be loaded.
"""

import argparse
import csv
import glob
import os
import re

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="View saved spectra from CSV with a slider.")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="CSV file or directory containing the CSV file(s). Default: current directory.",
    )
    return parser.parse_args()


def find_csv_path(path):
    if os.path.isfile(path):
        return path

    if os.path.isdir(path):
        csv_files = sorted(glob.glob(os.path.join(path, "*.csv")))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in directory: {path}")
        return csv_files[0]

    raise FileNotFoundError(f"Path does not exist: {path}")


def parse_wavelengths(header):
    wavelengths = []
    for label in header[1:]:
        match = re.search(r"([-+]?[0-9]*\.?[0-9]+)", label)
        if match:
            wavelengths.append(float(match.group(1)))
        else:
            raise ValueError(f"Cannot parse wavelength from header label '{label}'")
    return np.array(wavelengths)


def load_csv_spectra(csv_file):
    with open(csv_file, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise ValueError("CSV file is empty")

        wavelengths = parse_wavelengths(header)
        timestamps = []
        intensities = []

        for row in reader:
            if len(row) < 2:
                continue
            timestamps.append(row[0])
            intensities.append([float(x) for x in row[1:]])

    if not intensities:
        raise ValueError("CSV contains no intensity rows")

    intensity_array = np.array(intensities, dtype=float)
    return wavelengths, timestamps, intensity_array


def create_figure(wavelengths, timestamps, intensity_array, csv_file):
    n_frames = intensity_array.shape[0]
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.subplots_adjust(bottom=0.25)

    line, = ax.plot(wavelengths, intensity_array[0], color="tab:blue")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Intensity")
    ax.set_title(f"{os.path.basename(csv_file)} \nFrame 1 / {n_frames} - {timestamps[0]}")
    ax.grid(True, alpha=0.3)

    plt.subplots_adjust(left=0.1, right=0.95, top=0.92, bottom=0.18)

    slider_ax = plt.axes([0.1, 0.11, 0.8, 0.04])
    frame_slider = Slider(
        slider_ax,
        "Frame",
        1,
        n_frames,
        valinit=1,
        valstep=1,
        color="lightblue",
        valfmt="%0.0f",
    )

    def update(val):
        frame_idx = int(round(val)) - 1
        frame_idx = max(0, min(frame_idx, n_frames - 1))
        line.set_ydata(intensity_array[frame_idx])
        ax.set_ylim(0, np.max(intensity_array[frame_idx]) * 1.1)
        ax.set_title(
            f"{os.path.basename(csv_file)} \nFrame {frame_idx + 1} / {n_frames} - {timestamps[frame_idx]}"
        )
        fig.canvas.draw_idle()

    frame_slider.on_changed(update)

    button_prev_ax = plt.axes([0.12, 0.03, 0.12, 0.05])
    button_prev = Button(button_prev_ax, "<< Prev", color="lightgray", hovercolor="0.975")

    def prev_frame(event):
        current = int(round(frame_slider.val))
        if current > 1:
            frame_slider.set_val(current - 1)

    button_prev.on_clicked(prev_frame)

    button_next_ax = plt.axes([0.26, 0.03, 0.12, 0.05])
    button_next = Button(button_next_ax, "Next >>", color="lightgray", hovercolor="0.975")

    def next_frame(event):
        current = int(round(frame_slider.val))
        if current < n_frames:
            frame_slider.set_val(current + 1)

    button_next.on_clicked(next_frame)

    button_reset_ax = plt.axes([0.78, 0.03, 0.12, 0.05])
    button_reset = Button(button_reset_ax, "Reset", color="lightgray", hovercolor="0.975")

    def reset(event):
        frame_slider.reset()

    button_reset.on_clicked(reset)

    def on_key(event):
        if event.key in ["left", "a"]:
            prev_frame(event)
        elif event.key in ["right", "d"]:
            next_frame(event)
        elif event.key in ["home", "r"]:
            reset(event)

    fig.canvas.mpl_connect("key_press_event", on_key)
    fig.canvas.draw_idle()

    return fig


def main():
    args = parse_args()
    csv_file = find_csv_path(args.path)
    wavelengths, timestamps, intensity_array = load_csv_spectra(csv_file)
    create_figure(wavelengths, timestamps, intensity_array, csv_file)
    plt.show()


if __name__ == "__main__":
    main()
