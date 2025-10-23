"""

Hilo 1 - Generador: genera temperatura, humedad y presión cada segundo.
Hilo 2 - Escribe los datos en CSV cada 5 segundos (primer registro inmediato).
Hilo 3 - Muestra una gráfica simple y una descripción en una ventana Tkinter.

"""

import threading   
import time
import random
import csv
import os
from collections import deque
from datetime import datetime

import tkinter as tk




def crear_compartido(maxlen=300):
	return {
		'lock': threading.Lock(), # Crea un controlador de acceso	
		'history': deque(maxlen=maxlen), # Almacena los datos de las muestras
	}


def agregar_muestra(compartido, muestra): 
	with compartido['lock']: # Abre la seccion 
		compartido['history'].append(muestra) # Agrega la muestra al historial
 

def ultima(compartido): 
	with compartido['lock']:
		if compartido['history']: 
			return compartido['history'][-1] # Devuelve la ultima muestra si hay
		return None


def obtener_historial(compartido):
	with compartido['lock']:
		return list(compartido['history']) # Devuelve una copia del historial


def hilo_generador(compartido, evento_parada: threading.Event):
	"""Genera muestras cada segundo con pequeñas variaciones."""
	# Valores base realistas
	temperatura = random.uniform(15.0, 25.0)  # Celsius 
	humedad = random.uniform(40.0, 60.0)   # %
	presion = random.uniform(1000.0, 1025.0)  # hPa

	while not evento_parada.is_set(): # Bucle hasta que se indique parada
		# Variaciones pequeñas aleatorias
		temperatura += random.uniform(-0.5, 0.5)
		humedad += random.uniform(-1.0, 1.0)
		presion += random.uniform(-0.8, 0.8)

		temperatura = max(-50.0, min(60.0, temperatura))
		humedad = max(0.0, min(100.0, humedad))
		presion = max(300.0, min(1100.0, presion))

		ahora = datetime.now() # Timestamp actual
		muestra = (ahora, round(temperatura, 2), round(humedad, 2), round(presion, 2))
		agregar_muestra(compartido, muestra) # Agrega la muestra al compartido

		time.sleep(1)


def hilo_registrador(compartido, ruta_csv: str, evento_parada: threading.Event):
	dirname = os.path.dirname(ruta_csv) # Ruta del csv
	if dirname and not os.path.exists(dirname):# Crea el directorio si no existe
        
		os.makedirs(dirname, exist_ok=True) # Crea el directorio

	header = ["datetime", "temperatura_C", "humedad_percent", "presion_hPa"] # Cabecera CSV

	escribir_cabecera = not os.path.exists(ruta_csv) # Si el archivo no existe, escribir cabecera
	# Escribe la primera muestra inmediatamente si existe
	primera = ultima(compartido)
	if primera is not None: # Si hay una muestra
		with open(ruta_csv, "a", newline="") as f: # Abre el archivo en modo append
			writer = csv.writer(f) # Crea el escritor CSV
			if escribir_cabecera: # Si es necesario, escribe la cabecera
				writer.writerow(header) # Escribe la cabecera
				escribir_cabecera = False # Marca que ya se escribió
			ts, temperatura, humedad, presion = primera # Desempaqueta la muestra
			writer.writerow([ts.isoformat(sep=" "), temperatura, humedad, presion]) # Escribe la muestra
	while not evento_parada.wait(5): # Espera 5 segundos o hasta que se indique parada
		# Escribe la última muestra
		muestra = ultima(compartido)
		if muestra is None: # Si no hay muestra, continuar
			continue
		with open(ruta_csv, "a", newline="") as f: # Abre el archivo en modo append
			writer = csv.writer(f) # Crea el escritor CSV
			if escribir_cabecera: # Si es necesario, escribe la cabecera
				writer.writerow(header) # Escribe la cabecera
				escribir_cabecera = False # Marca que ya se escribió
			ts, temperatura, humedad, presion = muestra # Desempaqueta la muestra
			writer.writerow([ts.isoformat(sep=" "), temperatura, humedad, presion]) # Escribe la muestra


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
	"""Interfaz grafica """
 
	root = tk.Tk()
	root.title("Estación Meteorologica - Simulacion")

	width = 1200
	height = 1500

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
		canvas.create_text(140, 18, text="Presion (hPa)", fill=colors['pres'], anchor="w")

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

