$(document).ready(function () {
    const Toast = Swal.mixin({
        toast: true,
        position: "top",
        showConfirmButton: false,
        timer: 2000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.onmouseenter = Swal.stopTimer;
            toast.onmouseleave = Swal.resumeTimer;
        },
    });
    function generateCartId() {
        // Retrieve the value of "cartId" from local storage and assign it to the variable 'ls_cartId'
        const ls_cartId = localStorage.getItem("cartId");

        // Check if the retrieved value is null (i.e., "cartId" does not exist in local storage)
        if (ls_cartId === null) {
            // Initialize an empty string variable 'cartId' to store the new cart ID
            var cartId = "";

            // Loop 10 times to generate a 10-digit random cart ID
            for (var i = 0; i < 10; i++) {
                // Generate a random number between 0 and 9, convert it to an integer, and append it to 'cartId'
                cartId += Math.floor(Math.random() * 10);
            }

            // Store the newly generated 'cartId' in local storage with the key "cartId"
            localStorage.setItem("cartId", cartId);
        }

        // Return the existing cart ID from local storage if it was found, otherwise return the newly generated 'cartId'
        return ls_cartId || cartId;
    }

    $(document).on("click", ".add_to_cart", function () {
        const button_el = $(this);
        const id = button_el.attr("data-id");
        const qty = $(".quantity").val();
        const size = $("input[name='size']:checked").val();
        const color = $("input[name='color']:checked").val();
        const cart_id = generateCartId();

        $.ajax({
            url: "/add_to_cart/",
            data: {
                id: id,
                qty: qty,
                size: size,
                color: color,
                cart_id: cart_id,
            },
            beforeSend: function () {
                button_el.html('Добавление... <i class="fas fa-spinner fa-spin ms-2"></i>');
            },
            success: function (response) {
                if (response.cart_id) {
                    localStorage.setItem("cartId", response.cart_id);
                }
                console.log(response);
                if (typeof window.showToast === 'function') {
                    window.showToast(response.message || 'Добавлено в корзину', 'success');
                } else {
                    Toast.fire({ icon: 'success', title: response.message });
                }
                button_el.html('Добавлено в корзину <i class="fas fa-check-circle ms-2"></i>');
                $(".total_cart_items").text(response.total_cart_items);
                $(".cart-count-badge-mobile").toggle(response.total_cart_items > 0);
                if (window.innerWidth >= 768 && response.total_cart_items !== undefined) {
                    window.dispatchEvent(new CustomEvent("show-mini-cart", {
                        detail: {
                            total_cart_items: response.total_cart_items,
                            cart_sub_total: response.cart_sub_total || "0.00",
                        },
                    }));
                }
            },
            error: function (xhr, status, error) {
                button_el.html('Добавить в корзину <i class="fas fa-shopping-cart ms-2"></i>');

                console.log("Error Status: " + xhr.status); // Logs the status code, e.g., 400
                console.log("Response Text: " + xhr.responseText); // Logs the actual response text (JSON string)

                // Try parsing the JSON response
                try {
                    let errorResponse = JSON.parse(xhr.responseText);
                    console.log("Error Message: " + errorResponse.error); // Logs "Missing required parameters"
                    Toast.fire({
                        icon: "error",
                        title: errorResponse.error,
                    });
                } catch (e) {
                    console.log("Could not parse JSON response");
                }

                // Optionally show an alert or display the error message in the UI
                console.log("Error: " + xhr.status + " - " + error);
            },
        });
    });

    $(document).on("click", ".update_cart_qty", function () {
        const button_el = $(this);
        const update_type = button_el.attr("data-update_type");
        const product_id = button_el.attr("data-product_id");
        const item_id = button_el.attr("data-item_id");
        const cart_id = generateCartId();
        var qty = $(".item-qty-" + item_id).val();

        if (update_type === "increase") {
            $(".item-qty-" + item_id).val(parseInt(qty) + 1);
            qty++;
        } else {
            if (parseInt(qty) <= 1) {
                $(".item-qty-" + item_id).val(1);
                qty = 1;
            } else {
                $(".item-qty-" + item_id).val(parseInt(qty) - 1);
                qty--;
            }
        }

        $.ajax({
            url: "/add_to_cart/",
            data: {
                id: product_id,
                qty: qty,
                cart_id: cart_id,
            },
            beforeSend: function () {
                button_el.html('<i class="fas fa-spinner fa-spin"></i>');
            },
            success: function (response) {
                if (response.cart_id) {
                    localStorage.setItem("cartId", response.cart_id);
                }
                Toast.fire({
                    icon: "success",
                    title: response.message,
                });
                if (update_type === "increase") {
                    button_el.html("+");
                } else {
                    button_el.html("-");
                }
                $(".item_sub_total_" + item_id).text(response.item_sub_total + " сом");
                $(".cart_sub_total").text(response.cart_sub_total + " сом");
            },
            error: function (xhr, status, error) {
                console.log("Error Status: " + xhr.status);
                console.log("Response Text: " + xhr.responseText);
                try {
                    let errorResponse = JSON.parse(xhr.responseText);
                    console.log("Error Message: " + errorResponse.error);
                    alert(errorResponse.error);
                } catch (e) {
                    console.log("Could not parse JSON response");
                }
                console.log("Error: " + xhr.status + " - " + error);
            },
        });
    });

    $(document).on("click", ".delete_cart_item", function () {
        const button_el = $(this);
        const item_id = button_el.attr("data-item_id");
        const product_id = button_el.attr("data-product_id");
        const cart_id = generateCartId();

        $.ajax({
            url: "/delete_cart_item/",
            data: {
                id: product_id,
                item_id: item_id,
                cart_id: cart_id,
            },
            beforeSend: function () {
                button_el.prop("disabled", true).html('<i class="fas fa-spinner fa-spin tw-text-sm"></i>');
            },
            success: function (response) {
                if (typeof window.showToast === 'function') {
                    window.showToast(response.message || 'Товар удалён из корзины', 'success');
                } else {
                    Toast.fire({ icon: 'success', title: response.message });
                }
                $(".total_cart_items").text(response.total_cart_items);
                $(".cart-count-badge-mobile, #cart-count-mobile").toggle(response.total_cart_items > 0);
                $("#cart-heading-count, #cart-items-count").text(response.total_cart_items);
                $(".cart_sub_total").text(response.cart_sub_total);
                $(".item_div_" + item_id).remove();
                if (response.total_cart_items === 0) {
                    window.location.href = "/cart/";
                    return;
                }
                button_el.prop("disabled", false).html('<i class="fas fa-trash tw-text-sm"></i>');
            },
            complete: function () {
                button_el.prop("disabled", false).html('<i class="fas fa-trash tw-text-sm"></i>');
            },
            error: function (xhr, status, error) {
                console.log("Error Status: " + xhr.status);
                console.log("Response Text: " + xhr.responseText);
                try {
                    let errorResponse = JSON.parse(xhr.responseText);
                    console.log("Error Message: " + errorResponse.error);
                    alert(errorResponse.error);
                } catch (e) {
                    console.log("Could not parse JSON response");
                }
                console.log("Error: " + xhr.status + " - " + error);
            },
        });
    });

    const fetchCountry = () => {
        fetch("https://api.ipregistry.co/?key=tryout")
            .then(function (response) {
                return response.json();
            })
            .then(function (payload) {
                console.log(payload.location.country.name + ", " + payload.location.city);
            });
    };
    fetchCountry();

    $(document).on("change", ".search-filter, .category-filter, .rating-filter, input[name='price-filter'], input[name='prices'], input[name='items-display'], .size-filter, .colors-filter", function () {
        if ($("#shop-filters-form").length && $("#shop-filters-form").attr("hx-get")) return;
        let filters = {
            categories: [],
            rating: [],
            colors: [],
            sizes: [],
            prices: "",
            display: "",
            searchFilter: "",
        };

        $(".category-filter:checked").each(function () {
            filters.categories.push($(this).val());
        });

        $(".rating-filter:checked").each(function () {
            filters.rating.push($(this).val());
        });

        $(".size-filter:checked").each(function () {
            filters.sizes.push($(this).val());
        });

        $(".colors-filter:checked").each(function () {
            filters.colors.push($(this).val());
        });

        filters.display = $("input[name='items-display']:checked").val();
        filters.prices = $("input[name='price-filter']:checked").val();
        filters.searchFilter = $("input[name='search-filter']").val();

        console.log(filters);

        $.ajax({
            url: "/filter_products/",
            method: "GET",
            data: filters,
            success: function (response) {
                var target = $("#product-grid").length ? "#product-grid" : "#products-list";
                $(target).html(response.html);
                $(".product_count").html(response.product_count);
            },
            error: function (error) {
                console.log("Error fetching filtered products:", error);
            },
        });
    });

    $(document).on("click", ".reset_shop_filter_btn", function () {
        let filters = {
            categories: [],
            rating: [],
            colors: [],
            sizes: [],
            prices: "",
            display: "",
            searchFilter: "",
        };

        $(".category-filter:checked").each(function () {
            $(this).prop("checked", false);
        });

        $(".rating-filter:checked").each(function () {
            $(this).prop("checked", false);
        });

        $(".size-filter:checked").each(function () {
            $(this).prop("checked", false);
        });

        $(".colors-filter:checked").each(function () {
            $(this).prop("checked", false);
        });

        $("input[name='items-display']").each(function () {
            $(this).prop("checked", false);
        });

        $("input[name='price-filter'], input[name='prices']").each(function () {
            $(this).prop("checked", false);
        });

        $("input[name='search-filter'], input[name='q']").val("");

        if ($("#shop-filters-form").length && $("#shop-filters-form").attr("hx-get") && window.htmx) {
            Toast.fire({ icon: "success", title: "Фильтр успешно сброшен" });
            var url = $("#shop-filters-form").attr("action") || "/shop/";
            var sk = document.getElementById("product-grid-skeleton");
            if (sk) sk.classList.remove("tw-hidden");
            htmx.ajax("GET", url, { target: "#product-grid", swap: "innerHTML", headers: { "HX-Request": "true" } }).then(function () {
                if (sk) sk.classList.add("tw-hidden");
            });
            return;
        }

        Toast.fire({ icon: "success", title: "Фильтр успешно сброшен" });

        $.ajax({
            url: "/filter_products/",
            method: "GET",
            data: filters,
            success: function (response) {
                var target = $("#product-grid").length ? "#product-grid" : "#products-list";
                $(target).html(response.html);
                $(".product_count").html(response.product_count);
            },
            error: function (error) {
                console.log("Error fetching filtered products:", error);
            },
        });
    });
});
