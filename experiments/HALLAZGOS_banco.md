# Hallazgos del banco de exámenes por nivel

Material de apoyo para la memoria del TFG. Reproducible con:

```
PYTHONPATH=src .venv_mac/bin/python experiments/banco_examenes.py
```

## Qué es

`src/ai/exam_bank.py` reúne **33 exámenes conceptuales** repartidos por cinco
niveles (Primaria, ESO, Bachillerato, Universidad — Ing. Informática — y Máster)
y un abanico de asignaturas. Cada pregunta lleva su rúbrica y **tres respuestas
de alumno con la nota que pondría un profesor** (notable / aprobado / suspenso),
99 respuestas en total. Las notas humanas son de referencia (asignadas por el
autor según rúbrica), no de un tribunal real.

## Resultado global

| Métrica | Sin sinónimos | **Con sinónimos por concepto** |
|---|---|---|
| N respuestas | 99 | 99 |
| Spearman (ρ) | +0,872 | **+0,931** |
| Pearson (r) | +0,875 | **+0,946** |
| MAE | 1,44 / 10 | **0,96 / 10** |
| RMSE | 2,17 / 10 | **1,34 / 10** |
| Discrepancias ≥ 2,5 puntos | 24 / 99 (24 %) | **9 / 99 (9 %)** |

Por nivel, ρ pasa de 0,84–0,91 a **0,91–0,95** sin caer en ningún tramo: el
sistema **ordena** las respuestas como un profesor desde Primaria hasta Máster.

## Un bug encontrado y corregido

El banco destapó un **falso positivo del detector de negación**: en
"dos **no metales** comparten pares de electrones para formar una molécula", el
"no" de "no metales" hacía que se marcaran como *negados* los conceptos
posteriores, hundiendo un notable de Química de 10 a 6,0. Se corrigió añadiendo
"no metales/metal/metálico" a las excepciones léxicas del negador (igual que
"no solo … sino"). Tras el arreglo, ese notable puntúa 8,8 y hay un test de
regresión (`tests/test_negation.py::test_no_metales_no_es_negacion`).

## La limitación que se atacó: paráfrasis

La mayoría de las 24 discrepancias iniciales eran del mismo tipo: **el sistema
infravaloraba respuestas correctas expresadas con palabras propias**, porque la
detección de conceptos era literal. El alumno **describía** el concepto sin
**nombrarlo** ("último en entrar, primero en salir" en vez de "LIFO").

### Solución: sinónimos por concepto

Cada concepto de la rúbrica puede declarar `synonyms`: paráfrasis que el profesor
acepta como equivalentes (campo opcional en `key_concepts`, también en la API web
`KeyConcept.synonyms`). El grader acredita el concepto si aparece el término, un
sinónimo como subcadena, o **todos los tokens de contenido del sinónimo** con
tolerancia morfológica (mismo umbral fuzzy 0,80: "metes"≈"meter"). Es
determinista e interpretable, y **respeta la negación** (un sinónimo negado,
"sin ningún dato ni etiqueta", no acredita el concepto).

| Respuesta del alumno | Profesor | Sin sinón. | Con sinón. |
|---|---|---|---|
| "el último que metes es el primero que sacas" (LIFO) | 7,0 | 0,16 | **~4–7** |
| "convertir palabras en vectores donde las parecidas están cerca" (embedding) | 7,0 | 0,17 | **~7** |
| "es un programa que se está ejecutando" (proceso) | 6,5 | 1,66 | **~5–6** |

Efecto global: ρ 0,872 → **0,931**, MAE 1,44 → **0,96**, discrepancias 24 % → **9 %**.

No se "parchea" subiendo la similitud global (rompería los 40 casos de
`validate.py` y premiaría respuestas vacías): los sinónimos son **aditivos** —un
concepto sin `synonyms` se comporta igual que antes—, por eso la suite de
validación sigue al 100 %.

## Lo que queda (honesto): 9 discrepancias

- **2 sobrevaloraciones** por presencia de términos sin coherencia ("el sujeto y
  el predicado son signos de puntuación"; "la fotosíntesis consume oxígeno"). Es
  el límite del enfoque por conceptos; lo marca el **verificador LLM**
  (`/api/verify_answer`).
- **7 infravaloraciones** que ya **no son paráfrasis**, sino respuestas
  genuinamente **incompletas** (solo nombran parte de la rúbrica). Que una
  respuesta a medias saque menos que una completa es el comportamiento correcto.

## Lectura para la defensa

El corrector determinista es un **evaluador trazable de terminología** que ordena
muy bien (ρ≈0,93 en todos los niveles, de Primaria a Máster) y, con los
**sinónimos por concepto**, deja de penalizar la paráfrasis sin perder
interpretabilidad ni inflar respuestas falsas. Se equivoca de forma **predecible**
y el sistema es honesto sobre el 9 % restante, en vez de aparentar una corrección
"perfecta".
