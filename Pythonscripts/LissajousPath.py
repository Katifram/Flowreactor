import argparse
import math
import time
from dataclasses import dataclass

import serial


@dataclass
class AxisSpec:
	minimum: float
	maximum: float
	frequency_ratio: float
	phase_rad: float = 0.0


def clamp(value: float, low: float, high: float) -> float:
	return max(low, min(high, value))


def lissajous_value(t: float, period: float, axis: AxisSpec) -> float:
	omega = 2.0 * math.pi / period
	s = math.sin(axis.frequency_ratio * omega * t + axis.phase_rad)
	midpoint = 0.5 * (axis.minimum + axis.maximum)
	amplitude = 0.5 * (axis.maximum - axis.minimum)
	return midpoint + amplitude * s


def map_to_4_20ma(value: float, min_value: float, max_value: float) -> float:
	if max_value <= min_value:
		raise ValueError("max_value must be greater than min_value")
	normalized = (value - min_value) / (max_value - min_value)
	normalized = clamp(normalized, 0.0, 1.0)
	return 4.0 + normalized * 16.0


def map_to_dac_code(ma: float, dac_bits: int) -> int:
	if dac_bits < 1:
		raise ValueError("dac_bits must be at least 1")
	ma_clamped = clamp(ma, 4.0, 20.0)
	normalized = (ma_clamped - 4.0) / 16.0
	return int(round(normalized * ((1 << dac_bits) - 1)))


def build_line(template: str, values: dict) -> str:
	try:
		return template.format(**values)
	except KeyError as exc:
		raise ValueError(f"Unknown placeholder in --line-template: {exc}") from exc


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"Generate 3-variable Lissajous trajectories with per-axis min/max bounds, "
			"4:3 base figure, and slower third axis."
		)
	)

	parser.add_argument("--x-min", type=float, default=0.0)
	parser.add_argument("--x-max", type=float, default=100.0)
	parser.add_argument("--y-min", type=float, default=0.0)
	parser.add_argument("--y-max", type=float, default=100.0)
	parser.add_argument("--z-min", type=float, default=0.0)
	parser.add_argument("--z-max", type=float, default=100.0)

	parser.add_argument("--period", type=float, default=20.0, help="Base period in seconds")
	parser.add_argument(
		"--duration",
		type=float,
		default=20.0,
		help="How long to run in seconds (set to same as period for one full cycle)",
	)
	parser.add_argument("--sample-rate", type=float, default=20.0, help="Samples per second")

	parser.add_argument("--fx", type=float, default=3.0, help="Frequency ratio for X")
	parser.add_argument("--fy", type=float, default=4.0, help="Frequency ratio for Y")
	parser.add_argument("--fz", type=float, default=1.0, help="Frequency ratio for Z (slower axis)")

	parser.add_argument("--phase-x-deg", type=float, default=0.0)
	parser.add_argument("--phase-y-deg", type=float, default=90.0)
	parser.add_argument("--phase-z-deg", type=float, default=0.0)

	parser.add_argument("--port", type=str, default="COM4")
	parser.add_argument("--baud", type=int, default=115200)
	parser.add_argument("--serial-timeout", type=float, default=0.2)
	parser.add_argument(
		"--send-serial",
		action="store_true",
		help="If set, stream commands to serial. Otherwise print preview lines only.",
	)

	parser.add_argument(
		"--line-template",
		type=str,
		default="SET X_MA {x_ma:.3f};SET Y_MA {y_ma:.3f};SET Z_MA {z_ma:.3f}",
		help=(
			"Template for each command line. Placeholders: "
			"t,x,y,z,x_ma,y_ma,z_ma,x_dac,y_dac,z_dac"
		),
	)
	parser.add_argument("--dac-bits", type=int, default=12)
	parser.add_argument("--preview-lines", type=int, default=10)

	return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
	if args.period <= 0:
		raise ValueError("--period must be > 0")
	if args.duration <= 0:
		raise ValueError("--duration must be > 0")
	if args.sample_rate <= 0:
		raise ValueError("--sample-rate must be > 0")

	bounds = [
		("x", args.x_min, args.x_max),
		("y", args.y_min, args.y_max),
		("z", args.z_min, args.z_max),
	]
	for axis_name, mn, mx in bounds:
		if mx <= mn:
			raise ValueError(f"--{axis_name}-max must be greater than --{axis_name}-min")


def generate_samples(args: argparse.Namespace):
	x_axis = AxisSpec(args.x_min, args.x_max, args.fx, math.radians(args.phase_x_deg))
	y_axis = AxisSpec(args.y_min, args.y_max, args.fy, math.radians(args.phase_y_deg))
	z_axis = AxisSpec(args.z_min, args.z_max, args.fz, math.radians(args.phase_z_deg))

	dt = 1.0 / args.sample_rate
	count = int(args.duration * args.sample_rate)

	for i in range(count):
		t = i * dt
		x = lissajous_value(t, args.period, x_axis)
		y = lissajous_value(t, args.period, y_axis)
		z = lissajous_value(t, args.period, z_axis)

		x_ma = map_to_4_20ma(x, args.x_min, args.x_max)
		y_ma = map_to_4_20ma(y, args.y_min, args.y_max)
		z_ma = map_to_4_20ma(z, args.z_min, args.z_max)

		sample = {
			"t": t,
			"x": x,
			"y": y,
			"z": z,
			"x_ma": x_ma,
			"y_ma": y_ma,
			"z_ma": z_ma,
			"x_dac": map_to_dac_code(x_ma, args.dac_bits),
			"y_dac": map_to_dac_code(y_ma, args.dac_bits),
			"z_dac": map_to_dac_code(z_ma, args.dac_bits),
		}
		yield sample


def main() -> None:
	args = parse_args()
	validate_args(args)

	samples = list(generate_samples(args))
	preview_count = min(args.preview_lines, len(samples))

	print("3-variable Lissajous generator")
	print(f"X:Y ratio = {args.fx}:{args.fy}, Z ratio = {args.fz}")
	print(f"period={args.period}s duration={args.duration}s sample_rate={args.sample_rate}Hz")
	print("Preview:")
	for i in range(preview_count):
		line = build_line(args.line_template, samples[i])
		print(line)

	if not args.send_serial:
		print("Dry run only. Use --send-serial to stream commands.")
		return

	print(f"Opening serial port {args.port} @ {args.baud}...")
	with serial.Serial(args.port, args.baud, timeout=args.serial_timeout) as ser:
		time.sleep(2.0)
		next_tick = time.perf_counter()
		dt = 1.0 / args.sample_rate

		for sample in samples:
			line = build_line(args.line_template, sample)
			ser.write((line + "\n").encode("ascii", errors="ignore"))

			next_tick += dt
			sleep_s = next_tick - time.perf_counter()
			if sleep_s > 0:
				time.sleep(sleep_s)

	print("Finished streaming.")


if __name__ == "__main__":
	main()
