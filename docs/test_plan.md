# Тест-план

## Цель

Проверить, что приложение соответствует ТЗ: клиенты, заказы, отчеты, импорт/экспорт, CLI, GUI, логирование и тесты.

## Автоматические проверки

```bash
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing --cov-fail-under=60
```

Покрытие считается по основной логике и CLI. GUI проверяется вручную.

Проверяются:

- валидация моделей;
- CRUD клиентов;
- запрет удаления клиента с заказами;
- CRUD заказов;
- фильтрация по статусу и датам;
- отчет по статусам;
- топ-3 клиентов;
- выручка за период;
- экспорт JSON;
- импорт JSON;
- экспорт XML;
- импорт XML;
- отклонение некорректных данных;
- CLI-отчет;
- CLI-экспорт;
- CLI-импорт;
- обработка ошибки импорта;
- настройка логирования;
- запуск `delivery.py` как точки входа.

## Ручные проверки CLI

```bash
.\.venv\Scripts\python.exe main_cli.py --db data/manual.db report --period month
.\.venv\Scripts\python.exe main_cli.py --db data/manual.db export --file data/orders.json
.\.venv\Scripts\python.exe main_cli.py --db data/import_json.db import --file data/orders.json
.\.venv\Scripts\python.exe main_cli.py --db data/manual.db export --file data/orders.xml
.\.venv\Scripts\python.exe main_cli.py --db data/import_xml.db import --file data/orders.xml
```

Ожидаемый результат:

- отчет выводит статусы, топ-3 клиентов и выручку;
- JSON и XML создаются;
- импорт из JSON и XML проходит без ошибок.

## Ручные проверки GUI

```bash
.\.venv\Scripts\python.exe main_gui.py
```

Проверить:

- открывается главное окно;
- клиент добавляется, редактируется и удаляется;
- клиент с заказом не удаляется;
- заказ добавляется через форму;
- заказ редактируется;
- заказ удаляется;
- фильтр по статусу меняет список заказов;
- фильтр по датам меняет список заказов;
- кнопка отчета показывает статистику;
- экспорт создает JSON или XML;
- импорт загружает JSON или XML.

## Регрессионная проверка перед GitHub

Перед публикацией проекта:

```bash
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing --cov-fail-under=60
.\.venv\Scripts\python.exe main_cli.py --db data/final_check.db report --period month
.\.venv\Scripts\python.exe main_cli.py --db data/final_check.db export --file data/final_check.json
```

После проверки удалить временные файлы из `data/`, если они не нужны для демонстрации.
