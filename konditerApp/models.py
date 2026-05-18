import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from .validators import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_PRODUCT_IMAGE_EXTENSIONS,
    validate_document_extension,
    validate_product_image_extension,
)


def document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    owner = instance.user_id or 'anonymous'
    return f'uploads/documents/user_{owner}/{uuid.uuid4().hex}{extension}'


def product_image_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    slug = instance.slug or 'product'
    return f'uploads/products/{slug}/{uuid.uuid4().hex}{extension}'


class UserProfile(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Покупатель'
        ADMIN = 'admin', 'Админ'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'профиль пользователя'
        verbose_name_plural = 'профили пользователей'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'

    @property
    def is_site_admin(self):
        return self.role == self.Role.ADMIN or self.user.is_staff or self.user.is_superuser


class ProductCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'категория каталога'
        verbose_name_plural = 'категории каталога'

    def __str__(self):
        return self.name


class Product(models.Model):
    class StockStatus(models.TextChoices):
        AVAILABLE = 'available', 'В наличии'
        PREORDER = 'preorder', 'Под заказ'
        UNAVAILABLE = 'unavailable', 'Недоступен'

    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products',
    )
    sku = models.CharField(max_length=40, unique=True, blank=True, null=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    image = models.FileField(
        upload_to=product_image_upload_path,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=sorted(ALLOWED_PRODUCT_IMAGE_EXTENSIONS)),
            validate_product_image_extension,
        ],
    )
    description = models.TextField()
    ingredients = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    weight_grams = models.PositiveIntegerField(default=100)
    stock_status = models.CharField(
        max_length=20,
        choices=StockStatus.choices,
        default=StockStatus.AVAILABLE,
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})


class CustomerRequest(models.Model):
    class RequestType(models.TextChoices):
        ORDER = 'order', 'Заказ'
        CALLBACK = 'callback', 'Обратный звонок'
        QUESTION = 'question', 'Вопрос'

    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        IN_PROGRESS = 'in_progress', 'В работе'
        DONE = 'done', 'Завершена'
        CANCELLED = 'cancelled', 'Отменена'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='requests',
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name='requests',
        null=True,
        blank=True,
    )
    request_type = models.CharField(max_length=20, choices=RequestType.choices, default=RequestType.ORDER)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    admin_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'заявка'
        verbose_name_plural = 'заявки'

    def __str__(self):
        return f'{self.get_request_type_display()} от {self.name}'


class UploadedDocument(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    request = models.ForeignKey(
        CustomerRequest,
        on_delete=models.SET_NULL,
        related_name='documents',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=160)
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[
            FileExtensionValidator(allowed_extensions=sorted(ALLOWED_DOCUMENT_EXTENSIONS)),
            validate_document_extension,
        ],
    )
    original_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'загруженный документ'
        verbose_name_plural = 'загруженные документы'

    def __str__(self):
        return self.title
