import pytest

from database import Database
from models import Customer, Order, OrderItem


@pytest.fixture
def database(tmp_path):
    db = Database(tmp_path / "delivery.db")
    yield db
    db.close()


def create_order(
    database, customer_id, order_date="2025-04-20", status="новый", price=100
):
    return database.create_order(
        Order(
            customer_id=customer_id,
            order_date=order_date,
            status=status,
            items=[OrderItem("Товар", 2, price)],
        )
    )


def test_customer_crud_and_delete_restriction(database):
    customer = database.create_customer(Customer("Иван", "+7", "Москва"))
    assert customer.id is not None

    updated = database.update_customer(
        Customer("Иван Петров", "+7 999", "Казань", id=customer.id)
    )
    assert updated.name == "Иван Петров"

    order = create_order(database, customer.id)
    with pytest.raises(ValueError):
        database.delete_customer(customer.id)

    database.delete_order(order.id)
    database.delete_customer(customer.id)
    assert database.get_customer(customer.id) is None


def test_order_crud_filters_and_report(database):
    first = database.create_customer(Customer("Иван"))
    second = database.create_customer(Customer("Анна"))
    order = create_order(database, first.id, "2025-04-20", "новый", 500)
    create_order(database, second.id, "2025-04-21", "выполнен", 900)

    filtered = database.list_orders(
        status="новый", date_from="2025-04-01", date_to="2025-04-30"
    )
    assert len(filtered) == 1
    assert filtered[0]["id"] == order.id

    changed = database.update_order(
        Order(
            id=order.id,
            customer_id=first.id,
            order_date="2025-04-22",
            status="в доставке",
            items=[OrderItem("Новый товар", 1, 300)],
        )
    )
    assert changed.status == "в доставке"
    assert changed.total == 300

    report = database.report("month", reference_date="2025-04-25")
    assert report["orders_by_status"]["в доставке"] == 1
    assert report["orders_by_status"]["выполнен"] == 1
    assert report["revenue"] == 2100
    assert report["top_clients"][0]["name"] == "Анна"


def test_report_period_bounds(database):
    customer = database.create_customer(Customer("Иван"))
    create_order(database, customer.id, "2025-04-20", "новый", 100)
    create_order(database, customer.id, "2025-05-01", "новый", 100)

    report = database.report("month", reference_date="2025-04-25")
    assert report["date_from"] == "2025-04-01"
    assert report["date_to"] == "2025-04-30"
    assert report["revenue"] == 200
