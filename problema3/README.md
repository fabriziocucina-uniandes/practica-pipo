# Problema 3: Arquitectura Medallion — Bronze y Silver

## Concepto

En pipelines de datos modernos, los datos pasan por capas. Cada capa tiene un propósito distinto:

| Capa       | Propósito                                   | Regla                                            |
| ---------- | ------------------------------------------- | ------------------------------------------------ |
| **Bronze** | Guardar los datos exactamente como llegaron | Nunca se modifica. Es la fuente de verdad cruda. |
| **Silver** | Limpiar, transformar y enriquecer el bronze | Datos listos para analizar                       |
| **Gold**   | Agregaciones y métricas para consumo final  | Tablas que usa un dashboard o un reporte         |

Este patrón se llama **arquitectura medallion** y es el estándar en plataformas como Databricks, Azure y Snowflake.

La regla más importante: **el bronze nunca se toca después de escribirse**. Si algo sale mal en silver, puedes volver a procesar desde bronze sin perder nada.

---

## Tu tarea

Usa la misma API del clima de Bogotá:

```
GET https://api.open-meteo.com/v1/forecast?latitude=4.71&longitude=-74.07&current_weather=true
```

### Paso 1 — Capa Bronze

Crea una tabla `bronze_registros` y guarda los datos **exactamente como llegan de la API**, sin ninguna transformación. Solo agrega una columna `ingested_at` con el momento en que corriste el script.

La tabla debe tener:

| Columna       | Descripción                          |
| ------------- | ------------------------------------ |
| `temperature` | Tal cual viene de la API             |
| `windspeed`   | Tal cual viene de la API             |
| `weathercode` | Tal cual viene de la API             |
| `time`        | Tal cual viene de la API             |
| `ingested_at` | Timestamp de ingesta (lo agregas tú) |

No hay PRIMARY KEY aquí — el bronze es append only, cada ejecución agrega una fila nueva.

---

### Paso 2 — Capa Silver

Crea una tabla `silver_registros` que se construye **leyendo desde bronze**, no desde la API.

Aplica estas transformaciones (las mismas del ejercicio 2):

- Renombrar `temperature` → `temperature_c`
- Agregar `temperature_f` = `(temperature * 9/5) + 32`
- Renombrar `windspeed` → `windspeed_kmh`
- Agregar `wind_category` según la velocidad
- Agregar `weather_description` según el weathercode
- Renombrar `time` → `measured_at`

Para deduplicar, reconstruye silver desde cero en cada ejecución:

1. Borra todo el contenido de `silver_registros`
2. Lee desde bronze, quedándote con el registro más reciente de cada momento

---

### Paso 3 — Separar las responsabilidades

Tu script debe tener dos funciones claramente separadas:

```
load_bronze(conn, data)     # recibe datos de la API, inserta en bronze
load_silver(conn)           # lee desde bronze, transforma, inserta en silver
```

El `main` llama primero `load_bronze` y luego `load_silver`. Silver nunca habla con la API.

---

### Paso 4 — Verificar

Corre el script 3 veces. Luego consulta:

```sql
SELECT COUNT(*) FROM bronze_registros;  -- debe crecer con cada ejecución
SELECT COUNT(*) FROM silver_registros;  -- debe mantenerse igual (idempotente)
```

---

## Criterios de éxito

- [ ] Existen dos tablas: `bronze_registros` y `silver_registros`
- [ ] Bronze guarda los datos crudos sin transformar
- [ ] Silver se construye leyendo desde bronze
- [ ] Las funciones `load_bronze` y `load_silver` están separadas
- [ ] Bronze crece con cada ejecución, silver no tiene duplicados por `time`

## Pistas

- Para leer desde bronze: `cur.execute("SELECT * FROM bronze_registros")`
- `cur.fetchall()` devuelve todas las filas como lista de tuplas
- Puedes acceder a las columnas por índice: `fila[0]`, `fila[1]`, etc.

---

## Patrones que practicamos

| Patrón                     | Dónde aparece                                                              |
| -------------------------- | -------------------------------------------------------------------------- |
| **Arquitectura medallion** | Separar los datos en capas bronze y silver con responsabilidades distintas |
| **Append-only**            | Bronze nunca se modifica, solo se agregan filas nuevas                     |
| **Truncate and reload**    | Silver se borra y se reconstruye completo en cada ejecución                |
| **Separación de capas**    | Silver lee de bronze, nunca de la API directamente                         |
