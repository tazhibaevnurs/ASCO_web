/**
 * Минификация локальных JS для production (PSI «Minify JavaScript»).
 * Запуск: npm run minify:js
 */
const fs = require("fs");
const path = require("path");
const { minify } = require("terser");

const root = path.join(__dirname, "..", "static", "assets", "js");
const files = [
    "custom.js",
    "function.js",
    "base-init.js",
    "third-party-deferred.js",
    "slider-bg.js",
];

async function run() {
    for (const f of files) {
        const input = path.join(root, f);
        if (!fs.existsSync(input)) {
            console.warn("skip (нет файла):", f);
            continue;
        }
        const code = fs.readFileSync(input, "utf8");
        const out = await minify(code, {
            compress: {
                passes: 2,
                drop_debugger: true,
                drop_console: true,
            },
            mangle: true,
            format: { comments: false },
        });
        if (out.error) {
            throw out.error;
        }
        const outName = f.replace(/\.js$/, ".min.js");
        fs.writeFileSync(path.join(root, outName), out.code);
        console.log("OK", f, "->", outName, "(" + Buffer.byteLength(out.code, "utf8") + " B)");
    }
}

run().catch((e) => {
    console.error(e);
    process.exit(1);
});
