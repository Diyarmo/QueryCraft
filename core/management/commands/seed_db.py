import random
from datetime import timezone as dt_timezone
from typing import List, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from core.models import Customer, Order, Product


class Command(BaseCommand):
    help = "Populate the database with synthetic but relationally consistent data."

    DEFAULT_COUNTS = {"customers": 250, "products": 120, "orders": 1000}
    CATEGORY_POOL = [
        "wallet",
        "staking",
        "education",
        "nft",
        "analytics",
        "defi",
        "payments",
        "gaming",
    ]
    PRICE_RANGE = (1, 1_000)

    def add_arguments(self, parser):
        parser.add_argument(
            "--customers",
            type=int,
            default=self.DEFAULT_COUNTS["customers"],
            help="Ensure at least this many customers exist (default: %(default)s).",
        )
        parser.add_argument(
            "--products",
            type=int,
            default=self.DEFAULT_COUNTS["products"],
            help="Ensure at least this many products exist (default: %(default)s).",
        )
        parser.add_argument(
            "--orders",
            type=int,
            default=self.DEFAULT_COUNTS["orders"],
            help="Ensure at least this many orders exist (default: %(default)s).",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Delete existing orders/products/customers before seeding.",
        )

    def handle(self, *args, **options):
        faker = Faker()
        customer_target = max(1, options["customers"])
        product_target = max(1, options["products"])
        order_target = max(1, options["orders"])

        with transaction.atomic():
            if options["purge"]:
                self._purge_existing()

            customers, new_customers = self._ensure_customers(
                faker, customer_target
            )
            products, new_products = self._ensure_products(
                faker, product_target
            )
            new_orders = self._ensure_orders(faker, customers, products, order_target)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeding complete: "
                f"{new_customers} new customers, "
                f"{new_products} new products, "
                f"{new_orders} new orders."
            )
        )

    def _purge_existing(self) -> None:
        self.stdout.write("Purging existing orders, products, and customers...")
        Order.objects.all().delete()
        Product.objects.all().delete()
        Customer.objects.all().delete()

    def _ensure_customers(self, faker: Faker, target: int) -> Tuple[List[Customer], int]:
        current = Customer.objects.count()
        to_create = max(0, target - current)
        created = 0

        if to_create:
            existing_emails = set(
                Customer.objects.values_list("email", flat=True)
            )
            customers = []
            for _ in range(to_create):
                email = faker.unique.email()
                while email in existing_emails:
                    email = faker.unique.email()
                existing_emails.add(email)
                customers.append(
                    Customer(
                        name=faker.name(),
                        email=email,
                        registration_date=faker.date_time_between(
                            start_date="-2y", end_date="now", tzinfo=dt_timezone.utc
                        ),
                    )
                )
            Customer.objects.bulk_create(customers, batch_size=500)
            faker.unique.clear()
            created = to_create

        return list(Customer.objects.all()), created

    def _ensure_products(self, faker: Faker, target: int) -> Tuple[List[Product], int]:
        current = Product.objects.count()
        to_create = max(0, target - current)
        created = 0

        if to_create:
            products = []
            for _ in range(to_create):
                products.append(
                    Product(
                        name=faker.unique.catch_phrase(),
                        category=random.choice(self.CATEGORY_POOL),
                        price=faker.random_int(
                            min=self.PRICE_RANGE[0], max=self.PRICE_RANGE[1]
                        ) * 1_000_000,
                    )
                )
            Product.objects.bulk_create(products, batch_size=500)
            faker.unique.clear()
            created = to_create

        return list(Product.objects.all()), created

    def _ensure_orders(
        self, faker: Faker, customers: List[Customer], products: List[Product], target: int
    ) -> int:
        if not customers or not products:
            raise CommandError("Customers and products must exist before creating orders.")

        current = Order.objects.count()
        to_create = max(0, target - current)

        if not to_create:
            return 0

        customer_pool = customers
        product_pool = products
        statuses = [status.value for status in Order.Status]
        orders: List[Order] = []

        for _ in range(to_create):
            customer = random.choice(customer_pool)
            product = random.choice(product_pool)
            order_date = faker.date_time_between(
                start_date=customer.registration_date, end_date="now", tzinfo=dt_timezone.utc
            )
            orders.append(
                Order(
                    customer=customer,
                    product=product,
                    order_date=order_date,
                    quantity=faker.random_int(min=1, max=5),
                    status=random.choice(statuses),
                )
            )

        Order.objects.bulk_create(orders, batch_size=500)
        return to_create
