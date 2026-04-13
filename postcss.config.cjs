/**
 * Сборка темы: инлайн @import + cssnano.
 * Исходник: static/assets/css/styles.css → static/assets/css/styles.min.css
 * (PurgeCSS опционально: purgecss.config.cjs + npx purgecss --config …)
 */
module.exports = {
    map: false,
    plugins: [
        require('postcss-import'),
        require('autoprefixer'),
        require('cssnano')({
            preset: [
                'default',
                {
                    discardComments: { removeAll: true },
                },
            ],
        }),
    ],
};
