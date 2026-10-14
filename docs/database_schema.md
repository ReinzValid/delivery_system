# Схема базы данных

## customers

| Поле | Тип | Ограничения |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | NOT NULL |
| phone | TEXT | NOT NULL DEFAULT '' |
| address | TEXT | NOT NULL DEFAULT '' |

## orders

| Поле | Тип | Ограничения |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| customer_id | INTEGER | NOT NULL, FOREIGN KEY, ON DELETE RESTRICT |
| order_date | TEXT | NOT NULL, формат YYYY-MM-DD |
| status | TEXT | NOT NULL, CHECK |
| total | REAL | NOT NULL, CHECK total >= 0 |

Статусы заказа:

- новый
- в доставке
- выполнен
- отменён

## order_items

| Поле | Тип | Ограничения |
| --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| order_id | INTEGER | NOT NULL, FOREIGN KEY, ON DELETE CASCADE |
| product_name | TEXT | NOT NULL |
| quantity | INTEGER | NOT NULL, CHECK quantity > 0 |
| price | REAL | NOT NULL, CHECK price >= 0 |

## Связи

- Один клиент может иметь много заказов.
- Один заказ содержит много товаров.
- Клиент не удаляется, если у него есть заказы.
- При удалении заказа автоматически удаляются его товары.

## Индексы

- `idx_orders_customer` ускоряет выборку заказов клиента.
- `idx_orders_status` ускоряет фильтр по статусу.
- `idx_orders_date` ускоряет фильтр по дате.

## Отчеты

- Количество заказов по статусам: `GROUP BY status`.
- Топ-3 клиента: `JOIN customers`, `SUM(total)`, `GROUP BY customer`.
- Выручка за период: `SUM(total)` с фильтром по датам.
