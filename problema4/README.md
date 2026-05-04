# Problema 4: Pipeline Cloud — Lambda + Step Functions + S3 + Athena

## Concepto

Hasta ahora el pipeline vivía en tu máquina. En este ejercicio lo llevas a la nube:

- Las ingestas corren en **AWS Lambda** (sin servidor, sin máquina que gestionar)
- **Step Functions** orquesta el orden de ejecución
- Los datos crudos llegan a **S3 en formato JSON** (bronze)
- Una Lambda limpia y normaliza los datos a **Parquet** (silver)
- Otra Lambda construye el **star schema** (gold)
- **Athena** lee el gold directamente desde S3 con SQL

Al final tendrás un star schema consultable desde Athena sin ninguna base de datos tradicional.

---

## Conceptos que debes entender antes de empezar

### Parquet
Formato de archivo columnar. A diferencia de CSV o JSON que guardan fila por fila, Parquet guarda columna por columna. Esto significa que si solo consultas `temperature_c`, Athena solo lee esa columna y no toca el resto — mucho más rápido y barato. Es el estándar en data lakes modernos.

### Particionamiento
Forma de organizar los archivos en S3 para que Athena no tenga que leer todo. Si particionas por `year=/month=`, cuando haces `WHERE year=2024 AND month=01`, Athena solo abre esa carpeta y omite todo lo demás. Sin particionamiento, escanea todos los archivos del prefijo — más lento y más caro.

### Tabla de hechos (fact table)
Contiene los eventos o mediciones — lo que ocurrió. En este ejercicio: cada lectura de clima es un hecho. Tiene métricas numéricas (`temperature_c`, `windspeed_kmh`) y claves foráneas que apuntan a las dimensiones. Suele ser la tabla más grande.

### Tablas de dimensión (dim tables)
Contienen el contexto descriptivo del hecho — el quién, qué, dónde, cuándo. En este ejercicio: `dim_city`, `dim_country`, `dim_date`. Cambian poco y son más pequeñas que la tabla de hechos.

### Star Schema
Modelo de datos donde la tabla de hechos está en el centro y las dimensiones la rodean como puntas de una estrella. Optimizado para consultas analíticas con JOINs simples.

### Data Lake en S3
Almacenar datos en S3 como archivos (JSON, Parquet, CSV) en vez de una base de datos tradicional. No hay servidor que gestionar, escala infinito, y el costo es muy bajo. La separación en bronze/silver/gold define la calidad de los datos, no el sistema de almacenamiento.

### Schema on read
En bases de datos tradicionales defines el esquema al crear la tabla (schema on write). En un data lake, los archivos no tienen esquema propio — el esquema se define cuando consultas. Athena lee el Parquet y aplica el esquema que tú defines en Glue. Esto da flexibilidad pero también responsabilidad: si el archivo tiene un tipo distinto al esquema definido, la consulta falla.

### AWS Glue Data Catalog
Catálogo de metadatos que le dice a Athena dónde están los datos en S3 y cómo interpretar los archivos (columnas, tipos, particiones). Sin Glue, Athena no sabe que existen tus archivos Parquet.

### Lambda
Función en la nube que corre código sin que gestiones ningún servidor. Le das el código Python, defines cuánta memoria y tiempo máximo de ejecución, y AWS se encarga del resto. Solo pagas por el tiempo que corre.

### Step Functions
Orquestador de flujos en AWS. Define el orden y las condiciones de ejecución de tus Lambdas — cuáles corren en paralelo, cuáles esperan a otras, qué pasa si una falla. El flujo se define como un JSON (Amazon States Language).

### pyarrow
Librería de Python para leer y escribir archivos Parquet. Como Lambda no la tiene instalada por defecto, hay que empaquetar la librería junto con el código o usar un Lambda Layer.

---

## Fuentes de datos

| Lambda | API | Datos |
|---|---|---|
| `lambda_weather` | Open-Meteo | Mediciones de clima para 10 ciudades |
| `lambda_countries` | REST Countries | Metadata de países (región, población) |

**Las 10 ciudades a consultar:**

```python
CITIES = [
    {"id": "bogota",       "name": "Bogotá",        "lat":  4.71,  "lon": -74.07, "country": "CO"},
    {"id": "buenos_aires", "name": "Buenos Aires",   "lat": -34.61, "lon": -58.37, "country": "AR"},
    {"id": "sao_paulo",    "name": "São Paulo",      "lat": -23.55, "lon": -46.63, "country": "BR"},
    {"id": "lima",         "name": "Lima",           "lat": -12.05, "lon": -77.04, "country": "PE"},
    {"id": "ciudad_mexico","name": "Ciudad de México","lat": 19.43, "lon": -99.13, "country": "MX"},
    {"id": "santiago",     "name": "Santiago",       "lat": -33.45, "lon": -70.67, "country": "CL"},
    {"id": "caracas",      "name": "Caracas",        "lat": 10.48,  "lon": -66.88, "country": "VE"},
    {"id": "quito",        "name": "Quito",          "lat":  -0.23, "lon": -78.52, "country": "EC"},
    {"id": "montevideo",   "name": "Montevideo",     "lat": -34.90, "lon": -56.19, "country": "UY"},
    {"id": "asuncion",     "name": "Asunción",       "lat": -25.29, "lon": -57.65, "country": "PY"},
]
```

---

## Star Schema

```
                    ┌─────────────┐
                    │  dim_date   │
                    │─────────────│
                    │ date_key PK │
                    │ year        │
                    │ month       │
                    │ day         │
                    │ hour        │
                    │ season      │
                    └──────┬──────┘
                           │
┌──────────────┐    ┌──────▼───────────┐    ┌──────────────────┐
│   dim_city   │    │   fact_weather   │    │  dim_country     │
│──────────────│    │──────────────────│    │──────────────────│
│ city_id PK   ├───►│ city_id FK       │◄───┤ country_code PK  │
│ city_name    │    │ country_code FK  │    │ country_name     │
│ country_code │    │ date_key FK      │    │ region           │
│ lat          │    │ temperature_c    │    │ subregion        │
│ lon          │    │ temperature_f    │    │ population       │
└──────────────┘    │ windspeed_kmh    │    │ area_km2         │
                    │ wind_category    │    └──────────────────┘
                    │ weather_desc     │
                    │ ingested_at      │
                    └──────────────────┘
```

---

## Arquitectura AWS

```
Open-Meteo API ──► lambda_weather ──┐
                                    ├──► S3: bronze/weather/      (JSON crudo)
REST Countries ──► lambda_countries ┘──► S3: bronze/countries/    (JSON crudo)
                        │
                Step Functions
                        │
                lambda_silver                                      (limpia y normaliza)
                        │
                        ├──► S3: silver/weather/year=YYYY/month=MM/   (Parquet)
                        └──► S3: silver/countries/                    (Parquet)
                        │
                Step Functions
                        │
                lambda_gold                                        (construye star schema)
                        │
                        ├──► S3: gold/fact_weather/year=YYYY/month=MM/   (Parquet)
                        ├──► S3: gold/dim_city/                          (Parquet)
                        ├──► S3: gold/dim_country/                       (Parquet)
                        └──► S3: gold/dim_date/                          (Parquet)
                                    │
                              Glue Catalog
                                    │
                                 Athena
```

---

## Tu tarea

### Paso 1 — Crear el bucket S3

Crea un bucket llamado `practica-pipo-datalake` con tres prefijos:
- `bronze/`
- `silver/`
- `gold/`

### Paso 2 — Lambda de clima (`lambda_weather`)

Crea una Lambda en Python que:

1. Itere sobre la lista de ciudades
2. Llame al endpoint de Open-Meteo por cada ciudad:
   ```
   GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true
   ```
3. Guarde **un archivo JSON por ciudad** en S3:
   ```
   bronze/weather/{city_id}/{timestamp}.json
   ```

El JSON que guardas debe incluir la respuesta cruda de la API más el `city_id` y el `ingested_at`.

La Lambda necesita el layer de `requests` o usar `urllib` (que ya viene en Python).

### Paso 3 — Lambda de países (`lambda_countries`)

Crea una Lambda que:

1. Llame a la API de países:
   ```
   GET https://restcountries.com/v3.1/alpha?codes=CO,AR,BR,PE,MX,CL,VE,EC,UY,PY
   ```
2. Guarde la respuesta en S3:
   ```
   bronze/countries/latest.json
   ```

### Paso 4 — Lambda silver (`lambda_silver`)

Crea una Lambda que:

1. Lea todos los archivos JSON de `bronze/weather/` y `bronze/countries/`
2. Limpie y normalice los datos (las mismas transformaciones de ejercicios anteriores)
3. Guarde como Parquet en silver — **una fila por registro, sin duplicados**:

```
silver/weather/year=YYYY/month=MM/data.parquet
silver/countries/data.parquet
```

**Reglas de transformación:**
- `temperature_f` = `(temperature_c * 9/5) + 32`
- `wind_category`: calma / moderado / fuerte
- `weather_description`: despejado / nublado / lluvia / otro

Usa `pyarrow` para escribir Parquet. Necesitarás empaquetar la librería en la Lambda (Lambda Layer o deployment package).

### Paso 5 — Lambda gold (`lambda_gold`)

Crea una Lambda que:

1. Lea los Parquet de `silver/weather/` y `silver/countries/`
2. Construya las cuatro tablas del star schema
3. Guarde cada tabla como Parquet en gold, particionando la tabla de hechos:

```
gold/fact_weather/year=YYYY/month=MM/data.parquet
gold/dim_city/data.parquet
gold/dim_country/data.parquet
gold/dim_date/data.parquet
```

**Regla clave:** gold nunca lee de bronze. Solo lee de silver.

**`season`**: en el hemisferio sur, los meses 12-2 son verano, 3-5 otoño, 6-8 invierno, 9-11 primavera. En el norte, al revés.

### Paso 6 — Step Functions

Crea una Step Functions State Machine que ejecute los pasos en este orden:

```
Parallel State:
  ├── lambda_weather
  └── lambda_countries
        │
        ▼ (cuando ambas terminen)
  lambda_silver
        │
        ▼
  lambda_gold
```

Las dos ingestas corren en **paralelo**. Silver espera a que las dos terminen. Gold espera a silver.

Usa una **Express Workflow** (más barata para pipelines frecuentes).

### Paso 7 — Glue Catalog + Athena

1. Crea una base de datos en Glue llamada `practica_pipo`
2. Crea tablas externas en Glue apuntando a cada prefijo de **gold**
3. En Athena, ejecuta estas consultas para verificar:

```sql
-- ¿Cuál es la ciudad más caliente ahora mismo?
SELECT c.city_name, f.temperature_c
FROM fact_weather f
JOIN dim_city c ON f.city_id = c.city_id
ORDER BY f.temperature_c DESC
LIMIT 1;

-- ¿Cuál es la temperatura promedio por región?
SELECT co.region, ROUND(AVG(f.temperature_c), 2) AS avg_temp
FROM fact_weather f
JOIN dim_country co ON f.country_code = co.country_code
GROUP BY co.region
ORDER BY avg_temp DESC;

-- ¿Cuántas ciudades tienen viento fuerte?
SELECT COUNT(*) 
FROM fact_weather 
WHERE wind_category = 'fuerte';
```

---

## Permisos IAM necesarios

Cada Lambda necesita un rol con estas políticas:
- `lambda_weather` y `lambda_countries`: `s3:PutObject` en el bucket
- `lambda_silver`: `s3:GetObject` (bronze) y `s3:PutObject` (silver)
- `lambda_gold`: `s3:GetObject` (silver) y `s3:PutObject` (gold)
- Step Functions: `lambda:InvokeFunction` para las cuatro Lambdas

---

## Criterios de éxito

- [ ] Las tres Lambdas corren sin error
- [ ] El bucket tiene JSON en bronze/, Parquet limpio en silver/, star schema en gold/
- [ ] Los Parquet de fact_weather en gold están particionados por año y mes
- [ ] Las tres consultas de Athena devuelven resultados
- [ ] Correr la Step Machine dos veces no duplica datos en gold (idempotente)
- [ ] gold nunca lee de bronze — solo de silver

---

## Patrones que practicamos

| Patrón | Dónde aparece |
|---|---|
| **Data Lake en S3** | Bronze, silver y gold como prefijos en un bucket, sin base de datos |
| **Serverless ingestion** | Lambdas sin servidor que se activan bajo demanda |
| **Orquestación con Step Functions** | Ejecución paralela de ingestas + transformación secuencial |
| **Columnar storage** | Parquet es más eficiente que JSON para consultas analíticas |
| **Particionamiento** | `year=/month=` permite a Athena escanear solo los datos relevantes |
| **Schema on read** | Athena define el esquema al consultar, no al escribir |
| **Star schema** | Separar hechos de dimensiones para análisis eficiente |
| **Idempotencia** | La transformación reconstruye silver desde bronze en cada ejecución |
