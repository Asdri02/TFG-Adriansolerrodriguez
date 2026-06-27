# Memoria del TFG

Fuente LaTeX de la memoria del Trabajo de Fin de Grado y el PDF compilado
(`main.pdf`, ~63 páginas).

## Estructura

- `main.tex` — documento principal (formato UNIE: Times 12, interlineado 1,5).
- `chapters/` — capítulos (`00_resumen` … `07_referencias`, más
  `045_consideraciones`).
- `referencias.bib` — bibliografía en BibTeX (8 referencias).
- `figures/` — capturas reales de la aplicación web.
- `main.pdf` — versión compilada.

## Compilación

Con [Tectonic](https://tectonic-typesetting.github.io/):

```
tectonic main.tex
```

La bibliografía usa **APA autor-año en español** mediante `apacite` + `bibtex`
(elegido como alternativa a `biblatex`/`biber` por incompatibilidad de versiones
de biber con la biblatex incluida en el compilador). Las citas se escriben con
`\textcite{}` / `\parencite{}`, aliasadas a `\citet` / `\citep`.

> Pendiente del autor: rellenar el nombre del tutor en la portada (`main.tex`).
