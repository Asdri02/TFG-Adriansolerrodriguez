# Validación externa con datos reales

Material para la memoria. Hasta ahora todas las notas humanas eran de referencia
(asignadas por el autor). Aquí probamos contra **notas de profesores humanos
reales** de un dataset público.

## Dataset usado: Mohler (Universidad de North Texas)

- Curso universitario de **Informática**, en **inglés**.
- 87 preguntas con respuesta de referencia + **2.442 respuestas de alumnos**,
  cada una con la nota media de **dos correctores humanos** (0–5 → escalada a 0–10).
- Descarga automática (no se versiona): repo `dbbrandt/short_answer_granding_capstone_project`
  (`data/sag`); dataset original Mohler et al., 2011.
- Runner: `experiments/mohler_validacion.py`.

## Resultado

| Métrica | Valor |
|---|---|
| Spearman global | +0,54 |
| Spearman medio por pregunta | +0,49 |
| Pearson | +0,48 |
| MAE | 4,33 / 10 |
| MAE quitando el sesgo constante | **1,63 / 10** |

### Lectura honesta

1. **Es un suelo, no el mejor caso.** El dataset está en inglés, donde nuestras
   features de **negación y sinónimos** (en español) no actúan: solo se prueba el
   motor base (conceptos + similitud). Además la rúbrica se **deriva
   automáticamente** de la respuesta de referencia (palabras de contenido, peso
   uniforme), bastante peor que una rúbrica de profesor.

2. **El error es sobre todo de ESCALA, no de criterio.** Media humana 8,38 vs
   sistema 4,15: los correctores de Mohler son muy generosos (80 % de notas ≥7),
   nuestro grader es estricto (20 %). Al restar ese desfase constante, el MAE pasa
   de 4,33 a **1,63**. Es decir, el sistema **ordena** de forma parecida pero en
   una escala más severa; recalibrar la leniencia (lo hace el módulo
   `/api/calibrate_grade` con ejemplos del profesor) cerraría buena parte del hueco.

3. **Cuantifica de cuánto dependen las rúbricas y el idioma.** Frente al banco
   propio (español, rúbrica curada + sinónimos: ρ≈0,93), aquí ρ≈0,54. La
   diferencia mide lo que aportan una rúbrica bien hecha y las features de idioma.

## Recalibración: cerrar el desfase de escala (datos reales)

Como el error era sobre todo de escala, se añadió una **capa de calibración
determinista** (`src/ai/calibration.py`, `ScoreCalibrator`, lineal o isotónica)
que aprende el mapeo nota_grader → nota_profesor. Se evaluó **con honestidad**:
ajustada en el 70 % de Mohler y medida en el 30 % NO visto
(`experiments/mohler_calibracion.py`).

| En TEST (no visto) | MAE | RMSE | Pearson | Spearman |
|---|---|---|---|---|
| Cruda | 4,18 | 5,00 | +0,47 | +0,53 |
| **Calibración lineal** | **1,42** | 1,97 | +0,48 | +0,53 |
| Calibración isotónica | 1,46 | 2,07 | +0,45 | +0,53 |

- **MAE 4,18 → 1,42 en datos no vistos**: el desfase era sistemático y se corrige
  con muy pocas notas del profesor.
- **El Spearman no cambia** (mapeo monótono): la calibración no inventa orden,
  solo ajusta la escala a la leniencia del corrector.

### Caveat honesto (importante para la defensa)

El calibrador ajustado fue `nota = clip(0,336·cruda + 7,02; 0; 10)`. Como los
correctores de Mohler son muy generosos, ese mapeo lleva **una respuesta cruda de
0 a un 7,0**. Es decir: **la calibración reproduce fielmente el criterio (y la
leniencia) del profesor de referencia, incluida su poca discriminación**. No es un
fallo —es lo que significa calibrar— pero implica que la calibración es tan buena
(y tan exigente) como las notas con las que se la alimenta. Por eso conviene
combinarla con rúbricas y sinónimos curados, que sí discriminan.

## Sobre conseguir más exámenes reales (colegio / universidad / máster)

- **Con respuestas de alumno ya corregidas** (lo que sirve para validar como aquí):
  son datasets de investigación, casi todos en inglés:
  - **Mohler** (universidad, CS) — usado aquí.
  - **ASAP-SAS** (Kaggle, nivel escolar, ciencias; ~17 000 respuestas) — requiere
    cuenta de Kaggle para descargar.
  - **SemEval-2013 Task 7 / BEETLE / SciEntsBank** (ciencias).
  - Dataset **multilingüe** (MDPI Data 2026, *JorGPT*) que podría incluir español;
    su web bloquea la descarga automática (HTTP 403), habría que bajarlo a mano.
- **Exámenes oficiales españoles** (EvAU/PAU, p.ej. examenesdepau.com, gobiernos
  autonómicos): traen **enunciado + criterios de corrección + solución modelo**,
  pero **no respuestas reales de alumnos con su nota**, así que sirven para nutrir
  preguntas/rúbricas reales, no para medir concordancia con el profesor (las notas
  habría que sintetizarlas, como en `exam_bank.py`).

## Conclusión para la defensa

El sistema, sobre notas humanas reales y en su peor escenario (inglés, sin rúbrica
curada), **mantiene una correlación moderada (ρ≈0,5) y un error que es casi todo
de escala** (MAE 1,6 tras recalibrar). Con rúbrica curada, sinónimos del profesor
y calibración de leniencia —todo ya implementado— el rendimiento sube
sustancialmente (ρ≈0,93 en el banco propio). Es un resultado honesto que delimita
con números cuándo el corrector es fiable y cuándo necesita ayuda del profesor.
