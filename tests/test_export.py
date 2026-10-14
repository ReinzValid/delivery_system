import json

import pytest

from data_export import export_orders, import_orders, parse_payload
from database import Database
from models import Customer, Order, OrderItem


def build_database(path):
    db = Database(path)
    customer = db.create_customer(Customer("Иван", "+7", "Москва"))
    assert customer.id is not None
    db.create_order(
        Order(
            customer_id=customer.id,
            order_date="2025-04-20",
            status="выполнен",
            items=[OrderItem("Пицца", 2, 750)],
        )
    )
    return db


def test_json_export_import(tmp_path):
    source = build_database(tmp_path / "source.db")
    file_path = tmp_path / "orders.json"
    export_orders(source, file_path)

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    assert len(payload["customers"]) == 1
    assert len(payload["orders"]) == 1

    target = Database(tmp_path / "target.db")
    result = import_orders(target, file_path)
    assert result == {"customers": 1, "orders": 1}
    assert target.revenue() == 1500

    source.close()
    target.close()


def test_xml_export_import(tmp_path):
    source = build_database(tmp_path / "source.db")
    file_path = tmp_path / "orders.xml"
    export_orders(source, file_path)

    target = Database(tmp_path / "target.db")
    result = import_orders(target, file_path)
    assert result == {"customers": 1, "orders": 1}
    assert target.list_orders()[0]["status"] == "выполнен"

    source.close()
    target.close()


def test_import_rejects_bad_payload():
    with pytest.raises(ValueError):
        parse_payload(
            {
                "customers": [],
                "orders": [{"customer_id": 1, "order_date": "2025-04-20"}],
            }
        )


def test_import_allows_order_for_existing_customer(tmp_path):
    target = Database(tmp_path / "target.db")
    customer = target.create_customer(Customer("Иван"))
    assert customer.id is not None
    file_path = tmp_path / "orders.json"
    file_path.write_text(
        json.dumps(
            {
                "orders": [
                    {
                        "customer_id": customer.id,
                        "order_date": "2025-04-20",
                        "status": "новый",
                        "total": 500,
                        "items": [
                            {"product_name": "Пицца", "quantity": 1, "price": 500}
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = import_orders(target, file_path)
    assert result == {"customers": 0, "orders": 1}
    assert target.revenue() == 500
    target.close()


def test_import_rejects_order_without_customer(tmp_path):
    target = Database(tmp_path / "target.db")
    file_path = tmp_path / "orders.json"
    file_path.write_text(
        json.dumps(
            {
                "orders": [
                    {
                        "customer_id": 999,
                        "order_date": "2025-04-20",
                        "status": "новый",
                        "total": 500,
                        "items": [
                            {"product_name": "Пицца", "quantity": 1, "price": 500}
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        import_orders(target, file_path)
    target.close()
