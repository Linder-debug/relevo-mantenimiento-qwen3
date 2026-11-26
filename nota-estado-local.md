# Nota técnica: brecha entre evaluación HF y ejecución local GGUF (en diagnóstico)

Medido el 26-nov-2026 con el mismo evaluador y las mismas 36 notas held-out.

## Hechos medidos

- Evaluación HF (transformers, Colab, adapter recién entrenado): F1 0.8372, 36/41 trabajos,
  1 cierre falso, 0 salidas ilegibles.
- Ejecución local (GGUF Q4_K_M, llama.cpp b12728, laptop CPU): F1 0.6234, 24/41,
  9 cierres falsos en 8 notas, 2 salidas con JSON inválido (lista vacía + comilla sobrante).
- El GGUF local es bit a bit el mismo archivo que se evaluó en Colab (SHA-256
  90c7be886cdf270989b6dab9af559ef17e4ece3eceb533f73e48aa00745a13e0 verificado en ambos).
- Procedencia: el GGUF se generó por conversión CPU (convert_hf_to_gguf.py F16 +
  llama-quantize Q4_K_M) desde la carpeta fusionada guardada por la misma corrida de
  entrenamiento. La carpeta fusionada no tiene hash propio registrado; la conversión usó
  llama.cpp sin commit fijado.
- Patrón del fallo local: 14 notas devuelven contenido vacío; 11 son fallos reales
  (la evaluación HF extrajo el registro correcto). Esas 11 tienen notas más cortas
  (mediana 75 vs 103 caracteres) y latencia mediana 0,51 s vs 5,29 s: abstención inmediata,
  no truncamiento (36/36 fin=stop). El prompt de sistema es idéntico al de la evaluación HF.

## Causa: no aislada

Candidatas: (a) runtime de la laptop (llama.cpp b12728), (b) tubería de conversión a GGUF,
(c) la cuantización Q4_K_M en sí. La discriminación requiere una nueva inferencia controlada
(mismo GGUF en otro runtime, o F16/Q4_K_M regenerados con commit fijado), pendiente al
momento de este borrador.

## Reproducción 26-nov-2026 14:55 (prueba dirigida de 4 notas)

Mismo GGUF (hash verificado en la corrida) y mismo motor (b12728, commit ea7229481,
Clang 22.1.8, Windows x86_64), en la misma laptop. Filas 1, 5, 9 y 35 del mismo eval:

- Fila 1 (omisión conocida): {"registros": []} en 7 tokens, 2,33 s. Omisión reproducida.
- Fila 5 (control): extracción correcta, idéntica al esperado campo por campo (76 tokens).
- Fila 9 (omisión conocida): {"registros": []} en 7 tokens, 0,58 s. Omisión reproducida.
- Fila 35 (control vacío): contenido correcto pero comilla sobrante al final
  ({"registros":[]}") → JSON inválido, mismo tipo de defecto que las 2 salidas ilegibles
  de la evaluación de 36.
- 4/4 fin=stop; prompt ~289-303 tokens. Sin --verbose-prompt en esta build: no se pudo
  capturar el prompt renderizado.

Interpretación: el patrón de la evaluación de 36 se reproduce en estas 4 filas (mismas
omisiones en las mismas filas; control correcto). Esto respalda reproducibilidad del patrón
en estas pruebas; no prueba determinismo general ni aísla la causa, que sigue abierta.
Registro: salidas-4notas-20261126-145503.jsonl y llama-server-20261126-145503.log en la
laptop; captura de video de la ejecución completa usada en el video demo.
