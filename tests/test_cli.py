import runpy
import sys

import pytest

import logger_config
import main_cli
from database import Database
from models import Customer, Order, OrderItem


def fill_database(path):
    database = Database(path)
    customer = database.create_customer(Customer("Иван", "+7", "Москва"))
    assert customer.id is not None
    database.create_order(
        Order(
            customer_id=customer.id,
            order_date="2025-04-20",
            status="выполнен",
            items=[OrderItem("Пицца", 2, 750)],
        )
    )
    database.close()


def test_cli_report_outputs_summary(tmp_path, capsys):
    db_path = tmp_path / "delivery.db"
    fill_database(db_path)

    code = main_cli.main(
        [
            "--db",
            str(db_path),
            "report",
            "--period",
            "month",
            "--from",
            "2025-04-01",
            "--to",
            "2025-04-30",
        ]
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "Отчет за период 2025-04-01 - 2025-04-30" in output
    assert "выполнен: 1" in output
    assert "Общая выручка: 1500.00" in output


def test_cli_export_and_import(tmp_path, capsys):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    export_file = tmp_path / "orders.json"
    fill_database(source_db)

    export_code = main_cli.main(["--db", str(source_db), "export", "--file", str(export_file)])
    import_code = main_cli.main(["--db", str(target_db), "import", "--file", str(export_file)])

    output = capsys.readouterr().out
    assert export_code == 0
    assert import_code == 0
    assert "Экспорт выполнен" in output
    assert "Импортировано: клиентов 1, заказов 1" in output

    database = Database(target_db)
    assert database.revenue() == 1500
    database.close()


def test_cli_import_error_returns_failure(tmp_path, capsys):
    code = main_cli.main(
        ["--db", str(tmp_path / "delivery.db"), "import", "--file", str(tmp_path / "missing.json")]
    )

    output = capsys.readouterr()
    assert code == 1
    assert "missing.json" in output.err


def test_logger_returns_project_logger():
    logger = logger_config.configure_logging()
    assert logger.name == "delivery_system"


def test_delivery_entrypoint_runs_report(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "delivery.db"
    fill_database(db_path)
    monkeypatch.setattr(sys, "argv", ["delivery.py", "--db", str(db_path), "report"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("delivery", run_name="__main__")

    output = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "Количество заказов по статусам" in output
