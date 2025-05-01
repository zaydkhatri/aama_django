// Static/js/product-variants.js

document.addEventListener('DOMContentLoaded', function () {
    // Size selection
    const sizeOptions = document.querySelectorAll('.size-option');
    const selectedSizeInput = document.getElementById('selected-size-id');

    sizeOptions.forEach(option => {
        option.addEventListener('click', function () {
            // Remove active class from all options
            sizeOptions.forEach(opt => opt.classList.remove('active'));

            // Add active class to clicked option
            this.classList.add('active');

            // Update hidden input with selected size ID
            selectedSizeInput.value = this.dataset.sizeId;
        });
    });

    // Fabric selection and color loading
    const fabricSelect = document.getElementById('fabric-select');
    const colorContainer = document.getElementById('color-selection-container');
    const colorOptions = document.getElementById('color-options');
    const selectedColorInput = document.getElementById('selected-color-id');

    if (fabricSelect) {
        fabricSelect.addEventListener('change', function () {
            const fabricId = this.value;

            if (fabricId) {
                // Show color selection container
                colorContainer.style.display = 'block';

                // Fetch colors for selected fabric
                fetch(`/api/fabric/${fabricId}/colors/`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Network response was not ok');
                        }
                        return response.json();
                    })
                    .then(data => {
                        // Clear current options
                        colorOptions.innerHTML = '';

                        // Add new color options
                        if (data.colors && data.colors.length > 0) {
                            data.colors.forEach((color, index) => {
                                const colorStyle = color.color_code ?
                                    `background-color: ${color.color_code};` : '';

                                const colorClass = index === 0 ? 'color-option active' : 'color-option';

                                const colorElement = document.createElement('div');
                                colorElement.className = colorClass;
                                colorElement.dataset.colorId = color.id;
                                colorElement.style = colorStyle;
                                colorElement.title = color.name;

                                // Add click event to the new color option
                                colorElement.addEventListener('click', function () {
                                    document.querySelectorAll('.color-option').forEach(opt => {
                                        opt.classList.remove('active');
                                    });

                                    this.classList.add('active');
                                    selectedColorInput.value = this.dataset.colorId;
                                });

                                colorOptions.appendChild(colorElement);
                            });

                            // Set first color as selected by default
                            if (data.colors.length > 0) {
                                selectedColorInput.value = data.colors[0].id;
                            }
                        } else {
                            colorOptions.innerHTML =
                                '<p class="text-muted">No colors available for this fabric</p>';
                            selectedColorInput.value = '';
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching colors:', error);
                        colorOptions.innerHTML =
                            '<p class="text-danger">Error loading colors. Please try again.</p>';
                    });
            } else {
                // Hide color selection if no fabric selected
                colorContainer.style.display = 'none';
                selectedColorInput.value = '';
            }
        });
    }

    // Quantity buttons
    const minusBtn = document.querySelector('.quantity-btn.minus');
    const plusBtn = document.querySelector('.quantity-btn.plus');
    const quantityInput = document.getElementById('product-quantity');

    if (minusBtn && plusBtn && quantityInput) {
        minusBtn.addEventListener('click', function () {
            let value = parseInt(quantityInput.value);
            if (value > 1) {
                quantityInput.value = value - 1;
            }
        });

        plusBtn.addEventListener('click', function () {
            let value = parseInt(quantityInput.value);
            quantityInput.value = value + 1;
        });

        // Validate input to ensure it's a positive number
        quantityInput.addEventListener('change', function () {
            let value = parseInt(this.value);
            if (isNaN(value) || value < 1) {
                this.value = 1;
            }
        });
    }

    // Product form validation
    const productForm = document.querySelector('.product-options-form');

    if (productForm) {
        productForm.addEventListener('submit', function (event) {
            // Check if fabric is selected when required
            const fabricSelect = document.getElementById('fabric-select');
            if (fabricSelect && fabricSelect.required && !fabricSelect.value) {
                event.preventDefault();
                alert('Please select a fabric.');
                return false;
            }

            // Check if color is selected when available
            const colorInput = document.getElementById('selected-color-id');
            const colorContainer = document.getElementById('color-selection-container');

            if (colorContainer &&
                colorContainer.style.display !== 'none' &&
                (!colorInput.value || colorInput.value === '')) {
                event.preventDefault();
                alert('Please select a color.');
                return false;
            }

            return true;
        });
    }
});