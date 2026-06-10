"""Testes do cálculo de duração de jornada que cruza meia-noite.

Regressão pro bug onde _duracao_horas retornava valor negativo em turnos
noturnos, fazendo os checks de jornada (Art. 58/71) passarem com falso "OK".
"""

from __future__ import annotations

from engine.clt_validator import _duracao_horas


def test_duracao_diurna_normal():
    assert _duracao_horas("08:00", "17:00") == 9.0
    assert _duracao_horas("10:00", "16:00") == 6.0


def test_duracao_com_minutos():
    assert _duracao_horas("08:30", "12:00") == 3.5
    assert _duracao_horas("09:15", "17:45") == 8.5


def test_duracao_overnight_cruza_meia_noite():
    # 22h → 02h = 4h (não -20h)
    assert _duracao_horas("22:00", "02:00") == 4.0
    # 23h → 07h = 8h
    assert _duracao_horas("23:00", "07:00") == 8.0


def test_duracao_fecha_meia_noite():
    # 18h → 00h = 6h (não -18h)
    assert _duracao_horas("18:00", "00:00") == 6.0


def test_duracao_overnight_detecta_jornada_excessiva():
    # Turno de 22h às 16h do dia seguinte = 18h — tem que ser positivo
    # pra que o check de jornada máxima (Art. 58) detecte a violação.
    dur = _duracao_horas("22:00", "16:00")
    assert dur == 18.0
    assert dur > 8  # excede jornada normal — check deve disparar
