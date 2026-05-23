import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import CategoryForm, DocumentUploadForm, ProductForm
from .models import CustomerRequest, CustomerRequestItem, Order, OrderItem, Product, ProductCategory, Review, UserProfile


class PublicPagesTests(TestCase):
    def test_home_and_catalog_are_available(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('catalog')).status_code, 200)

    def test_catalog_search_filter(self):
        category = ProductCategory.objects.create(name='Торты', slug='cakes')
        Product.objects.create(
            category=category,
            name='Шоколадный торт',
            slug='chocolate-cake',
            description='Торт с шоколадным кремом',
            price=1200,
        )

        response = self.client.get(reverse('catalog'), {'q': 'шоколад'})

        self.assertContains(response, 'Шоколадный торт')


class AccountTests(TestCase):
    def test_registration_creates_customer_profile(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'buyer01',
                'first_name': 'Иван',
                'last_name': 'Петров',
                'email': 'buyer@example.com',
                'phone': '+7 900 000-00-00',
                'password1': 'StrongPass12345',
                'password2': 'StrongPass12345',
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='buyer01')
        self.assertEqual(user.profile.role, UserProfile.Role.CUSTOMER)


class UploadValidationTests(TestCase):
    def test_rejects_unsafe_file_extension(self):
        user = User.objects.create_user(username='buyer', password='StrongPass12345')
        form = DocumentUploadForm(
            data={'title': 'Договор', 'request': ''},
            files={'file': SimpleUploadedFile('script.exe', b'bad', content_type='application/octet-stream')},
            user=user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)


class ProductAdminFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp()
        cls._override_media = override_settings(MEDIA_ROOT=cls._media_root)
        cls._override_media.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override_media.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)

    def setUp(self):
        self.category = ProductCategory.objects.create(name='Торты', slug='cakes')

    def product_data(self, **overrides):
        data = {
            'category': self.category.pk,
            'sku': '',
            'name': 'Торт Прага',
            'slug': '',
            'description': 'Шоколадный торт с кремом',
            'ingredients': '',
            'price': '1200.00',
            'weight_grams': 900,
            'stock_status': Product.StockStatus.AVAILABLE,
            'is_active': 'on',
            'is_featured': '',
        }
        data.update(overrides)
        return data

    def test_product_slug_is_generated_from_cyrillic_name(self):
        form = ProductForm(data=self.product_data())

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(product.slug, 'tort-praga')

    def test_product_name_allows_quotes(self):
        form = ProductForm(data=self.product_data(name='Торт "Прага"'))

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(product.slug, 'tort-praga')

    def test_product_stock_status_defaults_when_missing(self):
        data = self.product_data()
        data.pop('stock_status')
        form = ProductForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(product.stock_status, Product.StockStatus.AVAILABLE)

    def test_product_price_accepts_comma_decimal_separator(self):
        form = ProductForm(data=self.product_data(price='499,99'))

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(product.price, Decimal('499.99'))

    def test_product_image_field_has_image_validation_attrs(self):
        form = ProductForm()
        attrs = form.fields['image'].widget.attrs

        self.assertIn('.jpg', attrs['accept'])
        self.assertIn('jpg', attrs['data-file-extensions'])
        self.assertEqual(attrs['data-max-size'], str(5 * 1024 * 1024))

    def test_product_slug_gets_unique_suffix(self):
        Product.objects.create(category=self.category, name='Торт Прага', description='Первый', price=1000)
        form = ProductForm(data=self.product_data(sku='KND-NEW-001'))

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(product.slug, 'tort-praga-2')

    def test_manual_slug_is_optional_but_validated_when_present(self):
        Product.objects.create(category=self.category, name='Торт Прага', slug='manual-slug', description='Первый', price=1000)
        duplicate = ProductForm(data=self.product_data(name='Другой торт', slug='manual slug'))
        unique = ProductForm(data=self.product_data(name='Другой торт', slug='новый торт'))

        self.assertFalse(duplicate.is_valid())
        self.assertIn('slug', duplicate.errors)
        self.assertTrue(unique.is_valid(), unique.errors)
        self.assertEqual(unique.save().slug, 'novyy-tort')

    def test_product_can_be_created_without_image(self):
        form = ProductForm(data=self.product_data())

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertFalse(product.image)

    def test_product_can_be_created_with_uploaded_image(self):
        image = SimpleUploadedFile(
            'cake.png',
            b'\x89PNG\r\n\x1a\n',
            content_type='image/png',
        )
        form = ProductForm(data=self.product_data(), files={'image': image})

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertTrue(product.image.name.startswith('products/tort-praga/'))

    def test_edit_without_new_image_keeps_existing_image_and_slug(self):
        product = Product.objects.create(
            category=self.category,
            name='Торт Прага',
            slug='old-praga',
            image='catalog/placeholders/praga-cake.png',
            description='Старое описание',
            price=1000,
        )
        form = ProductForm(
            data=self.product_data(name='Торт Прага обновленный', slug='', description='Новое описание'),
            instance=product,
        )

        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.slug, 'old-praga')
        self.assertEqual(updated.image.name, 'catalog/placeholders/praga-cake.png')


class CategoryAdminFormTests(TestCase):
    def test_category_form_does_not_show_slug_field(self):
        form = CategoryForm()

        self.assertNotIn('slug', form.fields)

    def test_category_slug_is_generated_from_name(self):
        form = CategoryForm(data={'name': 'Пирожные', 'description': 'Порционные десерты', 'is_active': 'on'})

        self.assertTrue(form.is_valid(), form.errors)
        category = form.save()
        self.assertEqual(category.slug, 'pirozhnye')

    def test_category_slug_gets_unique_suffix(self):
        ProductCategory.objects.create(name='Пирожные архив', slug='pirozhnye')
        form = CategoryForm(data={'name': 'Пирожные', 'description': '', 'is_active': 'on'})

        self.assertTrue(form.is_valid(), form.errors)
        category = form.save()
        self.assertEqual(category.slug, 'pirozhnye-2')

    def test_existing_category_slug_is_not_changed(self):
        category = ProductCategory.objects.create(name='Старое название', slug='old-category')
        category.name = 'Новое название'
        category.save()

        self.assertEqual(category.slug, 'old-category')


class OrderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='StrongPass12345')
        self.category = ProductCategory.objects.create(name='Торты', slug='cakes')
        self.product = Product.objects.create(
            category=self.category,
            name='Торт Прага',
            slug='praga-test',
            description='Шоколадный торт',
            price=1000,
        )

    def test_order_item_quantity_and_total_are_calculated(self):
        order = Order.objects.create(user=self.user)
        item = OrderItem.objects.create(order=order, product=self.product, quantity=3, price=self.product.price)
        order.recalculate_total()

        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.subtotal, self.product.price * 3)
        self.assertEqual(order.total_price, self.product.price * 3)

    def test_product_order_view_saves_quantity(self):
        self.client.login(username='buyer', password='StrongPass12345')
        response = self.client.post(reverse('order_create', kwargs={'slug': self.product.slug}), {'quantity': 2})

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        item = order.items.get()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(order.total_price, self.product.price * 2)

    def test_request_create_requires_login_on_get(self):
        response = self.client.get(reverse('request_create'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        self.assertIn(reverse('request_create'), response['Location'])

    def test_request_create_requires_login_on_post(self):
        response = self.client.post(
            reverse('request_create'),
            {
                'request_type': CustomerRequest.RequestType.ORDER,
                'product': self.product.pk,
                'quantity': 2,
                'name': 'Иван',
                'email': 'buyer@example.com',
                'phone': '+7 900 000-00-00',
                'message': 'Нужен торт к празднику',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CustomerRequest.objects.count(), 0)
        self.assertEqual(CustomerRequestItem.objects.count(), 0)

    def test_request_create_saves_quantity_and_total(self):
        self.client.login(username='buyer', password='StrongPass12345')
        response = self.client.post(
            reverse('request_create'),
            {
                'request_type': CustomerRequest.RequestType.ORDER,
                'product': self.product.pk,
                'quantity': 3,
                'name': 'Иван',
                'email': 'buyer@example.com',
                'phone': '+7 900 000-00-00',
                'message': 'Нужен торт к празднику',
            },
        )

        self.assertEqual(response.status_code, 302)
        customer_request = CustomerRequest.objects.get(user=self.user)
        request_item = customer_request.items.get()
        self.assertEqual(request_item.product, self.product)
        self.assertEqual(request_item.quantity, 3)
        self.assertEqual(request_item.subtotal, self.product.price * 3)
        self.assertEqual(customer_request.total_price, self.product.price * 3)

    def test_site_admin_requests_shows_request_items(self):
        admin = User.objects.create_user(username='admin', password='StrongPass12345', is_staff=True)
        customer_request = CustomerRequest.objects.create(
            user=self.user,
            product=self.product,
            request_type=CustomerRequest.RequestType.ORDER,
            name='Иван',
            email='buyer@example.com',
            phone='+7 900 000-00-00',
            message='Нужен торт к празднику',
        )
        CustomerRequestItem.objects.create(
            request=customer_request,
            product=self.product,
            quantity=4,
            price=self.product.price,
        )
        self.client.login(username='admin', password='StrongPass12345')

        response = self.client.get(reverse('site_admin_requests'))

        self.assertContains(response, self.product.name)
        self.assertContains(response, '4')
        self.assertContains(response, self.product.price * 4)

    def test_site_admin_catalog_search_is_case_insensitive_for_cyrillic(self):
        admin = User.objects.create_user(username='admin', password='StrongPass12345', is_staff=True)
        self.client.login(username='admin', password='StrongPass12345')

        response = self.client.get(reverse('site_admin_catalog'), {'q': 'торт'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_site_admin_catalog_search_finds_multiple_terms_and_description(self):
        admin = User.objects.create_user(username='admin', password='StrongPass12345', is_staff=True)
        self.client.login(username='admin', password='StrongPass12345')

        response = self.client.get(reverse('site_admin_catalog'), {'q': 'шоколадный прага'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_customer_cannot_open_site_admin_directly(self):
        self.client.login(username='buyer', password='StrongPass12345')
        response = self.client.get(reverse('site_admin_orders'))

        self.assertEqual(response.status_code, 302)

    def test_catalog_order_button_opens_product_page_with_quantity(self):
        response = self.client.get(reverse('catalog'))

        self.assertContains(response, self.product.get_absolute_url())
        self.assertContains(response, 'Выбрать количество')

    def test_order_detail_shows_items_composition(self):
        order = Order.objects.create(user=self.user)
        OrderItem.objects.create(order=order, product=self.product, quantity=2, price=self.product.price)
        order.recalculate_total()
        self.client.login(username='buyer', password='StrongPass12345')

        response = self.client.get(reverse('order_detail', kwargs={'pk': order.pk}))

        self.assertContains(response, 'Состав заказа')
        self.assertContains(response, self.product.name)
        self.assertContains(response, '2')

    def test_header_links_are_role_specific(self):
        admin = User.objects.create_user(username='admin', password='StrongPass12345', is_staff=True)

        anonymous_response = self.client.get(reverse('home'))
        self.assertContains(anonymous_response, 'Отзывы')

        self.client.login(username='buyer', password='StrongPass12345')
        customer_response = self.client.get(reverse('home'))
        self.assertContains(customer_response, 'Кабинет')
        self.assertContains(customer_response, 'Отзывы')
        self.assertNotContains(customer_response, 'Админ-панель')

        self.client.logout()
        self.client.login(username='admin', password='StrongPass12345')
        admin_response = self.client.get(reverse('home'))
        self.assertContains(admin_response, 'Админ-панель')
        self.assertContains(admin_response, 'Отзывы')
        self.assertNotContains(admin_response, 'Кабинет')

    def test_dashboard_shows_review_link_only_for_completed_order_without_review(self):
        done_order = Order.objects.create(user=self.user, status=Order.Status.DONE)
        OrderItem.objects.create(order=done_order, product=self.product, quantity=1, price=self.product.price)
        new_order = Order.objects.create(user=self.user, status=Order.Status.NEW)
        OrderItem.objects.create(order=new_order, product=self.product, quantity=1, price=self.product.price)
        reviewed_order = Order.objects.create(user=self.user, status=Order.Status.DONE)
        Review.objects.create(user=self.user, order=reviewed_order, rating=5, text='Уже оставлен отзыв')
        self.client.login(username='buyer', password='StrongPass12345')

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, reverse('order_review_create', kwargs={'order_pk': done_order.pk}))
        self.assertNotContains(response, reverse('order_review_create', kwargs={'order_pk': new_order.pk}))
        self.assertNotContains(response, reverse('order_review_create', kwargs={'order_pk': reviewed_order.pk}))

    def test_completed_order_review_is_created_pending(self):
        done_order = Order.objects.create(user=self.user, status=Order.Status.DONE)
        self.client.login(username='buyer', password='StrongPass12345')

        response = self.client.post(
            reverse('order_review_create', kwargs={'order_pk': done_order.pk}),
            {'rating': 5, 'text': 'Заказ завершен отлично'},
        )

        self.assertEqual(response.status_code, 302)
        review = Review.objects.get(order=done_order)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.status, Review.Status.PENDING)

    def test_order_review_rejects_foreign_unfinished_and_duplicate_orders(self):
        other = User.objects.create_user(username='other', password='StrongPass12345')
        foreign_order = Order.objects.create(user=other, status=Order.Status.DONE)
        unfinished_order = Order.objects.create(user=self.user, status=Order.Status.NEW)
        reviewed_order = Order.objects.create(user=self.user, status=Order.Status.DONE)
        Review.objects.create(user=self.user, order=reviewed_order, rating=5, text='Первый отзыв уже есть')
        self.client.login(username='buyer', password='StrongPass12345')

        foreign_response = self.client.post(
            reverse('order_review_create', kwargs={'order_pk': foreign_order.pk}),
            {'rating': 5, 'text': 'Чужой заказ'},
        )
        unfinished_response = self.client.post(
            reverse('order_review_create', kwargs={'order_pk': unfinished_order.pk}),
            {'rating': 5, 'text': 'Еще рано оставлять отзыв'},
        )
        duplicate_response = self.client.post(
            reverse('order_review_create', kwargs={'order_pk': reviewed_order.pk}),
            {'rating': 4, 'text': 'Повторный отзыв'},
        )

        self.assertEqual(foreign_response.status_code, 404)
        self.assertEqual(unfinished_response.status_code, 302)
        self.assertEqual(duplicate_response.status_code, 302)
        self.assertFalse(Review.objects.filter(order=unfinished_order).exists())
        self.assertEqual(Review.objects.filter(order=reviewed_order).count(), 1)


class ReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='StrongPass12345')
        self.admin = User.objects.create_user(username='admin', password='StrongPass12345', is_staff=True)

    def test_anonymous_user_cannot_create_review(self):
        response = self.client.post(reverse('review_create'), {'rating': 5, 'text': 'Очень хороший отзыв'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)

    def test_authenticated_user_creates_pending_review(self):
        self.client.login(username='buyer', password='StrongPass12345')
        response = self.client.post(reverse('review_create'), {'rating': 5, 'text': 'Очень вкусные торты'})

        self.assertEqual(response.status_code, 302)
        review = Review.objects.get(user=self.user)
        self.assertEqual(review.status, Review.Status.PENDING)

    def test_public_home_shows_only_approved_reviews(self):
        Review.objects.create(user=self.user, rating=5, text='Опубликованный отзыв', status=Review.Status.APPROVED)
        Review.objects.create(user=self.user, rating=1, text='Скрытый отзыв', status=Review.Status.PENDING)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Опубликованный отзыв')
        self.assertNotContains(response, 'Скрытый отзыв')

    def test_public_reviews_page_shows_only_approved_reviews(self):
        Review.objects.create(user=self.user, rating=5, text='Виден на странице отзывов', status=Review.Status.APPROVED)
        Review.objects.create(user=self.user, rating=2, text='Не прошел модерацию', status=Review.Status.REJECTED)

        response = self.client.get(reverse('reviews'))

        self.assertContains(response, 'Виден на странице отзывов')
        self.assertNotContains(response, 'Не прошел модерацию')

    def test_site_admin_can_update_review_status(self):
        review = Review.objects.create(user=self.user, rating=4, text='Ждет решения модератора')
        self.client.login(username='admin', password='StrongPass12345')
        response = self.client.post(
            reverse('site_admin_review_update', kwargs={'pk': review.pk}),
            {'status': Review.Status.REJECTED, 'moderation_comment': 'Нужно уточнить детали'},
        )

        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.status, Review.Status.REJECTED)
        self.assertEqual(review.moderation_comment, 'Нужно уточнить детали')
