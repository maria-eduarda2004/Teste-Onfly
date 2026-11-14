"""Testes adicionais para casos de borda, limites de leitura e contrato do CLI"""

from __future__ import annotations

from pathlib import Path

import pytest
from helpers import run_cli

from onfly_report.cli import main


def test_reads_more_than_200_reservations(tmp_path: Path) -> None:
    """Garante que o repositório lê todas as linhas"""
    rows = [
        {
            "reservation_id": f"R-{i}",
            "amount": "10.00",
            "checkin_date": "2025-01-10",
            "checkout_date": "2025-01-11",
        }
        for i in range(1, 251)
    ]
    report = run_cli(tmp_path, rows)
    assert report["summary"]["total_reservations"] == 250
    assert report["summary"]["confirmed_reservations"] == 250
    assert report["summary"]["total_room_nights"] == 250
    assert report["summary"]["total_amount_brl"] == "2500.00"


def test_top_hotels_tie_breaker_by_hotel_id_ascending(tmp_path: Path) -> None:
    """Em caso de empate no valor total_brl, desempata por hotel_id em ordem crescente"""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H05", "hotel_name": "Hotel E", "amount": "500.00"},
            {"reservation_id": "R-2", "hotel_id": "H02", "hotel_name": "Hotel B", "amount": "500.00"},
            {"reservation_id": "R-3", "hotel_id": "H01", "hotel_name": "Hotel A", "amount": "800.00"},
            {"reservation_id": "R-4", "hotel_id": "H03", "hotel_name": "Hotel C", "amount": "500.00"},
        ],
        top=4,
    )
    assert [hotel["hotel_id"] for hotel in report["top_hotels"]] == ["H01", "H02", "H03", "H05"]


def test_nights_across_year_boundary_and_by_month_order(tmp_path: Path) -> None:
    """Calcula as noites na virada de ano e agrupa pelo mês de check in em ordem ascendente"""
    report = run_cli(
        tmp_path,
        [
            {
                "reservation_id": "R-1",
                "checkin_date": "2025-02-10",
                "checkout_date": "2025-02-12",
                "rooms": "1",
                "amount": "300.00",
            },
            {
                "reservation_id": "R-2",
                "checkin_date": "2024-12-30",
                "checkout_date": "2025-01-02",
                "rooms": "2",
                "amount": "600.00",
            },
        ],
    )
    assert report["summary"]["total_room_nights"] == 8  # 2 noites + (3 dias * 2 quartos)
    assert report["by_month"] == [
        {"month": "2024-12", "reservations": 1, "room_nights": 6, "total_brl": "600.00"},
        {"month": "2025-02", "reservations": 1, "room_nights": 2, "total_brl": "300.00"},
    ]


def test_zero_confirmed_reservations_avoids_division_by_zero(tmp_path: Path) -> None:
    """Quando não possui reservas 'CONFIRMED', average_nightly_rate_brl deverá ser '0.00'."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "status": "CANCELLED", "amount": "400.00"},
            {"reservation_id": "R-2", "status": "NO_SHOW", "amount": "300.00"},
        ],
    )
    assert report["summary"] == {
        "total_reservations": 2,
        "confirmed_reservations": 0,
        "cancelled_reservations": 1,
        "no_show_reservations": 1,
        "total_room_nights": 0,
        "total_amount_brl": "0.00",
        "average_nightly_rate_brl": "0.00",
    }
    assert report["by_month"] == []
    assert report["top_hotels"] == []


def test_cli_exit_code_2_on_missing_input_file(tmp_path: Path) -> None:
    """Retorna código de saída 2 quando o arquivo de entrada for inexistente"""
    missing_input = tmp_path / "inexistente.csv"
    rates_path = tmp_path / "rates.csv"
    output_path = tmp_path / "out.json"
    rates_path.write_text("currency,rate_to_brl\nBRL,1.000000\n", encoding="utf-8")

    exit_code = main(
        [
            "--input",
            str(missing_input),
            "--rates",
            str(rates_path),
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 2


def test_cli_exit_code_2_on_invalid_top_argument(tmp_path: Path) -> None:
    """Retorna código de saída 2 quando --top < 1"""
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--input",
                str(tmp_path / "reservas.csv"),
                "--rates",
                str(tmp_path / "rates.csv"),
                "--top",
                "0",
            ]
        )
    assert exc_info.value.code == 2