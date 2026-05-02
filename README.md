# TFG - Sistema Inteligente de Corrección de Exámenes

Este proyecto desarrolla un sistema de evaluación automática capaz de corregir exámenes a partir de imágenes digitales.

A diferencia de enfoques basados en aprendizaje automático, el sistema implementa un enfoque híbrido que combina OCR, procesamiento de texto y evaluación semántica basada en conceptos clave.

---

## Funcionalidad

El sistema sigue el siguiente pipeline:

1. Lectura de imagen de examen
2. Extracción de texto mediante OCR
3. Identificación de pregunta y respuesta
4. Generación de referencia (controlada)
5. Evaluación semántica de la respuesta del alumno
6. Asignación de nota y feedback

---

## Ejemplo de ejecución

Entrada (imagen):
- Imagen de un examen con pregunta y respuesta escrita

Salida del sistema:

--- OCR ---
Pregunta detectada: ¿Cuál es la función de la mitocondria?
Respuesta detectada: La mitocondria produce energía para la célula.

--- CORRECCIÓN ---
Nota: 6.0
Conceptos detectados: ['mitocondria', 'energía']
Conceptos parciales: ['respiración celular']
Conceptos ausentes: ['ATP']

---

## Estructura del proyecto

src/ # Núcleo del sistema
data/ # Imágenes de entrada
requirements.txt


---

## Tecnologías utilizadas

- Python
- OpenCV
- NumPy
- Tesseract OCR
- Técnicas básicas de NLP

---

## Estado actual

El sistema permite:

- Procesar imágenes reales
- Extraer texto de forma automática
- Evaluar respuestas abiertas de forma aproximada
- Generar feedback basado en conceptos

---

## Limitaciones

- Dependencia de la calidad del OCR
- Evaluación basada en conceptos (no comprensión completa)
- No sustituye el criterio humano

---

## Ejecución

Instalar dependencias:

pip install -r requirements.txt


Ejecutar:

python src/test_full_pipeline.py


---

## Herramientas de desarrollo

`bridge.py` es un script auxiliar (review/improve/explain de archivos del repo)
que usa la API de Claude y la API de GitHub. **No forma parte del sistema de
corrección** y no es necesario para ejecutar el pipeline ni los tests.

Para utilizarlo:

1. Instala sus dependencias: `pip install -r requirements-dev.txt`
2. Copia `.env.example` a `.env` y rellena `ANTHROPIC_API_KEY` y `GITHUB_TOKEN`.

---

## Adrián Soler Rodríguez

Trabajo de Fin de Grado
