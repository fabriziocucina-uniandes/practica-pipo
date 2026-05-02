import requests
import json
from datetime import datetime
import sqlite3

#Todo esto es mas enfocado a OLAP.
#Para Backend es OLTP

#Mostrando el JSON antes de la transformacion
url_response = requests.get("https://api.open-meteo.com/v1/forecast?latitude=4.71&longitude=-74.07&current_weather=true")

data_json = url_response.json()["current_weather"]
json_result = json.dumps(data_json, indent=4)
print(json_result)


#Despues de la transformacion con el nuevo JSON
temperature_farenheit = data_json["temperature"]
w_speed = data_json["windspeed"]
w_code = data_json["weathercode"]
momento_actual = datetime.now()
formato = str(momento_actual.strftime("%d/%m/%Y %H:%M"))

if w_speed >= 0 and w_speed <= 19:
    wind_category = "calma"
elif w_speed >= 20 and w_speed <= 49:
    wind_category = "moderado"
else:
    wind_category = "fuerte"

if w_code == 0:
    weather_code = "despejado"
elif w_code in [1, 2, 3]:
    weather_code = "nublado"
elif w_code in [61, 63, 65]:
    weather_code = "lluvia"
else:
    weather_code = "otro"

nuevo_json = {
    "temperature_c": data_json["temperature"],
    "temperature_f": (temperature_farenheit * 9/5) + 32,
    "windspeed_kmh": data_json["windspeed"],
    "wind_category": wind_category,
    "weathercode": data_json["weathercode"],
    "weather_description": weather_code,
    "measured_at": data_json["time"],
    "ingested_at": formato
}

data_db = (     
    nuevo_json["temperature_c"],    
    nuevo_json["temperature_f"],
    nuevo_json["windspeed_kmh"],
    nuevo_json["wind_category"],
    nuevo_json["weathercode"],
    nuevo_json["weather_description"],
    nuevo_json["measured_at"], 
    nuevo_json["ingested_at"]
)

print(json.dumps(nuevo_json, indent=4))

# Iniciamos la conexion y creacion de la base de datos

connection = sqlite3.connect("problema2\weather.db")
cur = connection.cursor()

# En idempotencia no necesariamente el ID va a ser el PRIMARY KEY
# De esta forma, el Pipe line se va a romper muy facil

#cur.execute(""" DROP TABLE IF EXISTS registros""")

cur.execute(""" 
        CREATE TABLE IF NOT EXISTS registros (
            temperature_c REAL,
            temperature_f REAL,
            windspeed_kmh REAL,
            wind_category TEXT,
            weathercode INTEGER,
            weather_description TEXT,
            measured_at TEXT PRIMARY KEY,
            ingested_at TEXT
        );
""")

cur.execute(""" 
        INSERT INTO registros(temperature_c, temperature_f, windspeed_kmh,
            wind_category, weathercode, weather_description, measured_at, ingested_at)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(measured_at) DO UPDATE SET
            temperature_c = excluded.temperature_c,
            temperature_f = excluded.temperature_f,
            windspeed_kmh = excluded.windspeed_kmh,
            wind_category = excluded.wind_category,
            weathercode = excluded.weathercode,
            weather_description = excluded.weather_description,
            ingested_at = excluded.ingested_at

""", data_db)


""" 
Esta no es la mejor forma de hacerlo, pero digamos que hace lo mismo.
Se va a quedar como comentario y debe ser ignorado.

cur.execute(
        INSERT OR IGNORE INTO registros(temperature_c, temperature_f, windspeed_kmh,
            wind_category, weathercode, weather_description, measured_at, ingested_at)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?)
, data_db)

#Hacer el Merge

cur.execute( 
        UPDATE registros
        SET
            temperature_c = :temperature_c,
            temperature_f = :temperature_f,
            windspeed_kmh = :windspeed_kmh,
            wind_category = :wind_category,
            weathercode = :weathercode,
            weather_description = :weather_description,
            measured_at = :measured_at,
            ingested_at = :ingested_at
        WHERE measured_at = :measured_at
, data_db)
"""

cur.execute(""" 
    SELECT COUNT(*) FROM registros
""")

print("--- Datos en la Base de Datos ---")

filas = cur.fetchall()

for fila in filas:
    print(fila)

cur.execute(""" SELECT * FROM registros """)
filas_contenido = cur.fetchall()

for fila in filas_contenido:
    print(fila)

connection.commit()
connection.close()
