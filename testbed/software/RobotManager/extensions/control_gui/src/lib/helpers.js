export function shadeColor(color, percent) {
    // very minimal RGB-only implementation:
    const num = parseInt(color.slice(1), 16), amt = Math.round(2.55 * percent), R = (num >> 16) + amt,
        G = (num >> 8 & 0x00FF) + amt, B = (num & 0x0000FF) + amt;
    return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 + (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 + (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
}


export function getColor(color) {
    const color_array = _getColor(color);
    return `rgba(${color_array.r}, ${color_array.g}, ${color_array.b}, ${color_array.a})`;
}

function _getColor(color) {
    if (Array.isArray(color)) {
        // Python-style [r, g, b] or [r, g, b, a] with 0–1 values
        const [r, g, b, a = 1] = color;
        return {
            r: Math.round(r * 255),
            g: Math.round(g * 255),
            b: Math.round(b * 255),
            a: a
        };
    } else if (typeof color === 'string') {
        if (color.startsWith('#')) {
            let r, g, b, a = 1;
            if (color.length === 4) {
                // #rgb shorthand
                r = parseInt(color[1] + color[1], 16);
                g = parseInt(color[2] + color[2], 16);
                b = parseInt(color[3] + color[3], 16);
            } else if (color.length === 7) {
                // #rrggbb
                r = parseInt(color.slice(1, 3), 16);
                g = parseInt(color.slice(3, 5), 16);
                b = parseInt(color.slice(5, 7), 16);
            }
            return {r, g, b, a};
        } else if (color.startsWith('rgb')) {
            const match = color.match(/rgba?\(([^)]+)\)/);
            if (match) {
                const parts = match[1].split(',').map(x => parseFloat(x.trim()));
                const [r, g, b, a = 1] = parts;
                return {r, g, b, a};
            }
        }
    }

    throw new Error('Unsupported color format: ' + color);
}

export function interpolateColors(color1, color2, fraction) {
    const c1 = _getColor(color1);
    const c2 = _getColor(color2);

    const r = Math.round(c1.r + (c2.r - c1.r) * fraction);
    const g = Math.round(c1.g + (c2.g - c1.g) * fraction);
    const b = Math.round(c1.b + (c2.b - c1.b) * fraction);
    const a = c1.a + (c2.a - c1.a) * fraction;

    return `rgba(${r}, ${g}, ${b}, ${a.toFixed(3)})`;
}


export function simulateSine(widget, {
    min, max, periodMs, offset = (min + max) / 2, amp = (max - min) / 2
}) {
    let start = performance.now();

    function step(now) {
        const t = (now - start) % periodMs;
        const theta = (2 * Math.PI * t) / periodMs;
        const value = offset + amp * Math.sin(theta);
        widget.update({value});
        requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
}


// export function splitPath(path) {
//     // Remove any leading/trailing slashes
//     path = path.replace(/^\/+|\/+$/g, '');
//     const parts = path.split('/');
//
//     if (!parts.length || parts[0] === '') {
//         return ['', ''];
//     }
//
//     const first = parts[0];
//     const remainder = parts.slice(1).join('/');
//     return [first, remainder];
// }

export function stripId(path, targetId) {
    // Remove leading/trailing slashes
    path = path.replace(/^\/+|\/+$/g, '');
    const parts = path.split('/');

    const index = parts.indexOf(targetId);
    if (index === -1) {
        return null;
    }

    return parts.slice(index + 1).join('/');
}


export function splitPath(path) {
    // Trim leading/trailing slashes, then split on '/'
    const trimmed = path.replace(/^\/+|\/+$/g, '');
    if (trimmed === '') {
        return ["", ""];
    }
    const parts = trimmed.split('/');
    const first = parts[0];
    const remainder = parts.slice(1).join('/');
    return [first, remainder];
}