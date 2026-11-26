# Extractor de pendientes de notas de turno (Qwen3-1.7B ajustado)

Convierte notas de turno de mantenimiento en español en registros JSON estructurados.
Ajuste fino (LoRA) de Qwen3-1.7B, ejecutable de forma local en una laptop sin GPU dedicada.
Entrada al Qwen Local Hackathon 2026.

## What it does

Para un encargado de mantenimiento que releva turnos: convierte una nota de turno en espanol
en un JSON con los trabajos detectados. Un registro por par equipo-trabajo, con `equipo`,
`pendiente`, `estado` (abierto / cerrado / por confirmar), `cita` literal de la nota y `plazo`.
Las notas sin trabajos devuelven `{"registros": []}`. El punto dificil: negaciones
("no se cerro..."), correcciones sobre la marcha y notas que solo informan.

## Why we built it

En pases de turno reales los pendientes se pierden entre texto libre. Una extraccion
estructurada permite tableros y alertas. El modelo base no sigue el contrato JSON ni respeta
negaciones (0/41 trabajos correctos), asi que el ajuste fino era necesario.

## Dataset

88 notas de turno de mantenimiento en espanol, ficticias y originales de este proyecto
(paquete "Bloque 2": referencias redactadas antes de generar salidas, manifiesto SHA-256
fijado antes de la linea base): 40 entrenamiento, 12 validacion, 36 evaluacion held-out,
con particiones disjuntas y categorias equilibradas (claros, negacion, varios equipos,
contradictorios, sin pendientes). NO provienen del starter: la receta `json-extractor` de
finetune-anywhere es una tarea distinta (60 casos de peticiones de compra). Del starter
(MIT, (c) 2026 M Junaid) se reutilizan el formato de receta, la configuracion de
entrenamiento y el script de validacion.

Los datos estan en `data/` (train / valid / eval) con su manifiesto en `SHA256SUMS`,
bajo licencia CC-BY-4.0 (ver `LICENSE-DATOS.txt`).

## Training

unsloth 2026.11.12 sobre Qwen/Qwen3-1.7B (revision a972f43), LoRA rango 16 alfa 32,
lr 2e-4, 3 epocas, semilla 42, max_seq_length 1024, batch 1 con acumulacion 4.
Plataforma: Google Colab gratuito, Tesla T4. Entrenamiento medido: 86,5 segundos.
torch 2.14.1+cu130, transformers 4.57.6, trl 0.22.2, peft 0.21.2.

## Run it locally

- Descarga del modelo (GGUF Q4_K_M, 1,1 GB): en la seccion Releases de este repositorio,
  tag `v1.0`, asset `qwen3-1.7b-pendientes.gguf`. SHA-256 del archivo evaluado:
  90c7be886cdf270989b6dab9af559ef17e4ece3eceb533f73e48aa00745a13e0.
- Runtime: llama.cpp `llama-server -m qwen3-1.7b-pendientes.gguf -c 2048`, cliente
  `/v1/chat/completions` con `temperature 0`, `max_tokens 256` y el prompt de sistema
  incluido en `prompt-sistema.txt`. Probado en laptop Windows i9-13900H, 16 GB RAM, solo CPU.

## Before and after

Evaluacion con `evaluar.py` (en este repositorio) sobre 36 notas held-out (41 trabajos esperados):

| Metrica | Base | Ajustado |
| --- | ---: | ---: |
| Trabajos identificados | 0 / 41 | 36 / 41 |
| F1 micro | 0.0000 | 0.8372 |
| Precision / exhaustividad | 0 / 0 | 0.80 / 0.878 |
| Cierres falsos | 7 | 1 |
| Salidas ilegibles | 7 | 0 |

Ejemplo real (nota held-out fila 1, salidas verbatim en `model.yaml`): el base devuelve JSON
con tipos incorrectos (pendiente=true, plazo="null"); el ajustado devuelve el registro correcto.

Limitacion conocida, declarada abiertamente: la ejecucion local con el GGUF Q4_K_M en
llama.cpp b12728 rinde por debajo de la evaluacion HF (F1 0,6234 vs 0,8372; 11 notas con
trabajo esperado devuelven lista vacia de inmediato). Al momento de esta publicacion la causa
no esta aislada (cuantizacion, conversion o runtime). Detalles medidos en
`nota-estado-local.md`.

## What we learned

El ajuste con 40 ejemplos basta para el contrato JSON y las negaciones en la evaluacion HF.
Pendiente: cerrar la brecha entre el modelo servido con transformers y su version cuantizada
local, y fijar commits de la tuberias de conversion para hacerla reproducible.

## Estructura del repositorio y licencias

- `LICENSE-MODELO.txt` — Apache-2.0 para el modelo ajustado (obra derivada del base
  Qwen3-1.7B, Apache-2.0; avisos en `NOTICE`).
- `LICENSE-DATOS.txt` — CC-BY-4.0 para `data/` y `SHA256SUMS` (las 88 notas, obra original).
- `LICENSE-CODIGO.txt` — MIT para `evaluar.py`, `reglas.py`, `prompt-sistema.txt` y demas
  archivos de codigo y documentacion del proyecto.
- `resultados-eval-hf.json`, `resultados-eval-local.json`, `linea-base-eval.json` —
  salidas reales de evaluacion.
- `nota-estado-local.md` — estado medido del diagnostico local.
- `model.yaml` — ficha de la entrada al hackathon.

## Team

Linder Lopez (https://github.com/Linder-debug). Datos, evaluador y redaccion: obra original de
este proyecto (paquete Bloque 2). Herramientas del starter: finetune-anywhere (MIT,
(c) 2026 M Junaid). Modelo base: Qwen3-1.7B de Qwen, licencia Apache-2.0
(https://huggingface.co/Qwen/Qwen3-1.7B).
