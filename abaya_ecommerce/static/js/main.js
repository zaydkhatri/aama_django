(function ($) {
    'use strict';

    /*--------------------------------------------------------------
    # Document Ready
    --------------------------------------------------------------*/
    $(document).ready(function () {
        // Initialize tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Initialize popovers
        var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });

        // Auto-hide alerts after 5 seconds
        setTimeout(function () {
            $('.alert-dismissible').alert('close');
        }, 5000);

        // Back to top button
        $(window).scroll(function () {
            if ($(this).scrollTop() > 300) {
                $('#back-to-top').addClass('active');
            } else {
                $('#back-to-top').removeClass('active');
            }
        });

        // Click event to scroll to top
        $('#back-to-top').on('click', function (e) {
            e.preventDefault();
            $('html, body').animate({ scrollTop: 0 }, 300);
            return false;
        });

        // Initialize Hero Slider if exists
        if ($('.hero-slider').length) {
            new Swiper('.hero-slider', {
                loop: true,
                speed: 800,
                autoplay: {
                    delay: 5000,
                    disableOnInteraction: false,
                },
                pagination: {
                    el: '.swiper-pagination',
                    clickable: true,
                },
                navigation: {
                    nextEl: '.swiper-button-next',
                    prevEl: '.swiper-button-prev',
                },
            });
        }

        // Initialize Product Slider if exists
        if ($('.product-slider').length) {
            new Swiper('.product-slider', {
                slidesPerView: 1,
                spaceBetween: 10,
                pagination: {
                    el: '.swiper-pagination',
                    clickable: true,
                },
                breakpoints: {
                    640: {
                        slidesPerView: 2,
                        spaceBetween: 20,
                    },
                    768: {
                        slidesPerView: 3,
                        spaceBetween: 20,
                    },
                    1024: {
                        slidesPerView: 4,
                        spaceBetween: 30,
                    },
                },
            });
        }

        // Handle quantity input buttons
        $('.quantity-btn').on('click', function () {
            var $button = $(this);
            var $input = $button.parent().find('input');
            var oldValue = parseInt($input.val());
            var newVal = 1;

            if ($button.hasClass('plus')) {
                newVal = oldValue + 1;
            } else {
                if (oldValue > 1) {
                    newVal = oldValue - 1;
                }
            }

            $input.val(newVal);
            $input.trigger('change');
        });

        // Product gallery thumbnail click
        $('.product-gallery-thumb').on('click', function () {
            var imgSrc = $(this).find('img').attr('src');
            $('.product-gallery-main img').attr('src', imgSrc);
            $('.product-gallery-thumb').removeClass('active');
            $(this).addClass('active');
        });

        // Size options click
        $('.size-option').on('click', function () {
            $('.size-option').removeClass('active');
            $(this).addClass('active');
        });

        // Color options click
        $('.color-option').on('click', function () {
            $('.color-option').removeClass('active');
            $(this).addClass('active');
        });

        // Product tabs click
        $('.product-tab-link').on('click', function (e) {
            e.preventDefault();
            var target = $(this).attr('href');
            $('.product-tab-link').removeClass('active');
            $(this).addClass('active');
            $('.product-tab-content').removeClass('active');
            $(target).addClass('active');
        });

        // Rating stars interaction
        $('.rating-star').on('click', function () {
            var value = $(this).data('value');
            $('input[name="rating"]').val(value);
            $('.rating-star').removeClass('active');
            $('.rating-star').each(function () {
                if ($(this).data('value') <= value) {
                    $(this).addClass('active');
                }
            });
        });

        // Payment method selection
        $('.payment-method').on('click', function () {
            $('.payment-method').removeClass('active');
            $(this).addClass('active');
            $(this).find('input[type="radio"]').prop('checked', true);
        });

        // Show/hide shipping address form
        $('#shipping_address_toggle').on('change', function () {
            if ($(this).is(':checked')) {
                $('#shipping_address_form').slideDown();
            } else {
                $('#shipping_address_form').slideUp();
            }
        });

        // Show/hide billing address form
        $('#billing_address_toggle').on('change', function () {
            if ($(this).is(':checked')) {
                $('#billing_address_form').slideDown();
            } else {
                $('#billing_address_form').slideUp();
            }
        });

        // AJAX Add to Cart
        $('.add-to-cart-form').on('submit', function (e) {
            e.preventDefault();
            var form = $(this);
            var url = form.attr('action');
            var btn = form.find('button[type="submit"]');
            var btnText = btn.html();

            btn.html('<i class="fas fa-spinner fa-spin"></i> Adding...');
            btn.prop('disabled', true);

            $.ajax({
                type: "POST",
                url: url,
                data: form.serialize(),
                success: function (data) {
                    if (data.status === 'success') {
                        // Update cart count
                        $('.header-icon .badge').text(data.cart_count);

                        // Show success message
                        showNotification(data.message, 'success');

                        // Reset button
                        btn.html(btnText);
                        btn.prop('disabled', false);
                    } else {
                        // Show error message
                        showNotification(data.message, 'danger');

                        // Reset button
                        btn.html(btnText);
                        btn.prop('disabled', false);
                    }
                },
                error: function () {
                    // Show error message
                    showNotification('An error occurred. Please try again.', 'danger');

                    // Reset button
                    btn.html(btnText);
                    btn.prop('disabled', false);
                }
            });
        });

        // AJAX Add to Wishlist
        $('.add-to-wishlist').on('click', function (e) {
            e.preventDefault();
            var btn = $(this);
            var url = btn.data('url');
            var productId = btn.data('product-id');

            $.ajax({
                type: "POST",
                url: url,
                data: {
                    'product_id': productId,
                    'csrfmiddlewaretoken': $('input[name=csrfmiddlewaretoken]').val()
                },
                success: function (data) {
                    if (data.status === 'success') {
                        // Update wishlist count
                        $('.wishlist-count').text(data.wishlist_count);

                        // Show success message
                        showNotification(data.message, 'success');

                        // Change button style
                        btn.addClass('active');
                    } else {
                        // Show info message
                        showNotification(data.message, 'info');
                    }
                },
                error: function () {
                    // Show error message
                    showNotification('An error occurred. Please try again.', 'danger');
                }
            });
        });

        // AJAX Cart Update
        $('.cart-update-form').on('submit', function (e) {
            e.preventDefault();
            var form = $(this);
            var url = form.attr('action');

            $.ajax({
                type: "POST",
                url: url,
                data: form.serialize(),
                success: function (data) {
                    if (data.status === 'success') {
                        // Update cart totals
                        $('.cart-item-total-' + form.find('input[name="item_id"]').val()).text('$' + data.item_total.toFixed(2));
                        $('.cart-total').text('$' + data.cart_total.toFixed(2));

                        // Show success message
                        showNotification(data.message, 'success');
                    } else {
                        // Show error message
                        showNotification(data.message, 'danger');
                    }
                },
                error: function () {
                    // Show error message
                    showNotification('An error occurred. Please try again.', 'danger');
                }
            });
        });

        // AJAX Apply Coupon
        $('#coupon-form').on('submit', function (e) {
            e.preventDefault();
            var form = $(this);
            var url = form.attr('action');
            var btn = form.find('button[type="submit"]');
            var btnText = btn.html();

            btn.html('<i class="fas fa-spinner fa-spin"></i>');
            btn.prop('disabled', true);

            $.ajax({
                type: "POST",
                url: url,
                data: form.serialize(),
                success: function (data) {
                    if (data.status === 'success') {
                        // Update page with new totals
                        window.location.reload();
                    } else {
                        // Show error message
                        showNotification(data.message, 'danger');

                        // Reset button
                        btn.html(btnText);
                        btn.prop('disabled', false);
                    }
                },
                error: function () {
                    // Show error message
                    showNotification('An error occurred. Please try again.', 'danger');

                    // Reset button
                    btn.html(btnText);
                    btn.prop('disabled', false);
                }
            });
        });
    });

    /*--------------------------------------------------------------
    # Helper Functions
    --------------------------------------------------------------*/
    // Show notification toast
    function showNotification(message, type) {
        var toast = $('<div class="toast align-items-center text-white bg-' + type + ' border-0" role="alert" aria-live="assertive" aria-atomic="true">');
        toast.html('<div class="d-flex"><div class="toast-body">' + message + '</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>');

        $('.toast-container').append(toast);

        var toastElement = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 5000
        });

        toastElement.show();

        // Remove toast after hidden
        toast.on('hidden.bs.toast', function () {
            $(this).remove();
        });
    }

})(jQuery);