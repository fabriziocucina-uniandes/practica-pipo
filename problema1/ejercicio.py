import requests
import sqlite3

# 1. Obtener los datos de la API
url_response = requests.get("https://api.open-meteo.com/v1/forecast?latitude=4.71&longitude=-74.07&current_weather=true")
data_json = url_response.json()['current_weather']

# 2. Crear la TUPLA
data_db = (     
    data_json['temperature'],
    data_json['windspeed'],
    data_json['weathercode'],
    data_json['time']
)

# 3. Conexión
connection = sqlite3.connect("clima.db")
cur = connection.cursor()

# --- EL TRUCO PARA ELIMINAR EL ERROR ---
# Borramos la tabla vieja que tiene el error de nombre y la creamos de cero
cur.execute("DROP TABLE IF EXISTS registros")

cur.execute("""
    CREATE TABLE registros (
        temperature REAL,
        windspeed   REAL,
        weathercode INTEGER,
        period      TEXT
    )
""")

# 4. Inserción
cur.execute(""" 
    INSERT INTO registros (temperature, windspeed, weathercode, period)
    VALUES (?, ?, ?, ?)
""", data_db)

# 5. SELECT para ver resultados
cur.execute("SELECT * FROM registros")
filas = cur.fetchall()

print("\n--- DATOS EN LA BASE DE DATOS ---")
for fila in filas:
    print(fila)

# 6. Guardar y cerrar
connection.commit()
connection.close()

print("\n¡Proceso finalizado con éxito!")