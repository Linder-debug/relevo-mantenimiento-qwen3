"""Evalúa las reglas o las salidas comparison.json del starter."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import unicodedata

from reglas import extraer

ROOT = Path(__file__).resolve().parent
CAMPOS = {"equipo", "pendiente", "estado", "cita", "plazo"}
ESTADOS = {"abierto", "cerrado", "por confirmar"}
VARIANTES = ("base_output", "finetuned_output")


def normalizar(texto):
    return " ".join(unicodedata.normalize("NFC", texto).casefold().split())


def identidad(registro):
    return normalizar(registro["equipo"]), normalizar(registro["pendiente"])


def interpretar(salida):
    valor = json.loads(salida)
    if not isinstance(valor, dict) or set(valor) != {"registros"}:
        raise ValueError("Se esperaba un objeto con la clave registros")
    registros = valor["registros"]
    if not isinstance(registros, list):
        raise ValueError("registros debe ser una lista")
    return registros


def registro_valido(registro):
    return (
        isinstance(registro, dict)
        and set(registro) == CAMPOS
        and all(isinstance(registro[campo], str) and registro[campo].strip()
                for campo in CAMPOS - {"plazo"})
        and registro["estado"] in ESTADOS
        and (registro["plazo"] is None or
             isinstance(registro["plazo"], str) and bool(registro["plazo"].strip()))
    )


def cociente(numerador, denominador):
    return round(numerador / denominador, 4) if denominador else None


def evaluar(referencias, salidas):
    totales = Counter()
    detalles = []
    for indice, (fila, salida) in enumerate(zip(referencias, salidas, strict=True), 1):
        mensajes = fila["messages"]
        nota = mensajes[-2]["content"]
        esperados = interpretar(mensajes[-1]["content"])
        conteo = Counter(notas=1, esperados=len(esperados))
        cierres_falsos = []
        error = None
        try:
            registros = interpretar(salida)
        except (TypeError, ValueError) as exc:
            registros = []
            error = str(exc)
            conteo["salidas_ilegibles"] = 1
        conteo["predichos"] = len(registros)
        validos = [r for r in registros if registro_valido(r)]
        conteo["registros_invalidos"] = len(registros) - len(validos)

        esperados_por_id = {identidad(r): r for r in esperados}
        predichos_por_id = Counter(identidad(r) for r in validos)
        conteo["coincidencias"] = len(predichos_por_id.keys() & esperados_por_id.keys())
        cotejados = set()
        cierres_validos = set()
        for registro in registros:
            if not registro_valido(registro):
                if isinstance(registro, dict) and registro.get("estado") == "cerrado":
                    cierres_falsos.append({"motivo": "registro de cierre inválido", "registro": registro})
                continue
            clave = identidad(registro)
            referencia = esperados_por_id.get(clave)
            cita_literal = registro["cita"] in nota
            conteo["citas_literales"] += int(cita_literal)
            if registro["estado"] == "cerrado":
                if not cita_literal or referencia is None or referencia["estado"] != "cerrado":
                    cierres_falsos.append({"motivo": "cierre sin respaldo según la rúbrica automática",
                                          "registro": registro})
                elif clave in cierres_validos:
                    conteo["cierres_duplicados"] += 1
                else:
                    cierres_validos.add(clave)
            if referencia is None or clave in cotejados:
                continue
            cotejados.add(clave)
            for campo in ("estado", "cita", "plazo"):
                conteo[f"{campo}_exacto"] += int(registro[campo] == referencia[campo])
        conteo["cierres_falsos"] = len(cierres_falsos)
        conteo["notas_con_cierre_falso"] = int(bool(cierres_falsos))
        conteo["notas_sin_registros_correctas"] = int(
            not esperados and not registros and error is None
        )
        totales.update(conteo)
        detalles.append({"fila": indice, **conteo, "error": error,
                         "cierres_falsos_detalle": cierres_falsos, "salida": salida})

    tp, pred, ref = (totales[k] for k in ("coincidencias", "predichos", "esperados"))
    return {
        "conteos": dict(totales),
        "metricas": {
            "precision_micro": cociente(tp, pred),
            "exhaustividad_micro": cociente(tp, ref),
            "f1_micro": cociente(2 * tp, pred + ref),
            "estado_exacto_sobre_coincidentes": cociente(totales["estado_exacto"], tp),
            "cita_exacta_sobre_coincidentes": cociente(totales["cita_exacto"], tp),
            "plazo_exacto_sobre_coincidentes": cociente(totales["plazo_exacto"], tp),
            "cita_literal_sobre_predichos": cociente(totales["citas_literales"], pred),
        },
        "por_nota": detalles,
    }


def cargar_particion(nombre):
    ruta = ROOT / "data" / f"{nombre}.jsonl"
    datos = ruta.read_bytes()
    manifiesto = dict(
        (archivo, huella) for huella, archivo in
        (linea.split(maxsplit=1) for linea in (ROOT / "SHA256SUMS").read_text().splitlines())
    )
    huella = hashlib.sha256(datos).hexdigest()
    if huella != manifiesto[f"data/{ruta.name}"]:
        raise ValueError(f"SHA-256 distinto del manifiesto: {ruta.name}")
    return [json.loads(linea) for linea in datos.decode("utf-8").splitlines()], huella


def cotejar_starter(referencias, comparacion):
    if not isinstance(comparacion, list) or len(referencias) != len(comparacion):
        raise ValueError("La comparación no contiene la totalidad de la partición solicitada")
    for indice, (fila, registro) in enumerate(zip(referencias, comparacion), 1):
        if (registro.get("messages") != fila["messages"][:-1]
                or json.loads(registro["reference"]) != json.loads(fila["messages"][-1]["content"])):
            raise ValueError(f"Entrada o referencia distinta en la fila {indice}")
        if any(not isinstance(registro.get(variante), str) for variante in VARIANTES):
            raise ValueError(f"Faltan salidas del starter en la fila {indice}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("valid", "eval"), required=True)
    fuente = parser.add_mutually_exclusive_group(required=True)
    fuente.add_argument("--reglas", action="store_true")
    fuente.add_argument("--comparison", type=Path)
    args = parser.parse_args()
    try:
        referencias, huella = cargar_particion(args.split)
        if args.reglas:
            salidas = [json.dumps(extraer(fila["messages"][-2]["content"]), ensure_ascii=False)
                       for fila in referencias]
            resultados = {"reglas": evaluar(referencias, salidas)}
        else:
            comparacion = json.loads(args.comparison.read_text(encoding="utf-8"))
            cotejar_starter(referencias, comparacion)
            resultados = {variante: evaluar(referencias, [fila[variante] for fila in comparacion])
                          for variante in VARIANTES}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"split": args.split, "sha256": huella, "resultados": resultados},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
