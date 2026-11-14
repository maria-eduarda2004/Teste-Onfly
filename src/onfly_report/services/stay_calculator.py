"""Cálculo de noites ocupadas."""

from __future__ import annotations

from datetime import date

"""Calcula as noites de quarto, da seguinte forma: diferença de dias x quartos"""
def calculate_room_nights(checkin: date, checkout: date, rooms: int) -> int:
    return (checkout - checkin).days * rooms
