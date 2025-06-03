// convert [r,g,b] (0–1 or 0–255) or [r,g,b,a] into "#rrggbb" or "rgba(r,g,b,a)"
export function arrayToColor(arr) {
    if (!arr) return undefined;
    let [r, g, b, a] = arr;
    // detect normalized 0–1
    if (r <= 1 && g <= 1 && b <= 1) {
        r = Math.round(r * 255);
        g = Math.round(g * 255);
        b = Math.round(b * 255);
    }
    if (a !== undefined) {
        // opacity given
        return `rgba(${r},${g},${b},${a})`;
    }
    // to hex
    const hh = x => x.toString(16).padStart(2, '0');
    return `#${hh(r)}${hh(g)}${hh(b)}`;
}

// Utility for drawing arrows (with head flush against the line)
export function drawArrow(ctx, from, to, color, lineWidth) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const angle = Math.atan2(dy, dx);
    const dist = Math.hypot(dx, dy);

    // cap head length to 30% of the arrow, with a default based on lineWidth
    const defaultHead = lineWidth * 5;
    const headLength = Math.min(defaultHead, dist * 0.3);

    // styling
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'butt';
    ctx.lineJoin = 'miter';

    // 1) draw the full shaft up to the tip
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();

    // 2) draw the head as a filled triangle overlapping the shaft
    ctx.beginPath();
    ctx.moveTo(to.x, to.y);
    ctx.lineTo(
        to.x - headLength * Math.cos(angle - Math.PI / 6),
        to.y - headLength * Math.sin(angle - Math.PI / 6)
    );
    ctx.lineTo(
        to.x - headLength * Math.cos(angle + Math.PI / 6),
        to.y - headLength * Math.sin(angle + Math.PI / 6)
    );
    ctx.closePath();
    ctx.fill();
}

// Utility for drawing simple shapes
export function drawShapeAt(ctx, pos, size, shape, fillColor, strokeColor, lineWidth, rotation = 0) {
    if (shape === 'square') {
        ctx.save();
        ctx.translate(pos.x, pos.y);
        ctx.rotate(rotation + Math.PI / 4);
        ctx.beginPath();
        ctx.rect(-size, -size, 2 * size, 2 * size);
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.lineWidth = lineWidth;
        ctx.strokeStyle = strokeColor;
        ctx.stroke();
        ctx.restore();
    } else if (shape === 'triangle') {
        ctx.save();
        ctx.translate(pos.x, pos.y);
        ctx.rotate(rotation);
        ctx.beginPath();
        for (let i = 0; i < 3; i++) {
            const a = i * 2 * Math.PI / 3;
            const x = size * Math.cos(a);
            const y = size * Math.sin(a);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.lineWidth = lineWidth;
        ctx.strokeStyle = strokeColor;
        ctx.stroke();
        ctx.restore();
    } else {
        // circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, size, 0, 2 * Math.PI);
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.lineWidth = lineWidth;
        ctx.strokeStyle = strokeColor;
        ctx.stroke();
    }
}

// Base class for all map objects
export class MapObject {
    constructor(id, {
        visible = true,
        dim = false,
        alpha = 1,
        color = '#000',
        text = '',
        name = '',
        showName = false,
        showCoordinates = false,
        showTrail = false,
        layer = 1,
    } = {}) {
        this.id = id;
        this.visible = visible;
        this.dim = dim;
        this.alpha = alpha;
        this.color = color;
        this.name = name;
        this.text = text;
        this.showName = showName;
        this.showCoordinates = showCoordinates;
        this.showTrail = showTrail;
        this.trailHistory = [];
        this.layer = layer;
    }

    getAlpha() {
        return this.alpha * (this.dim ? 0.5 : 1);
    }
}

// Point object
export class PointObject extends MapObject {
    constructor(id, {x, y, size = 5, shape = 'circle', ...rest} = {}) {
        super(id, rest);
        this.x = x;
        this.y = y;
        this.size = size;
        this.shape = shape;
    }

    draw(ctx, map) {
        if (!this.visible) return;
        ctx.save();

        const isSelected = map.selectedObjectId === this.id;
        // full opacity if selected
        ctx.globalAlpha = isSelected ? 1 : this.getAlpha();

        // world→canvas
        const pos = map.worldToCanvas(this.x, this.y);
        // bump size when selected
        const drawSize = isSelected ? this.size * 1.5 : this.size;

        if (this.showTrail && this.trailHistory.length > 1) {
            ctx.save();
            ctx.globalAlpha = map.trailsAlpha;              // use the α from Python
            ctx.strokeStyle = this.color;
            ctx.lineWidth = map.globalTrailSize;          // use Python’s line width
            ctx.beginPath();
            const ph = this.trailHistory.map(p => map.worldToCanvas(p.x, p.y));
            ctx.moveTo(ph[0].x, ph[0].y);
            ph.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
            ctx.stroke();
            ctx.restore();
        }


        // draw the point itself
        drawShapeAt(ctx, pos, drawSize, this.shape, this.color, '#000', 1);

        // labels (shifted by drawSize)
        let label = '';
        if (this.showName) label += this.name;
        if (this.showCoordinates) label += ` [${this.x.toFixed(2)},${this.y.toFixed(2)}]`;
        if (label) {
            ctx.font = `${map.globalTextSize}px Arial`;
            ctx.fillStyle = this.color;
            ctx.textAlign = 'center';
            ctx.fillText(label, pos.x, pos.y - drawSize - map.globalTextSize / 2);
        }
        if (this.text) {
            ctx.fillText(this.text, pos.x, pos.y + drawSize + map.globalTextSize);
        }

        // highlight circle
        if (isSelected) {
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, drawSize + 4, 0, 2 * Math.PI);
            ctx.lineWidth = 2;
            ctx.strokeStyle = this.color;
            ctx.stroke();
        }

        ctx.restore();
    }
}

// Agent object with orientation and optional trail
export class AgentObject extends MapObject {
    constructor(id, {
        position = [0, 0],
        psi = 0,
        size = 5,
        shape = 'circle',
        showTrail = false,
        showName = true,
        showCoordinates = false,
        ...rest
    } = {}) {
        super(id, {showTrail, showName, showCoordinates, ...rest});
        this.position = position;
        this.psi = psi;
        this.size = size;
        this.shape = shape;
    }

    draw(ctx, map) {
        if (!this.visible) return;
        ctx.save();

        const isSelected = map.selectedObjectId === this.id;
        ctx.globalAlpha = isSelected ? 1 : this.getAlpha();

        // world→canvas
        const pos = map.worldToCanvas(this.position[0], this.position[1]);
        const drawSize = isSelected ? this.size * 1.5 : this.size;

        if (this.showTrail && this.trailHistory.length > 1) {
            ctx.save();
            ctx.globalAlpha = map.trailsAlpha;              // use the α from Python
            ctx.strokeStyle = this.color;
            ctx.lineWidth = map.globalTrailSize;          // use Python’s line width
            ctx.beginPath();
            const ph = this.trailHistory.map(p => map.worldToCanvas(p.x, p.y));
            ctx.moveTo(ph[0].x, ph[0].y);
            ph.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
            ctx.stroke();
            ctx.restore();
        }


        // 2) heading arrow
        const arrowLenWorld = (this.size * 4) / map.scaleX;
        const arrowEndWorld = [
            this.position[0] + Math.cos(this.psi) * arrowLenWorld,
            this.position[1] + Math.sin(this.psi) * arrowLenWorld
        ];
        const end = map.worldToCanvas(arrowEndWorld[0], arrowEndWorld[1]);
        drawArrow(ctx, pos, end, this.color, Math.max(1, this.size / 5));

        // 3) body
        drawShapeAt(ctx, pos, drawSize, this.shape, this.color, '#000', 1, this.psi);

        // 4) label: always vertically above or below
        if (this.showName || this.showCoordinates) {
            // build text
            let label = '';
            if (this.showName) label += this.name;
            if (this.showCoordinates) {
                label += ` [${this.position[0].toFixed(2)},${this.position[1].toFixed(2)}]`;
            }

            // compute ψ in [0,360)
            const deg = ((this.psi * 180 / Math.PI) + 360) % 360;
            // if ψ∈[0..180), arrow is pointing "upper" half → place label below
            // else → place label above
            const yOffset = (deg < 180)
                ? (drawSize + map.globalTextSize)      // below marker
                : -(drawSize + 2);                     // above marker (small gap)

            ctx.font = `${map.globalTextSize}px Arial`;
            ctx.fillStyle = this.color;
            ctx.textAlign = 'center';
            ctx.fillText(label, pos.x, pos.y + yOffset);
        }

        // 5) optional free‐form text under the body (always below)
        if (this.text) {
            ctx.font = `${map.globalTextSize}px Arial`;
            ctx.fillStyle = this.color;
            ctx.textAlign = 'center';
            ctx.fillText(this.text, pos.x, pos.y + drawSize + map.globalTextSize);
        }

        // 6) highlight if selected
        if (isSelected) {
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, drawSize + 4, 0, 2 * Math.PI);
            ctx.lineWidth = 2;
            ctx.strokeStyle = this.color;
            ctx.stroke();
        }

        ctx.restore();
    }
}

// Vision agent with a field of view
export class VisionAgentObject extends AgentObject {
    constructor(id, {visionRadius = 0, visionFov = Math.PI, ...rest} = {}) {
        super(id, rest);
        this.visionRadius = visionRadius;
        this.visionFov = visionFov;
    }

    draw(ctx, map) {
        if (!this.visible) return;

        // 1) draw the FOV behind everything
        if (this.visionRadius > 0) {
            ctx.save();
            ctx.globalAlpha = this.getAlpha() * 0.3;
            const pos = map.worldToCanvas(this.position[0], this.position[1]);
            const radiusPx = this.visionRadius * map.scaleX;
            const startAngle = -this.psi - this.visionFov / 2;
            const endAngle = -this.psi + this.visionFov / 2;
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
            ctx.arc(pos.x, pos.y, radiusPx, startAngle, endAngle);
            ctx.closePath();
            ctx.fillStyle = this.color;
            ctx.fill();
            ctx.restore();
        }

        // 2) then draw the agent arrow, body, and labels on top
        super.draw(ctx, map);
    }
}

// Vector arrow object
export class VectorObject extends MapObject {
    constructor(id, {origin = [0, 0], vec = [0, 0], thickness = 1, ...rest} = {}) {
        super(id, rest);
        this.origin = origin;
        this.vec = vec;
        this.thickness = thickness;
    }

    draw(ctx, map) {
        if (!this.visible) return;
        ctx.save();
        ctx.globalAlpha = this.getAlpha();
        const start = map.worldToCanvas(this.origin[0], this.origin[1]);
        const end = map.worldToCanvas(this.origin[0] + this.vec[0], this.origin[1] + this.vec[1]);
        drawArrow(ctx, start, end, this.color, this.thickness);
        if (this.showName) {
            const midX = (start.x + end.x) / 2;
            const midY = (start.y + end.y) / 2;
            let angle = Math.atan2(end.y - start.y, end.x - start.x);

            if (angle > Math.PI / 2) angle -= Math.PI;
            if (angle < -Math.PI / 2) angle += Math.PI;
            ctx.save();
            ctx.translate(midX, midY);
            ctx.rotate(angle);
            ctx.font = `${map.globalTextSize}px Arial`;
            ctx.fillStyle = this.color;
            ctx.textAlign = 'center';
            ctx.fillText(this.name, 0, -this.thickness - map.globalTextSize / 2);
            if (this.text) ctx.fillText(this.text, 0, this.thickness + map.globalTextSize);
            ctx.restore();
        }
        ctx.restore();
    }


}

// Coordinate system axes
export class CoordinateSystemObject extends MapObject {
    constructor(id, {
        origin = [0, 0], ex = [1, 0], ey = [0, 1], thickness = 1, colors = {ex: '#f00', ey: '#0f0'}, ...rest
    } = {}) {
        super(id, rest);
        this.origin = origin;
        this.ex = ex;
        this.ey = ey;
        this.thickness = thickness;
        this.colors = colors;
    }

    draw(ctx, map) {
        if (!this.visible) return;
        ctx.save();
        ctx.globalAlpha = this.getAlpha();
        const org = map.worldToCanvas(this.origin[0], this.origin[1]);
        const exEnd = map.worldToCanvas(this.origin[0] + this.ex[0], this.origin[1] + this.ex[1]);
        const eyEnd = map.worldToCanvas(this.origin[0] + this.ey[0], this.origin[1] + this.ey[1]);
        drawArrow(ctx, org, exEnd, this.colors.ex, this.thickness);
        drawArrow(ctx, org, eyEnd, this.colors.ey, this.thickness);
        if (this.showName) {
            ctx.font = `${map.globalTextSize}px Arial`;
            ctx.fillStyle = this.color;
            ctx.textAlign = 'center';
            ctx.fillText(this.name, org.x, org.y + this.thickness + map.globalTextSize);
            if (this.text) ctx.fillText(this.text, org.x, org.y + this.thickness + 2 * map.globalTextSize);
        }
        ctx.restore();
    }
}

// Line segment object
export class LineObject extends MapObject {
    constructor(id, {start, end, thickness = 1, style = 'solid', showName = true, ...rest} = {}) {
        super(id, rest);
        this.start = start;
        this.end = end;
        this.thickness = thickness;
        this.showName = showName;
        this.style = style;
    }

    _resolve(ref, map) {
        if (Array.isArray(ref)) return {x: ref[0], y: ref[1]};
        return null;
    }

    // ── replace the entire draw(...) on LineObject with this ──
    draw(ctx, map) {
        if (!this.visible) return;
        const sCoord = this._resolve(this.start, map);
        const eCoord = this._resolve(this.end, map);
        if (!sCoord || !eCoord) return;
        const s = map.worldToCanvas(sCoord.x, sCoord.y);
        const e = map.worldToCanvas(eCoord.x, eCoord.y);

        ctx.save();
        ctx.globalAlpha = this.getAlpha();
        // ── apply a dash pattern based on style ──
        if (this.style === 'dashed') {
            ctx.setLineDash([5, 5]);
        } else if (this.style === 'dotted') {
            ctx.setLineDash([2, 2]);
        } else { // solid
            ctx.setLineDash([]);
        }

        ctx.lineWidth = this.thickness;
        ctx.strokeStyle = this.color;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(e.x, e.y);
        ctx.stroke();
        ctx.setLineDash([]);  // reset

        // ── upright label ──
        if (this.showName) {
            const midX = 0.5 * (s.x + e.x);
            const midY = 0.5 * (s.y + e.y);
            let ang = Math.atan2(e.y - s.y, e.x - s.x);
            // keep angle within ±90°
            if (ang > Math.PI / 2) ang -= Math.PI;
            if (ang < -Math.PI / 2) ang += Math.PI;

            ctx.save();
            ctx.translate(midX, midY);
            ctx.rotate(ang);
            ctx.font = `${map.globalTextSize}px Arial`;
            ctx.fillStyle = this.color;
            ctx.textAlign = 'center';
            // always draw name above the line
            ctx.fillText(this.name, 0, -this.thickness - map.globalTextSize / 2);
            if (this.text) {
                ctx.fillText(this.text, 0, this.thickness + map.globalTextSize);
            }
            ctx.restore();
        }

        ctx.restore();
    }

}

// Rectangle object
export class RectangleObject extends MapObject {
    constructor(id, {
        mid = [0, 0], width = 1, height = width, fill = null, lineColor = '#000', thickness = 1, ...rest
    } = {}) {
        super(id, rest);
        this.mid = mid;
        this.width = width;
        this.height = height;
        this.fill = fill;
        this.lineColor = lineColor;
        this.thickness = thickness;
    }

    draw(ctx, map) {
        if (!this.visible) return;
        ctx.save();
        ctx.globalAlpha = this.getAlpha();
        const left = this.mid[0] - this.width / 2;
        const top = this.mid[1] + this.height / 2;
        const tl = map.worldToCanvas(left, top);
        const br = map.worldToCanvas(this.mid[0] + this.width / 2, this.mid[1] - this.height / 2);
        const w = Math.abs(br.x - tl.x);
        const h = Math.abs(br.y - tl.y);
        if (this.fill) {
            ctx.fillStyle = this.fill;
            ctx.fillRect(tl.x, tl.y, w, h);
        }
        ctx.lineWidth = this.thickness;
        ctx.strokeStyle = this.lineColor;
        ctx.strokeRect(tl.x, tl.y, w, h);
        ctx.restore();
    }
}

// Circle object
export class CircleObject extends MapObject {
    constructor(id, {mid = [0, 0], diameter = 1, fill = null, lineColor = '#000', thickness = 1, ...rest} = {}) {
        super(id, rest);
        this.mid = mid;
        this.diameter = diameter;
        this.fill = fill;
        this.lineColor = lineColor;
        this.thickness = thickness;
    }

    draw(ctx, map) {
        if (!this.visible) return;
        ctx.save();
        ctx.globalAlpha = this.getAlpha();
        const pos = map.worldToCanvas(this.mid[0], this.mid[1]);
        const radius = (this.diameter * map.scaleX) / 2;
        if (this.fill) {
            ctx.fillStyle = this.fill;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
            ctx.fill();
        }
        ctx.lineWidth = this.thickness;
        ctx.strokeStyle = this.lineColor;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.restore();
    }
}

// Class representing a group of map objects
export class MapObjectGroup {
    constructor(name, parent = null) {
        this.name = name;
        this.parent = parent;
        this.groups = {};
        this.objects = {};
        this.visible = true;
    }

    get fullPath() {
        return this.parent ? `${this.parent.fullPath}/${this.name}` : this.name;
    }

    getEffectiveVisible() {
        return this.visible && (this.parent ? this.parent.getEffectiveVisible() : true);
    }

    addGroup(name) {
        if (!this.groups[name]) {
            this.groups[name] = new MapObjectGroup(name, this);
        }
        return this.groups[name];
    }

    removeGroup(name) {
        delete this.groups[name];
    }

    addObject(obj) {
        this.objects[obj.id] = obj;
    }

    removeObject(id) {
        delete this.objects[id];
    }

    getObject(id) {
        return this.objects[id];
    }
}