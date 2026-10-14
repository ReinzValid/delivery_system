# Быстрая доставка

Внутреннее приложение для учета клиентов, заказов, отчетов и импорта/экспорта данных.

## Стек

- Python 3.8+
- SQLite
- Tkinter
- argparse
- logging
- pytest
- pytest-cov
- JSON и XML

## Структура

```text
delivery_system/
├── main_cli.py
├── delivery.py
├── main_gui.py
├── database.py
├── models.py
├── data_export.py
├── logger_config.py
├── docs/
├── tests/
├── logs/
├── data/
├── requirements.txt
└── README.md
```

## Установка

```bash
cd delivery_system
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## CLI

```bash
.\.venv\Scripts\python.exe delivery.py report --period month
.\.venv\Scripts\python.exe delivery.py export --file orders_backup.json
.\.venv\Scripts\python.exe delivery.py export --file orders_backup.xml
.\.venv\Scripts\python.exe delivery.py import --file orders_backup.json
.\.venv\Scripts\python.exe delivery.py import --file orders_backup.xml
```

Альтернативная точка входа:

```bash
.\.venv\Scripts\python.exe main_cli.py report --period month
.\.venv\Scripts\python.exe main_cli.py export --file orders_backup.json
.\.venv\Scripts\python.exe main_cli.py export --file orders_backup.xml
.\.venv\Scripts\python.exe main_cli.py import --file orders_backup.json
.\.venv\Scripts\python.exe main_cli.py import --file orders_backup.xml
```

Можно указать другой файл БД:

```bash
.\.venv\Scripts\python.exe main_cli.py --db data/test.db report --period week
```

## GUI

```bash
.\.venv\Scripts\python.exe main_gui.py
```

В GUI доступны список заказов, фильтр по статусу и датам, добавление, редактирование, удаление заказов, управление клиентами, отчет, импорт и экспорт.

## Тесты

Для проверки тестов и покрытия нужно поставить dev-зависимости:

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

```bash
.\.venv\Scripts\python.exe -m pytest
```

Проверка покрытия основной логики:

```bash
.\.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing --cov-fail-under=60
```

## Документация

- [docs/database_schema.md](docs/database_schema.md) — схема базы данных и SQL-логика.
- [docs/test_plan.md](docs/test_plan.md) — план ручной и автоматической проверки.

## Правила данных

- Клиент: имя, телефон, адрес.
- Заказ: дата, клиент, статус, список товаров, итоговая сумма.
- Статусы: новый, в доставке, выполнен, отменён.
- Клиента нельзя удалить, если с ним связаны заказы.
- Импорт проверяет структуру, даты, статусы, товары, суммы и связи с клиентами.
