// SPDX-License-Identifier: MIT
(() => {
    const form = document.getElementById('registrationForm');
    const initialInput = document.getElementById('initial');
    const nameInput = document.getElementById('name');

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const status = document.getElementById('status');
        const button = form.querySelector('button');
        button.disabled = true;
        status.textContent = 'JOINING…';
        try {
            const response = await fetch(`/api/public/register/${encodeURIComponent(form.dataset.registrationToken)}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    initial: initialInput.value.trim().toUpperCase(),
                    name: nameInput.value.trim().toUpperCase()
                })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'TRY AGAIN');
            window.location.replace('/');
        } catch (error) {
            status.textContent = error.message || 'OFFLINE — TRY AGAIN';
            button.disabled = false;
        }
    });
})();
