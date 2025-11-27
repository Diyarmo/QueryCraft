from django.db import models
from django.utils import timezone


class Customer(models.Model):
    """Represents an end user that can place orders."""

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    registration_date = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-registration_date", "id"]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


class Product(models.Model):
    """Product catalog entry."""

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=120, db_index=True)
    price = models.PositiveBigIntegerField(help_text="Stored in IRR; no fractional values.")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.category})"


class Order(models.Model):
    """Represents a purchase of a product by a customer."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="orders"
    )
    order_date = models.DateTimeField(default=timezone.now, db_index=True)
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    class Meta:
        ordering = ["-order_date", "id"]

    def __str__(self) -> str:
        return f"Order #{self.pk or 'new'}"
