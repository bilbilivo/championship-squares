// SPDX-License-Identifier: MIT
// One push connection, coalesced reads, and polling only while push is unavailable.
class GameSync {
    constructor(applyState, env = globalThis) {
        this.applyState = applyState;
        this.env = env;
        this.active = false;
        this.pendingMutations = 0;
        this.generation = 0;
        this.dirty = false;
        this.loading = false;
        this.timer = null;
        this.source = null;
        this.fallback = null;
        this.onVisibility = () => {
            if (env.document.hidden) this.disconnect();
            else this.connect();
        };
        this.onOnline = () => this.connect();
    }

    start() {
        if (this.active) return;
        this.active = true;
        this.env.document.addEventListener('visibilitychange', this.onVisibility);
        this.env.addEventListener('online', this.onOnline);
        this.connect();
    }

    stop() {
        this.active = false;
        this.generation++;
        this.disconnect();
        this.env.document.removeEventListener('visibilitychange', this.onVisibility);
        this.env.removeEventListener('online', this.onOnline);
    }

    connect() {
        if (!this.active || this.env.document.hidden) return;
        this.refresh();
        if (this.source) return;
        this.startFallback();
        if (!this.env.EventSource) return;
        this.source = new this.env.EventSource('/api/events');
        this.source.addEventListener('game-updated', () => this.refresh());
        this.source.onopen = () => {
            this.env.clearInterval(this.fallback);
            this.fallback = null;
            this.refresh(); // Catch up after reconnect, including a server restart.
        };
        this.source.onerror = () => this.startFallback();
    }

    disconnect() {
        this.source?.close();
        this.source = null;
        this.env.clearInterval(this.fallback);
        this.fallback = null;
        this.env.clearTimeout(this.timer);
        this.timer = null;
    }

    startFallback() {
        if (this.fallback === null) {
            this.fallback = this.env.setInterval(() => this.refresh(), 5000);
        }
    }

    beginMutation() {
        this.pendingMutations++;
        this.generation++;
        return () => {
            this.pendingMutations--;
            this.refresh();
        };
    }

    async mutate(operation) {
        const finish = this.beginMutation();
        try {
            return await operation();
        } finally {
            finish();
        }
    }

    refresh() {
        this.dirty = true;
        if (!this.active || this.env.document.hidden || this.loading ||
            this.pendingMutations || this.timer !== null) return;
        this.timer = this.env.setTimeout(() => {
            this.timer = null;
            this.load();
        }, 40);
    }

    async load() {
        if (!this.active || this.env.document.hidden || this.pendingMutations) return;
        this.loading = true;
        this.dirty = false;
        const generation = this.generation;
        const controller = new this.env.AbortController();
        const timeout = this.env.setTimeout(() => controller.abort(), 10000);
        let failed = false;
        try {
            const response = await this.env.fetch('/api/state', {
                cache: 'no-store', signal: controller.signal
            });
            if (!response.ok) throw new Error(`State request failed: ${response.status}`);
            const data = await response.json();
            if (this.active && !this.env.document.hidden &&
                generation === this.generation && !this.pendingMutations) {
                this.applyState(data);
            } else {
                this.dirty = true;
            }
        } catch (error) {
            failed = true;
            this.env.console.error('Unable to sync game:', error);
        } finally {
            this.env.clearTimeout(timeout);
            this.loading = false;
            if (failed && this.active && !this.env.document.hidden) {
                this.timer = this.env.setTimeout(() => {
                    this.timer = null;
                    this.refresh();
                }, 5000);
            } else if (this.dirty) {
                this.refresh();
            }
        }
    }
}

if (typeof module !== 'undefined') module.exports = GameSync;
