"""Línea base: frases de mantenimiento con un equipo y un estado explícito."""
import re

EQUIPO = re.compile(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+-\d+)\b")
PLAZO = re.compile(r"\b(?:antes de las \d{2}:\d{2}|antes del \w+|el (?:lunes|martes|miércoles|jueves|viernes|sábado|domingo|próximo turno|próximo relevo|turno de tarde)|mañana)\b", re.I)
PATRONES = (
    ("abierto", r"(?:no se (?:cerró|completó)|queda pendiente|quedó pendiente|figura pendiente|falta|hay que)\s+(?P<tarea>.+?)\s+(?:de|en)\s+{equipo}"),
    ("cerrado", r"(?:se cerró|se completó|terminó)\s+(?P<tarea>.+?)\s+de\s+{equipo}"),
    ("cerrado", r"(?P<tarea>.+?)\s+de\s+{equipo}\s+(?:quedó cerrad[ao]|se dio por concluid[ao]|se completó|ya está list[ao])"),
    ("abierto", r"(?P<tarea>.+?)\s+de\s+{equipo}\s+(?:quedó para|sigue pendiente)"),
)
CONFLICTO = re.compile(r"contradic|discrep|rectific|correcci|inicialmente|una nota y|otro lo|otra, ambas|mismo renglón", re.I)
ARTICULO = re.compile(r"^(?:el|la|los|las)\s+", re.I)


def extraer(nota):
    """Devuelve un JSON compatible con el contrato. Se abstiene en frases complejas."""
    registros = []
    if CONFLICTO.search(nota):
        return {"registros": registros}
    for parte in re.split(r"(?<=[.!?])\s+|;", nota):
        cita = parte.strip()
        equipos = list(EQUIPO.finditer(cita))
        if len(equipos) != 1:
            continue
        equipo = equipos[0].group()
        for estado, patron in PATRONES:
            ajuste = re.search(patron.format(equipo=re.escape(equipo)), cita, re.I)
            if not ajuste:
                continue
            tarea = ARTICULO.sub("", ajuste["tarea"].split(":")[-1].strip())
            plazo = PLAZO.search(cita)
            registros.append(dict(equipo=equipo, pendiente=tarea, estado=estado,
                                  cita=cita, plazo=plazo.group() if plazo else None))
            break
    return {"registros": registros}
