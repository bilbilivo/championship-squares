// SPDX-License-Identifier: MIT
// Present each end-game event once per loaded page and clean up on reset.
class CelebrationSync {
    constructor(openCelebration) {
        this.openCelebration = openCelebration;
        this.initialized = false;
        this.lastSeenId = null;
        this.cleanup = null;
    }

    observe(celebration) {
        const id = celebration?.id || null;
        if (!this.initialized) {
            this.initialized = true;
            this.lastSeenId = id;
            return false;
        }
        if (!id) {
            this.close();
            return false;
        }
        if (id === this.lastSeenId) return false;
        return this.present(celebration);
    }

    present(celebration) {
        const id = celebration?.id;
        if (!id || id === this.lastSeenId) return false;
        this.initialized = true;
        this.lastSeenId = id;
        this.close();
        this.cleanup = this.openCelebration(celebration, () => this.dismiss());
        return true;
    }

    dismiss() {
        this.close();
    }

    close() {
        const cleanup = this.cleanup;
        this.cleanup = null;
        if (typeof cleanup === 'function') cleanup();
    }
}

if (typeof module !== 'undefined') module.exports = CelebrationSync;
