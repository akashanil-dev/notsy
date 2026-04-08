/* ═════════════════════════════════════════════════
   Notsy — App JavaScript
   ═════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    // ── Auto-dismiss toasts ────────────────────────
    document.querySelectorAll('.toast').forEach(toast => {
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    });


    // ── Pin toggle (AJAX) ──────────────────────────
    document.querySelectorAll('.note-pin-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const id = btn.dataset.id;
            try {
                const res = await fetch(`/notes/${id}/pin/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRF(),
                        'Content-Type': 'application/json',
                    },
                });
                if (res.ok) {
                    const data = await res.json();
                    btn.classList.toggle('pinned', data.pinned);
                    const svg = btn.querySelector('svg');
                    svg.setAttribute('fill', data.pinned ? 'currentColor' : 'none');
                    btn.title = data.pinned ? 'Unpin' : 'Pin';
                    setTimeout(() => location.reload(), 300);
                }
            } catch (err) {
                console.error('Pin toggle failed:', err);
            }
        });
    });


    // ── Color picker toggle ────────────────────────
    document.querySelectorAll('.color-trigger').forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            const wrap = trigger.closest('.color-picker-wrap');
            const dropdown = wrap.querySelector('.color-picker-dropdown');
            document.querySelectorAll('.color-picker-dropdown.open').forEach(d => {
                if (d !== dropdown) d.classList.remove('open');
            });
            dropdown.classList.toggle('open');
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.color-picker-dropdown.open').forEach(d => {
            d.classList.remove('open');
        });
    });

    // Color dot click in cards
    document.querySelectorAll('.color-picker-dropdown .color-dot').forEach(dot => {
        dot.addEventListener('click', async (e) => {
            e.stopPropagation();
            e.preventDefault();
            const id = dot.dataset.id;
            const color = dot.dataset.color;

            try {
                const formData = new FormData();
                formData.append('color', color);

                const res = await fetch(`/notes/${id}/color/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCSRF() },
                    body: formData,
                });
                if (res.ok) {
                    const card = document.querySelector(`#note-card-${id}`);
                    card.className = card.className.replace(/note-color-\w+/g, '');
                    card.classList.add(`note-color-${color}`);
                    dot.closest('.color-picker-dropdown').classList.remove('open');
                }
            } catch (err) {
                console.error('Color update failed:', err);
            }
        });
    });


    // ── Editor: Mode toggle (text ↔ checklist) ─────
    const noteTypeInput = document.getElementById('id_note_type');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const modeToggleLabel = document.getElementById('mode-toggle-label');
    const modeToggleIcon = document.getElementById('mode-toggle-icon');
    const textEditor = document.getElementById('text-editor');
    const checklistEditor = document.getElementById('checklist-editor');
    const contentTextarea = document.getElementById('note-content');

    let currentMode = window.INITIAL_NOTE_TYPE || 'text';
    let checklistItems = window.CHECKLIST_INITIAL || [];

    // SVG icons
    const listIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>';
    const textIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="17" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="17" y1="18" x2="3" y2="18"/></svg>';

    function updateModeUI() {
        if (!modeToggleBtn) return;

        if (currentMode === 'text') {
            if (textEditor) textEditor.style.display = '';
            if (checklistEditor) checklistEditor.style.display = 'none';
            modeToggleLabel.textContent = 'Convert to list';
            modeToggleIcon.innerHTML = listIcon;
        } else {
            if (textEditor) textEditor.style.display = 'none';
            if (checklistEditor) checklistEditor.style.display = '';
            modeToggleLabel.textContent = 'Convert to text';
            modeToggleIcon.innerHTML = textIcon;
        }

        if (noteTypeInput) noteTypeInput.value = currentMode;
    }

    if (modeToggleBtn) {
        updateModeUI();

        modeToggleBtn.addEventListener('click', () => {
            if (currentMode === 'text') {
                // Convert text → checklist
                const text = contentTextarea ? contentTextarea.value : '';
                const lines = text.split('\n').filter(l => l.trim() !== '');
                checklistItems = lines.map((line, i) => ({
                    text: line.trim(),
                    is_checked: false,
                    order: i,
                }));
                if (checklistItems.length === 0) {
                    checklistItems.push({ text: '', is_checked: false, order: 0 });
                }
                currentMode = 'checklist';
                renderChecklist();
                updateModeUI();
            } else {
                // Convert checklist → text
                const text = checklistItems
                    .filter(item => item.text.trim() !== '')
                    .map(item => item.text)
                    .join('\n');
                if (contentTextarea) contentTextarea.value = text;
                currentMode = 'text';
                updateModeUI();
            }
        });
    }


    // ── Editor: Color picker ───────────────────────
    const colorInput = document.getElementById('id_color');
    if (colorInput) {
        const currentColor = colorInput.value || 'default';
        document.querySelectorAll('.editor-color-dot').forEach(dot => {
            if (dot.dataset.color === currentColor) dot.classList.add('active');
            dot.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelectorAll('.editor-color-dot').forEach(d => d.classList.remove('active'));
                dot.classList.add('active');
                colorInput.value = dot.dataset.color;
            });
        });
    }


    // ── Checklist editor ───────────────────────────
    const container = document.getElementById('checklist-items');
    const jsonInput = document.getElementById('checklist-items-json');
    const addBtn = document.getElementById('checklist-add-btn');

    function renderChecklist() {
        if (!container) return;
        container.innerHTML = '';
        checklistItems.forEach((item, index) => {
            const el = createChecklistItemEl(item, index);
            container.appendChild(el);
        });
        updateJSON();
    }

    function createChecklistItemEl(item, index) {
        const div = document.createElement('div');
        div.className = 'checklist-item';
        div.draggable = true;
        div.dataset.index = index;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = item.is_checked;
        checkbox.addEventListener('change', () => {
            checklistItems[index].is_checked = checkbox.checked;
            textInput.classList.toggle('checked-text', checkbox.checked);
            updateJSON();
        });

        const textInput = document.createElement('input');
        textInput.type = 'text';
        textInput.value = item.text;
        textInput.placeholder = 'List item...';
        if (item.is_checked) textInput.classList.add('checked-text');
        textInput.addEventListener('input', () => {
            checklistItems[index].text = textInput.value;
            updateJSON();
        });
        textInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                // Insert new item after this one
                checklistItems.splice(index + 1, 0, { text: '', is_checked: false });
                renderChecklist();
                setTimeout(() => {
                    const allInputs = container.querySelectorAll('input[type="text"]');
                    allInputs[index + 1]?.focus();
                }, 30);
            }
            if (e.key === 'Backspace' && textInput.value === '' && checklistItems.length > 1) {
                e.preventDefault();
                checklistItems.splice(index, 1);
                renderChecklist();
                const allInputs = container.querySelectorAll('input[type="text"]');
                const prev = allInputs[Math.max(0, index - 1)];
                prev?.focus();
            }
        });

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'checklist-item-remove';
        removeBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
        removeBtn.addEventListener('click', () => {
            if (checklistItems.length <= 1) {
                checklistItems[0].text = '';
                checklistItems[0].is_checked = false;
                renderChecklist();
                return;
            }
            checklistItems.splice(index, 1);
            renderChecklist();
        });

        div.appendChild(checkbox);
        div.appendChild(textInput);
        div.appendChild(removeBtn);

        // Drag & drop
        div.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', index);
            div.style.opacity = '0.5';
        });
        div.addEventListener('dragend', () => { div.style.opacity = '1'; });
        div.addEventListener('dragover', (e) => {
            e.preventDefault();
            div.style.borderTop = '2px solid var(--coral)';
        });
        div.addEventListener('dragleave', () => { div.style.borderTop = 'none'; });
        div.addEventListener('drop', (e) => {
            e.preventDefault();
            div.style.borderTop = 'none';
            const fromIndex = parseInt(e.dataTransfer.getData('text/plain'));
            if (fromIndex !== index) {
                const [moved] = checklistItems.splice(fromIndex, 1);
                checklistItems.splice(index, 0, moved);
                renderChecklist();
            }
        });

        return div;
    }

    function updateJSON() {
        if (!jsonInput) return;
        jsonInput.value = JSON.stringify(checklistItems.map((item, i) => ({
            text: item.text,
            is_checked: item.is_checked,
            order: i,
        })));
    }

    if (addBtn) {
        addBtn.addEventListener('click', () => {
            checklistItems.push({ text: '', is_checked: false });
            renderChecklist();
            setTimeout(() => {
                const allInputs = container.querySelectorAll('input[type="text"]');
                allInputs[allInputs.length - 1]?.focus();
            }, 30);
        });
    }

    // Initial render if in checklist mode
    if (currentMode === 'checklist' && container) {
        if (checklistItems.length === 0) {
            checklistItems.push({ text: '', is_checked: false });
        }
        renderChecklist();
    }


    // ── Keyboard shortcut: Ctrl+S to save ──────────
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const form = document.getElementById('note-form');
            if (form) form.submit();
        }
    });


    // ── Utility ────────────────────────────────────
    function getCSRF() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

});
