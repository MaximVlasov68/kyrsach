from django.contrib import admin

from .models import CustomerRequest, Product, ProductCategory, UploadedDocument, UserProfile


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
    list_display = ('name', 'category', 'price', 'weight_grams', 'stock_status', 'is_active', 'is_featured')
    list_filter = ('category', 'stock_status', 'is_active', 'is_featured')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description', 'ingredients')


@admin.register(CustomerRequest)
class CustomerRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'request_type', 'status', 'product', 'created_at')
    list_filter = ('request_type', 'status', 'created_at')
    search_fields = ('name', 'email', 'phone', 'message')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'original_name', 'mime_type', 'size', 'created_at')
    list_filter = ('mime_type', 'created_at')
    search_fields = ('title', 'original_name', 'user__username', 'user__email')
    readonly_fields = ('original_name', 'mime_type', 'size', 'created_at')
