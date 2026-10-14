import argparse
import sys

try:
    from .data_export import export_orders, import_orders
    from .database import Database
    from .logger_config import configure_logging
    from .models import STATUSES
except ImportError:
    from data_export import export_orders, import_orders
    from database import Database
    from logger_config import configure_logging
    from models import STATUSES


def build_parser():
    parser = argparse.ArgumentParser(prog="delivery.py")
    parser.add_argument("--db", default=None, help="Путь к SQLite-файлу")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument(
        "--period", choices=("day", "week", "month"), default="month"
    )
    report_parser.add_argument("--from", dest="date_from")
    report_parser.add_argument("--to", dest="date_to")

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--file", required=True)

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--file", required=True)

    return parser


def main(argv=None):
    logger = configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    with Database(args.db) as database:
        try:
            if args.command == "report":
                report = database.report(args.period, args.date_from, args.date_to)
                sys.stdout.write(format_report(report))
            elif args.command == "export":
                path = export_orders(database, args.file)
                logger.info("Exported orders to %s", path)
                sys.stdout.write("Экспорт выполнен: %s\n" % path)
            elif args.command == "import":
                result = import_orders(database, args.file)
                logger.info("Imported orders from %s", args.file)
                sys.stdout.write(
                    "Импортировано: клиентов %s, заказов %s\n"
                    % (result["customers"], result["orders"])
                )
        except Exception as error:
            logger.exception("CLI command failed")
            sys.stderr.write("%s\n" % error)
            return 1
    return 0


def format_report(report):
    lines = [
        "Отчет за период %s - %s" % (report["date_from"], report["date_to"]),
        "",
        "Количество заказов по статусам:",
    ]
    for status in STATUSES:
        lines.append("%s: %s" % (status, report["orders_by_status"].get(status, 0)))
    lines.extend(["", "Топ-3 клиента по сумме заказов:"])
    if report["top_clients"]:
        for index, client in enumerate(report["top_clients"], start=1):
            lines.append("%s. %s - %.2f" % (index, client["name"], client["total"]))
    else:
        lines.append("Нет данных")
    lines.extend(["", "Общая выручка: %.2f" % report["revenue"]])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
