"""Política de status das reservas."""

from __future__ import annotations

"""Indica se a reserva entra em totais financeiros e de noite"""
def is_billable(status: str) -> bool:
    return status == "CONFIRMED"
