import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import date

try:
    from .data_export import export_orders, import_orders
    from .database import Database
    from .logger_config import configure_logging
    from .models import Customer, Order, OrderItem, STATUSES
except ImportError:
    from data_export import export_orders, import_orders
    from database import Database
    from logger_config import configure_logging
    from models import Customer, Order, OrderItem, STATUSES


class DeliveryApp:
    def __init__(self, root, database=None):
        self.root = root
        self.root.title("Быстрая доставка")
        self.database = database or Database()
        self.logger = configure_logging()
        self.status_filter = tk.StringVar(value="Все")
        self.date_from = tk.StringVar()
        self.date_to = tk.StringVar()
        self._build()
        self.refresh_orders()

    def _build(self):
        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="Статус").pack(side=tk.LEFT)
        status_box = ttk.Combobox(
            toolbar,
            textvariable=self.status_filter,
            values=["Все"] + list(STATUSES),
            width=16,
            state="readonly",
        )
        status_box.pack(side=tk.LEFT, padx=(4, 12))
        status_box.bind("<<ComboboxSelected>>", lambda event: self.refresh_orders())

        ttk.Label(toolbar, text="Дата с").pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self.date_from, width=12).pack(
            side=tk.LEFT, padx=(4, 8)
        )
        ttk.Label(toolbar, text="по").pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self.date_to, width=12).pack(
            side=tk.LEFT, padx=(4, 12)
        )
        ttk.Button(toolbar, text="Фильтр", command=self.refresh_orders).pack(
            side=tk.LEFT
        )
        ttk.Button(toolbar, text="Сброс", command=self.reset_filters).pack(
            side=tk.LEFT, padx=(4, 12)
        )

        actions = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Добавить", command=self.add_order).pack(side=tk.LEFT)
        ttk.Button(actions, text="Редактировать", command=self.edit_order).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(actions, text="Удалить", command=self.delete_order).pack(
            side=tk.LEFT
        )
        ttk.Button(actions, text="Клиенты", command=self.open_customers).pack(
            side=tk.LEFT, padx=(12, 4)
        )
        ttk.Button(actions, text="Показать отчёт", command=self.show_report).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(actions, text="Экспорт", command=self.export_data).pack(
            side=tk.RIGHT
        )
        ttk.Button(actions, text="Импорт", command=self.import_data).pack(
            side=tk.RIGHT, padx=4
        )

        columns = ("id", "date", "customer", "status", "total", "items")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=18)
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Дата")
        self.tree.heading("customer", text="Клиент")
        self.tree.heading("status", text="Статус")
        self.tree.heading("total", text="Сумма")
        self.tree.heading("items", text="Товары")
        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("date", width=110)
        self.tree.column("customer", width=180)
        self.tree.column("status", width=120)
        self.tree.column("total", width=90, anchor=tk.E)
        self.tree.column("items", width=360)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.tree.bind("<Double-1>", lambda event: self.edit_order())

    def reset_filters(self):
        self.status_filter.set("Все")
        self.date_from.set("")
        self.date_to.set("")
        self.refresh_orders()

    def refresh_orders(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        status = None if self.status_filter.get() == "Все" else self.status_filter.get()
        date_from = self.date_from.get().strip() or None
        date_to = self.date_to.get().strip() or None
        try:
            orders = self.database.list_orders(
                status=status, date_from=date_from, date_to=date_to
            )
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))
            return
        for order in orders:
            self.tree.insert(
                "",
                tk.END,
                iid=str(order["id"]),
                values=(
                    order["id"],
                    order["order_date"],
                    order["customer_name"],
                    order["status"],
                    "%.2f" % order["total"],
                    order["items"] or "",
                ),
            )

    def selected_order_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Заказ", "Выберите заказ")
            return None
        return int(selected[0])

    def add_order(self):
        if not self.database.list_customers():
            messagebox.showwarning("Клиенты", "Сначала добавьте клиента")
            self.open_customers()
            return
        OrderDialog(self.root, self.database, on_save=self.refresh_orders)

    def edit_order(self):
        order_id = self.selected_order_id()
        if order_id is None:
            return
        OrderDialog(
            self.root,
            self.database,
            order=self.database.get_order(order_id),
            on_save=self.refresh_orders,
        )

    def delete_order(self):
        order_id = self.selected_order_id()
        if order_id is None:
            return
        if not messagebox.askyesno("Удаление", "Удалить заказ?"):
            return
        try:
            self.database.delete_order(order_id)
            self.refresh_orders()
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def open_customers(self):
        CustomersDialog(self.root, self.database)

    def show_report(self):
        report = self.database.report("month")
        window = tk.Toplevel(self.root)
        window.title("Отчёт")
        text = tk.Text(window, width=70, height=18)
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        lines = [
            "Период: %s - %s" % (report["date_from"], report["date_to"]),
            "",
            "Заказы по статусам:",
        ]
        lines.extend(
            "%s: %s" % (status, report["orders_by_status"][status])
            for status in STATUSES
        )
        lines.extend(["", "Топ-3 клиентов:"])
        if report["top_clients"]:
            lines.extend(
                "%s. %s - %.2f" % (index, item["name"], item["total"])
                for index, item in enumerate(report["top_clients"], 1)
            )
        else:
            lines.append("Нет данных")
        lines.extend(["", "Выручка: %.2f" % report["revenue"]])
        text.insert("1.0", "\n".join(lines))
        text.configure(state=tk.DISABLED)

    def export_data(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("XML", "*.xml")],
        )
        if not path:
            return
        try:
            export_orders(self.database, path)
            messagebox.showinfo("Экспорт", "Экспорт выполнен")
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def import_data(self):
        path = filedialog.askopenfilename(filetypes=[("JSON/XML", "*.json *.xml")])
        if not path:
            return
        try:
            result = import_orders(self.database, path)
            self.refresh_orders()
            messagebox.showinfo(
                "Импорт",
                "Клиентов: %s, заказов: %s" % (result["customers"], result["orders"]),
            )
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))


class OrderDialog:
    def __init__(self, parent, database, order=None, on_save=None):
        self.database = database
        self.order = order
        self.on_save = on_save
        self.window = tk.Toplevel(parent)
        self.window.title("Заказ")
        self.date_var = tk.StringVar(
            value=order.order_date if order else date.today().isoformat()
        )
        self.status_var = tk.StringVar(value=order.status if order else STATUSES[0])
        self.customer_var = tk.StringVar()
        self.item_rows = []
        self._build()
        self._load_customers()
        if order:
            self.customer_var.set(self._customer_label(order.customer_id))
            for item in order.items:
                self.add_item_row(item)
        else:
            self.add_item_row()

    def _build(self):
        form = ttk.Frame(self.window, padding=10)
        form.pack(fill=tk.BOTH, expand=True)

        ttk.Label(form, text="Дата").grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Entry(form, textvariable=self.date_var, width=18).grid(
            row=0, column=1, sticky=tk.W, pady=3
        )

        ttk.Label(form, text="Клиент").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.customer_box = ttk.Combobox(
            form, textvariable=self.customer_var, width=34, state="readonly"
        )
        self.customer_box.grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=3)

        ttk.Label(form, text="Статус").grid(row=2, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=list(STATUSES),
            width=18,
            state="readonly",
        ).grid(row=2, column=1, sticky=tk.W, pady=3)

        headers = ttk.Frame(form)
        headers.grid(row=3, column=0, columnspan=4, sticky=tk.EW, pady=(10, 0))
        ttk.Label(headers, text="Товар", width=28).pack(side=tk.LEFT)
        ttk.Label(headers, text="Кол-во", width=10).pack(side=tk.LEFT)
        ttk.Label(headers, text="Цена", width=10).pack(side=tk.LEFT)

        self.items_frame = ttk.Frame(form)
        self.items_frame.grid(row=4, column=0, columnspan=4, sticky=tk.EW)

        buttons = ttk.Frame(form)
        buttons.grid(row=5, column=0, columnspan=4, sticky=tk.EW, pady=(10, 0))
        ttk.Button(buttons, text="+", width=4, command=self.add_item_row).pack(
            side=tk.LEFT
        )
        ttk.Button(buttons, text="Сохранить", command=self.save).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Отмена", command=self.window.destroy).pack(
            side=tk.RIGHT, padx=4
        )

    def _load_customers(self):
        self.customers = self.database.list_customers()
        self.customer_box["values"] = [
            self._customer_label(customer.id) for customer in self.customers
        ]
        if self.customers and not self.customer_var.get():
            self.customer_var.set(self._customer_label(self.customers[0].id))

    def _customer_label(self, customer_id):
        customer = self.database.get_customer(customer_id)
        return "%s - %s" % (customer.id, customer.name) if customer else ""

    def add_item_row(self, item=None):
        frame = ttk.Frame(self.items_frame)
        frame.pack(fill=tk.X, pady=2)
        product = ttk.Entry(frame, width=28)
        quantity = ttk.Entry(frame, width=10)
        price = ttk.Entry(frame, width=10)
        product.pack(side=tk.LEFT)
        quantity.pack(side=tk.LEFT, padx=4)
        price.pack(side=tk.LEFT)
        ttk.Button(
            frame, text="-", width=3, command=lambda: self.remove_item_row(frame)
        ).pack(side=tk.LEFT, padx=4)
        if item:
            product.insert(0, item.product_name)
            quantity.insert(0, str(item.quantity))
            price.insert(0, str(item.price))
        self.item_rows.append((frame, product, quantity, price))

    def remove_item_row(self, frame):
        if len(self.item_rows) == 1:
            return
        self.item_rows = [row for row in self.item_rows if row[0] is not frame]
        frame.destroy()

    def save(self):
        try:
            customer_id = int(self.customer_var.get().split(" - ", 1)[0])
            items = [
                OrderItem(product.get(), quantity.get(), price.get())
                for frame, product, quantity, price in self.item_rows
            ]
            order = Order(
                id=self.order.id if self.order else None,
                customer_id=customer_id,
                order_date=self.date_var.get(),
                status=self.status_var.get(),
                items=items,
            )
            if self.order:
                self.database.update_order(order)
            else:
                self.database.create_order(order)
            if self.on_save:
                self.on_save()
            self.window.destroy()
        except Exception as error:
            messagebox.showerror("Ошибка", str(error), parent=self.window)


class CustomersDialog:
    def __init__(self, parent, database):
        self.database = database
        self.window = tk.Toplevel(parent)
        self.window.title("Клиенты")
        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.address_var = tk.StringVar()
        self._build()
        self.refresh()

    def _build(self):
        frame = ttk.Frame(self.window, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(
            frame,
            columns=("id", "name", "phone", "address"),
            show="headings",
            height=10,
        )
        for column, title, width in (
            ("id", "ID", 50),
            ("name", "Имя", 160),
            ("phone", "Телефон", 140),
            ("address", "Адрес", 220),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width)
        self.tree.grid(row=0, column=0, columnspan=4, sticky=tk.NSEW)
        self.tree.bind("<<TreeviewSelect>>", lambda event: self.load_selected())

        ttk.Label(frame, text="Имя").grid(row=1, column=0, sticky=tk.W, pady=(8, 2))
        ttk.Label(frame, text="Телефон").grid(row=1, column=1, sticky=tk.W, pady=(8, 2))
        ttk.Label(frame, text="Адрес").grid(row=1, column=2, sticky=tk.W, pady=(8, 2))
        ttk.Entry(frame, textvariable=self.name_var, width=24).grid(
            row=2, column=0, sticky=tk.W
        )
        ttk.Entry(frame, textvariable=self.phone_var, width=20).grid(
            row=2, column=1, sticky=tk.W, padx=4
        )
        ttk.Entry(frame, textvariable=self.address_var, width=32).grid(
            row=2, column=2, sticky=tk.W
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=4, sticky=tk.EW, pady=(8, 0))
        ttk.Button(buttons, text="Добавить", command=self.add_customer).pack(
            side=tk.LEFT
        )
        ttk.Button(buttons, text="Сохранить", command=self.update_customer).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(buttons, text="Удалить", command=self.delete_customer).pack(
            side=tk.LEFT
        )
        ttk.Button(buttons, text="Закрыть", command=self.window.destroy).pack(
            side=tk.RIGHT
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for customer in self.database.list_customers():
            self.tree.insert(
                "",
                tk.END,
                iid=str(customer.id),
                values=(customer.id, customer.name, customer.phone, customer.address),
            )

    def load_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        self.name_var.set(values[1])
        self.phone_var.set(values[2])
        self.address_var.set(values[3])

    def selected_id(self):
        selected = self.tree.selection()
        return int(selected[0]) if selected else None

    def add_customer(self):
        try:
            self.database.create_customer(
                Customer(
                    self.name_var.get(), self.phone_var.get(), self.address_var.get()
                )
            )
            self.clear_form()
            self.refresh()
        except Exception as error:
            messagebox.showerror("Ошибка", str(error), parent=self.window)

    def update_customer(self):
        customer_id = self.selected_id()
        if customer_id is None:
            messagebox.showwarning("Клиент", "Выберите клиента", parent=self.window)
            return
        try:
            self.database.update_customer(
                Customer(
                    self.name_var.get(),
                    self.phone_var.get(),
                    self.address_var.get(),
                    id=customer_id,
                )
            )
            self.refresh()
        except Exception as error:
            messagebox.showerror("Ошибка", str(error), parent=self.window)

    def delete_customer(self):
        customer_id = self.selected_id()
        if customer_id is None:
            messagebox.showwarning("Клиент", "Выберите клиента", parent=self.window)
            return
        try:
            self.database.delete_customer(customer_id)
            self.clear_form()
            self.refresh()
        except Exception as error:
            messagebox.showerror("Ошибка", str(error), parent=self.window)

    def clear_form(self):
        self.name_var.set("")
        self.phone_var.set("")
        self.address_var.set("")


def main():
    root = tk.Tk()
    DeliveryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
