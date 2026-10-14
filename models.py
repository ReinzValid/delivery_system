from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


STATUSES = ("новый", "в доставке", "выполнен", "отменён")


def validate_date(value):
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("Дата должна быть в формате YYYY-MM-DD") from None
    return value


def clean_text(value, field_name, required=False):
    value = "" if value is None else str(value).strip()
    if required and not value:
        raise ValueError("%s не может быть пустым" % field_name)
    return value


@dataclass
class Customer:
    name: str
    phone: str = ""
    address: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        self.name = clean_text(self.name, "Имя", True)
        self.phone = clean_text(self.phone, "Телефон")
        self.address = clean_text(self.address, "Адрес")
        if self.id is not None and int(self.id) < 1:
            raise ValueError("ID клиента должен быть положительным")
        self.id = None if self.id is None else int(self.id)


@dataclass
class OrderItem:
    product_name: str
    quantity: int
    price: float
    id: Optional[int] = None

    def __post_init__(self):
        self.product_name = clean_text(self.product_name, "Товар", True)
        self.quantity = int(self.quantity)
        self.price = float(self.price)
        if self.quantity < 1:
            raise ValueError("Количество должно быть больше нуля")
        if self.price < 0:
            raise ValueError("Цена не может быть отрицательной")
        if self.id is not None and int(self.id) < 1:
            raise ValueError("ID позиции должен быть положительным")
        self.id = None if self.id is None else int(self.id)

    @property
    def total(self):
        return round(self.quantity * self.price, 2)


@dataclass
class Order:
    customer_id: int
    order_date: str
    status: str
    items: List[OrderItem] = field(default_factory=list)
    id: Optional[int] = None
    total: Optional[float] = None

    def __post_init__(self):
        self.customer_id = int(self.customer_id)
        if self.customer_id < 1:
            raise ValueError("ID клиента должен быть положительным")
        self.order_date = validate_date(str(self.order_date).strip())
        self.status = clean_text(self.status, "Статус", True)
        if self.status not in STATUSES:
            raise ValueError("Недопустимый статус заказа")
        self.items = [
            item if isinstance(item, OrderItem) else OrderItem(**item)
            for item in self.items
        ]
        if not self.items:
            raise ValueError("Заказ должен содержать хотя бы один товар")
        calculated = round(sum(item.total for item in self.items), 2)
        if self.total is None:
            self.total = calculated
        else:
            self.total = round(float(self.total), 2)
            if abs(self.total - calculated) > 0.01:
                raise ValueError("Итоговая сумма не совпадает со списком товаров")
        if self.id is not None and int(self.id) < 1:
            raise ValueError("ID заказа должен быть положительным")
        self.id = None if self.id is None else int(self.id)
