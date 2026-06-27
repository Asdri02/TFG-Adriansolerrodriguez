# Guion de defensa: preguntas difíciles y respuestas

Preparación para el tribunal. Cada respuesta debe poder darse sin leer, idealmente
con un ejemplo o en la pizarra. No memorices el texto: entiende el porqué.

## 1. "Tu 0,93 es concordancia contigo mismo, ¿no?"

Cierto, y por eso no es la cifra principal. La validación seria está en el conjunto
de Mohler, con **dos correctores humanos reales**. Ahí lo importante no es el número
del sistema en abstracto, sino frente al **techo humano**: los dos profesores solo
concuerdan entre sí con un Spearman de **0,60**. El sistema alcanza **0,55** con el
promedio humano, es decir, en torno al **90 % del acuerdo que tienen dos humanos
entre sí**, y además en su peor escenario (inglés, rúbrica automática). Ningún
corrector, ni humano, llega a 1: pedir más que el acuerdo humano-humano no tiene
sentido.

## 2. "¿Por qué no usar embeddings / sentence-transformers para la paráfrasis?"

Por dos razones, una de principio y una empírica. De principio: la interpretabilidad.
En evaluación, una nota debe poder justificarse concepto a concepto, y un vector
denso no lo permite. Empírica: comparé el sistema con dos líneas base en el mismo
banco. "Solo palabras clave" da Spearman 0,86 y "TF-IDF coseno" 0,84; el sistema
completo, **0,93** con un MAE de **0,96** frente a 1,64 y 2,19. Una similitud simple
no penaliza lo erróneo ni distingue qué concepto importa. Los embeddings son una
línea de trabajo futuro razonable, pero como complemento, no como sustituto del
núcleo interpretable.

## 3. "El título dice 'a partir de imágenes' pero validas texto tecleado."

Hay una evaluación de OCR sobre texto impreso: con imagen limpia el error es 0 % y
la nota no cambia; bajo desenfoque o rotación el error de lectura sube, pero el
impacto en la **nota** se mantiene bajo (una rotación de 4° da 25 % de error de
caracteres y solo 0,3 puntos de diferencia), porque lo que importa es que
sobrevivan los conceptos, no cada letra. El ruido fuerte sí rompe el OCR, y es un
límite reconocido. El manuscrito queda explícitamente fuera de alcance: es un
problema distinto y más difícil, y el trabajo se centra en la evaluación de la
respuesta una vez extraída.

## 4. "¿Por qué el suelo mínimo se aplica DESPUÉS de la penalización de longitud?"

Para que el suelo cumpla su función: proteger una respuesta que ya demuestra
comprensión. Si se aplicara antes, la penalización por longitud podría volver a
hundir la nota por debajo del umbral y anularlo. Aplicándolo al final, una vez que
la cobertura conceptual es suficiente, la nota no baja del suelo por ningún motivo,
ni por baja similitud ni por brevedad.

## 5. "¿Cómo decides hasta dónde llega una negación?"

La negación se limita a su cláusula. Divido la respuesta por puntuación y por
ciertas conjunciones, y dentro de cada cláusula busco un negador antes del concepto.
Así "la mitocondria no produce ATP" niega ATP, pero "a diferencia del cloroplasto,
que no respira, la mitocondria sí produce ATP" no lo niega, porque la negación está
en otra cláusula. La lista de negadores es conservadora a propósito, con excepciones
como "no solo... sino" o "no metales", porque el peor error de un corrector es
castigar una respuesta correcta.

## 6. "La calibración isotónica, ¿por qué no cambia el Spearman?"

Porque es un mapeo monótono creciente: reordena la escala pero no el orden de las
respuestas. El Spearman mide orden, así que es invariante ante cualquier
transformación monótona. La calibración corrige el desfase de escala (un sistema
severo frente a un corrector generoso) sin inventar orden. Lo validé entrenando con
el 70 % de Mohler y midiendo en el 30 % no visto: el MAE bajó de 4,18 a 1,42 sin que
el Spearman se moviera.

## 7. "¿Dónde empieza y acaba la inteligencia artificial en tu sistema?"

El núcleo —corrección por conceptos, polaridad, sinónimos, similitud, calibración—
es determinista y no usa modelos de lenguaje. El modelo de lenguaje interviene solo
en funciones opcionales y acotadas: proponer rúbricas, verificar factualidad como
segunda opinión (sin reescribir la nota) y juzgar redacción. Sin clave de servicio,
todo el flujo principal sigue funcionando. Es un sistema híbrido con un núcleo
auditable, no un envoltorio de un modelo de lenguaje.

## 8. "¿Qué harías con más tiempo?"

Tres cosas, por impacto: conseguir respuestas reales corregidas por varios
profesores en español para repetir la medida del techo humano en mi idioma; evaluar
el OCR sobre manuscrito real; e incorporar embeddings como señal adicional,
midiendo si mejoran sin sacrificar interpretabilidad.

## Números que debes saber de memoria

- Acuerdo humano-humano (Mohler): **Spearman 0,60**.
- Sistema vs. humano (Mohler, peor caso): **0,55**, ~90 % del techo.
- Banco propio (conceptual, con sinónimos): **Spearman 0,93**, MAE **0,96**.
- Líneas base: palabras clave **0,86**, TF-IDF **0,84**; sistema **0,93**.
- Calibración en test no visto: MAE **4,18 → 1,42**, Spearman invariante.
- OCR impreso limpio: **0 %** de error; rotación 4°: 25 % CER pero solo 0,3 de Δnota.
