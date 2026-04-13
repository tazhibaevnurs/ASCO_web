/**
 * PurgeCSS через API — обход бага CLI с путями на Windows.
 * Запуск: node scripts/run-purgecss.cjs (после npm run build:theme)
 */
const fs = require('fs');
const path = require('path');
const { PurgeCSS } = require('purgecss');

const root = path.resolve(__dirname, '..');
const cssPath = path.join(root, 'static', 'assets', 'css', 'styles.min.css');
const cfg = require(path.join(root, 'purgecss.config.js'));

async function main() {
    const result = await new PurgeCSS().purge({
        content: cfg.content,
        css: [cssPath],
        safelist: cfg.safelist,
    });
    const out = result[0].css;
    fs.writeFileSync(cssPath, out, 'utf8');
    console.log('PurgeCSS OK:', cssPath, 'bytes:', Buffer.byteLength(out, 'utf8'));
}

main().catch(function (err) {
    console.error(err);
    process.exit(1);
});
