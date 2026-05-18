from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .forms import DocumentUploadForm
from .models import CustomerRequest, CustomerRequestItem, Order, OrderItem, Product, ProductCategory, UserProfile


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

        self.client.login(username='buyer', password='StrongPass12345')
        customer_response = self.client.get(reverse('home'))
        self.assertContains(customer_response, 'Кабинет')
        self.assertNotContains(customer_response, 'Админ-панель')

        self.client.logout()
        self.client.login(username='admin', password='StrongPass12345')
        admin_response = self.client.get(reverse('home'))
        self.assertContains(admin_response, 'Админ-панель')
        self.assertNotContains(admin_response, 'Кабинет')
