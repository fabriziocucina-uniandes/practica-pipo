import requests
import sqlite3
import json
from datetime import datetime


#Capa Bronze
def load_bronze(conn, data):
    cur.execute(""" 
            CREATE TABLE IF NOT EXISTS bronze_registros (
                temperature REAL,
                windspeed REAL,
                weathercode INTEGER,
                time TEXT,
                ingested_at TEXT      
            );
    """)

    # Patron Append-Only
    cur.execute(""" 
            INSERT INTO bronze_registros (
                temperature,
                windspeed,
                weathercode,
                time,
                ingested_at
            )
        VALUES 
            (?, ?, ?, ?, ?)
    """, data)

    valores = cur.execute(""" SELECT * FROM bronze_registros""")

    for valor in valores:
        print(valor)

    cur.execute(""" SELECT COUNT(*) FROM bronze_registros""")

    filas = cur.fetchall()

    for fila in filas:
        print(fila)

#Capa Silver

def load_silver(conn):
    
    cur.execute(""" 
            CREATE TABLE IF NOT EXISTS silver_registros ( 
                temperature_c REAL,
                temperature_f REAL,
                windspeed_kmh REAL,
                wind_category REAL,
                weather_description TEXT,
                measured_at TEXT
            );
    """)
    
    cur.execute(""" DELETE FROM silver_registros; """)

    cur.execute(""" 
            INSERT INTO silver_registros (
                temperature_c,
                temperature_f,
                windspeed_kmh,
                wind_category,
                weather_description,
                measured_at
            )
            SELECT 
                temperature,
                (temperature * 9/5) + 32,
                windspeed,
                CASE 
                    WHEN windspeed >= 0 AND windspeed <= 19 THEN 'calma'
                    WHEN windspeed >= 20 AND windspeed <= 39 THEN 'moderado'
                    ELSE 'fuerte'
                END,
                CASE
                    WHEN weathercode = 0 THEN 'despejado'
                    WHEN weathercode >= 1 AND weathercode <= 29 THEN 'nublado'
                    WHEN weathercode >= 30 AND weathercode <= 59 THEN 'lluvioso'
                END,
                time
            FROM bronze_registros
            WHERE ingested_at = (
                SELECT MAX(ingested_at)
                FROM bronze_registros AS b2
                WHERE b2.time = bronze_registros.time
                );
    """)

    valores = cur.execute(""" SELECT * FROM silver_registros""")

    for valor in valores:
        print(valor)

    cur.execute(""" SELECT COUNT(*) FROM silver_registros""")

    filas = cur.fetchall()

    for fila in filas:
        print(fila)
    

if __name__ == "__main__":
    response = requests.get("https://api.open-meteo.com/v1/forecast?latitude=4.71&longitude=-74.07&current_weather=true")

    response_json = response.json()['current_weather']
    response_json_show = json.dumps(response_json, indent=4)
    print(response_json_show)
    ingested_at = datetime.now()

    data_db = (
        response_json['temperature'],
        response_json['windspeed'],
        response_json['weathercode'],
        response_json['time'],
        ingested_at
    )


    connection = sqlite3.connect("medallion.db")
    cur = connection.cursor()
    
    load_bronze(connection, data_db)
    load_silver(connection)

    connection.commit()
    connection.close()