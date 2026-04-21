# Problema 2: Transformación e Idempotencia

## Conceptos

**Transformación**: no guardar los datos exactamente como llegan de la API. Limpiarlos, enriquecerlos y darles un formato útil.

**Idempotencia**: si corres el script 10 veces seguidas, el resultado debe ser el mismo que si lo corres 1 vez. Sin duplicados, sin errores.

Estos dos conceptos son fundamentales en cualquier pipeline de datos real.

---

## Tu tarea

Usa la misma API del ejercicio 1:

```
GET https://api.open-meteo.com/v1/forecast?latitude=4.71&longitude=-74.07&current_weather=true
```

### Paso 1 — Transformar los datos

Antes de insertar, transforma la respuesta de la API así:

| Campo original | Campo transformado | Transformación |
|---|---|---|
| `temperature` | `temperature_c` | Sin cambio, solo renombrar |
| `temperature` | `temperature_f` | Convertir a Fahrenheit: `(temp * 9/5) + 32` |
| `windspeed` | `windspeed_kmh` | Sin cambio, solo renombrar |
| `windspeed` | `wind_category` | Categorizar (ver tabla abajo) |
| `weathercode` | `weathercode` | Sin cambio |
| `weathercode` | `weather_description` | Traducir código a texto (ver tabla abajo) |
| `time` | `measured_at` | Sin cambio, solo renombrar |

**Categorías de viento:**

| windspeed (km/h) | wind_category |
|---|---|
| 0 - 19 | "calma" |
| 20 - 49 | "moderado" |
| 50 o más | "fuerte" |

**Descripción del weathercode** (solo necesitas estos):

| weathercode | weather_description |
|---|---|
| 0 | "despejado" |
| 1, 2, 3 | "nublado" |
| 61, 63, 65 | "lluvia" |
| cualquier otro | "otro" |

---

### Paso 2 — Diseñar la tabla

Crea una tabla `registros` con todas las columnas transformadas. Incluye también `ingested_at` con el momento en que corriste el script.

---

### Paso 3 — Hacer el script idempotente

El campo `measured_at` es el timestamp de la medición. La API actualiza el clima cada hora, entonces dos ejecuciones en la misma hora devuelven el mismo `measured_at`.

Haz que tu script no duplique registros si se corre varias veces con el mismo `measured_at`.

Pista: investiga `INSERT OR REPLACE` y cómo funciona con una `PRIMARY KEY`.

---

### Paso 4 — Verificar

Corre tu script 3 veces seguidas. Luego consulta:

```sql
SELECT COUNT(*) FROM registros;
```

Si el resultado es mayor a lo esperado, tu script no es idempotente todavía.

---

## Criterios de éxito

- [ ] Los datos se transforman correctamente antes de insertar
- [ ] Correr el script múltiples veces no genera duplicados
- [ ] La tabla tiene todas las columnas transformadas
- [ ] `SELECT COUNT(*)` da el mismo resultado sin importar cuántas veces corriste el script

## Pistas

- Para hacer una columna llave primaria: `campo TEXT PRIMARY KEY`
- `INSERT OR REPLACE` reemplaza el registro si la llave ya existe
- Puedes usar un diccionario de Python para mapear weathercode a descripción
