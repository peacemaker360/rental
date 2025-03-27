document.addEventListener('DOMContentLoaded', function () {
    // Handle clickable rows
    document.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', function (e) {
            // Don't trigger if clicking buttons/links/forms
            if (!e.target.closest('a, button, .dropdown-menu, form')) {
                window.location.href = this.dataset.href;
            }
        });
    });

    // Initialize tooltips if using Bootstrap tooltips
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});