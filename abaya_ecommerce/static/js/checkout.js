// static/js/checkout.js

document.addEventListener('DOMContentLoaded', function () {
    // Handle shipping address form visibility
    const shippingAddressChoice = document.querySelectorAll('input[name="shipping_address_choice"]');
    const existingShippingAddress = document.getElementById('existing-shipping-address');
    const newShippingAddress = document.getElementById('new-shipping-address');

    shippingAddressChoice.forEach(function (radio) {
        radio.addEventListener('change', function () {
            if (this.value === 'existing') {
                existingShippingAddress.style.display = 'block';
                newShippingAddress.style.display = 'none';
            } else {
                existingShippingAddress.style.display = 'none';
                newShippingAddress.style.display = 'block';
            }
        });
    });

    // Handle billing address form visibility
    const billingSameAsShipping = document.getElementById('id_billing_same_as_shipping');
    const billingAddressForm = document.getElementById('billing-address-form');

    if (billingSameAsShipping) {
        billingSameAsShipping.addEventListener('change', function () {
            if (this.checked) {
                billingAddressForm.style.display = 'none';
            } else {
                billingAddressForm.style.display = 'block';
            }
        });
    }

    // Handle billing address choice
    const billingAddressChoice = document.querySelectorAll('input[name="billing_address_choice"]');
    const existingBillingAddress = document.getElementById('existing-billing-address');
    const newBillingAddress = document.getElementById('new-billing-address');

    billingAddressChoice.forEach(function (radio) {
        radio.addEventListener('change', function () {
            if (this.value === 'existing') {
                existingBillingAddress.style.display = 'block';
                newBillingAddress.style.display = 'none';
            } else {
                existingBillingAddress.style.display = 'none';
                newBillingAddress.style.display = 'block';
            }
        });
    });

    // Set initial state
    if (document.querySelector('input[name="shipping_address_choice"]:checked')) {
        document.querySelector('input[name="shipping_address_choice"]:checked').dispatchEvent(new Event('change'));
    }

    if (billingSameAsShipping) {
        billingSameAsShipping.dispatchEvent(new Event('change'));
    }

    if (document.querySelector('input[name="billing_address_choice"]:checked')) {
        document.querySelector('input[name="billing_address_choice"]:checked').dispatchEvent(new Event('change'));
    }

    // Handle payment method selection
    const paymentMethods = document.querySelectorAll('.payment-method');

    paymentMethods.forEach(function (method) {
        method.addEventListener('click', function () {
            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;

                paymentMethods.forEach(function (m) {
                    m.classList.remove('active');
                });

                this.classList.add('active');
            }
        });
    });

    // Coupon code form submit via AJAX
    const couponForm = document.getElementById('coupon-form');
    if (couponForm) {
        couponForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(this);
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;

            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            submitButton.disabled = true;

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Reload page to show updated totals
                        window.location.reload();
                    } else {
                        // Display error
                        showNotification(data.message || 'Invalid coupon code', 'danger');
                        submitButton.innerHTML = originalText;
                        submitButton.disabled = false;
                    }
                })
                .catch(error => {
                    showNotification('An error occurred. Please try again.', 'danger');
                    submitButton.innerHTML = originalText;
                    submitButton.disabled = false;
                });
        });
    }

    // Function to show notifications
    function showNotification(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        const container = document.querySelector('.toast-container');
        container.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 5000
        });

        bsToast.show();

        toast.addEventListener('hidden.bs.toast', function () {
            toast.remove();
        });
    }
});