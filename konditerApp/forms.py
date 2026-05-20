from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import CustomerRequest, Order, Product, ProductCategory, Review, UploadedDocument, UserProfile
from .validators import (
    normalize_text,
    validate_document_extension,
    validate_document_mime,
    validate_phone,
    validate_product_image_extension,
    validate_product_image_mime,
    validate_review_text,
    validate_safe_name,
)


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(label='Имя', max_length=120)
    last_name = forms.CharField(label='Фамилия', max_length=120, required=False)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='Телефон', max_length=30, required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_username(self):
        username = normalize_text(self.cleaned_data['username'])
        validate_safe_name(username)
        return username

    def clean_first_name(self):
        value = normalize_text(self.cleaned_data['first_name'])
        validate_safe_name(value)
        return value

    def clean_last_name(self):
        value = normalize_text(self.cleaned_data.get('last_name'))
        if value:
            validate_safe_name(value)
        return value

    def clean_phone(self):
        value = normalize_text(self.cleaned_data.get('phone'))
        validate_phone(value)
        return value

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='Имя', max_length=120)
    last_name = forms.CharField(label='Фамилия', max_length=120, required=False)
    email = forms.EmailField(label='Email')

    class Meta:
        model = UserProfile
        fields = ['phone', 'company']
        labels = {
            'phone': 'Телефон',
            'company': 'Компания',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['first_name'].initial = self.user.first_name
        self.fields['last_name'].initial = self.user.last_name
        self.fields['email'].initial = self.user.email
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_first_name(self):
        value = normalize_text(self.cleaned_data['first_name'])
        validate_safe_name(value)
        return value

    def clean_last_name(self):
        value = normalize_text(self.cleaned_data.get('last_name'))
        if value:
            validate_safe_name(value)
        return value

    def clean_phone(self):
        value = normalize_text(self.cleaned_data.get('phone'))
        validate_phone(value)
        return value

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise ValidationError('Этот email уже используется другим пользователем.')
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        if commit:
            self.user.save()
            profile.save()
        return profile


class CustomerRequestForm(forms.ModelForm):
    quantity = forms.IntegerField(
        label='Количество',
        min_value=1,
        initial=1,
        required=True,
        widget=forms.NumberInput(attrs={'min': 1, 'step': 1}),
    )

    class Meta:
        model = CustomerRequest
        fields = ['request_type', 'product', 'quantity', 'name', 'email', 'phone', 'message']
        labels = {
            'request_type': 'Тип обращения',
            'product': 'Товар',
            'name': 'Имя',
            'email': 'Email',
            'phone': 'Телефон',
            'message': 'Сообщение',
        }
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['product'].required = True
        self.fields['product'].queryset = Product.objects.filter(is_active=True).select_related('category')
        if self.user and self.user.is_authenticated:
            self.fields['name'].initial = self.fields['name'].initial or self.user.get_full_name() or self.user.username
            self.fields['email'].initial = self.fields['email'].initial or self.user.email
            profile = getattr(self.user, 'profile', None)
            if profile:
                self.fields['phone'].initial = self.fields['phone'].initial or profile.phone
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_name(self):
        value = normalize_text(self.cleaned_data['name'])
        validate_safe_name(value)
        return value

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity < 1:
            raise ValidationError('Количество должно быть не меньше 1.')
        return quantity

    def clean_product(self):
        product = self.cleaned_data['product']
        if product.stock_status == Product.StockStatus.UNAVAILABLE:
            raise ValidationError('Этот товар сейчас недоступен для заказа.')
        return product


class ProductOrderForm(forms.Form):
    quantity = forms.IntegerField(
        label='Количество',
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'min': 1, 'step': 1, 'data-order-quantity': 'true'}),
    )
    customer_comment = forms.CharField(
        label='Комментарий к заказу',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Например: дата, упаковка или пожелания'}),
    )

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product')
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity < 1:
            raise ValidationError('Количество должно быть не меньше 1.')
        if self.product.stock_status == Product.StockStatus.UNAVAILABLE:
            raise ValidationError('Этот товар сейчас недоступен для заказа.')
        return quantity

    def clean_customer_comment(self):
        value = normalize_text(self.cleaned_data.get('customer_comment'))
        if any(symbol in value for symbol in ['<', '>', '{', '}']):
            raise ValidationError('Комментарий содержит недопустимые символы.')
        return value

    def clean_phone(self):
        value = normalize_text(self.cleaned_data.get('phone'))
        validate_phone(value)
        return value

    def clean_message(self):
        value = normalize_text(self.cleaned_data['message'])
        if len(value) < 10:
            raise ValidationError('Опишите обращение подробнее, минимум 10 символов.')
        if any(symbol in value for symbol in ['<', '>', '{', '}']):
            raise ValidationError('Сообщение содержит недопустимые символы.')
        return value


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        labels = {
            'rating': 'Оценка',
            'text': 'Текст отзыва',
        }
        widgets = {
            'rating': forms.Select(choices=[(value, f'{value} из 5') for value in range(5, 0, -1)]),
            'text': forms.Textarea(attrs={'rows': 4, 'maxlength': 1000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_text(self):
        value = normalize_text(self.cleaned_data['text'])
        validate_review_text(value)
        return value


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedDocument
        fields = ['title', 'request', 'file']
        labels = {
            'title': 'Название документа',
            'request': 'Связанная заявка',
            'file': 'Файл',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['request'].required = False
        self.fields['request'].queryset = CustomerRequest.objects.filter(user=self.user)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_title(self):
        value = normalize_text(self.cleaned_data['title'])
        validate_safe_name(value)
        return value

    def clean_file(self):
        file_obj = self.cleaned_data['file']
        validate_document_extension(file_obj)
        validate_document_mime(file_obj)
        if file_obj.size > 10 * 1024 * 1024:
            raise ValidationError('Размер файла не должен превышать 10 МБ.')
        return file_obj

    def save(self, commit=True):
        document = super().save(commit=False)
        uploaded = self.cleaned_data['file']
        document.user = self.user
        document.original_name = uploaded.name
        document.mime_type = getattr(uploaded, 'content_type', '')
        document.size = uploaded.size
        if commit:
            document.save()
            self.save_m2m()
        return document


class CategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'slug', 'description', 'is_active']
        labels = {
            'name': 'Название',
            'slug': 'URL-идентификатор',
            'description': 'Описание',
            'is_active': 'Активна',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_name(self):
        value = normalize_text(self.cleaned_data['name'])
        validate_safe_name(value)
        return value


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category',
            'sku',
            'name',
            'slug',
            'image',
            'description',
            'ingredients',
            'price',
            'weight_grams',
            'stock_status',
            'is_active',
            'is_featured',
        ]
        labels = {
            'category': 'Категория',
            'sku': 'Артикул / SKU',
            'name': 'Название',
            'slug': 'URL-идентификатор',
            'image': 'Изображение',
            'description': 'Описание',
            'ingredients': 'Состав',
            'price': 'Цена',
            'weight_grams': 'Вес, г',
            'stock_status': 'Наличие',
            'is_active': 'Активен',
            'is_featured': 'На главной',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'ingredients': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_name(self):
        value = normalize_text(self.cleaned_data['name'])
        validate_safe_name(value)
        return value

    def clean_sku(self):
        value = normalize_text(self.cleaned_data.get('sku'))
        if value and not value.replace('-', '').replace('_', '').isalnum():
            raise ValidationError('SKU может содержать буквы, цифры, дефис и подчеркивание.')
        return value.upper() if value else None

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            validate_product_image_extension(image)
            validate_product_image_mime(image)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError('Размер изображения не должен превышать 5 МБ.')
        return image
