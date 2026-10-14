import pytest

from models import Customer, Order, OrderItem


def test_customer_requires_name():
    with pytest.raises(ValueError):
        Customer("")


def test_order_calculates_total():
    order = Order(
        customer_id=1,
        order_date="2025-04-20",
        status="новый",
        items=[OrderItem("Пицца", 2, 750), OrderItem("Сок", 1, 150)],
    )
    assert order.total == 1650


def test_order_rejects_bad_status():
    with pytest.raises(ValueError):
        Order(
            customer_id=1,
            order_date="2025-04-20",
            status="ошибка",
            items=[OrderItem("Пицца", 1, 500)],
        )


def test_order_rejects_wrong_total():
    with pytest.raises(ValueError):
        Order(
            customer_id=1,
            order_date="2025-04-20",
            status="новый",
            total=1,
            items=[OrderItem("Пицца", 1, 500)],
        )
