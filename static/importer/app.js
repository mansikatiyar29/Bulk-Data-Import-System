/**
 * Global UI interactivity for the Bulk Data Import System.
 * - Responsive sidebar toggle (hamburger / backdrop)
 * - Animated number counters
 * - Scroll-reveal animations
 * - Toast notifications
 * - Auto-dismissing alerts
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        initSidebar();
        initCounters();
        initReveal();
        initToasts();
        initAutoDismissAlerts();
    });

    /* ================= SIDEBAR ================= */
    function initSidebar() {
        var toggle = document.getElementById('sidebar-toggle');
        var backdrop = document.getElementById('sidebar-backdrop');

        if (!toggle || !backdrop) return;

        var close = function () {
            document.body.classList.remove('sidebar-open');
            toggle.setAttribute('aria-expanded', 'false');
        };
        var open = function () {
            document.body.classList.add('sidebar-open');
            toggle.setAttribute('aria-expanded', 'true');
        };

        toggle.addEventListener('click', function () {
            document.body.classList.contains('sidebar-open') ? close() : open();
        });
        backdrop.addEventListener('click', close);
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') close();
        });

        // Close the drawer after navigating to a page.
        document.querySelectorAll('[data-nav]').forEach(function (link) {
            link.addEventListener('click', close);
        });

        // Re-sync on resize so the drawer is never stuck open on desktop.
        window.addEventListener('resize', function () {
            if (window.innerWidth > 991.98) close();
        });
        window.addEventListener('orientationchange', function () {
            if (window.innerWidth > 991.98) close();
        });
    }

    /* ================= ANIMATED COUNTERS ================= */
    function initCounters() {
        var els = document.querySelectorAll('[data-counter]');
        if (!window.IntersectionObserver || !els.length) return;

        var observer = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                var el = entry.target;
                var target = parseFloat(el.getAttribute('data-counter') || '0');
                var decimals = parseInt(el.getAttribute('data-counter-decimals') || '2', 10);
                var isDecimal = el.getAttribute('data-counter-decimals') !== null;
                var duration = 900;
                var start = null;

                function step(ts) {
                    if (!start) start = ts;
                    var progress = Math.min((ts - start) / duration, 1);
                    // easeOutCubic for a snappy finish
                    var eased = 1 - Math.pow(1 - progress, 3);
                    var val = target * eased;
                    if (isDecimal) {
                        el.textContent = val.toFixed(decimals) + '%';
                    } else {
                        el.textContent = Math.round(val).toLocaleString();
                    }
                    if (progress < 1) requestAnimationFrame(step);
                    else el.textContent = isDecimal
                        ? target.toFixed(decimals) + '%'
                        : target.toLocaleString();
                }
                requestAnimationFrame(step);
                obs.unobserve(el);
            });
        }, { threshold: 0.4 });

        els.forEach(function (el) { observer.observe(el); });
    }

    /* ================= SCROLL REVEAL ================= */
    function initReveal() {
        var els = document.querySelectorAll('.reveal');
        if (!els.length) return;
        if (!window.IntersectionObserver) {
            els.forEach(function (el) { el.classList.add('visible'); });
            return;
        }
        var observer = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('visible');
                obs.unobserve(entry.target);
            });
        }, { threshold: 0.12 });
        els.forEach(function (el) { observer.observe(el); });
    }

    /* ================= TOASTS ================= */
    function initToasts() {
        // Expose a tiny global helper: window.showToast(message, type)
        var container = document.getElementById('toast-container') || document.body;
        window.showToast = function (message, type) {
            type = type || 'info';
            var icons = {
                success: 'bi-check-circle-fill',
                danger: 'bi-exclamation-triangle-fill',
                warning: 'bi-exclamation-triangle-fill',
                info: 'bi-info-circle-fill',
            };
            var colors = {
                success: 'text-success',
                danger: 'text-danger',
                warning: 'text-warning',
                info: 'text-primary',
            };
            var toast = document.createElement('div');
            toast.className = 'toast align-items-center border-0 fade show';
            toast.setAttribute('role', 'alert');
            toast.style.background = '#fff';
            toast.style.boxShadow = '0 8px 25px rgba(0,0,0,0.14)';
            toast.dataset.bsAutoHide = 'true';
            toast.innerHTML =
                '<div class="d-flex">' +
                '<div class="toast-body fw-semibold d-flex align-items-center gap-2">' +
                '<i class="bi ' + (icons[type] || icons.info) + ' ' + (colors[type] || colors.info) + '"></i>' +
                '<span class="small">' + message + '</span>' +
                '</div>' +
                '<button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
                '</div>';
            container.appendChild(toast);
            var bsToast = new bootstrap.Toast(toast, { delay: 3500 });
            toast.addEventListener('hidden.bs.toast', function () { toast.remove(); });
            bsToast.show();
            setTimeout(function () { toast.remove(); }, 4000);
        };
    }

    /* ================= AUTO-DISMISS ALERTS ================= */
    function initAutoDismissAlerts() {
        var alerts = document.querySelectorAll('.alert[data-autodismiss]');
        if (!alerts.length) return;
        alerts.forEach(function (alert) {
            var delay = parseInt(alert.getAttribute('data-autodismiss'), 10) || 5000;
            setTimeout(function () {
                alert.classList.add('fade');
                setTimeout(function () {
                    if (alert.parentNode) alert.remove();
                }, 400);
            }, delay);
        });
    }
})();