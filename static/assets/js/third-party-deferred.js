/**
 * Отложенная загрузка аналитики / чатов / метрик (TBT).
 * Вставьте вызовы GTM / Yandex.Metrika в window.__ASCO_LOAD_THIRD_PARTY__ в отдельном шаблоне или здесь.
 */
(function () {
    var loaded = false;
    function loadThirdParty() {
        if (loaded) return;
        loaded = true;
        if (typeof window.__ASCO_LOAD_THIRD_PARTY__ === 'function') {
            try {
                window.__ASCO_LOAD_THIRD_PARTY__();
            } catch (e) {}
        }
    }
    setTimeout(loadThirdParty, 4500);
    ['scroll', 'click', 'touchstart'].forEach(function (ev) {
        window.addEventListener(ev, loadThirdParty, { once: true, passive: true });
    });
})();
