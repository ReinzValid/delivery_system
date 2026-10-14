import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, List, Mapping, Optional, Tuple

try:
    from .models import Customer, Order, OrderItem
except ImportError:
    from models import Customer, Order, OrderItem


def export_orders(database, file_path):
    path = Path(file_path)
    payload = serialize_database(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    elif path.suffix.lower() == ".xml":
        _write_xml(path, payload)
    else:
        raise ValueError("Поддерживаются только файлы .json и .xml")
    return path


def import_orders(database, file_path):
    path = Path(file_path)
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    elif path.suffix.lower() == ".xml":
        payload = _read_xml(path)
    else:
        raise ValueError("Поддерживаются только файлы .json и .xml")
    customers, orders = parse_payload(payload)
    for customer in customers:
        database.upsert_customer(customer)
    for order in orders:
        if not database.get_customer(order.customer_id):
            raise ValueError(
                "Клиент %s для заказа %s не найден"
                % (order.customer_id, order.id or "без ID")
            )
        database.upsert_order(order)
    return {"customers": len(customers), "orders": len(orders)}


def serialize_database(database):
    customers = [
        {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "address": customer.address,
        }
        for customer in database.list_customers()
    ]
    orders = []
    for order in database.list_order_models():
        orders.append(
            {
                "id": order.id,
                "customer_id": order.customer_id,
                "order_date": order.order_date,
                "status": order.status,
                "total": order.total,
                "items": [
                    {
                        "id": item.id,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "price": item.price,
                    }
                    for item in order.items
                ],
            }
        )
    return {"customers": customers, "orders": orders}


def parse_payload(payload: Any) -> Tuple[List[Customer], List[Order]]:
    if not isinstance(payload, dict):
        raise ValueError("Файл должен содержать объект с customers и orders")
    customers_data = _list_field(payload, "customers")
    orders_data = _list_field(payload, "orders")
    customers = [
        _customer_from_dict(_mapping_item(item, "Клиент")) for item in customers_data
    ]
    orders = []
    for item in orders_data:
        order = _order_from_dict(_mapping_item(item, "Заказ"))
        orders.append(order)
    return customers, orders


def _customer_from_dict(data: Mapping[str, Any]) -> Customer:
    return Customer(
        id=_optional_int(data.get("id")),
        name=_required_text(data.get("name"), "name"),
        phone=_optional_text(data.get("phone")),
        address=_optional_text(data.get("address")),
    )


def _order_from_dict(data: Mapping[str, Any]) -> Order:
    items_data = _list_field(data, "items")
    return Order(
        id=_optional_int(data.get("id")),
        customer_id=_required_int(data.get("customer_id"), "customer_id"),
        order_date=_required_text(data.get("order_date"), "order_date"),
        status=_required_text(data.get("status"), "status"),
        total=_optional_float(data.get("total")),
        items=[
            _order_item_from_dict(_mapping_item(item, "Позиция заказа"))
            for item in items_data
        ],
    )


def _order_item_from_dict(data: Mapping[str, Any]) -> OrderItem:
    return OrderItem(
        id=_optional_int(data.get("id")),
        product_name=_required_text(data.get("product_name"), "product_name"),
        quantity=_required_int(data.get("quantity"), "quantity"),
        price=_required_float(data.get("price"), "price"),
    )


def _list_field(data: Mapping[str, Any], field_name: str) -> List[Any]:
    value = data.get(field_name, [])
    if not isinstance(value, list):
        raise ValueError("%s должен быть списком" % field_name)
    return value


def _mapping_item(value: Any, item_name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("%s должен быть объектом" % item_name)
    return value


def _required_text(value: Any, field_name: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError("%s обязателен" % field_name)
    return text


def _optional_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _write_xml(path, payload):
    root = ET.Element("delivery")
    customers_root = ET.SubElement(root, "customers")
    for customer in payload["customers"]:
        ET.SubElement(
            customers_root,
            "customer",
            {
                "id": str(customer["id"]),
                "name": customer["name"],
                "phone": customer["phone"],
                "address": customer["address"],
            },
        )
    orders_root = ET.SubElement(root, "orders")
    for order in payload["orders"]:
        order_node = ET.SubElement(
            orders_root,
            "order",
            {
                "id": str(order["id"]),
                "customer_id": str(order["customer_id"]),
                "order_date": order["order_date"],
                "status": order["status"],
                "total": str(order["total"]),
            },
        )
        for item in order["items"]:
            ET.SubElement(
                order_node,
                "item",
                {
                    "id": str(item["id"]),
                    "product_name": item["product_name"],
                    "quantity": str(item["quantity"]),
                    "price": str(item["price"]),
                },
            )
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="utf-8", xml_declaration=True)


def _read_xml(path):
    root = ET.parse(str(path)).getroot()
    if root.tag != "delivery":
        raise ValueError("Корневой XML-элемент должен быть delivery")
    customers = []
    for node in root.findall("./customers/customer"):
        customers.append(
            {
                "id": _optional_int(node.get("id")),
                "name": node.get("name"),
                "phone": node.get("phone", ""),
                "address": node.get("address", ""),
            }
        )
    orders = []
    for node in root.findall("./orders/order"):
        orders.append(
            {
                "id": _optional_int(node.get("id")),
                "customer_id": _required_int(node.get("customer_id"), "customer_id"),
                "order_date": node.get("order_date"),
                "status": node.get("status"),
                "total": _required_float(node.get("total"), "total"),
                "items": [
                    {
                        "id": _optional_int(item.get("id")),
                        "product_name": item.get("product_name"),
                        "quantity": _required_int(item.get("quantity"), "quantity"),
                        "price": _required_float(item.get("price"), "price"),
                    }
                    for item in node.findall("./item")
                ],
            }
        )
    return {"customers": customers, "orders": orders}


def _optional_int(value: Any) -> Optional[int]:
    return None if value in (None, "") else int(value)


def _required_int(value: Any, field_name: str) -> int:
    if value in (None, ""):
        raise ValueError("%s обязателен" % field_name)
    return int(value)


def _required_float(value: Any, field_name: str) -> float:
    if value in (None, ""):
        raise ValueError("%s обязателен" % field_name)
    return float(value)


def _optional_float(value: Any) -> Optional[float]:
    return None if value in (None, "") else float(value)
