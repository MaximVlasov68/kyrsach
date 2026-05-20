from django.contrib import admin
from django.utils.html import format_html

from .models import CustomerRequest, CustomerRequestItem, Order, OrderItem, Product, ProductCategory, Review, UploadedDocument, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'company', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone', 'company')


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'sku', 'category', 'price', 'weight_grams', 'stock_status', 'is_active', 'is_featured')
    list_filter = ('category', 'stock_status', 'is_active', 'is_featured')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'sku', 'description', 'ingredients')
    readonly_fields = ('image_preview',)

    @admin.display(description='Фото')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:72px;height:48px;object-fit:cover;border-radius:6px;">', obj.image.url)
        return 'Нет фото'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'short_text', 'status', 'created_at')
    list_filter = ('status', 'rating', 'created_at')
    search_fields = ('user__username', 'user__email', 'text', 'moderation_comment')
    readonly_fields = ('created_at',)
    actions = ['approve_reviews', 'reject_reviews', 'hide_reviews']

    @admin.display(description='Текст')
    def short_text(self, obj):
        return obj.text[:90] + ('...' if len(obj.text) > 90 else '')

    @admin.action(description='Одобрить выбранные отзывы')
    def approve_reviews(self, request, queryset):
        queryset.update(status=Review.Status.APPROVED)

    @admin.action(description='Отклонить выбранные отзывы')
    def reject_reviews(self, request, queryset):
        queryset.update(status=Review.Status.REJECTED)

    @admin.action(description='Скрыть выбранные отзывы')
    def hide_reviews(self, request, queryset):
        queryset.update(status=Review.Status.HIDDEN)


class CustomerRequestItemInline(admin.TabularInline):
    model = CustomerRequestItem
    extra = 0
    fields = ('product', 'quantity', 'price', 'subtotal')
    readonly_fields = ('subtotal',)


@admin.register(CustomerRequest)
class CustomerRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'request_type', 'status', 'product', 'created_at')
    list_filter = ('request_type', 'status', 'created_at')
    search_fields = ('name', 'email', 'phone', 'message', 'items__product__name', 'items__product__sku')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CustomerRequestItemInline]


@admin.register(CustomerRequestItem)
class CustomerRequestItemAdmin(admin.ModelAdmin):
    list_display = ('request', 'product', 'quantity', 'price', 'subtotal')
    search_fields = ('=request__id', 'product__name', 'product__sku')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'quantity', 'price', 'subtotal')
    readonly_fields = ('subtotal',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'items_summary', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('=id', 'user__username', 'user__email', 'items__product__name', 'items__product__sku')
    readonly_fields = ('total_price', 'created_at', 'updated_at')
    inlines = [OrderItemInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalculate_total()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'subtotal')
    search_fields = ('=order__id', 'product__name', 'product__sku')


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'original_name', 'mime_type', 'size', 'created_at')
    list_filter = ('mime_type', 'created_at')
    search_fields = ('title', 'original_name', 'user__username', 'user__email')
    readonly_fields = ('original_name', 'mime_type', 'size', 'created_at')
