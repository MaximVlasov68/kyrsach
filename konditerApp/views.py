from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    CategoryForm,
    CustomerRequestForm,
    DocumentUploadForm,
    ProductForm,
    ProfileForm,
    RegistrationForm,
)
from .models import CustomerRequest, Product, ProductCategory, UploadedDocument, UserProfile
from .services import send_registration_email, send_request_created_email


def get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if user.is_staff or user.is_superuser:
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=['role'])
    return profile


def is_site_admin(user):
    if not user.is_authenticated:
        return False
    return user.is_staff or user.is_superuser or get_profile(user).role == UserProfile.Role.ADMIN


def paginate(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get('page'))


def home(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True).select_related('category')[:6]
    categories = ProductCategory.objects.filter(is_active=True)[:8]
    request_form = CustomerRequestForm()
    return render(
        request,
        'konditerApp/home.html',
        {
            'featured_products': featured_products,
            'categories': categories,
            'request_form': request_form,
        },
    )


def catalog(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = ProductCategory.objects.filter(is_active=True)
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    stock_status = request.GET.get('stock', '').strip()
    sort = request.GET.get('sort', 'name')

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(ingredients__icontains=query)
            | Q(category__name__icontains=query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)
    if stock_status:
        products = products.filter(stock_status=stock_status)

    ordering = {
        'name': 'name',
        'price_asc': 'price',
        'price_desc': '-price',
        'new': '-created_at',
    }.get(sort, 'name')
    products = products.order_by(ordering)

    return render(
        request,
        'konditerApp/catalog.html',
        {
            'products': paginate(request, products, 9),
            'categories': categories,
            'stock_choices': Product.StockStatus.choices,
            'filters': {
                'q': query,
                'category': category_slug,
                'stock': stock_status,
                'sort': sort,
            },
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('category'), slug=slug, is_active=True)
    form = CustomerRequestForm(initial={'product': product, 'request_type': CustomerRequest.RequestType.ORDER})
    return render(request, 'konditerApp/product_detail.html', {'product': product, 'form': form})


def search(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.none()
    requests = CustomerRequest.objects.none()
    if query:
        products = Product.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query)
        ).select_related('category')[:10]
        if is_site_admin(request.user):
            requests = CustomerRequest.objects.filter(
                Q(name__icontains=query) | Q(email__icontains=query) | Q(message__icontains=query)
            )[:10]
    return render(request, 'konditerApp/search.html', {'query': query, 'products': products, 'requests': requests})


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            UserProfile.objects.create(
                user=user,
                role=UserProfile.Role.CUSTOMER,
                phone=form.cleaned_data.get('phone', ''),
            )
            send_registration_email(user)
            login(request, user)
            messages.success(request, 'Регистрация завершена. Добро пожаловать!')
            return redirect('dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard(request):
    if is_site_admin(request.user):
        return redirect('site_admin_dashboard')
    profile = get_profile(request.user)
    requests = CustomerRequest.objects.filter(user=request.user).select_related('product')[:5]
    documents = UploadedDocument.objects.filter(user=request.user)[:5]
    return render(
        request,
        'konditerApp/dashboard/customer.html',
        {'profile': profile, 'requests': requests, 'documents': documents},
    )


@login_required
def profile_edit(request):
    profile = get_profile(request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлен.')
            return redirect('dashboard')
    else:
        form = ProfileForm(instance=profile, user=request.user)
    return render(request, 'konditerApp/dashboard/profile_form.html', {'form': form})


def request_create(request):
    initial = {}
    product_slug = request.GET.get('product')
    if product_slug:
        product = Product.objects.filter(slug=product_slug, is_active=True).first()
        if product:
            initial['product'] = product
            initial['request_type'] = CustomerRequest.RequestType.ORDER

    if request.method == 'POST':
        form = CustomerRequestForm(request.POST)
        if form.is_valid():
            customer_request = form.save(commit=False)
            if request.user.is_authenticated:
                customer_request.user = request.user
            customer_request.save()
            send_request_created_email(customer_request)
            messages.success(request, 'Заявка отправлена. Мы свяжемся с вами после обработки.')
            return redirect('dashboard' if request.user.is_authenticated else 'home')
    else:
        form = CustomerRequestForm(initial=initial)
    return render(request, 'konditerApp/request_form.html', {'form': form})


@login_required
def document_upload(request):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Документ успешно загружен.')
            return redirect('dashboard')
    else:
        form = DocumentUploadForm(user=request.user)
    return render(request, 'konditerApp/dashboard/document_form.html', {'form': form})


@login_required
def document_download(request, pk):
    document = get_object_or_404(UploadedDocument, pk=pk)
    if document.user != request.user and not is_site_admin(request.user):
        raise Http404()
    return FileResponse(document.file.open('rb'), as_attachment=True, filename=document.original_name or document.file.name)


@user_passes_test(is_site_admin)
def site_admin_dashboard(request):
    stats = {
        'users_count': User.objects.count(),
        'products_count': Product.objects.count(),
        'requests_new': CustomerRequest.objects.filter(status=CustomerRequest.Status.NEW).count(),
        'documents_count': UploadedDocument.objects.count(),
    }
    recent_requests = CustomerRequest.objects.select_related('user', 'product')[:8]
    return render(
        request,
        'konditerApp/site_admin/dashboard.html',
        {'stats': stats, 'recent_requests': recent_requests},
    )


@user_passes_test(is_site_admin)
def site_admin_users(request):
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    users = User.objects.select_related('profile').order_by('username')
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query))
    if role:
        users = users.filter(profile__role=role)
    return render(
        request,
        'konditerApp/site_admin/users.html',
        {'users': paginate(request, users), 'query': query, 'role': role, 'roles': UserProfile.Role.choices},
    )


@user_passes_test(is_site_admin)
@require_POST
def site_admin_user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = get_profile(user)
    profile.role = request.POST.get('role', profile.role)
    profile.save(update_fields=['role'])
    user.is_active = request.POST.get('is_active') == 'on'
    user.save(update_fields=['is_active'])
    messages.success(request, 'Пользователь обновлен.')
    return redirect('site_admin_users')


@user_passes_test(is_site_admin)
def site_admin_catalog(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.select_related('category')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    categories = ProductCategory.objects.all()
    return render(
        request,
        'konditerApp/site_admin/catalog.html',
        {'products': paginate(request, products), 'categories': categories, 'query': query},
    )


@user_passes_test(is_site_admin)
def site_admin_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Товар создан.')
            return redirect('site_admin_catalog')
    else:
        form = ProductForm()
    return render(request, 'konditerApp/site_admin/product_form.html', {'form': form, 'title': 'Новый товар'})


@user_passes_test(is_site_admin)
def site_admin_product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Товар обновлен.')
            return redirect('site_admin_catalog')
    else:
        form = ProductForm(instance=product)
    return render(request, 'konditerApp/site_admin/product_form.html', {'form': form, 'title': 'Редактирование товара'})


@user_passes_test(is_site_admin)
def site_admin_category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория создана.')
            return redirect('site_admin_catalog')
    else:
        form = CategoryForm()
    return render(request, 'konditerApp/site_admin/product_form.html', {'form': form, 'title': 'Новая категория'})


@user_passes_test(is_site_admin)
def site_admin_requests(request):
    status = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    requests = CustomerRequest.objects.select_related('user', 'product')
    if status:
        requests = requests.filter(status=status)
    if query:
        requests = requests.filter(Q(name__icontains=query) | Q(email__icontains=query) | Q(message__icontains=query))
    return render(
        request,
        'konditerApp/site_admin/requests.html',
        {
            'requests': paginate(request, requests),
            'status': status,
            'query': query,
            'statuses': CustomerRequest.Status.choices,
        },
    )


@user_passes_test(is_site_admin)
@require_POST
def site_admin_request_update(request, pk):
    customer_request = get_object_or_404(CustomerRequest, pk=pk)
    status = request.POST.get('status')
    if status in CustomerRequest.Status.values:
        customer_request.status = status
        customer_request.admin_comment = request.POST.get('admin_comment', '').strip()
        customer_request.save(update_fields=['status', 'admin_comment', 'updated_at'])
        messages.success(request, 'Заявка обновлена.')
    return redirect('site_admin_requests')


@user_passes_test(is_site_admin)
def site_admin_documents(request):
    query = request.GET.get('q', '').strip()
    documents = UploadedDocument.objects.select_related('user', 'request')
    if query:
        documents = documents.filter(
            Q(title__icontains=query) | Q(original_name__icontains=query) | Q(user__username__icontains=query)
        )
    return render(
        request,
        'konditerApp/site_admin/documents.html',
        {'documents': paginate(request, documents), 'query': query},
    )
