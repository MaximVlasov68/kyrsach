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
                    const safeName = /^[A-Za-zА-Яа-яЁё0-9\s\-'.]+$/;
                    if (!safeName.test(value)) {
                        showHint(field, 'Используйте буквы, цифры, пробелы, дефис, точку или апостроф.');
                        isValid = false;
                    }
                }

                if (field.type === 'file' && field.files.length) {
                    const allowed = ['doc', 'docx', 'pdf', 'xls', 'xlsx', 'odt', 'ods', 'txt', 'rtf', 'csv'];
                    const file = field.files[0];
                    const extension = file.name.split('.').pop().toLowerCase();
                    if (!allowed.includes(extension)) {
                        showHint(field, `Разрешенные форматы: ${allowed.join(', ')}.`);
                        isValid = false;
                    }
                    if (file.size > 10 * 1024 * 1024) {
                        showHint(field, 'Размер файла не должен превышать 10 МБ.');
                        isValid = false;
                    }
                }
            });

            if (!isValid) {
                event.preventDefault();
            }
        });
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
