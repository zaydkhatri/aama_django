// JavaScript for currency selector functionality
document.addEventListener('DOMContentLoaded', function () {
    // Submit currency form when clicking on a currency option
    document.querySelectorAll('.currency-form button').forEach(function (button) {
        button.addEventListener('click', function () {
            this.closest('form').submit();
        });
    });
});