"""Simulación de una estación meteorológica usando hilos.

Hilo 1 - Generador: genera temperatura, humedad y presión cada segundo.
Hilo 2 - Logger: escribe los datos en CSV cada 5 segundos (primer registro inmediato).
Hilo 3 - GUI: muestra una gráfica simple y una descripción en una ventana Tkinter.

Ejecución: python3 semaforos.py
"""

import threading
import time
import random
import csv
import os
from collections import deque
from datetime import datetime

try:
	import tkinter as tk
except Exception as e:
	print("Tkinter no está disponible en este entorno:", e)
	raise


# helper functions for shared weather data (no classes)
def create_shared(maxlen=300):
	"""Create a shared data structure with a lock and a history deque."""
	return {
		'lock': threading.Lock(),
		'history': deque(maxlen=maxlen),
	}


def add_sample(shared, sample):
	with shared['lock']:
		shared['history'].append(sample)


def latest(shared):
	with shared['lock']:
		if shared['history']:
			return shared['history'][-1]
		return None


def get_history(shared):
	with shared['lock']:
		return list(shared['history'])


def generator_thread(shared, stop_event: threading.Event):
	"""Genera muestras cada segundo con pequeñas variaciones."""
	# Valores base realistas
	temp = random.uniform(15.0, 25.0)  # Celsius
	hum = random.uniform(40.0, 60.0)   # %
	pres = random.uniform(1000.0, 1025.0)  # hPa

	while not stop_event.is_set():
		# small random walk
		temp += random.uniform(-0.5, 0.5)
		hum += random.uniform(-1.0, 1.0)
		pres += random.uniform(-0.8, 0.8)

		temp = max(-50.0, min(60.0, temp))
		hum = max(0.0, min(100.0, hum))
		pres = max(300.0, min(1100.0, pres))

		now = datetime.now()
		sample = (now, round(temp, 2), round(hum, 2), round(pres, 2))
		add_sample(shared, sample)

		time.sleep(1)


def logger_thread(shared, csv_path: str, stop_event: threading.Event):
	dirname = os.path.dirname(csv_path)
	if dirname and not os.path.exists(dirname):
        
		os.makedirs(dirname, exist_ok=True)

	# abrir en modo append
	header = ["datetime", "temperature_C", "humidity_percent", "pressure_hPa"]

	# write header if file doesn't exist
	write_header = not os.path.exists(csv_path)

	# First immediate write if we have a sample
	first = latest(shared)
	if first is not None:
		with open(csv_path, "a", newline="") as f:
			writer = csv.writer(f)
			if write_header:
				writer.writerow(header)
				write_header = False
			ts, t, h, p = first
			writer.writerow([ts.isoformat(sep=" "), t, h, p])

	while not stop_event.wait(5):
		sample = latest(shared)
		if sample is None:
			continue
		with open(csv_path, "a", newline="") as f:
			writer = csv.writer(f)
			if write_header:
				writer.writerow(header)
				write_header = False
			ts, t, h, p = sample
			writer.writerow([ts.isoformat(sep=" "), t, h, p])


def describe_trend(history):
	"""Genera una descripción simple basada en los últimos puntos."""
	if len(history) < 2:
		return "Recopilando datos..."

	# usar los últimos 3 puntos si existen
	last = history[-1]
	prev = history[-2]

	_, t1, h1, p1 = prev
	_, t2, h2, p2 = last

	def trend(a, b, tol):
		if b - a > tol:
			return "subiendo"
		if a - b > tol:
			return "bajando"
		return "estable"

	t_tr = trend(t1, t2, 0.3)
	h_tr = trend(h1, h2, 1.0)
	p_tr = trend(p1, p2, 0.3)

	desc = f"Temperatura {t_tr} ({t2} °C), humedad {h_tr} ({h2} %), presión {p_tr} ({p2} hPa)."
	return desc


def run_gui(shared, stop_event):
	"""Function-based GUI replacing WeatherGUI class."""
	root = tk.Tk()
	root.title("Estación Meteorológica - Simulación")

	width = 800
	height = 400

	canvas = tk.Canvas(root, width=width, height=height, bg="white")
	canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

	desc_var = tk.StringVar()
	desc_label = tk.Label(root, textvariable=desc_var, anchor="w", justify=tk.LEFT)
	desc_label.pack(side=tk.TOP, fill=tk.X)

	# bind close
	def on_close():
		stop_event.set()
		root.after(200, root.destroy)

	root.protocol("WM_DELETE_WINDOW", on_close)

	colors = {'temp': 'red', 'hum': 'blue', 'pres': 'green'}
	yranges = {'temp': (-20, 50), 'hum': (0, 100), 'pres': (900, 1050)}

	def draw():
		history = get_history(shared)
		canvas.delete("all")
		if not history:
			canvas.create_text(width/2, height/2, text="Esperando datos...", fill="gray")
			return

		for i in range(1, 10):
			y = i * height / 10
			canvas.create_line(0, y, width, y, fill="#f0f0f0")

		times = [t for (t, _, _, _) in history]
		temps = [v for (_, v, _, _) in history]
		hums = [v for (_, _, v, _) in history]
		press = [v for (_, _, _, v) in history]

		def plot(series, yrange, color):
			if not series:
				return
			miny, maxy = yrange
			if miny == maxy:
				miny -= 1
				maxy += 1
			n = len(series)
			if n < 2:
				return
			xs = [i * (width-60) / (n-1) + 30 for i in range(n)]
			ys = [height - 30 - ((val - miny) * (height-60) / (maxy-miny)) for val in series]
			pts = []
			for x, y in zip(xs, ys):
				pts.extend([x, y])
			canvas.create_line(*pts, fill=color, width=2, smooth=True)
			canvas.create_text(width-50, ys[-1], text=str(series[-1]), fill=color, anchor="w")

		def dynamic_range(values, default_range, margin_frac=0.1):
			if not values:
				return default_range
			mn = min(values)
			mx = max(values)
			if mn == mx:
				mn -= 1
				mx += 1
			rng = mx - mn
			mn -= rng * margin_frac
			mx += rng * margin_frac
			return (mn, mx)

		t_range = dynamic_range(temps, yranges['temp'])
		h_range = dynamic_range(hums, yranges['hum'])
		p_range = dynamic_range(press, yranges['pres'])

		plot(temps, t_range, colors['temp'])
		plot(hums, h_range, colors['hum'])
		plot(press, p_range, colors['pres'])

		canvas.create_rectangle(8, 8, 220, 50, fill="#ffffff", outline="#ddd")
		canvas.create_text(20, 18, text="Temperatura (°C)", fill=colors['temp'], anchor="w")
		canvas.create_text(20, 32, text="Humedad (%)", fill=colors['hum'], anchor="w")
		canvas.create_text(140, 18, text="Presión (hPa)", fill=colors['pres'], anchor="w")

	def update_loop():
		draw()
		hist = get_history(shared)
		desc = describe_trend(hist)
		desc_var.set(desc)
		if not stop_event.is_set():
			root.after(1000, update_loop)

	update_loop()
	root.mainloop()


def main():
	shared = create_shared(maxlen=180)
	stop_event = threading.Event()

	here = os.path.dirname(os.path.abspath(__file__))
	csv_path = os.path.join(here, "weather_log.csv")

	gen = threading.Thread(target=generator_thread, args=(shared, stop_event), daemon=True)
	log = threading.Thread(target=logger_thread, args=(shared, csv_path, stop_event), daemon=True)

	gen.start()
	log.start()

	try:
		run_gui(shared, stop_event)
	except KeyboardInterrupt:
		stop_event.set()


if __name__ == "__main__":
	main()

