"""Horas úteis entre dois instantes (horário de Brasília): segunda a sexta, 08:00–18:00. Feriados não tratados (ver suposicoes.md)."""
import datetime as dt

ABRE, FECHA = 8, 18

def _fmt(s):
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S") if isinstance(s, str) else s

def horas_uteis(ini, fim):
    """Horas de trabalho entre ini e fim (float). Zero se fim <= ini."""
    a, b = _fmt(ini), _fmt(fim)
    if b <= a:
        return 0.0
    total = 0.0
    dia = a.replace(hour=0, minute=0, second=0, microsecond=0)
    while dia <= b:
        if dia.weekday() < 5:
            abre = dia.replace(hour=ABRE)
            fecha = dia.replace(hour=FECHA)
            x, y = max(a, abre), min(b, fecha)
            if y > x:
                total += (y - x).total_seconds() / 3600
        dia += dt.timedelta(days=1)
    return total
