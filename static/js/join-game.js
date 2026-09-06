/* SPDX-License-Identifier: MIT */
(() => {
    const button = document.getElementById('joinGameBtn');
    const dialog = document.getElementById('joinGameDialog');
    const status = document.getElementById('joinGameStatus');
    const qr = document.getElementById('joinGameQr');
    const link = document.getElementById('joinGameLink');

    button.addEventListener('click', async () => {
        qr.hidden = true;
        link.hidden = true;
        status.hidden = false;
        status.textContent = 'Loading QR code…';
        dialog.showModal();
        try {
            const response = await fetch('/api/join', { cache: 'no-store' });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Unable to load the QR code. Please try again.');
            qr.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(data.svg)}`;
            link.href = data.url;
            link.textContent = data.url;
            qr.hidden = false;
            link.hidden = false;
            status.hidden = true;
        } catch (error) {
            status.textContent = error.message || 'Unable to load the QR code. Please try again.';
        }
    });
    dialog.addEventListener('click', (event) => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
})();
