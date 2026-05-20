document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.querySelector('[data-menu-toggle]');
    const nav = document.querySelector('[data-main-nav]');

    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            nav.classList.toggle('is-open');
        });
    }

    document.querySelectorAll('[data-validate-form]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            let isValid = true;
            clearHints(form);

            form.querySelectorAll('input, textarea, select').forEach((field) => {
                if (field.type === 'hidden' || field.disabled) {
                    return;
                }

                const value = (field.value || '').trim();
                const label = field.closest('.form-field')?.querySelector('span')?.textContent || field.name;

                if (field.required && !value) {
                    showHint(field, `${label} обязательно к заполнению.`);
                    isValid = false;
                    return;
                }

                if (field.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                    showHint(field, 'Введите корректный email.');
                    isValid = false;
                }

                if ((field.name || '').includes('phone') && value && !/^\+?[0-9\s\-()]{7,20}$/.test(value)) {
                    showHint(field, 'Введите корректный телефон.');
                    isValid = false;
                }

                if (['username', 'first_name', 'last_name', 'name', 'title'].includes(field.name) && value) {
                    const safeName = /^[A-Za-zА-Яа-яЁё0-9\s\-'.\"«»]+$/;
                    if (!safeName.test(value)) {
                        showHint(field, 'Используйте буквы, цифры, пробелы, дефис, точку, кавычки или апостроф.');
                        isValid = false;
                    }
                }

                if (field.type === 'file' && field.files.length) {
                    const allowed = (field.dataset.fileExtensions || 'doc,docx,pdf,xls,xlsx,odt,ods,txt,rtf,csv')
                        .split(',')
                        .map((extension) => extension.trim().toLowerCase())
                        .filter(Boolean);
                    const maxSize = Number.parseInt(field.dataset.maxSize || `${10 * 1024 * 1024}`, 10);
                    const maxSizeLabel = field.dataset.maxSizeLabel || '10 МБ';
                    const file = field.files[0];
                    const extension = file.name.split('.').pop().toLowerCase();
                    if (!allowed.includes(extension)) {
                        showHint(field, `Разрешенные форматы: ${allowed.join(', ')}.`);
                        isValid = false;
                    }
                    if (file.size > maxSize) {
                        showHint(field, `Размер файла не должен превышать ${maxSizeLabel}.`);
                        isValid = false;
                    }
                }
            });

            if (!isValid) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll('[data-order-form]').forEach((form) => {
        const quantityInput = form.querySelector('[data-order-quantity]');
        const totalNode = form.querySelector('[data-order-total]');
        const price = Number.parseFloat(form.dataset.price || '0');

        const updateTotal = () => {
            const quantity = Math.max(1, Number.parseInt(quantityInput.value || '1', 10));
            quantityInput.value = quantity;
            totalNode.textContent = `${(price * quantity).toFixed(2)} ₽`;
        };

        if (quantityInput && totalNode) {
            quantityInput.addEventListener('input', updateTotal);
            quantityInput.addEventListener('change', updateTotal);
            updateTotal();
        }
    });
});

function clearHints(form) {
    form.querySelectorAll('.invalid-hint').forEach((hint) => hint.remove());
    form.querySelectorAll('.is-invalid').forEach((field) => field.classList.remove('is-invalid'));
}

function showHint(field, message) {
    field.classList.add('is-invalid');
    const hint = document.createElement('small');
    hint.className = 'invalid-hint';
    hint.textContent = message;
    field.insertAdjacentElement('afterend', hint);
}
