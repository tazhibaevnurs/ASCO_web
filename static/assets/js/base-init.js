/**
 * Инициализация после defer-загрузки HTMX и jQuery: тосты Django, HTMX-ошибки,
 * мобильное меню, мини-корзина. Вынесено из base.html для defer у внешних скриптов.
 */
(function () {
    document.body.addEventListener('htmx:responseError', function (evt) {
        var xhr = evt.detail.xhr;
        var status = xhr ? xhr.status : 'unknown';
        if (status === 403 || status === 404 || status >= 500) {
            console.error('[HTMX] Ошибка запроса:', {
                status: status,
                url: evt.detail.requestConfig.pathInfo.requestPath,
                response: xhr ? xhr.responseText : '',
            });
        }
    });

    var messages = typeof window.__DJANGO_MESSAGES__ !== 'undefined' ? window.__DJANGO_MESSAGES__ : [];
    if (messages.length > 0) {
        var icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            danger: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle',
        };
        var colors = {
            success: 'tw-bg-green-50 tw-border-green-200 tw-text-green-800',
            error: 'tw-bg-red-50 tw-border-red-200 tw-text-red-800',
            danger: 'tw-bg-red-50 tw-border-red-200 tw-text-red-800',
            warning: 'tw-bg-amber-50 tw-border-amber-200 tw-text-amber-800',
            info: 'tw-bg-blue-50 tw-border-blue-200 tw-text-blue-800',
        };
        var iconColors = {
            success: 'tw-text-green-500',
            error: 'tw-text-red-500',
            danger: 'tw-text-red-500',
            warning: 'tw-text-amber-500',
            info: 'tw-text-blue-500',
        };
        var container = document.getElementById('django-toasts');
        var containerMobile = document.getElementById('django-toasts-mobile');
        messages.forEach(function (m) {
            var tag = m.tag === 'error' || m.tag === 'danger' ? 'error' : m.tag || 'info';
            var icon = icons[tag] || icons.info;
            var color = colors[tag] || colors.info;
            var iconColor = iconColors[tag] || iconColors.info;
            var text = (m.text || '')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
            var div = document.createElement('div');
            div.className =
                'django-toast tw-pointer-events-auto tw-flex tw-items-start tw-gap-3 tw-p-4 tw-rounded-xl tw-shadow-lg tw-border tw-max-w-sm tw-w-full tw-bg-white ' +
                color;
            div.setAttribute('role', 'alert');
            div.innerHTML =
                '<span class="tw-flex-shrink-0 ' +
                iconColor +
                '"><i class="fas ' +
                icon +
                ' tw-text-xl"></i></span><p class="tw-flex-1 tw-m-0 tw-text-sm tw-font-medium">' +
                text +
                '</p><button type="button" class="django-toast-close tw-flex-shrink-0 tw-p-1 tw-rounded tw-text-gray-400 hover:tw-text-gray-600 tw-bg-transparent tw-border-0 tw-outline-none focus:tw-outline-none focus:tw-ring-0" aria-label="Закрыть">&times;</button>';
            if (!container || !containerMobile) return;
            container.appendChild(div);
            var divMobile = div.cloneNode(true);
            containerMobile.appendChild(divMobile);
            var closeToast = function () {
                [div, divMobile].forEach(function (t) {
                    if (t.parentNode) t.parentNode.removeChild(t);
                });
            };
            div.querySelector('.django-toast-close').addEventListener('click', closeToast);
            divMobile.querySelector('.django-toast-close').addEventListener('click', closeToast);
            setTimeout(closeToast, 5000);
        });
    }

    window.showToast = function (text, tag) {
        var icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            danger: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle',
        };
        var colors = {
            success: 'tw-bg-green-50 tw-border-green-200 tw-text-green-800',
            error: 'tw-bg-red-50 tw-border-red-200 tw-text-red-800',
            danger: 'tw-bg-red-50 tw-border-red-200 tw-text-red-800',
            warning: 'tw-bg-amber-50 tw-border-amber-200 tw-text-amber-800',
            info: 'tw-bg-blue-50 tw-border-blue-200 tw-text-blue-800',
        };
        var iconColors = {
            success: 'tw-text-green-500',
            error: 'tw-text-red-500',
            danger: 'tw-text-red-500',
            warning: 'tw-text-amber-500',
            info: 'tw-text-blue-500',
        };
        var container = document.getElementById('django-toasts');
        var containerMobile = document.getElementById('django-toasts-mobile');
        if (!container || !containerMobile) return;
        tag = tag === 'error' || tag === 'danger' ? 'error' : tag || 'info';
        var icon = icons[tag] || icons.info;
        var color = colors[tag] || colors.info;
        var iconColor = iconColors[tag] || iconColors.info;
        var safeText = (text || '')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
        var div = document.createElement('div');
        div.className =
            'django-toast tw-pointer-events-auto tw-flex tw-items-start tw-gap-3 tw-p-4 tw-rounded-xl tw-shadow-lg tw-border tw-max-w-sm tw-w-full tw-bg-white ' +
            color;
        div.setAttribute('role', 'alert');
        div.innerHTML =
            '<span class="tw-flex-shrink-0 ' +
            iconColor +
            '"><i class="fas ' +
            icon +
            ' tw-text-xl"></i></span><p class="tw-flex-1 tw-mt-0 tw-mb-0 tw-text-sm tw-font-medium">' +
            safeText +
            '</p><button type="button" class="django-toast-close tw-flex-shrink-0 tw-p-1 tw-rounded tw-text-gray-400 hover:tw-text-gray-600 tw-bg-transparent tw-border-0 tw-outline-none focus:tw-outline-none focus:tw-ring-0" aria-label="Закрыть">&times;</button>';
        container.appendChild(div);
        var divMobile = div.cloneNode(true);
        containerMobile.appendChild(divMobile);
        var closeToast = function () {
            [div, divMobile].forEach(function (t) {
                if (t.parentNode) t.parentNode.removeChild(t);
            });
        };
        div.querySelector('.django-toast-close').addEventListener('click', closeToast);
        divMobile.querySelector('.django-toast-close').addEventListener('click', closeToast);
        setTimeout(closeToast, 5000);
    };

    document.body.addEventListener('showWishlistToast', function (e) {
        var d = e.detail;
        if (d && d.text) window.showToast(d.text, d.tag || 'success');
    });
    document.body.addEventListener('wishlistIds', function (e) {
        if (e.detail && Array.isArray(e.detail))
            try {
                localStorage.setItem('wishlist_ids', JSON.stringify(e.detail));
            } catch (err) {}
    });
    if (document.body.getAttribute('data-user-authenticated') !== 'true') {
        try {
            var stored = localStorage.getItem('wishlist_ids');
            if (stored) {
                var arr = JSON.parse(stored);
                if (Array.isArray(arr) && arr.length > 0) {
                    var idsParam = arr.join(',');
                    var syncUrl = document.body.getAttribute('data-sync-wishlist-url');
                    if (syncUrl)
                        fetch(syncUrl + '?ids=' + encodeURIComponent(idsParam), { credentials: 'same-origin' })
                            .then(function (r) {
                                return r.json();
                            })
                            .then(function (data) {
                                if (data.reload) location.reload();
                            });
                }
            }
        } catch (err) {}
    }

    function initMenuAndCart() {
        if (typeof jQuery === 'undefined') return;
        var $ = jQuery;
        $(document).on('click', '.mobile-dropdown-link', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var $link = $(this);
            var $parent = $link.closest('.mobile-dropdown-item');
            var $submenu = $parent.find('.mobile-submenu-list');
            $('.mobile-dropdown-item').not($parent).removeClass('active').find('.mobile-submenu-list').slideUp(300);
            $parent.toggleClass('active');
            $submenu.slideToggle(300);
        });
        $('.mobile-dropdown-item').removeClass('active');
        $('.mobile-submenu-list').hide();

        function showMiniCart(count, total) {
            if (window.innerWidth < 768) return;
            $('#mini-cart-count').text(count);
            $('#mini-cart-total').text(total);
            $('#mini-cart-popup').css('display', 'block').attr('aria-hidden', 'false');
            $('#mini-cart-backdrop').css('display', 'block').attr('aria-hidden', 'false');
        }
        function hideMiniCart() {
            $('#mini-cart-popup').css('display', 'none').attr('aria-hidden', 'true');
            $('#mini-cart-backdrop').css('display', 'none').attr('aria-hidden', 'true');
        }
        $(document).on('click', '.mini-cart-close, #mini-cart-backdrop', hideMiniCart);
        window.addEventListener('show-mini-cart', function (e) {
            showMiniCart(e.detail.total_cart_items, e.detail.cart_sub_total);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMenuAndCart);
    } else {
        initMenuAndCart();
    }
})();
