"""
exam_bank.py — Banco de exámenes por NIVEL educativo con corrección del profesor.

Objetivo: comprobar si el corrector puntúa "como un profesor" en un abanico
amplio de niveles y asignaturas. Cada pregunta trae una rúbrica y varias
respuestas de alumno, CADA UNA con su nota humana de referencia, de modo que se
puede medir si el sistema concuerda con esa corrección (ver
`experiments/banco_examenes.py`, que calcula Spearman/MAE por nivel y asignatura).

NIVELES: Primaria · ESO · Bachillerato · Universidad (Ing. Informática) · Máster.

ADVERTENCIA DE HONESTIDAD (para la memoria del TFG): las notas humanas NO son de
un tribunal real; son notas de referencia asignadas por el autor según rúbrica,
emulando el criterio de un profesor de ese nivel. Sirven para validar la
concordancia con un criterio explícito, no la exactitud absoluta. Las preguntas
son CONCEPTUALES (definir/explicar), que es el ámbito del grader semántico; el
cálculo numérico y la redacción se evalúan con otros módulos (answer_checker,
grade_writing) y quedan fuera de este banco a propósito.

Estructura de cada entrada:
    {
      "level":   "Primaria" | "ESO" | "Bachillerato" | "Universidad" | "Máster",
      "subject": "<asignatura>",
      "reference": ReferenceAnswer,
      "graded":  [(respuesta_alumno, nota_humana_0_10), ...],
    }
"""

from __future__ import annotations

from typing import Any, Dict, List

from ai.models import ReferenceAnswer


def _q(level: str, subject: str, question: str, ideal: str,
       concepts: List[tuple], graded: List[tuple]) -> Dict[str, Any]:
    """
    Cada concepto es `(concepto, peso)` o `(concepto, peso, [sinónimos])`. Los
    sinónimos son paráfrasis que el profesor acepta como equivalentes al término
    (p.ej. "último en entrar primero en salir" para "LIFO").
    """
    key_concepts = []
    for entry in concepts:
        concept, weight = entry[0], entry[1]
        synonyms = entry[2] if len(entry) > 2 else []
        kc = {"concept": concept, "weight": weight}
        if synonyms:
            kc["synonyms"] = synonyms
        key_concepts.append(kc)
    return {
        "level": level,
        "subject": subject,
        "reference": ReferenceAnswer(
            question=question, subject=subject, education_level=level,
            expected_answer_type="respuesta_corta", ideal_answer=ideal,
            key_concepts=key_concepts,
        ),
        "graded": [(a, float(s)) for a, s in graded],
    }


EXAMS: List[Dict[str, Any]] = []

# ════════════════════════════════════════════════════════════════════════════
#  PRIMARIA
# ════════════════════════════════════════════════════════════════════════════

EXAMS.append(_q(
    "Primaria", "Lengua", "¿Qué es un sustantivo? Pon un ejemplo.",
    "Un sustantivo es una palabra que nombra a personas, animales, cosas o ideas, "
    "como 'perro' o 'mesa'.",
    [("nombra", 0.4), ("personas", 0.2), ("animales", 0.2), ("cosas", 0.2)],
    [("Un sustantivo es una palabra que nombra personas, animales o cosas, como perro o mesa.", 10.0),
     ("Es una palabra que sirve para nombrar cosas.", 6.0),
     ("Un sustantivo es una palabra que indica una acción, como correr.", 1.5)],
))

EXAMS.append(_q(
    "Primaria", "Matemáticas", "¿Qué es una fracción?",
    "Una fracción representa una o varias partes iguales de un todo; tiene un "
    "numerador arriba y un denominador abajo.",
    [("partes iguales", 0.4, ["parte de un todo", "parte de algo", "trozo"]),
     ("numerador", 0.3), ("denominador", 0.3)],
    [("Una fracción son partes iguales de un todo, con numerador arriba y denominador abajo.", 10.0),
     ("Una fracción es una parte de algo, como media pizza.", 5.5),
     ("Una fracción es un número muy grande para multiplicar.", 1.0)],
))

EXAMS.append(_q(
    "Primaria", "Ciencias Naturales", "¿Para qué sirven las raíces de las plantas?",
    "Las raíces fijan la planta al suelo y absorben el agua y los nutrientes "
    "(las sales minerales) que la planta necesita.",
    [("fijan", 0.3, ["sujetar", "sujeta", "sostener", "agarrar"]),
     ("suelo", 0.2, ["tierra"]),
     ("absorben", 0.3, ["cogen", "toman", "chupan"]),
     ("agua", 0.2)],
    [("Las raíces fijan la planta al suelo y absorben el agua y los nutrientes.", 10.0),
     ("Sirven para sujetar la planta en la tierra.", 5.5),
     ("Las raíces sirven para dar flores y frutos bonitos.", 1.0)],
))

EXAMS.append(_q(
    "Primaria", "Ciencias Sociales", "Explica brevemente el ciclo del agua.",
    "En el ciclo del agua, el agua se evapora por el calor del sol, se condensa "
    "formando nubes y vuelve a caer como precipitación (lluvia o nieve).",
    [("evapora", 0.35), ("condensa", 0.3), ("nubes", 0.15), ("precipitación", 0.2)],
    [("El agua se evapora con el sol, se condensa en nubes y cae como precipitación.", 10.0),
     ("El agua se evapora y luego llueve.", 5.0),
     ("El agua del mar siempre se queda quieta en el mismo sitio.", 0.5)],
))

EXAMS.append(_q(
    "Primaria", "Inglés", "Escribe qué es 'the weather' y di tres ejemplos en inglés.",
    "'The weather' es el tiempo atmosférico; ejemplos son 'sunny' (soleado), "
    "'rainy' (lluvioso) y 'cloudy' (nublado).",
    [("tiempo", 0.3), ("sunny", 0.25), ("rainy", 0.25), ("cloudy", 0.2)],
    [("The weather es el tiempo: por ejemplo sunny, rainy y cloudy.", 10.0),
     ("El tiempo en inglés, como sunny y rainy.", 7.0),
     ("The weather significa el fin de semana en inglés.", 1.0)],
))

# ════════════════════════════════════════════════════════════════════════════
#  ESO
# ════════════════════════════════════════════════════════════════════════════

EXAMS.append(_q(
    "ESO", "Lengua", "¿Qué diferencia hay entre sujeto y predicado en una oración?",
    "El sujeto es la parte de la oración que indica de quién se dice algo y "
    "concuerda con el verbo; el predicado es lo que se dice del sujeto y su "
    "núcleo es el verbo.",
    [("sujeto", 0.25), ("predicado", 0.25), ("verbo", 0.3), ("concuerda", 0.2)],
    [("El sujeto dice de quién se habla y concuerda con el verbo; el predicado es lo que se dice y su núcleo es el verbo.", 10.0),
     ("El sujeto es quien hace la acción y el predicado lo que hace.", 6.5),
     ("El sujeto y el predicado son dos signos de puntuación.", 0.5)],
))

EXAMS.append(_q(
    "ESO", "Matemáticas", "Enuncia el teorema de Pitágoras.",
    "El teorema de Pitágoras afirma que en un triángulo rectángulo el cuadrado de "
    "la hipotenusa es igual a la suma de los cuadrados de los catetos.",
    [("triángulo rectángulo", 0.3), ("hipotenusa", 0.3), ("catetos", 0.25), ("cuadrado", 0.15)],
    [("En un triángulo rectángulo, el cuadrado de la hipotenusa es la suma de los cuadrados de los catetos.", 10.0),
     ("La hipotenusa al cuadrado es igual a los catetos.", 6.0),
     ("Es la fórmula para calcular el área de un círculo.", 0.5)],
))

EXAMS.append(_q(
    "ESO", "Biología y Geología", "¿Qué es la célula y qué tipos principales hay?",
    "La célula es la unidad básica de los seres vivos. Hay dos tipos principales: "
    "procariota, sin núcleo definido, y eucariota, con núcleo y orgánulos.",
    [("unidad básica", 0.3, ["parte más pequeña", "unidad mínima", "lo más pequeño"]),
     ("seres vivos", 0.2), ("procariota", 0.25), ("eucariota", 0.25)],
    [("La célula es la unidad básica de los seres vivos; hay procariotas sin núcleo y eucariotas con núcleo.", 10.0),
     ("La célula es la parte más pequeña de los seres vivos.", 5.5),
     ("La célula es un órgano del cuerpo humano como el hígado.", 1.0)],
))

EXAMS.append(_q(
    "ESO", "Física y Química", "¿Qué es un átomo y cuáles son sus partículas?",
    "El átomo es la partícula más pequeña de un elemento que conserva sus "
    "propiedades. Está formado por protones y neutrones en el núcleo y electrones "
    "alrededor.",
    [("partícula más pequeña", 0.25), ("protones", 0.25), ("neutrones", 0.2),
     ("electrones", 0.2), ("núcleo", 0.1)],
    [("El átomo es la partícula más pequeña de un elemento, con protones y neutrones en el núcleo y electrones alrededor.", 10.0),
     ("Es lo más pequeño de la materia, con protones y electrones.", 7.0),
     ("El átomo es una célula que tiene núcleo y membrana.", 1.0)],
))

EXAMS.append(_q(
    "ESO", "Geografía e Historia", "¿Qué fue la Revolución Industrial?",
    "La Revolución Industrial fue el proceso de transformación económica y social "
    "iniciado en Inglaterra en el siglo XVIII, basado en la máquina de vapor, las "
    "fábricas y la producción en serie.",
    [("transformación económica", 0.25, ["cambio económico", "cambios en la economía"]),
     ("Inglaterra", 0.2),
     ("máquina de vapor", 0.3, ["máquinas", "máquina"]),
     ("fábricas", 0.25, ["fábrica", "industrias"])],
    [("Fue la transformación económica iniciada en Inglaterra con la máquina de vapor y las fábricas.", 10.0),
     ("Fue cuando aparecieron las fábricas y las máquinas.", 6.0),
     ("Fue una guerra entre Francia y España en la Edad Media.", 0.5)],
))

EXAMS.append(_q(
    "ESO", "Tecnología", "¿Qué es un circuito eléctrico y qué elementos lo forman?",
    "Un circuito eléctrico es un camino cerrado por el que circula la corriente. "
    "Lo forman un generador (pila), conductores (cables), un receptor (bombilla) "
    "y un elemento de control (interruptor).",
    [("camino cerrado", 0.25, ["circuito"]),
     ("corriente", 0.2),
     ("generador", 0.2, ["pila", "batería"]),
     ("receptor", 0.2, ["bombilla", "lámpara"]),
     ("interruptor", 0.15)],
    [("Es un camino cerrado por el que circula la corriente, con generador, conductores, receptor e interruptor.", 10.0),
     ("Es un circuito con una pila y una bombilla por el que pasa la corriente.", 7.0),
     ("Es un programa de ordenador para encender luces.", 1.0)],
))

EXAMS.append(_q(
    "ESO", "Inglés", "Explica cuándo se usa el 'present simple' en inglés.",
    "El present simple se usa para hablar de hábitos, rutinas y hechos generales "
    "o verdades; en tercera persona del singular el verbo añade '-s'.",
    [("hábitos", 0.3, ["rutinas", "cosas que hacemos todos los días", "costumbres"]),
     ("rutinas", 0.25, ["hábitos", "todos los días"]),
     ("hechos generales", 0.25, ["verdades", "cosas que son siempre verdad"]),
     ("tercera persona", 0.2)],
    [("Se usa para hábitos, rutinas y hechos generales; en la tercera persona se añade una -s al verbo.", 10.0),
     ("Se usa para cosas que hacemos todos los días, como rutinas.", 6.5),
     ("Se usa para hablar del futuro lejano siempre.", 1.0)],
))

# ════════════════════════════════════════════════════════════════════════════
#  BACHILLERATO
# ════════════════════════════════════════════════════════════════════════════

EXAMS.append(_q(
    "Bachillerato", "Biología", "¿Qué es la fotosíntesis y qué produce?",
    "La fotosíntesis transforma la energía luminosa en energía química, "
    "produciendo glucosa a partir de dióxido de carbono y agua y liberando oxígeno.",
    [("energía luminosa", 0.2, ["luz", "luz del sol", "energía solar"]),
     ("glucosa", 0.25), ("dióxido de carbono", 0.2),
     ("oxígeno", 0.2), ("agua", 0.15)],
    [("Convierte la energía luminosa en química y produce glucosa a partir de dióxido de carbono y agua, liberando oxígeno.", 10.0),
     ("Las plantas usan la luz para producir glucosa y oxígeno.", 6.5),
     ("La fotosíntesis consume oxígeno y glucosa para dar energía.", 1.5)],
))

EXAMS.append(_q(
    "Bachillerato", "Física", "Enuncia la segunda ley de Newton.",
    "La segunda ley de Newton establece que la fuerza neta sobre un cuerpo es "
    "igual al producto de su masa por su aceleración (F = m·a), y la aceleración "
    "tiene la dirección de la fuerza.",
    [("fuerza", 0.3), ("masa", 0.25), ("aceleración", 0.25), ("proporcional", 0.2)],
    [("La fuerza neta sobre un cuerpo es igual a su masa por la aceleración, que es proporcional a la fuerza.", 10.0),
     ("La fuerza es la masa por la aceleración.", 6.5),
     ("Todo cuerpo sigue en reposo si no actúa ninguna temperatura.", 0.5)],
))

EXAMS.append(_q(
    "Bachillerato", "Química", "Define el enlace covalente y pon un ejemplo.",
    "El enlace covalente se forma cuando dos átomos, normalmente no metales, "
    "comparten uno o más pares de electrones; un ejemplo es la molécula de agua.",
    [("comparten electrones", 0.35), ("no metales", 0.2), ("pares de electrones", 0.2),
     ("molécula", 0.15), ("agua", 0.1)],
    [("Dos no metales comparten pares de electrones para formar una molécula, como el agua.", 10.0),
     ("Es cuando los átomos comparten electrones.", 6.0),
     ("Es la atracción entre iones de carga opuesta que se transfieren electrones.", 1.5)],
))

EXAMS.append(_q(
    "Bachillerato", "Matemáticas", "¿Qué representa la derivada de una función en un punto?",
    "La derivada de una función en un punto representa la tasa de variación "
    "instantánea, es decir, la pendiente de la recta tangente a la gráfica en ese punto.",
    [("tasa de variación", 0.35), ("pendiente", 0.3), ("recta tangente", 0.35)],
    [("Es la tasa de variación instantánea, o sea la pendiente de la recta tangente en ese punto.", 10.0),
     ("Es la pendiente de la función en un punto.", 6.5),
     ("Es el área que hay debajo de la gráfica de la función.", 1.0)],
))

EXAMS.append(_q(
    "Bachillerato", "Historia de España", "Explica las características del reinado de los Reyes Católicos.",
    "Isabel de Castilla y Fernando de Aragón unieron dinásticamente Castilla y "
    "Aragón, implantaron una monarquía autoritaria, conquistaron Granada en 1492 y "
    "crearon la Inquisición.",
    [("monarquía autoritaria", 0.25), ("Castilla", 0.15), ("Aragón", 0.15),
     ("Granada", 0.15), ("1492", 0.1), ("Inquisición", 0.2)],
    [("Unieron Castilla y Aragón en una monarquía autoritaria, conquistaron Granada en 1492 e instauraron la Inquisición.", 10.0),
     ("Los Reyes Católicos unieron Castilla y Aragón y conquistaron Granada.", 6.0),
     ("Los Reyes Católicos perdieron la guerra y abolieron la Inquisición.", 1.0)],
))

EXAMS.append(_q(
    "Bachillerato", "Filosofía", "Explica el imperativo categórico de Kant.",
    "El imperativo categórico es el principio moral kantiano que ordena actuar por "
    "deber de forma universal: obra según una máxima que pueda convertirse en ley "
    "universal y trata a la humanidad como fin y nunca solo como medio.",
    [("imperativo categórico", 0.2), ("universal", 0.2), ("deber", 0.15),
     ("máxima", 0.15), ("ley universal", 0.15), ("fin", 0.15)],
    [("Manda obrar por deber de forma universal, con una máxima que sea ley universal, tratando a la humanidad como fin.", 10.0),
     ("Dice que hay que actuar por deber siguiendo normas universales.", 6.0),
     ("Kant decía que hay que buscar el placer personal por encima de todo.", 0.5)],
))

EXAMS.append(_q(
    "Bachillerato", "Economía", "Define la inflación y explica una causa.",
    "La inflación es el aumento generalizado y sostenido de los precios, que reduce "
    "el poder adquisitivo del dinero; una causa es el exceso de demanda agregada "
    "respecto a la oferta.",
    [("aumento de los precios", 0.3, ["suben los precios", "subida de precios", "precios suben"]),
     ("generalizado", 0.15), ("sostenido", 0.15),
     ("poder adquisitivo", 0.2, ["el dinero vale menos", "valor del dinero", "dinero vale menos"]),
     ("demanda", 0.2)],
    [("Es el aumento generalizado y sostenido de los precios que reduce el poder adquisitivo; una causa es el exceso de demanda.", 10.0),
     ("Es cuando suben los precios y el dinero vale menos.", 6.0),
     ("Es cuando bajan los precios y aumenta el paro.", 1.0)],
))

# ════════════════════════════════════════════════════════════════════════════
#  UNIVERSIDAD — Ingeniería Informática
# ════════════════════════════════════════════════════════════════════════════

EXAMS.append(_q(
    "Universidad", "Programación", "¿Qué es la recursividad en programación?",
    "La recursividad es una técnica en la que una función se llama a sí misma para "
    "resolver un problema dividiéndolo en subproblemas más pequeños, y necesita un "
    "caso base que detenga las llamadas.",
    [("se llama a sí misma", 0.4), ("caso base", 0.3), ("subproblemas", 0.3)],
    [("Es cuando una función se llama a sí misma dividiendo el problema en subproblemas, con un caso base que para la recursión.", 10.0),
     ("Es una función que se llama a sí misma.", 6.0),
     ("Es un bucle for que repite instrucciones un número fijo de veces.", 1.5)],
))

EXAMS.append(_q(
    "Universidad", "Estructuras de Datos", "¿Qué es una pila (stack) y qué política sigue?",
    "Una pila es una estructura de datos lineal que sigue la política LIFO (último "
    "en entrar, primero en salir); sus operaciones básicas son push (apilar) y pop "
    "(desapilar).",
    [("LIFO", 0.4, ["último en entrar primero en salir", "ultimo en entrar y primero en salir",
                    "el ultimo que entra es el primero en salir", "ultimo en meter primero en sacar",
                    "ultimo elemento que metes primero que sacas", "ultimo en llegar primero en salir"]),
     ("push", 0.2, ["apilar"]), ("pop", 0.2, ["desapilar"]), ("lineal", 0.2)],
    [("Es una estructura lineal LIFO, el último en entrar es el primero en salir, con operaciones push y pop.", 10.0),
     ("Es una estructura donde el último elemento que metes es el primero que sacas.", 7.0),
     ("Es una estructura FIFO como una cola del supermercado.", 1.5)],
))

EXAMS.append(_q(
    "Universidad", "Algoritmia", "¿Qué mide la complejidad temporal de un algoritmo?",
    "La complejidad temporal mide cómo crece el número de operaciones de un "
    "algoritmo en función del tamaño de la entrada, normalmente con notación "
    "asintótica O grande para el peor caso.",
    [("operaciones", 0.3), ("tamaño de la entrada", 0.3), ("notación asintótica", 0.2),
     ("peor caso", 0.2)],
    [("Mide cómo crece el número de operaciones según el tamaño de la entrada, con notación asintótica O grande para el peor caso.", 10.0),
     ("Mide cuántas operaciones hace un algoritmo según la entrada.", 6.0),
     ("Mide la cantidad de memoria que ocupa un algoritmo.", 1.5)],
))

EXAMS.append(_q(
    "Universidad", "Bases de Datos", "¿Qué es una clave primaria en una base de datos relacional?",
    "Una clave primaria es un campo o conjunto de campos que identifica de forma "
    "única cada fila de una tabla y cuyo valor no puede ser nulo.",
    [("única", 0.3), ("tabla", 0.2), ("fila", 0.25), ("no nulo", 0.25)],
    [("Identifica de forma única cada fila de una tabla y su valor no puede ser nulo.", 10.0),
     ("Es un campo que identifica de forma única cada fila de la tabla.", 7.0),
     ("Es un campo que puede repetirse y tener valor nulo en la tabla.", 2.0)],
))

EXAMS.append(_q(
    "Universidad", "Redes", "¿Qué caracteriza al protocolo TCP?",
    "TCP es un protocolo de transporte orientado a conexión y fiable: garantiza la "
    "entrega ordenada de los segmentos, controla el flujo y retransmite los "
    "paquetes perdidos.",
    [("orientado a conexión", 0.3, ["con conexión", "establece conexión"]),
     ("fiable", 0.25, ["seguro", "sin pérdidas"]),
     ("entrega ordenada", 0.25, ["llegan bien", "llegan en orden", "datos llegan bien", "llegan correctamente"]),
     ("retransmite", 0.2, ["reenvía", "vuelve a enviar"])],
    [("Es un protocolo orientado a conexión y fiable que garantiza la entrega ordenada y retransmite los paquetes perdidos.", 10.0),
     ("Es un protocolo fiable que asegura que los datos llegan bien.", 6.5),
     ("Es un protocolo sin conexión y no fiable como UDP.", 1.0)],
))

EXAMS.append(_q(
    "Universidad", "Sistemas Operativos", "¿Qué es un proceso en un sistema operativo?",
    "Un proceso es un programa en ejecución, con su propio espacio de memoria, "
    "estado y recursos; el sistema operativo lo planifica para repartir la CPU "
    "entre varios procesos.",
    [("programa en ejecución", 0.4, ["programa que se está ejecutando", "programa ejecutándose",
                                     "programa corriendo", "programa que se ejecuta"]),
     ("espacio de memoria", 0.25, ["su propia memoria"]),
     ("planifica", 0.2, ["reparte la cpu", "asigna la cpu"]),
     ("CPU", 0.15, ["procesador"])],
    [("Es un programa en ejecución con su propio espacio de memoria y estado, que el sistema operativo planifica para repartir la CPU.", 10.0),
     ("Es un programa que se está ejecutando en el ordenador.", 6.5),
     ("Es un archivo guardado en el disco duro que no se ejecuta.", 1.0)],
))

EXAMS.append(_q(
    "Universidad", "Arquitectura de Computadores", "¿Qué es la memoria caché y para qué sirve?",
    "La memoria caché es una memoria pequeña y muy rápida situada entre la CPU y la "
    "memoria principal que guarda los datos e instrucciones más usados para "
    "aprovechar la localidad y reducir el tiempo de acceso.",
    [("rápida", 0.25, ["veloz", "más deprisa", "más rápido"]),
     ("CPU", 0.2, ["procesador"]),
     ("memoria principal", 0.2, ["ram"]),
     ("localidad", 0.2),
     ("tiempo de acceso", 0.15, ["más deprisa", "acceso rápido", "vaya más rápido"])],
    [("Es una memoria pequeña y muy rápida entre la CPU y la memoria principal que guarda lo más usado por localidad y reduce el tiempo de acceso.", 10.0),
     ("Es una memoria rápida que guarda datos para que la CPU vaya más deprisa.", 7.0),
     ("Es el disco duro donde se guardan los archivos del usuario.", 1.0)],
))

EXAMS.append(_q(
    "Universidad", "Inteligencia Artificial", "¿Qué es el aprendizaje supervisado?",
    "El aprendizaje supervisado es un tipo de aprendizaje automático en el que el "
    "modelo aprende a partir de datos etiquetados (entrada y salida conocidas) para "
    "predecir la salida de nuevos ejemplos.",
    [("datos etiquetados", 0.4, ["datos con etiquetas", "etiquetas", "ejemplos etiquetados"]),
     ("modelo", 0.2, ["algoritmo"]),
     ("predecir", 0.2, ["predice", "predicción"]),
     ("entrada", 0.2, ["salida conocida", "entrada y salida"])],
    [("El modelo aprende de datos etiquetados, con entrada y salida conocidas, para predecir la salida de nuevos ejemplos.", 10.0),
     ("Es cuando el modelo aprende con datos que tienen etiquetas.", 7.0),
     ("Es cuando el modelo aprende sin ningún dato ni etiqueta.", 1.5)],
))

# ════════════════════════════════════════════════════════════════════════════
#  MÁSTER — Ingeniería Informática / IA
# ════════════════════════════════════════════════════════════════════════════

EXAMS.append(_q(
    "Máster", "Machine Learning", "¿Qué es el sobreajuste (overfitting) y cómo se mitiga?",
    "El sobreajuste ocurre cuando un modelo aprende el ruido y los detalles de los "
    "datos de entrenamiento y generaliza mal con datos nuevos; se mitiga con "
    "regularización, más datos o validación cruzada.",
    [("ruido", 0.2), ("entrenamiento", 0.2),
     ("generaliza mal", 0.3, ["mal en test", "mal con datos nuevos", "mal en validación",
                              "no generaliza", "mal en datos nuevos"]),
     ("regularización", 0.3, ["validación cruzada", "más datos", "dropout"])],
    [("El modelo memoriza el ruido del entrenamiento y generaliza mal con datos nuevos; se mitiga con regularización, más datos o validación cruzada.", 10.0),
     ("Es cuando el modelo va muy bien en entrenamiento pero mal en test.", 7.0),
     ("Es cuando el modelo es demasiado simple y no aprende nada.", 1.5)],
))

EXAMS.append(_q(
    "Máster", "Sistemas Distribuidos", "Explica el teorema CAP.",
    "El teorema CAP afirma que un sistema distribuido no puede garantizar a la vez "
    "consistencia, disponibilidad y tolerancia a particiones; ante una partición "
    "hay que elegir entre consistencia y disponibilidad.",
    [("consistencia", 0.3), ("disponibilidad", 0.3),
     ("tolerancia a particiones", 0.3, ["particiones", "partición de red", "particiones de red"]),
     ("distribuido", 0.1)],
    [("Un sistema distribuido no puede dar a la vez consistencia, disponibilidad y tolerancia a particiones; ante una partición se elige entre consistencia y disponibilidad.", 10.0),
     ("Dice que no puedes tener consistencia, disponibilidad y particiones a la vez.", 7.5),
     ("Dice que todo sistema distribuido es siempre rápido y seguro.", 1.0)],
))

EXAMS.append(_q(
    "Máster", "Ciberseguridad", "¿Qué es el cifrado asimétrico?",
    "El cifrado asimétrico usa un par de claves, una pública y una privada: lo que "
    "se cifra con una se descifra con la otra, lo que permite confidencialidad y "
    "firma digital sin compartir una clave secreta.",
    [("clave pública", 0.3, ["claves pública", "clave publica", "una pública"]),
     ("clave privada", 0.3, ["claves privada", "clave privada", "una privada"]),
     ("par de claves", 0.2, ["dos claves", "pareja de claves"]),
     ("firma digital", 0.2, ["firmar", "autenticación"])],
    [("Usa un par de claves pública y privada: lo cifrado con una se descifra con la otra, permitiendo confidencialidad y firma digital.", 10.0),
     ("Usa una clave pública y una privada para cifrar y descifrar.", 7.0),
     ("Usa la misma clave secreta para cifrar y descifrar.", 1.5)],
))

EXAMS.append(_q(
    "Máster", "Big Data", "¿Qué es el paradigma MapReduce?",
    "MapReduce es un modelo de programación para procesar grandes volúmenes de "
    "datos en paralelo en un clúster: una fase map transforma los datos en pares "
    "clave-valor y una fase reduce los agrega.",
    [("map", 0.3), ("reduce", 0.3), ("paralelo", 0.2), ("clave-valor", 0.2)],
    [("Es un modelo para procesar grandes datos en paralelo: la fase map genera pares clave-valor y la fase reduce los agrega.", 10.0),
     ("Tiene una fase map y una fase reduce para procesar muchos datos.", 7.0),
     ("Es una base de datos relacional con tablas y claves primarias.", 1.0)],
))

EXAMS.append(_q(
    "Máster", "Cloud Computing", "¿Qué son los contenedores y en qué se diferencian de una máquina virtual?",
    "Un contenedor empaqueta una aplicación con sus dependencias y comparte el "
    "núcleo del sistema operativo anfitrión, por lo que es más ligero y rápido que "
    "una máquina virtual, que virtualiza el hardware completo y lleva su propio "
    "sistema operativo.",
    [("dependencias", 0.25, ["librerías", "lo que necesita la aplicación"]),
     ("núcleo", 0.25, ["sistema operativo", "kernel", "so del anfitrión"]),
     ("ligero", 0.25, ["ligeros", "más ligero"]),
     ("máquina virtual", 0.25, ["máquinas virtuales", "vm"])],
    [("Un contenedor empaqueta la aplicación con sus dependencias y comparte el núcleo del anfitrión, siendo más ligero que una máquina virtual que virtualiza el hardware completo.", 10.0),
     ("Los contenedores son más ligeros que las máquinas virtuales porque comparten el sistema operativo.", 7.5),
     ("Un contenedor y una máquina virtual son exactamente lo mismo.", 1.5)],
))

EXAMS.append(_q(
    "Máster", "Procesamiento del Lenguaje Natural", "¿Qué es un word embedding?",
    "Un word embedding es una representación vectorial densa de las palabras en la "
    "que las palabras con significados similares quedan cerca en el espacio "
    "vectorial, capturando relaciones semánticas.",
    [("representación vectorial", 0.35, ["vectores", "vector", "convertir palabras en vectores"]),
     ("similares", 0.25, ["parecidas", "parecidos", "parecido"]),
     ("espacio vectorial", 0.2, ["cerca en el espacio", "vectores cerca"]),
     ("semánticas", 0.2, ["significado", "significados parecidos"])],
    [("Es una representación vectorial densa de las palabras donde las palabras similares quedan cerca en el espacio vectorial, capturando relaciones semánticas.", 10.0),
     ("Es convertir palabras en vectores donde las parecidas están cerca.", 7.0),
     ("Es una lista alfabética de palabras guardada en un diccionario.", 1.5)],
))
