/* ═════════════════════════════════════════════════
   Notsy — App JavaScript
   Features: formatting, auto-links, tags, search
   highlighting, dark mode
   ═════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    // ── Dark mode ─────────────────────────────────
    const themeKey = 'notsy-theme';

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(themeKey, theme);

        // Update toggle icon visibility
        document.querySelectorAll('.dark-mode-icon-moon').forEach(el => {
            el.style.display = theme === 'dark' ? 'none' : 'block';
        });
        document.querySelectorAll('.dark-mode-icon-sun').forEach(el => {
            el.style.display = theme === 'dark' ? 'block' : 'none';
        });
    }

    // Load saved theme or default to light
    const savedTheme = localStorage.getItem(themeKey) || 'light';
    applyTheme(savedTheme);

    document.querySelectorAll('#dark-mode-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const current = document.documentElement.getAttribute('data-theme');
            applyTheme(current === 'dark' ? 'light' : 'dark');
        });
    });


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


    // ── Rich text editor (contenteditable) ─────────
    const richEditor = document.getElementById('rich-content');
    const contentTextarea = document.getElementById('note-content');
    const formattingToolbar = document.getElementById('formatting-toolbar');

    if (richEditor && contentTextarea) {
        // Load existing content into contenteditable
        // Content is already loaded from the template

        // Sync contenteditable back to textarea on form submit
        const noteForm = document.getElementById('note-form');
        if (noteForm) {
            noteForm.addEventListener('submit', () => {
                contentTextarea.value = richEditor.innerHTML;
            });
        }

        // Formatting buttons
        if (formattingToolbar) {
            formattingToolbar.querySelectorAll('.fmt-btn[data-cmd]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const cmd = btn.dataset.cmd;
                    richEditor.focus();
                    document.execCommand(cmd, false, null);
                    updateToolbarState();
                });
            });
        }

        // Keyboard shortcuts for formatting
        richEditor.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key.toLowerCase()) {
                    case 'b':
                        e.preventDefault();
                        document.execCommand('bold', false, null);
                        updateToolbarState();
                        break;
                    case 'i':
                        e.preventDefault();
                        document.execCommand('italic', false, null);
                        updateToolbarState();
                        break;
                    case 'u':
                        e.preventDefault();
                        document.execCommand('underline', false, null);
                        updateToolbarState();
                        break;
                }
            }
        });

        // Update toolbar state on selection changes
        document.addEventListener('selectionchange', () => {
            if (document.activeElement === richEditor) {
                updateToolbarState();
            }
        });

        // Auto-link detection on input
        richEditor.addEventListener('input', () => {
            autoLinkDetection(richEditor);
        });

        // Also run auto-link on paste
        richEditor.addEventListener('paste', (e) => {
            // Allow default paste, then process links after a tick
            setTimeout(() => {
                autoLinkDetection(richEditor);
            }, 50);
        });
    }

    function updateToolbarState() {
        if (!formattingToolbar) return;
        const commands = ['bold', 'italic', 'underline'];
        commands.forEach(cmd => {
            const btn = formattingToolbar.querySelector(`[data-cmd="${cmd}"]`);
            if (btn) {
                btn.classList.toggle('active', document.queryCommandState(cmd));
            }
        });
    }


    // ── Auto-link detection ────────────────────────
    function autoLinkDetection(editor) {
        // Walk all text nodes and find URLs not already inside <a>
        const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, null, false);
        const urlRegex = /(https?:\/\/[^\s<>]+)/g;
        const textNodes = [];

        while (walker.nextNode()) {
            textNodes.push(walker.currentNode);
        }

        textNodes.forEach(node => {
            if (node.parentElement && node.parentElement.tagName === 'A') return;
            const text = node.textContent;
            if (!urlRegex.test(text)) return;

            // Save cursor position
            const selection = window.getSelection();
            const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
            let cursorOffset = null;
            let cursorInThisNode = false;

            if (range && range.startContainer === node) {
                cursorOffset = range.startOffset;
                cursorInThisNode = true;
            }

            urlRegex.lastIndex = 0;
            const fragment = document.createDocumentFragment();
            let lastIndex = 0;
            let match;

            while ((match = urlRegex.exec(text)) !== null) {
                // Text before the URL
                if (match.index > lastIndex) {
                    fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.index)));
                }
                // The URL as a link
                const link = document.createElement('a');
                link.href = match[1];
                link.textContent = match[1];
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                fragment.appendChild(link);

                lastIndex = match.index + match[0].length;
            }

            // Remaining text after last URL
            if (lastIndex < text.length) {
                fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
            }

            if (lastIndex > 0) {
                node.parentNode.replaceChild(fragment, node);
            }
        });
    }


    // ── Editor: Mode toggle (text ↔ checklist) ─────
    const noteTypeInput = document.getElementById('id_note_type');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const modeToggleLabel = document.getElementById('mode-toggle-label');
    const modeToggleIcon = document.getElementById('mode-toggle-icon');
    const textEditor = document.getElementById('text-editor');
    const checklistEditor = document.getElementById('checklist-editor');

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
            if (formattingToolbar) formattingToolbar.style.display = '';
            if (modeToggleLabel) modeToggleLabel.textContent = 'To-do list';
            if (modeToggleIcon) modeToggleIcon.innerHTML = listIcon;
            modeToggleBtn.classList.remove('mode-active');
        } else {
            if (textEditor) textEditor.style.display = 'none';
            if (checklistEditor) checklistEditor.style.display = '';
            if (formattingToolbar) formattingToolbar.style.display = 'none';
            if (modeToggleLabel) modeToggleLabel.textContent = 'Text mode';
            if (modeToggleIcon) modeToggleIcon.innerHTML = textIcon;
            modeToggleBtn.classList.add('mode-active');
        }

        if (noteTypeInput) noteTypeInput.value = currentMode;
    }

    if (modeToggleBtn) {
        updateModeUI();

        modeToggleBtn.addEventListener('click', () => {
            if (currentMode === 'text') {
                // Capture content robustly BEFORE any DOM changes
                const savedHTML = richEditor ? richEditor.innerHTML : '';
                const savedText = richEditor
                    ? (richEditor.textContent || richEditor.innerText || '')
                    : (contentTextarea ? contentTextarea.value : '');

                // Parse lines from HTML (handles <div>, <br>, plain text)
                function extractLines(html, fallbackText) {
                    if (!html.trim()) return [];
                    const tmp = document.createElement('div');
                    tmp.innerHTML = html;
                    tmp.querySelectorAll('br').forEach(br => br.replaceWith('\n'));
                    const blocks = tmp.querySelectorAll('div, p');
                    if (blocks.length > 0) {
                        return Array.from(blocks).map(b => b.textContent.trim()).filter(Boolean);
                    }
                    return fallbackText.split('\n').map(l => l.trim()).filter(Boolean);
                }

                const lines = extractLines(savedHTML, savedText);
                checklistItems = lines.map((line, i) => ({
                    text: line,
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
                if (richEditor) richEditor.innerText = text;
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


    // ── Tag picker ─────────────────────────────────
    const noteTagIds = window.NOTE_TAG_IDS || [];
    // Pre-check tags that are already assigned
    noteTagIds.forEach(id => {
        const chip = document.getElementById(`tag-pick-${id}`);
        if (chip) {
            const checkbox = chip.querySelector('input[type="checkbox"]');
            if (checkbox) checkbox.checked = true;
        }
    });

    // Create new tag
    const addTagBtn = document.getElementById('add-tag-btn');
    if (addTagBtn) {
        addTagBtn.addEventListener('click', async () => {
            const nameInput = document.getElementById('new-tag-name');
            const colorSelect = document.getElementById('new-tag-color');
            const name = nameInput.value.trim();
            const color = colorSelect.value;

            if (!name) return;

            try {
                const formData = new FormData();
                formData.append('name', name);
                formData.append('color', color);

                const res = await fetch('/tags/create/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCSRF() },
                    body: formData,
                });

                if (res.ok) {
                    const data = await res.json();
                    // Add the new tag chip
                    const tagsContainer = document.getElementById('tag-picker-tags');
                    const chip = document.createElement('label');
                    chip.className = `tag-picker-chip tag-color-${data.color}`;
                    chip.id = `tag-pick-${data.id}`;
                    chip.innerHTML = `<input type="checkbox" name="note_tags" value="${data.id}" checked><span>${data.name}</span>`;
                    tagsContainer.appendChild(chip);
                    nameInput.value = '';
                } else {
                    const err = await res.json();
                    alert(err.error || 'Failed to create tag.');
                }
            } catch (err) {
                console.error('Tag creation failed:', err);
            }
        });

        // Handle Enter key in tag name input
        const nameInput = document.getElementById('new-tag-name');
        if (nameInput) {
            nameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addTagBtn.click();
                }
            });
        }
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

        // Custom SVG checkbox button
        const checkBtn = document.createElement('button');
        checkBtn.type = 'button';
        checkBtn.className = 'checklist-custom-check' + (item.is_checked ? ' is-checked' : '');
        checkBtn.setAttribute('aria-label', item.is_checked ? 'Uncheck item' : 'Check item');
        checkBtn.innerHTML = item.is_checked
            ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="2" y="2" width="20" height="20" rx="5" fill="var(--coral)" stroke="var(--coral)"/><polyline points="7 12 10.5 15.5 17 8" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`
            : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="2" y="2" width="20" height="20" rx="5" stroke="var(--border-strong, #bbb)" stroke-width="1.8"/></svg>`;

        checkBtn.addEventListener('click', () => {
            checklistItems[index].is_checked = !checklistItems[index].is_checked;
            textInput.classList.toggle('checked-text', checklistItems[index].is_checked);
            // Update icon
            checkBtn.className = 'checklist-custom-check' + (checklistItems[index].is_checked ? ' is-checked' : '');
            checkBtn.innerHTML = checklistItems[index].is_checked
                ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="2" y="2" width="20" height="20" rx="5" fill="var(--coral)" stroke="var(--coral)"/><polyline points="7 12 10.5 15.5 17 8" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`
                : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="2" y="2" width="20" height="20" rx="5" stroke="var(--border-strong, #bbb)" stroke-width="1.8"/></svg>`;
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

        div.appendChild(checkBtn);
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


    // ── Search highlighting ────────────────────────
    const searchQuery = getSearchQuery();
    if (searchQuery && searchQuery.length > 0) {
        document.querySelectorAll('[data-searchable]').forEach(el => {
            highlightText(el, searchQuery);
        });
    }

    function getSearchQuery() {
        const params = new URLSearchParams(window.location.search);
        return params.get('q') || '';
    }

    function highlightText(element, query) {
        if (!query || query.length < 1) return;

        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
        const textNodes = [];
        while (walker.nextNode()) {
            textNodes.push(walker.currentNode);
        }

        const queryLower = query.toLowerCase();

        textNodes.forEach(node => {
            const text = node.textContent;
            const textLower = text.toLowerCase();
            const index = textLower.indexOf(queryLower);
            if (index === -1) return;

            const fragment = document.createDocumentFragment();
            let lastIdx = 0;

            let searchIdx = 0;
            let currentIdx = textLower.indexOf(queryLower, searchIdx);

            while (currentIdx !== -1) {
                // Text before match
                if (currentIdx > lastIdx) {
                    fragment.appendChild(document.createTextNode(text.substring(lastIdx, currentIdx)));
                }

                // Highlighted match
                const mark = document.createElement('mark');
                mark.className = 'search-highlight';
                mark.textContent = text.substring(currentIdx, currentIdx + query.length);
                fragment.appendChild(mark);

                lastIdx = currentIdx + query.length;
                searchIdx = lastIdx;
                currentIdx = textLower.indexOf(queryLower, searchIdx);
            }

            // Remaining text
            if (lastIdx < text.length) {
                fragment.appendChild(document.createTextNode(text.substring(lastIdx)));
            }

            node.parentNode.replaceChild(fragment, node);
        });
    }


    // ── Keyboard shortcut: Ctrl+S to save ──────────
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const form = document.getElementById('note-form');
            if (form) {
                // Sync rich editor content before submit
                if (richEditor && contentTextarea) {
                    contentTextarea.value = richEditor.innerHTML;
                }
                form.submit();
            }
        }
    });


    // ── Auto-link detection for note cards (read-only) ─
    document.querySelectorAll('.note-card-content').forEach(el => {
        linkifyElement(el);
    });

    function linkifyElement(element) {
        const urlRegex = /(https?:\/\/[^\s<>]+)/g;
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
        const textNodes = [];
        while (walker.nextNode()) {
            textNodes.push(walker.currentNode);
        }

        textNodes.forEach(node => {
            if (node.parentElement && node.parentElement.tagName === 'A') return;
            const text = node.textContent;
            if (!urlRegex.test(text)) return;

            urlRegex.lastIndex = 0;
            const fragment = document.createDocumentFragment();
            let lastIndex = 0;
            let match;

            while ((match = urlRegex.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.index)));
                }
                const link = document.createElement('a');
                link.href = match[1];
                link.textContent = match[1];
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.style.color = 'var(--coral)';
                link.style.textDecoration = 'underline';
                link.onclick = (e) => e.stopPropagation();
                fragment.appendChild(link);
                lastIndex = match.index + match[0].length;
            }

            if (lastIndex < text.length) {
                fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
            }

            if (lastIndex > 0) {
                node.parentNode.replaceChild(fragment, node);
            }
        });
    }


    // ── Utility ────────────────────────────────────
    function getCSRF() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

});
