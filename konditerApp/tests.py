from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .forms import DocumentUploadForm
from .models import Product, ProductCategory, UserProfile


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
