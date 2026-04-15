# Problema 1: API → SQLite

## Objetivo

Consumir datos de una API pública y guardarlos en una base de datos SQLite.

## Instrucciones

Usa la siguiente API pública (no requiere registro):

```
GET https://api.open-meteo.com/v1/forecast?latitude=4.71&longitude=-74.07&current_weather=true
```

Esta API devuelve el clima actual de Bogotá. El campo que nos interesa es `current_weather`:

```json
{
  "current_weather": {
    "temperature": 18.5,
    "windspeed": 12.3,
    "weathercode": 3,
    "time": "2024-01-01T12:00"
  }
}
```

Tu tarea:

1. Llama a la API con la librería `requests`
2. Crea una base de datos SQLite llamada `clima.db` con una tabla `registros`
3. La tabla debe tener las columnas: `temperature`, `windspeed`, `weathercode`, `time`
4. Inserta el resultado de la API en la tabla
5. Haz una consulta `SELECT *` e imprime los resultados

## Pistas

- `sqlite3` ya viene con Python
- `pip install requests`
- `conn = sqlite3.connect("clima.db")`
- Recuerda `conn.commit()` después de insertar
