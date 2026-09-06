// SPDX-License-Identifier: MIT
// Keep a bounded number of bursts alive for as long as the celebration is open.
const CelebrationEffects = (() => {
    function fireworks(container, colors, delay = 0, env = globalThis) {
        const bursts = new Set();
        const timers = new Set();
        let stopped = false;

        function later(callback, ms) {
            const timer = env.setTimeout(() => {
                timers.delete(timer);
                callback();
            }, ms);
            timers.add(timer);
        }

        function stop() {
            stopped = true;
            timers.forEach(timer => env.clearTimeout(timer));
            timers.clear();
            bursts.forEach(burst => burst.remove());
            bursts.clear();
        }

        function launch() {
            if (stopped || !container.isConnected) {
                stop();
                return;
            }
            if (!env.document.hidden) {
                const burst = env.document.createElement('div');
                burst.className = 'firework';
                burst.style.left = `${15 + Math.random() * 70}%`;
                burst.style.top = `${15 + Math.random() * 70}%`;
                for (let i = 0; i < 12; i++) {
                    const particle = env.document.createElement('div');
                    const color = colors[i % colors.length];
                    particle.className = 'firework-particle';
                    particle.style.setProperty('--angle', `${i * 30}deg`);
                    particle.style.backgroundColor = color;
                    particle.style.boxShadow = `0 0 6px ${color}, 0 0 12px ${color}`;
                    burst.appendChild(particle);
                }
                container.appendChild(burst);
                bursts.add(burst);
                later(() => {
                    burst.remove();
                    bursts.delete(burst);
                }, 1500);
            }
            later(launch, 700);
        }

        if (delay) later(launch, delay);
        else launch();
        return stop;
    }

    function mount(overlay, colors, env = globalThis) {
        // End Game always starts this effect, including in lite/reduced-motion mode.
        overlay.classList.add('fireworks-playing');
        const cleanup = [
            fireworks(overlay.querySelector('#fireworksLeft'), colors, 0, env),
            fireworks(overlay.querySelector('#fireworksRight'), colors, 200, env)
        ];
        return () => {
            cleanup.forEach(stop => stop());
            overlay.classList.remove('fireworks-playing');
        };
    }

    return { fireworks, mount };
})();

if (typeof module !== 'undefined') module.exports = CelebrationEffects;
