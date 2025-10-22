# Parcial de sistemas operativos
## Integrantes
- Carlos ALberto Cardona Pulido
- William Steban Alfonso Giraldo



## Parte 2 (Buses).
### Descripción.
En este punto se maneja una simulación de un sistema de comunicacion por bus compartido implementada en Python usando multiprocessing. Varios dispositivos intentan enviar datos por un mismo canal. Se usa un semáforo para garantizar que solo un proceso acceda al bus a la vez y un árbitro para servir las peticiones en orden. El programa imprime en la terminal el estado de cada dispositivo. 

### Comandos a tener en cuenta: 
#### Paso 1: Se crea la carpeta y se prepara el entorno: 
![1](https://github.com/rokko3/Parcial-Sistemas-Operativos/blob/main/Imagenes/1.png)
#### Paso 2: Se crea el programa con nano
```
  nano bus.py
  Usar el siguiente codigo:
  #!/usr/bin/env python3
import argparse
import random
import time
from multiprocessing import Process, Semaphore, current_process

def usar_bus(sem: Semaphore, duracion: float, dispositivo: str, intento: int):
    print(f"[{ts()}] {dispositivo} intento {intento}: intentando usar bus")
    
    got_it = sem.acquire(block=False)
    
    try:
        if got_it:
            print(f"[{ts()}] {dispositivo} intento {intento}: usando bus (permiso concedido ✅)")
        else:
            print(f"[{ts()}] {dispositivo} intento {intento}: forzando entrada al bus 🚨 (sin permiso)")
        
        time.sleep(duracion)
        
        print(f"[{ts()}] {dispositivo} intento {intento}: liberando bus")
    finally:
        if got_it:
            sem.release()

def tarea_dispositivo(idx: int, sem: Semaphore, intentos: int, tmin: float, tmax: float):
    dispositivo = f"Dispositivo-{idx}"
    for intento in range(1, intentos + 1):
        time.sleep(random.uniform(0.1, 0.6))
        duracion = random.uniform(tmin, tmax)
        usar_bus(sem, duracion, dispositivo, intento)
    print(f"[{ts()}] {dispositivo}: terminado")

def ts():
    return time.strftime("%H:%M:%S")

def main():
    parser = argparse.ArgumentParser(
        description="Simulación de bus compartido con semáforo y acceso forzado"
    )
    parser.add_argument("--dispositivos", type=int, default=5, help="cantidad de procesos")
    parser.add_argument("--intentos", type=int, default=3, help="veces que cada proceso usa el bus")
    parser.add_argument("--tmin", type=float, default=0.5, help="uso mínimo del bus en segundos")
    parser.add_argument("--tmax", type=float, default=1.5, help="uso máximo del bus en segundos")
    args = parser.parse_args()

    sem = Semaphore(1)

    procesos = []
    for i in range(1, args.dispositivos + 1):
        p = Process(target=tarea_dispositivo, args=(i, sem, args.intentos, args.tmin, args.tmax), name=f"Dev-{i}")
        p.start()
        procesos.append(p)

    for p in procesos:
        p.join()

    print(f"[{ts()}] Simulación completada (modo forzado)")

if __name__ == "__main__":
    main()
```

#### Paso 3: Hacer el script ejecutable
![4](https://github.com/rokko3/Parcial-Sistemas-Operativos/blob/main/Imagenes/3.png)
#### Paso 4: Ejecutar el programa
```
  ./bus.py
```

### Prueba
![6](https://github.com/rokko3/Parcial-Sistemas-Operativos/blob/main/Imagenes/4.png)

