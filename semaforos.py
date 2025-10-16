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



def crear_compartido(maxlen=300):
	return {
		'lock': threading.Lock(),
		'history': deque(maxlen=maxlen),
	}


def agregar_muestra(compartido, muestra):
	with compartido['lock']:
		compartido['history'].append(muestra)


def ultima(compartido):
	with compartido['lock']:
		if compartido['history']:
			return compartido['history'][-1]
		return None


def obtener_historial(compartido):
	with compartido['lock']:
		return list(compartido['history'])


def hilo_generador(compartido, evento_parada: threading.Event):
	"""Genera muestras cada segundo con pequeñas variaciones."""
	# Valores base realistas
	temperatura = random.uniform(15.0, 25.0)  # Celsius
	humedad = random.uniform(40.0, 60.0)   # %
	presion = random.uniform(1000.0, 1025.0)  # hPa

	while not evento_parada.is_set():
		# small random walk
		temperatura += random.uniform(-0.5, 0.5)
		humedad += random.uniform(-1.0, 1.0)
		presion += random.uniform(-0.8, 0.8)

		temperatura = max(-50.0, min(60.0, temperatura))
		humedad = max(0.0, min(100.0, humedad))
		presion = max(300.0, min(1100.0, presion))

		ahora = datetime.now()
		muestra = (ahora, round(temperatura, 2), round(humedad, 2), round(presion, 2))
		agregar_muestra(compartido, muestra)

		time.sleep(1)


def hilo_registrador(compartido, ruta_csv: str, evento_parada: threading.Event):
	dirname = os.path.dirname(ruta_csv)
	if dirname and not os.path.exists(dirname):
        
		os.makedirs(dirname, exist_ok=True)

	header = ["datetime", "temperatura_C", "humedad_percent", "presion_hPa"]

	escribir_cabecera = not os.path.exists(ruta_csv)

	# First immediate write if we have a sample
	primera = ultima(compartido)
	if primera is not None:
		with open(ruta_csv, "a", newline="") as f:
			writer = csv.writer(f)
			if escribir_cabecera:
				writer.writerow(header)
				escribir_cabecera = False
			ts, temperatura, humedad, presion = primera
			writer.writerow([ts.isoformat(sep=" "), temperatura, humedad, presion])
	while not evento_parada.wait(5):
		muestra = ultima(compartido)
		if muestra is None:
			continue
		with open(ruta_csv, "a", newline="") as f:
			writer = csv.writer(f)
			if escribir_cabecera:
				writer.writerow(header)
				escribir_cabecera = False
			ts, temperatura, humedad, presion = muestra
			writer.writerow([ts.isoformat(sep=" "), temperatura, humedad, presion])


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


def ejecutar_gui(compartido, evento_parada):
	"""Interfaz gráfica (funcional) usando Tkinter."""
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
		evento_parada.set()
		root.after(200, root.destroy)

	root.protocol("WM_DELETE_WINDOW", on_close)


	colors = {'temp': 'red', 'hum': 'blue', 'pres': 'green'}
	yranges = {'temp': (-20, 50), 'hum': (0, 100), 'pres': (900, 1050)}

	def draw():
		historial = obtener_historial(compartido)
		canvas.delete("all")
		if not historial:
			canvas.create_text(width/2, height/2, text="Esperando datos", fill="gray")
			return

		for i in range(1, 10):
			y = i * height / 10
			canvas.create_line(0, y, width, y, fill="#f0f0f0")

		times = [t for (t, _, _, _) in historial]
		temps = [v for (_, v, _, _) in historial]
		hums = [v for (_, _, v, _) in historial]
		press = [v for (_, _, _, v) in historial]

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
		hist = obtener_historial(compartido)
		desc = describe_trend(hist)
		desc_var.set(desc)
		if not evento_parada.is_set():
			root.after(1000, update_loop)

	update_loop()
	root.mainloop()


def main():
	compartido = crear_compartido(maxlen=180)
	evento_parada = threading.Event()

	here = os.path.dirname(os.path.abspath(__file__))
	ruta_csv = os.path.join(here, "weather_log.csv")

	hilo_gen = threading.Thread(target=hilo_generador, args=(compartido, evento_parada), daemon=True)
	hilo_log = threading.Thread(target=hilo_registrador, args=(compartido, ruta_csv, evento_parada), daemon=True)

	hilo_gen.start()
	hilo_log.start()

	try:
		ejecutar_gui(compartido, evento_parada)
	except KeyboardInterrupt:
		evento_parada.set()


if __name__ == "__main__":
	main()

