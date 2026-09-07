// SPDX-License-Identifier: MIT
// Attach a session-bound CSRF token only to same-origin mutations.
(() => {
    const originalFetch = window.fetch.bind(window);
    let token = document.querySelector('meta[name="csrf-token"]')?.content;
    window.gameConnection = {public: document.documentElement.dataset.public === 'true'};
    window.fetch = async (input, options = {}) => {
        const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url, location.href);
        const method = (options.method || input.method || 'GET').toUpperCase();
        if (url.origin !== location.origin || ['GET', 'HEAD', 'OPTIONS'].includes(method)) {
            return originalFetch(input, options);
        }
        if (!token) {
            const bootstrap = await originalFetch('/api/csrf', {cache: 'no-store'});
            if (!bootstrap.ok) throw new Error('SESSION UNAVAILABLE');
            token = (await bootstrap.json()).csrf_token;
        }
        const headers = new Headers(options.headers || input.headers);
        headers.set('X-CSRF-Token', token);
        const response = await originalFetch(input, {...options, headers});
        token = response.headers.get('X-CSRF-Token') || token;
        return response;
    };
})();
