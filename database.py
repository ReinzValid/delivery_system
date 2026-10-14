import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Optional, Union

try:
    from .models import Customer, Order, OrderItem, STATUSES, validate_date
except ImportError:
    from models import Customer, Order, OrderItem, STATUSES, validate_date

CustomerInput = Union[Customer, Mapping[str, Any]]
OrderInput = Union[Order, Mapping[str, Any]]


class Database:
    def __init__(self, path=None):
        self.path = (
            Path(path)
            if path
            else Path(__file__).resolve().parent / "data" / "delivery.db"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.initialize()

    def initialize(self):
        statuses = ",".join("'%s'" % status for status in STATUSES)
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN (%s)),
                total REAL NOT NULL CHECK(total >= 0)
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                price REAL NOT NULL CHECK(price >= 0)
            );

            CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
            """
            % statuses
        )
        self.connection.commit()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def create_customer(self, customer: CustomerInput) -> Customer:
        customer = customer if isinstance(customer, Customer) else Customer(**customer)
        with self.connection:
            if customer.id is None:
                cursor = self.connection.execute(
                    "INSERT INTO customers(name, phone, address) VALUES (?, ?, ?)",
                    (customer.name, customer.phone, customer.address),
                )
                customer_id = cursor.lastrowid
                if customer_id is None:
                    raise RuntimeError("Не удалось получить ID клиента")
            else:
                self.connection.execute(
                    "INSERT INTO customers(id, name, phone, address) VALUES (?, ?, ?, ?)",
                    (customer.id, customer.name, customer.phone, customer.address),
                )
                customer_id = customer.id
        created = self.get_customer(customer_id)
        if created is None:
            raise RuntimeError("Клиент не найден после создания")
        return created

    def upsert_customer(self, customer: CustomerInput) -> Customer:
        customer = customer if isinstance(customer, Customer) else Customer(**customer)
        if customer.id is not None and self.get_customer(customer.id):
            return self.update_customer(customer)
        return self.create_customer(customer)

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        row = self.connection.execute(
            "SELECT id, name, phone, address FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if not row:
            return None
        return Customer(
            id=row["id"], name=row["name"], phone=row["phone"], address=row["address"]
        )

    def list_customers(self, search=None):
        if search:
            value = "%%%s%%" % search.strip()
            rows = self.connection.execute(
                """
                SELECT id, name, phone, address
                FROM customers
                WHERE name LIKE ? OR phone LIKE ? OR address LIKE ?
                ORDER BY name
                """,
                (value, value, value),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT id, name, phone, address FROM customers ORDER BY name"
            ).fetchall()
        return [
            Customer(
                id=row["id"],
                name=row["name"],
                phone=row["phone"],
                address=row["address"],
            )
            for row in rows
        ]

    def update_customer(self, customer: CustomerInput) -> Customer:
        customer = customer if isinstance(customer, Customer) else Customer(**customer)
        if customer.id is None:
            raise ValueError("Для обновления нужен ID клиента")
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?",
                (customer.name, customer.phone, customer.address, customer.id),
            )
        if cursor.rowcount == 0:
            raise ValueError("Клиент не найден")
        updated = self.get_customer(customer.id)
        if updated is None:
            raise RuntimeError("Клиент не найден после обновления")
        return updated

    def delete_customer(self, customer_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "DELETE FROM customers WHERE id = ?", (customer_id,)
                )
        except sqlite3.IntegrityError:
            raise ValueError("Клиента нельзя удалить, если есть заказы") from None
        if cursor.rowcount == 0:
            raise ValueError("Клиент не найден")

    def create_order(self, order: OrderInput) -> Order:
        order = order if isinstance(order, Order) else Order(**order)
        with self.connection:
            if order.id is None:
                cursor = self.connection.execute(
                    "INSERT INTO orders(customer_id, order_date, status, total) VALUES (?, ?, ?, ?)",
                    (order.customer_id, order.order_date, order.status, order.total),
                )
                order_id = cursor.lastrowid
                if order_id is None:
                    raise RuntimeError("Не удалось получить ID заказа")
            else:
                self.connection.execute(
                    "INSERT INTO orders(id, customer_id, order_date, status, total) VALUES (?, ?, ?, ?, ?)",
                    (
                        order.id,
                        order.customer_id,
                        order.order_date,
                        order.status,
                        order.total,
                    ),
                )
                order_id = order.id
            self._insert_items(order_id, order.items)
        created = self.get_order(order_id)
        if created is None:
            raise RuntimeError("Заказ не найден после создания")
        return created

    def upsert_order(self, order: OrderInput) -> Order:
        order = order if isinstance(order, Order) else Order(**order)
        if order.id is not None and self.get_order(order.id):
            return self.update_order(order)
        return self.create_order(order)

    def get_order(self, order_id: int) -> Optional[Order]:
        row = self.connection.execute(
            "SELECT id, customer_id, order_date, status, total FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            return None
        items = self._items_for_order(row["id"])
        return Order(
            id=row["id"],
            customer_id=row["customer_id"],
            order_date=row["order_date"],
            status=row["status"],
            items=items,
            total=row["total"],
        )

    def list_order_models(self):
        rows = self.connection.execute("SELECT id FROM orders ORDER BY id").fetchall()
        orders = []
        for row in rows:
            order = self.get_order(row["id"])
            if order is not None:
                orders.append(order)
        return orders

    def list_orders(self, status=None, date_from=None, date_to=None):
        filters = []
        params = []
        if status:
            if status not in STATUSES:
                raise ValueError("Недопустимый статус заказа")
            filters.append("o.status = ?")
            params.append(status)
        if date_from:
            filters.append("o.order_date >= ?")
            params.append(validate_date(date_from))
        if date_to:
            filters.append("o.order_date <= ?")
            params.append(validate_date(date_to))
        where_sql = "WHERE " + " AND ".join(filters) if filters else ""
        rows = self.connection.execute(
            """
            SELECT o.id, o.customer_id, c.name AS customer_name, o.order_date, o.status, o.total,
                   GROUP_CONCAT(oi.product_name || ' x' || oi.quantity, ', ') AS items
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            %s
            GROUP BY o.id, o.customer_id, c.name, o.order_date, o.status, o.total
            ORDER BY o.order_date DESC, o.id DESC
            """
            % where_sql,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def update_order(self, order: OrderInput) -> Order:
        order = order if isinstance(order, Order) else Order(**order)
        if order.id is None:
            raise ValueError("Для обновления нужен ID заказа")
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE orders SET customer_id = ?, order_date = ?, status = ?, total = ? WHERE id = ?",
                (
                    order.customer_id,
                    order.order_date,
                    order.status,
                    order.total,
                    order.id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("Заказ не найден")
            self.connection.execute(
                "DELETE FROM order_items WHERE order_id = ?", (order.id,)
            )
            self._insert_items(order.id, order.items)
        updated = self.get_order(order.id)
        if updated is None:
            raise RuntimeError("Заказ не найден после обновления")
        return updated

    def delete_order(self, order_id):
        with self.connection:
            cursor = self.connection.execute(
                "DELETE FROM orders WHERE id = ?", (order_id,)
            )
        if cursor.rowcount == 0:
            raise ValueError("Заказ не найден")

    def count_orders_by_status(self, date_from=None, date_to=None):
        filters, params = self._date_filters(date_from, date_to)
        rows = self.connection.execute(
            """
            SELECT status, COUNT(*) AS amount
            FROM orders
            %s
            GROUP BY status
            """
            % ("WHERE " + " AND ".join(filters) if filters else ""),
            params,
        ).fetchall()
        result = {status: 0 for status in STATUSES}
        for row in rows:
            result[row["status"]] = row["amount"]
        return result

    def top_clients_by_sum(self, limit=3, date_from=None, date_to=None):
        filters, params = self._date_filters(date_from, date_to)
        params.append(limit)
        rows = self.connection.execute(
            """
            SELECT c.id, c.name, COALESCE(SUM(o.total), 0) AS total
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            %s
            GROUP BY c.id, c.name
            ORDER BY total DESC, c.name ASC
            LIMIT ?
            """
            % ("WHERE " + " AND ".join(filters) if filters else ""),
            params,
        ).fetchall()
        return [
            {"id": row["id"], "name": row["name"], "total": round(row["total"], 2)}
            for row in rows
        ]

    def revenue(self, date_from=None, date_to=None):
        filters, params = self._date_filters(date_from, date_to)
        row = self.connection.execute(
            "SELECT COALESCE(SUM(total), 0) AS total FROM orders %s"
            % ("WHERE " + " AND ".join(filters) if filters else ""),
            params,
        ).fetchone()
        return round(row["total"], 2)

    def report(self, period="month", date_from=None, date_to=None, reference_date=None):
        if not date_from or not date_to:
            date_from, date_to = period_bounds(period, reference_date)
        return {
            "date_from": date_from,
            "date_to": date_to,
            "orders_by_status": self.count_orders_by_status(date_from, date_to),
            "top_clients": self.top_clients_by_sum(3, date_from, date_to),
            "revenue": self.revenue(date_from, date_to),
        }

    def _insert_items(self, order_id, items):
        self.connection.executemany(
            "INSERT INTO order_items(order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)",
            [
                (order_id, item.product_name, item.quantity, item.price)
                for item in items
            ],
        )

    def _items_for_order(self, order_id):
        rows = self.connection.execute(
            "SELECT id, product_name, quantity, price FROM order_items WHERE order_id = ? ORDER BY id",
            (order_id,),
        ).fetchall()
        return [
            OrderItem(
                id=row["id"],
                product_name=row["product_name"],
                quantity=row["quantity"],
                price=row["price"],
            )
            for row in rows
        ]

    def _date_filters(self, date_from=None, date_to=None):
        filters = []
        params = []
        if date_from:
            filters.append("order_date >= ?")
            params.append(validate_date(date_from))
        if date_to:
            filters.append("order_date <= ?")
            params.append(validate_date(date_to))
        return filters, params


def period_bounds(period, reference_date=None):
    reference = (
        date.today()
        if reference_date is None
        else date.fromisoformat(str(reference_date))
    )
    if period == "day":
        start = end = reference
    elif period == "week":
        start = reference - timedelta(days=reference.weekday())
        end = start + timedelta(days=6)
    elif period == "month":
        start = reference.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        end = next_month - timedelta(days=1)
    else:
        raise ValueError("Период должен быть day, week или month")
    return start.isoformat(), end.isoformat()
