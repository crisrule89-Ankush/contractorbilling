(function () {
    const hiddenFields = window.hiddenFormFields || [];
    const settings = window.formFieldSettings || {};

    // Hide fields switched off in Field Manager.
    hiddenFields.forEach(fieldName => {
        document.querySelectorAll(`[name="${fieldName}"]`).forEach(field => {
            const container = field.closest('.mb-3');
            if (container) {
                container.classList.add('d-none');
            }
        });
    });

    // Copy the identity and styling of the control being replaced.
    function carryOver(source, target) {
        if (source.id) target.id = source.id;
        target.name = source.name;
        if (source.disabled) target.disabled = true;
        if (source.readOnly) target.readOnly = true;
        if (source.required) target.required = true;
        if (source.title) target.title = source.title;
        const cls = source.className.replace(/form-select|form-control/g, '').trim();
        target.className = ((target.tagName === 'SELECT' ? 'form-select ' : 'form-control ') + cls).trim();
    }

    function buildSelect(source, options) {
        const select = document.createElement('select');
        carryOver(source, select);
        const blank = document.createElement('option');
        blank.value = '';
        select.appendChild(blank);
        options.forEach(text => {
            const opt = document.createElement('option');
            opt.value = text;
            opt.textContent = text;
            select.appendChild(opt);
        });
        // Keep the current value if it is one of the configured options.
        if (source.value && options.includes(source.value)) {
            select.value = source.value;
        }
        return select;
    }

    function buildInput(source, type) {
        const el = document.createElement(type === 'textarea' ? 'textarea' : 'input');
        carryOver(source, el);
        if (type === 'textarea') {
            el.rows = 2;
        } else {
            el.type = type;
        }
        if (source.value) el.value = source.value;
        return el;
    }

    // Apply the field type chosen in Field Manager to the built-in fields.
    Object.keys(settings).forEach(fieldName => {
        const config = settings[fieldName] || {};
        const type = config.type || 'text';
        const options = config.options || [];

        document.querySelectorAll(`[name="${fieldName}"]`).forEach(field => {
            const tag = field.tagName;
            if (tag !== 'INPUT' && tag !== 'SELECT' && tag !== 'TEXTAREA') return;
            if (field.type === 'hidden') return;

            let replacement = null;
            if (type === 'dropdown') {
                // Nothing to choose from means leave the existing control alone.
                if (!options.length) return;
                replacement = buildSelect(field, options);
            } else if (tag === 'SELECT' || tag === 'TEXTAREA' || field.type !== type) {
                replacement = buildInput(field, type);
            }

            if (replacement) {
                field.replaceWith(replacement);
            }
        });
    });
})();
