import struct
import zlib
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from konditerApp.models import Product, ProductCategory


CATEGORIES = [
    ('cakes', 'Торты', 'Классические и фирменные торты для праздников и витрины.'),
    ('pastries', 'Пирожные', 'Порционные десерты, эклеры, тарталетки и макаронс.'),
    ('chocolate', 'Шоколад', 'Плиточный шоколад и шоколадные изделия.'),
    ('candies', 'Конфеты', 'Трюфели, пралине и ассорти ручной работы.'),
    ('cookies', 'Печенье', 'Рассыпчатое, овсяное и сдобное печенье.'),
    ('marshmallow', 'Зефир', 'Воздушный зефир на фруктовом пюре.'),
    ('marmalade', 'Мармелад', 'Фруктовый мармелад и желейные сладости.'),
    ('bakery', 'Выпечка', 'Булочки, круассаны, слойки и пряники.'),
    ('gift-sets', 'Подарочные наборы', 'Готовые наборы сладостей для подарков.'),
    ('seasonal', 'Сезонные сладости', 'Коллекции к праздникам и сезонным событиям.'),
]

PRODUCTS = [
    ('KND-CAKE-001', 'Торт "Прага"', 'praga-cake', 'cakes', 'Шоколадный бисквит с нежным кремом и глянцевой глазурью.', 'Мука, яйца, какао, сливочное масло, молоко, сахар', '1350.00', 950, 'available', True, (171, 56, 71)),
    ('KND-CAKE-002', 'Торт "Наполеон"', 'napoleon-cake', 'cakes', 'Слоеный торт с заварным кремом и хрустящей крошкой.', 'Слоеное тесто, молоко, яйца, сливочное масло, сахар', '1190.00', 1000, 'available', True, (211, 151, 64)),
    ('KND-CAKE-003', 'Медовик классический', 'honey-cake', 'cakes', 'Медовые коржи со сметанным кремом и мягкой карамельной нотой.', 'Мед, мука, яйца, сметана, сахар', '980.00', 850, 'preorder', False, (186, 125, 48)),
    ('KND-PAST-001', 'Эклер ванильный', 'vanilla-eclair', 'pastries', 'Заварное пирожное с ванильным кремом и тонкой сахарной глазурью.', 'Заварное тесто, сливки, ваниль, яйца', '145.00', 80, 'available', True, (235, 205, 154)),
    ('KND-PAST-002', 'Макаронс ассорти', 'macarons-assorted', 'pastries', 'Нежные миндальные макаронс с ягодными, фисташковыми и шоколадными начинками.', 'Миндальная мука, белок, сахарная пудра, ганаш', '520.00', 180, 'available', True, (213, 101, 145)),
    ('KND-PAST-003', 'Тарталетка ягодная', 'berry-tartlet', 'pastries', 'Песочная тарталетка с заварным кремом и свежими ягодами.', 'Песочное тесто, крем патисьер, ягоды', '210.00', 120, 'available', False, (174, 44, 75)),
    ('KND-CHOC-001', 'Шоколад молочный с орехами', 'milk-chocolate-nuts', 'chocolate', 'Молочный шоколад с цельным фундуком и мягким сливочным вкусом.', 'Какао-масло, молоко, сахар, фундук', '260.00', 100, 'available', True, (113, 65, 44)),
    ('KND-CHOC-002', 'Шоколад темный 70%', 'dark-chocolate-70', 'chocolate', 'Насыщенный темный шоколад с выраженным какао-профилем.', 'Какао тертое, какао-масло, сахар', '240.00', 90, 'available', False, (55, 38, 31)),
    ('KND-CAND-001', 'Набор трюфелей', 'truffle-set', 'candies', 'Ассорти шоколадных трюфелей с какао, карамелью и кофе.', 'Шоколад, сливки, какао, карамель, кофе', '760.00', 240, 'available', True, (99, 64, 53)),
    ('KND-CAND-002', 'Конфеты пралине', 'praline-candies', 'candies', 'Шоколадные конфеты с ореховой начинкой пралине.', 'Шоколад, фундук, сахар, сливки', '620.00', 220, 'preorder', False, (129, 75, 49)),
    ('KND-COOK-001', 'Овсяное печенье', 'oat-cookies', 'cookies', 'Печенье с овсяными хлопьями, изюмом и легкой коричной нотой.', 'Овсяные хлопья, мука, изюм, корица', '180.00', 250, 'available', True, (193, 140, 76)),
    ('KND-COOK-002', 'Печенье с шоколадной крошкой', 'chocolate-chip-cookies', 'cookies', 'Рассыпчатое печенье с кусочками темного шоколада.', 'Мука, масло, сахар, шоколадная крошка', '220.00', 220, 'available', False, (151, 95, 58)),
    ('KND-ZEF-001', 'Зефир ванильный', 'vanilla-marshmallow', 'marshmallow', 'Классический ванильный зефир на яблочном пюре.', 'Яблочное пюре, сахар, белок, агар-агар, ваниль', '190.00', 180, 'available', True, (244, 230, 220)),
    ('KND-ZEF-002', 'Зефир смородиновый', 'blackcurrant-marshmallow', 'marshmallow', 'Воздушный зефир с ярким вкусом черной смородины.', 'Смородиновое пюре, сахар, белок, агар-агар', '210.00', 180, 'available', False, (112, 61, 115)),
    ('KND-MARM-001', 'Мармелад фруктовый', 'fruit-marmalade', 'marmalade', 'Ассорти мармелада с яблоком, апельсином, вишней и лимоном.', 'Фруктовое пюре, сахар, пектин', '240.00', 200, 'available', True, (222, 118, 45)),
    ('KND-MARM-002', 'Мармелад цитрусовый', 'citrus-marmalade', 'marmalade', 'Кисло-сладкий мармелад с лимоном, лаймом и апельсином.', 'Цитрусовый сок, сахар, пектин', '230.00', 200, 'available', False, (232, 172, 46)),
    ('KND-BAKE-001', 'Имбирные пряники', 'gingerbread-cookies', 'bakery', 'Пряники с имбирем, корицей и аккуратной сахарной росписью.', 'Мука, мед, имбирь, корица, сахарная глазурь', '310.00', 300, 'available', True, (156, 92, 52)),
    ('KND-BAKE-002', 'Круассан миндальный', 'almond-croissant', 'bakery', 'Слоеный круассан с миндальным кремом и лепестками миндаля.', 'Слоеное тесто, миндальный крем, миндаль', '190.00', 95, 'available', False, (207, 155, 84)),
    ('KND-GIFT-001', 'Подарочный набор "Сладкий вечер"', 'sweet-evening-gift-set', 'gift-sets', 'Коробка с трюфелями, макаронс, шоколадом и открыткой.', 'Трюфели, макаронс, шоколад, декоративная упаковка', '1490.00', 650, 'available', True, (143, 45, 63)),
    ('KND-SEAS-001', 'Новогодний набор пряников', 'new-year-gingerbread-set', 'seasonal', 'Праздничный набор расписных имбирных пряников.', 'Пряничное тесто, глазурь, специи', '890.00', 450, 'preorder', True, (29, 118, 111)),
]


class Command(BaseCommand):
    help = 'Заполняет каталог реалистичными тестовыми категориями и товарами.'

    def handle(self, *args, **options):
        categories = {}
        for slug, name, description in CATEGORIES:
            category, _ = ProductCategory.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'description': description, 'is_active': True},
            )
            categories[slug] = category

        created = 0
        updated = 0
        for item in PRODUCTS:
            sku, name, slug, category_slug, description, ingredients, price, weight, status, featured, color = item
            image_path = self._ensure_placeholder(slug, color)
            product, was_created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    'category': categories[category_slug],
                    'sku': sku,
                    'name': name,
                    'description': description,
                    'ingredients': ingredients,
                    'price': price,
                    'weight_grams': weight,
                    'stock_status': status,
                    'is_active': True,
                    'is_featured': featured,
                    'image': image_path,
                },
            )
            created += int(was_created)
            updated += int(not was_created and product.pk is not None)

        self.stdout.write(self.style.SUCCESS(f'Каталог заполнен: создано {created}, обновлено {updated}.'))

    def _ensure_placeholder(self, slug, color):
        relative_path = Path('catalog/placeholders') / f'{slug}.png'
        absolute_path = settings.MEDIA_ROOT / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        if not absolute_path.exists():
            absolute_path.write_bytes(build_png(640, 420, color))
        return str(relative_path).replace('\\', '/')


def build_png(width, height, base_color):
    rows = []
    r, g, b = base_color
    for y in range(height):
        row = bytearray([0])
        light = 1 + (y / height) * 0.28
        for x in range(width):
            accent = 1 + (x / width) * 0.12
            row.extend(
                (
                    min(255, int(r * light * accent)),
                    min(255, int(g * light)),
                    min(255, int(b * light)),
                )
            )
        rows.append(bytes(row))

    raw = b''.join(rows)
    png = b'\x89PNG\r\n\x1a\n'
    png += png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    png += png_chunk(b'IDAT', zlib.compress(raw, 9))
    png += png_chunk(b'IEND', b'')
    return png


def png_chunk(chunk_type, data):
    return (
        struct.pack('>I', len(data))
        + chunk_type
        + data
        + struct.pack('>I', zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )
