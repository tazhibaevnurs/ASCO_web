/**
 * Конвертация JPG/PNG из static/assets в WebP (рядом с исходником).
 * Запуск: npm run optimize:images
 */
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const ROOT = path.join(process.cwd(), 'static', 'assets');
const EXTS = new Set(['.jpg', '.jpeg', '.png']);

function walk(dir) {
    const out = [];
    for (const name of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, name.name);
        if (name.isDirectory()) out.push(...walk(p));
        else if (EXTS.has(path.extname(name.name).toLowerCase())) out.push(p);
    }
    return out;
}

async function main() {
    const files = walk(ROOT);
    let n = 0;
    for (const file of files) {
        const buf = fs.readFileSync(file);
        const webpPath = file.replace(/\.(jpe?g|png)$/i, '.webp');
        await sharp(buf).webp({ quality: 82 }).toFile(webpPath);
        n += 1;
        console.log('OK', webpPath);
    }
    console.log('Done, converted:', n, 'file(s).');
}

main().catch((err) => {
    console.error(err);
    process.exit(1);
});
