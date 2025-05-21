// convert [r,g,b] (0–1 or 0–255) or [r,g,b,a] into "#rrggbb" or "rgba(r,g,b,a)"
function arrayToColor(arr) {
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
function drawArrow(ctx, from, to, color, lineWidth) {
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
function drawShapeAt(ctx, pos, size, shape, fillColor, strokeColor, lineWidth, rotation = 0) {
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
class MapObject {
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
class PointObject extends MapObject {
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
class AgentObject extends MapObject {
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
class VisionAgentObject extends AgentObject {
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
class VectorObject extends MapObject {
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
class CoordinateSystemObject extends MapObject {
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
class LineObject extends MapObject {
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
class RectangleObject extends MapObject {
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
class CircleObject extends MapObject {
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
class MapObjectGroup {
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

// Main grid map class
class GridMap {
    constructor(mapContainer, canvas, {
        worldW = 10,
        worldH = 10,
        gridSize = 1,
        labelFont = '12px Roboto',
        labelMargin = 40,
        minLabelPx = 50,
        globalPointSize = 1,
        globalAgentSize = 1,
        globalVectorSize = 1,
        globalTrailSize = 1,
        globalTextSize = 12,
        globalLineThickness = 2,
        coordinate_system_size = 1,
    } = {}) {
        if (!mapContainer || !canvas) {
            console.error('GridMap: missing container or canvas');
            return;
        }
        this.mapContainer = mapContainer;
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // ── add these two lines back in ──
        this.objects = {};
        this.groups = {};

        // INITIAL “fake” serverOptions until we get real ones via init
        this.serverOptions = {
            grid: gridSize,
            size: [null, null],
            grid_color: [0.7, 0.7, 0.7],
            ticks_color: [0.7, 0.7, 0.7],
            grid_width: 1,
            major_grid_style: 'dotted',
            minor_grid_style: 'dotted',
            grid_border_width: 0,
        };

        // apply initial view + styling
        this.worldW = worldW;
        this.worldH = worldH;
        this.gridSize = this.serverOptions.grid;
        this.labelFont = labelFont;
        this.labelMargin = labelMargin;
        this.minLabelPx = minLabelPx;
        this.globalPointSize = globalPointSize;
        this.globalAgentSize = globalAgentSize;
        this.globalVectorSize = globalVectorSize;
        this.globalTrailSize = globalTrailSize;
        this.globalTextSize = globalTextSize;
        this.globalLineThickness = globalLineThickness;
        this.coordinate_system_size = coordinate_system_size;

        // initial colors
        this.gridLineColor = arrayToColor(this.serverOptions.grid_color);
        this.tickLabelColor = arrayToColor(this.serverOptions.ticks_color);

        // size & first draw
        this.updateSize();
        this.redraw();

        new ResizeObserver(() => {
            this.updateSize();
            this.redraw();
        }).observe(this.mapContainer);

        // Panning
        this.dragging = false;
        this.startX = 0;
        this.startY = 0;
        this.startOX = 0;
        this.startOY = 0;
        this.mapContainer.style.cursor = 'grab';
        this.mapContainer.addEventListener('mousedown', e => {
            this.dragging = true;
            this.startX = e.clientX;
            this.startY = e.clientY;
            this.startOX = this.offsetX;
            this.startOY = this.offsetY;
            this.mapContainer.style.cursor = 'grabbing';
        });
        window.addEventListener('mousemove', e => {
            if (!this.dragging) return;
            this.offsetX = this.startOX + (e.clientX - this.startX) / this.scaleX;
            this.offsetY = this.startOY - (e.clientY - this.startY) / this.scaleY;
            this.redraw();
        });
        window.addEventListener('mouseup', () => {
            this.dragging = false;
            this.mapContainer.style.cursor = 'grab';
        });

        // Zooming
        this.mapContainer.addEventListener('wheel', e => {
            e.preventDefault();
            const cx = this.cw / 2;
            const cy = this.ch / 2;
            const worldCx = cx / this.scaleX - this.worldW / 2 - this.offsetX;
            const worldCy = this.worldH / 2 - cy / this.scaleY - this.offsetY;
            const factor = 1 - e.deltaY * 0.001;
            this.scaleX *= factor;
            this.scaleY *= factor;
            this.offsetX = this.cw / (2 * this.scaleX) - this.worldW / 2 - worldCx;
            this.offsetY = this.worldH / 2 - (this.ch / (2 * this.scaleY)) - worldCy;
            this.redraw();
        });
    }

    // Group management
    createGroup(path) {
        const parts = Array.isArray(path) ? path : path.split('/');
        let parent = null;
        let group;
        for (let p of parts) {
            if (!parent) {
                if (!this.groups[p]) this.groups[p] = new MapObjectGroup(p, null);
                group = this.groups[p];
            } else {
                if (!parent.groups[p]) parent.groups[p] = new MapObjectGroup(p, parent);
                group = parent.groups[p];
            }
            parent = group;
        }
        return group;
    }

    getGroup(path) {
        const parts = Array.isArray(path) ? path : path.split('/');
        let group = null;
        let parent = null;
        for (let p of parts) {
            if (!parent) {
                group = this.groups[p];
            } else {
                group = parent.groups[p];
            }
            if (!group) return null;
            parent = group;
        }
        return group;
    }

    addObjectToGroup(path, obj) {
        const group = this.createGroup(path);
        group.addObject(obj);
        this.redraw();
    }

    addPointToGroup(path, id, options = {}) {
        const obj = new PointObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    addAgentToGroup(path, id, options = {}) {
        const obj = new AgentObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    addVisionAgentToGroup(path, id, options = {}) {
        const obj = new VisionAgentObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    addVectorToGroup(path, id, options = {}) {
        const obj = new VectorObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    addCoordinateSystemToGroup(path, id, options = {}) {
        const obj = new CoordinateSystemObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    addLineToGroup(path, id, options = {}) {
        const obj = new LineObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    addRectangleToGroup(path, id, options = {}) {
        const obj = new RectangleObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    addCircleToGroup(path, id, options = {}) {
        const obj = new CircleObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    getObjectByPath(fullPath) {
        const parts = fullPath.split('/');
        const id = parts.pop();
        const group = this.getGroup(parts);
        return group ? group.getObject(id) : null;
    }

    setGroupVisibility(path, visible) {
        const group = this.getGroup(path);
        if (group) {
            group.visible = visible;
            this.redraw();
        }
    }

    // Helper to flatten all grouped objects
    _getFlattenedGroupObjects() {
        const result = [];
        const traverse = (grp) => {
            if (grp.getEffectiveVisible()) {
                Object.values(grp.objects).forEach(obj => result.push(obj));
                Object.values(grp.groups).forEach(sub => traverse(sub));
            }
        };
        Object.values(this.groups).forEach(root => traverse(root));
        return result;
    }

    // Update canvas & map size
    updateSize() {
        this.cw = this.mapContainer.clientWidth;
        this.ch = this.mapContainer.clientHeight;
        this.canvas.width = this.cw;
        this.canvas.height = this.ch;
        const s = Math.max(this.cw / this.worldW, this.ch / this.worldH);
        this.scaleX = this.scaleY = s;
        this.offsetX = this.cw / (2 * s) - this.worldW / 2;
        this.offsetY = this.worldH / 2 - this.ch / (2 * s);
    }

    worldToCanvas(x, y) {
        return {
            x: (x + this.worldW / 2 + this.offsetX) * this.scaleX,
            y: (this.worldH / 2 - (y + this.offsetY)) * this.scaleY
        };
    }


    // ─────────────────────────────────────────────────────────────────────────
    // Replace your existing drawGrid with this version: border now drawn
    // just after the grid‐lines and before the labels.
    // ─────────────────────────────────────────────────────────────────────────
    GridMap

    drawGrid = function () {
        const ctx = this.ctx;

        // 1) viewport in world coords
        const wMinX = -this.worldW / 2 - this.offsetX;
        const wMaxX = wMinX + this.cw / this.scaleX;
        const wMaxY = this.worldH / 2 - this.offsetY;
        const wMinY = wMaxY - this.ch / this.scaleY;

        // 2) finite bounds?
        const hasBounds = (
            this.serverOptions.size[0] != null &&
            this.serverOptions.size[1] != null
        );
        const gridMinX = hasBounds ? -this.serverOptions.size[0] / 2 : wMinX;
        const gridMaxX = hasBounds ? this.serverOptions.size[0] / 2 : wMaxX;
        const gridMinY = hasBounds ? -this.serverOptions.size[1] / 2 : wMinY;
        const gridMaxY = hasBounds ? this.serverOptions.size[1] / 2 : wMaxY;

        // 3) how many world‐units between majors so labels ≥ minLabelPx apart
        const pxPerGrid = this.gridSize * this.scaleX;
        const labelStep = Math.max(1, Math.ceil(this.minLabelPx / pxPerGrid));

        // 4) raw major candidates
        const rawMajorsX = new Set(), rawMajorsY = new Set();
        const addMajors = (set, min, max, vMin, vMax) => {
            set.add(0);
            if (hasBounds) {
                set.add(min);
                set.add(max);
            }
            for (let k = 1; ; k++) {
                const v = k * labelStep * this.gridSize;
                const plusOK = hasBounds ? (v < max) : (v <= vMax);
                const minusOK = hasBounds ? (-v > min) : (-v >= vMin);
                if (!plusOK && !minusOK) break;
                if (plusOK) set.add(v);
                if (minusOK) set.add(-v);
            }
        };
        addMajors(rawMajorsX, gridMinX, gridMaxX, wMinX, wMaxX);
        addMajors(rawMajorsY, gridMinY, gridMaxY, wMinY, wMaxY);

        // 5) prune so labels aren’t too close
        const pruneMajors = (rawSet, min, max, mapToPx) => {
            const pts = [...rawSet]
                .filter(v => v >= min && v <= max)
                .map(v => ({v, px: mapToPx(v)}))
                .sort((a, b) => a.px - b.px);
            const kept = [];
            for (let {v, px} of pts) {
                if (!kept.length) {
                    kept.push({v, px});
                    continue;
                }
                const last = kept[kept.length - 1];
                if (Math.abs(px - last.px) < this.minLabelPx) {
                    const isEdgeOrZero = (v === 0 || v === min || v === max);
                    const lastEdgeOrZero = (last.v === 0 || last.v === min || last.v === max);
                    if (isEdgeOrZero && !lastEdgeOrZero) {
                        kept.pop();
                        kept.push({v, px});
                    }
                } else {
                    kept.push({v, px});
                }
            }
            return new Set(kept.map(o => o.v));
        };
        const majorsX = pruneMajors(
            rawMajorsX, gridMinX, gridMaxX,
            v => this.worldToCanvas(v, 0).x
        );
        const majorsY = pruneMajors(
            rawMajorsY, gridMinY, gridMaxY,
            v => this.worldToCanvas(0, v).y
        );

        // 6) draw vertical lines
        const startIdxX = Math.ceil(gridMinX / this.gridSize);
        const endIdxX = Math.floor(gridMaxX / this.gridSize);
        for (let idx = startIdxX; idx <= endIdxX; idx++) {
            const x = idx * this.gridSize;
            if (x < wMinX || x > wMaxX) continue;
            const isMajor = (idx % labelStep === 0);
            ctx.setLineDash(
                isMajor
                    ? (this.serverOptions.major_grid_style === 'dotted' ? [2, 2] : [])
                    : (this.serverOptions.minor_grid_style === 'dotted' ? [2, 2] : [])
            );
            ctx.lineWidth = this.serverOptions.grid_width;
            ctx.strokeStyle = this.gridLineColor;

            const top = this.worldToCanvas(x, gridMaxY);
            const bottom = this.worldToCanvas(x, gridMinY);
            ctx.beginPath();
            ctx.moveTo(top.x, top.y);
            ctx.lineTo(bottom.x, bottom.y);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // 7) draw horizontal lines
        const startIdxY = Math.ceil(gridMinY / this.gridSize);
        const endIdxY = Math.floor(gridMaxY / this.gridSize);
        for (let idx = startIdxY; idx <= endIdxY; idx++) {
            const y = idx * this.gridSize;
            if (y < wMinY || y > wMaxY) continue;
            const isMajor = (idx % labelStep === 0);
            ctx.setLineDash(
                isMajor
                    ? (this.serverOptions.major_grid_style === 'dotted' ? [2, 2] : [])
                    : (this.serverOptions.minor_grid_style === 'dotted' ? [2, 2] : [])
            );
            ctx.lineWidth = this.serverOptions.grid_width;
            ctx.strokeStyle = this.gridLineColor;

            const left = this.worldToCanvas(gridMinX, y);
            const right = this.worldToCanvas(gridMaxX, y);
            ctx.beginPath();
            ctx.moveTo(left.x, left.y);
            ctx.lineTo(right.x, right.y);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // 8) draw finite‐grid border *before* labels
        if (hasBounds) {
            const halfW = this.serverOptions.size[0] / 2;
            const halfH = this.serverOptions.size[1] / 2;
            const tl = this.worldToCanvas(-halfW, +halfH);
            const br = this.worldToCanvas(+halfW, -halfH);
            ctx.save();
            ctx.setLineDash([]);
            ctx.lineWidth = this.serverOptions.grid_border_width;
            ctx.strokeStyle = this.gridLineColor;
            ctx.strokeRect(tl.x, tl.y, br.x - tl.x, br.y - tl.y);
            ctx.restore();
        }

        // 9) draw tick‐labels on top of everything grid‐related
        ctx.font = this.labelFont;
        ctx.fillStyle = this.tickLabelColor;

        // X-axis labels along bottom
        ctx.textAlign = 'center';
        for (let x of majorsX) {
            if (x < wMinX || x > wMaxX) continue;
            const px = this.worldToCanvas(x, 0).x;
            ctx.fillText(x.toFixed(2), px, this.ch - 2);
        }

        // Y-axis labels along left
        ctx.textAlign = 'left';
        for (let y of majorsY) {
            if (y < wMinY || y > wMaxY) continue;
            const py = this.worldToCanvas(0, y).y;
            ctx.fillText(y.toFixed(2), 2, py + 3);
        }
    };


    drawOriginMarker() {
        const ctx = this.ctx;
        const p0 = this.worldToCanvas(0, 0);
        const lenX = this.gridSize * this.scaleX * this.coordinate_system_size;
        const lenY = this.gridSize * this.scaleY * this.coordinate_system_size;
        const head = 10;
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p0.x + lenX, p0.y);
        ctx.strokeStyle = 'red';
        ctx.lineWidth = 4;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(p0.x + lenX, p0.y);
        ctx.lineTo(p0.x + lenX - head, p0.y + head / 2);
        ctx.lineTo(p0.x + lenX - head, p0.y - head / 2);
        ctx.closePath();
        ctx.fillStyle = 'red';
        ctx.fill();
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p0.x, p0.y - lenY);
        ctx.strokeStyle = 'green';
        ctx.lineWidth = 4;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y - lenY);
        ctx.lineTo(p0.x - head / 2, p0.y - lenY + head);
        ctx.lineTo(p0.x + head / 2, p0.y - lenY + head);
        ctx.closePath();
        ctx.fillStyle = 'green';
        ctx.fill();
        ctx.beginPath();
        ctx.arc(p0.x, p0.y, 3, 0, 2 * Math.PI);
        ctx.fillStyle = '#000';
        ctx.fill();
    }

    // Legacy add/remove
    addObject(obj) {
        this.objects[obj.id] = obj;
        this.redraw();
    }

    removeObject(id) {
        delete this.objects[id];
        this.redraw();
    }

    clearObjects() {
        this.objects = {};
        this.redraw();
    }

    // Legacy convenience adders
    addPoint(id, options = {}) {
        return (new PointObject(id, options)) && this.addObject(new PointObject(id, options));
    }

    addAgent(id, options = {}) {
        return (new AgentObject(id, options)) && this.addObject(new AgentObject(id, options));
    }

    addVisionAgent(id, options = {}) {
        return (new VisionAgentObject(id, options)) && this.addObject(new VisionAgentObject(id, options));
    }

    addVector(id, options = {}) {
        return (new VectorObject(id, options)) && this.addObject(new VectorObject(id, options));
    }

    addCoordinateSystem(id, options = {}) {
        return (new CoordinateSystemObject(id, options)) && this.addObject(new CoordinateSystemObject(id, options));
    }

    addLine(id, options = {}) {
        return (new LineObject(id, options)) && this.addObject(new LineObject(id, options));
    }

    addRectangle(id, options = {}) {
        return (new RectangleObject(id, options)) && this.addObject(new RectangleObject(id, options));
    }

    addCircle(id, options = {}) {
        return (new CircleObject(id, options)) && this.addObject(new CircleObject(id, options));
    }


    // ─────────────────────────────────────────────────────────────────────────
    // Replace your existing redraw() with this version: grid (and its border/labels)
    // is drawn first, then all objects, then the origin marker.
    // ─────────────────────────────────────────────────────────────────────────

    redraw = function () {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.cw, this.ch);

        // 1) draw grid, border & tick labels underneath everything
        this.drawGrid();

        // 2) flatten legacy + grouped objects and sort by layer
        const legacyArr = Object.values(this.objects);
        const groupArr = this._getFlattenedGroupObjects();
        const allObjs = legacyArr.concat(groupArr)
            .sort((a, b) => a.layer - b.layer);

        // 3) draw all objects on top of the grid
        allObjs.forEach(o => o.draw(ctx, this));

        // 4) finally, draw your origin marker on top as well
        this.drawOriginMarker();
    };


}

// Factory function
export function createGridMap(mapContainer, canvas, options) {
    const gridMap = new GridMap(mapContainer, canvas, options);

    // --- Overlay toggle button + dynamic content ---
    const toggleBtn = document.createElement('button');
    toggleBtn.innerText = 'Table';
    Object.assign(toggleBtn.style, {
        position: 'absolute',
        top: '10px',
        right: '5px',
        zIndex: '1000',
        padding: '4px 8px',
        fontSize: '12px',
        cursor: 'pointer',
        opacity: '0.8',
        userSelect: 'none',
        width: '60px',
    });
    mapContainer.appendChild(toggleBtn);

    const resetBtn = document.createElement('button');
    resetBtn.innerText = 'Reset';
    Object.assign(resetBtn.style, {
        position: 'absolute',
        top: '40px',    // just below the Table button
        right: '5px',
        zIndex: '1000',
        padding: '4px 8px',
        fontSize: '12px',
        cursor: 'pointer',
        opacity: '0.8',
        userSelect: 'none',
        width: '60px',
    });
    mapContainer.appendChild(resetBtn);

    resetBtn.addEventListener('click', () => {
        // clear every object’s trail
        Object.values(gridMap.objects)
            .concat(gridMap._getFlattenedGroupObjects())
            .forEach(o => {
                o.trailHistory = [];
            });
        gridMap.redraw();
    });


    const overlay = document.createElement('div');
    Object.assign(overlay.style, {
        position: 'absolute',
        top: '0',
        left: '0',
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(255,255,255,0.7)',
        display: 'none',
        zIndex: '999',
        overflow: 'auto',
        paddingTop: '50px',
        paddingRight: '70px',
        paddingLeft: '10px',
        paddingBottom: '10px',
        // padding: '60px 70px 20px'
    });
    mapContainer.appendChild(overlay);

    // …right after mapContainer.appendChild(overlay);
    const infoBar = document.createElement('div');
    infoBar.id = 'map-info-bar';
    Object.assign(infoBar.style, {
        position: 'absolute',
        top: '2px',
        left: '2px',
        width: '80%',
        // backgroundColor: 'rgba(255, 255, 255, 0.7)',
        backgroundColor: 'rgba(65,220,129,0.31)',
        padding: '4px 30px',
        fontSize: '12px',
        display: 'none',
        zIndex: '1001',
        boxSizing: 'border-box',
        border: '1px solid #000',
        borderRadius: '5px'
    });
    mapContainer.appendChild(infoBar);

    // persistent open/closed state for each group panel:
    const groupOpenStates = {};

    const typeOpenStates = {};

    // …right after mapContainer.appendChild(infoBar);

    // ── persistent‐storage keys & loader/saver ──
    const STORAGE_KEY_GROUP = 'map_groupOpenStates';
    const STORAGE_KEY_TYPE = 'map_typeOpenStates';
    const STORAGE_KEY_OBJECT = 'map_objectStates';

    // load any saved states (defaults to `{}`)
    Object.assign(groupOpenStates, JSON.parse(localStorage.getItem(STORAGE_KEY_GROUP) || '{}'));
    Object.assign(typeOpenStates, JSON.parse(localStorage.getItem(STORAGE_KEY_TYPE) || '{}'));
    const savedObjStates = JSON.parse(localStorage.getItem(STORAGE_KEY_OBJECT) || '{}');

    // helpers
    function saveGroupStates() {
        localStorage.setItem(STORAGE_KEY_GROUP, JSON.stringify(groupOpenStates));
    }

    function saveTypeStates() {
        localStorage.setItem(STORAGE_KEY_TYPE, JSON.stringify(typeOpenStates));
    }

    function saveObjectState(obj) {
        const states = JSON.parse(localStorage.getItem(STORAGE_KEY_OBJECT) || '{}');
        states[obj.id] = {visible: obj.visible, showTrail: obj.showTrail};
        localStorage.setItem(STORAGE_KEY_OBJECT, JSON.stringify(states));
    }

    const STORAGE_KEY_GROUPVIS = 'map_groupVisibilityStates';
    const groupVisibilityStates = JSON.parse(
        localStorage.getItem(STORAGE_KEY_GROUPVIS) || '{}'
    );

    function saveGroupVisibilityStates() {
        localStorage.setItem(
            STORAGE_KEY_GROUPVIS,
            JSON.stringify(groupVisibilityStates)
        );
    }


// convenience method to center on a world coordinate:
    gridMap.centerOn = function (x, y) {
        this.offsetX = this.cw / (2 * this.scaleX) - this.worldW / 2 - x;
        this.offsetY = this.worldH / 2 - this.ch / (2 * this.scaleY) - y;
        this.redraw();
    };

    // ——— selection state & row‐highlighting ———
    gridMap.selectedObjectId = null;

    // highlight the matching row in the table overlay
    function highlightRowInOverlay(id) {
        const rows = overlay.querySelectorAll('tbody tr');
        rows.forEach(r => {
            // match against the data‐attribute we’ll set below
            r.style.backgroundColor = (r.dataset.objectId === id) ? 'lightblue' : '';
        });
    }

    gridMap.selectObjectById = function (id) {
        this.selectedObjectId = id;
        this.redraw();
        highlightRowInOverlay(id);

        const infoBar = document.getElementById('map-info-bar');
        if (id) {
            // find the object (legacy or in groups)
            let obj = this.objects[id] ||
                this._getFlattenedGroupObjects().find(o => o.id === id);
            if (!obj) return;

            const name = obj.name || obj.id;
            // compute a [x,y] to display
            const posArr = (typeof obj.x === 'number')
                ? [obj.x, obj.y]
                : (obj.position || obj.mid || obj.origin || [NaN, NaN]);
            // only build psiText if this object has a psi property
            let psiText = '';
            if (typeof obj.psi === 'number') {
                const deg = ((obj.psi * 180 / Math.PI) + 360) % 360;
                psiText = `&nbsp;&nbsp;<strong>Psi:</strong> <span id="map-info-psi">${deg.toFixed(2)}</span>`;
            }
            // two‐line HTML
            infoBar.innerHTML = `
           <div>
                <strong>${name}</strong> 
                &nbsp;
                <span id="map-info-position"><strong>x:</strong>${posArr[0].toFixed(2)} <strong>y:</strong> ${posArr[1].toFixed(2)}</span>
                ${psiText}
            </div>    
            <div style="margin-top:4px;">
                <label style="margin-right:12px;">
                    <input type="checkbox" id="infovisible" ${obj.visible ? 'checked' : ''}/>
                    Visible
                </label>
                <label style="margin-right:12px;">
                    <input type="checkbox" id="infotrails" ${obj.showTrail ? 'checked' : ''}/>
                    Trails
                </label>
                <span style="margin-right:12px;"><strong>ID:</strong> ${id}</span>
                <button id="infodeltrails">↩️</button>
            </div>
        `;
            infoBar.style.display = 'block';

            // ---- wire up controls ----
            const self = this;

            // VISIBLE checkbox: stop the click so map-click doesn't fire,
            // then on change toggle visibility and redraw
            const visCb = document.getElementById('infovisible');
            visCb.addEventListener('click', e => e.stopPropagation());
            visCb.addEventListener('change', e => {
                e.stopPropagation();
                obj.visible = e.target.checked;
                self.redraw();
                updateOverlay();
                saveObjectState(obj);
            });

            // TRAILS checkbox: same
            const trailCb = document.getElementById('infotrails');
            trailCb.addEventListener('click', e => e.stopPropagation());
            trailCb.addEventListener('change', e => {
                e.stopPropagation();
                obj.showTrail = e.target.checked;
                self.redraw();
                updateOverlay();
                saveObjectState(obj);
            });

            // DELETE TRAILS button
            const delBtn = document.getElementById('infodeltrails');
            delBtn.addEventListener('click', e => {
                e.stopPropagation();
                obj.trailHistory = [];
                self.redraw();
                updateOverlay();
            });

        } else {
            infoBar.style.display = 'none';
        }
    };


    overlay.addEventListener('wheel', e => {
        e.stopPropagation();
    });

    // ── helper: does this group (or any of its sub-groups) contain the selectedObjectId?
    function groupContainsSelected(group) {
        const sel = gridMap.selectedObjectId;
        if (!sel) return false;
        if (group.objects[sel]) return true;
        return Object.values(group.groups).some(sub => groupContainsSelected(sub));
    }


// —————————————————————————————————————————————————————————————————————
// 1) Replace your existing buildOverlay() with this version.
//    It tags each <td> with data-prop so we can later update in place.
// —————————————————————————————————————————————————————————————————————
    function buildOverlay() {
        overlay.innerHTML = '';

        // formatters
        const formatNum = v => (typeof v === 'number' ? v.toFixed(2) : '');
        const formatArr = arr =>
            '[' +
            (Array.isArray(arr)
                ? arr.map(n => (typeof n === 'number' ? n.toFixed(2) : '')).join(',')
                : '') +
            ']';

        function createArrow(expanded) {
            const a = document.createElement('span');
            a.style.display = 'inline-block';
            a.style.width = '0';
            a.style.height = '0';
            a.style.marginRight = '6px';
            a.style.borderLeft = '6px solid transparent';
            a.style.borderRight = '6px solid transparent';
            a.style.borderBottom = '8px solid #000';
            a.style.transition = 'transform 0.2s ease';
            a.style.transform = expanded ? 'rotate(180deg)' : 'rotate(90deg)';
            return a;
        }

        const propMap = {
            Visible: 'visible',
            Trails: 'showTrail',
            Dim: 'dim',
            Name: 'showName',
            Coords: 'showCoordinates'
        };

        function createGroupPanel(group) {
            const panel = document.createElement('div');
            const depth = group.fullPath.split('/').length - 1;
            panel.style.marginLeft = `${depth * 20}px`;
            panel.style.backgroundColor = `rgba(220,220,220,${Math.min(
                0.1 + depth * 0.05,
                0.4
            )})`;
            panel.style.border = '1px solid #ccc';
            panel.style.borderRadius = '4px';
            panel.style.padding = '8px';
            panel.style.margin = '4px 0';

            // ── HEADER ──
            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.alignItems = 'center';
            header.style.cursor = 'pointer';

            const containsSelected = groupContainsSelected(group);
            const expanded = containsSelected || groupOpenStates[group.fullPath] !== false;

            const arrow = createArrow(expanded);

            // visibility checkbox
            const visCb = document.createElement('input');
            visCb.type = 'checkbox';
            visCb.checked = group.visible;
            visCb.addEventListener('click', e => e.stopPropagation());
            visCb.addEventListener('change', () => {
                gridMap.setGroupVisibility(group.fullPath, visCb.checked);
                groupVisibilityStates[group.fullPath] = visCb.checked;
                saveGroupVisibilityStates();
                buildOverlay();               // ← rebuild so the “(n hidden)” count updates

            });

            // label with counts
            const total = countGroupObjects(group);
            const hidden = countHiddenGroupObjects(group);
            const label = document.createElement('span');
            label.textContent = `${group.name} (${total})${hidden > 0 ? ` (${hidden} hidden)` : ''}`;
            label.style.marginLeft = '4px';

            // “Show all” button
            const showAllBtn = document.createElement('button');
            showAllBtn.textContent = 'Show all';
            Object.assign(showAllBtn.style, {
                marginLeft: 'auto',
                padding: '2px 6px',
                fontSize: '10px',
                cursor: 'pointer'
            });
            showAllBtn.addEventListener('click', e => {
                e.stopPropagation();

                // make every object in this group & subgroups visible
                function recurse(g) {
                    Object.values(g.objects).forEach(o => {
                        if (!o.visible) {
                            o.visible = true;
                            saveObjectState(o);
                        }
                    });
                    Object.values(g.groups).forEach(recurse);
                }

                recurse(group);
                gridMap.redraw();
                updateOverlay();
                buildOverlay();
            });

            header.append(arrow, visCb, label, showAllBtn);
            panel.append(header);

            // expand/collapse
            const content = document.createElement('div');
            content.style.display = expanded ? '' : 'none';
            panel.append(content);
            header.addEventListener('click', () => {
                const isOpen = content.style.display !== 'none';
                content.style.display = isOpen ? 'none' : '';
                arrow.style.transform = isOpen ? 'rotate(90deg)' : 'rotate(180deg)';
                groupOpenStates[group.fullPath] = !isOpen;
                saveGroupStates();
            });

            // ── OBJECT-TYPE SECTIONS ──
            const types = [
                {
                    key: 'agents',
                    basicCols: ['ID', 'x', 'y', 'Psi', 'Visible'],
                    advCols: ['Trails', 'Dim', 'Name', 'Coords', 'Note']
                },
                {
                    key: 'visionagents',
                    basicCols: ['ID', 'x', 'y', 'Psi', 'Visible'],
                    advCols: ['Rad', 'FOV', 'Trails', 'Dim', 'Name', 'Coords', 'Note']
                },
                {
                    key: 'points',
                    basicCols: ['ID', 'x', 'y', 'Visible'],
                    advCols: ['Trails', 'Dim', 'Name', 'Coords', 'Note']
                },
                {key: 'vectors', basicCols: ['ID', 'Origin', 'Vec', 'Visible'], advCols: ['Dim', 'Name', 'Note']},
                {
                    key: 'coordinate_systems',
                    basicCols: ['ID', 'Origin', 'ex', 'ey', 'Visible'],
                    advCols: ['Dim', 'Name', 'Note']
                },
                {key: 'lines', basicCols: ['ID', 'Start', 'End', 'Visible'], advCols: ['Dim', 'Name', 'Note']},
                {key: 'rectangles', basicCols: ['ID', 'Mid', 'x', 'Visible'], advCols: ['Dim']},
                {key: 'circles', basicCols: ['ID', 'Mid', 'Diameter', 'Visible'], advCols: ['Dim']}
            ];

            types.forEach(typeDef => {
                const objs = Object.values(group.objects).filter(o => {
                    if (typeDef.key === 'agents') return o.constructor.name === 'AgentObject';
                    if (typeDef.key === 'visionagents') return o.constructor.name === 'VisionAgentObject';
                    if (typeDef.key === 'points') return o.constructor.name === 'PointObject';
                    return o.constructor.name.toLowerCase().includes(typeDef.key.slice(0, -1));
                });
                if (!objs.length) return;

                // SECTION HEADER
                const tblHeader = document.createElement('div');
                tblHeader.style.display = 'flex';
                tblHeader.style.alignItems = 'center';
                tblHeader.style.cursor = 'pointer';

                const sectionKey = `${group.fullPath}/${typeDef.key}`;
                const containsTypeSelected = objs.some(o => o.id === gridMap.selectedObjectId);
                const isExpanded = containsTypeSelected || typeOpenStates[sectionKey] !== false;

                const arrow2 = createArrow(isExpanded);

                // compute counts
                const total2 = objs.length;
                const hidden2 = objs.filter(o => !o.visible).length;
                const titleSpan = document.createElement('span');
                titleSpan.textContent = `${typeDef.key} (${total2})${hidden2 > 0 ? ` (${hidden2} hidden)` : ''}`;
                titleSpan.style.marginLeft = '4px';

                tblHeader.append(arrow2, titleSpan);
                content.append(tblHeader);

                // TABLE CONTAINER
                const tblContainer = document.createElement('div');
                tblContainer.style.display = isExpanded ? 'block' : 'none';
                content.append(tblContainer);
                // container for the table itself

                const table = document.createElement('table');
                table.style.width = '100%';
                table.style.borderCollapse = 'collapse';

                // THEAD
                const thead = document.createElement('thead');
                const trHead = document.createElement('tr');
                [...typeDef.basicCols, ''].forEach(hdr => {
                    const th = document.createElement('th');
                    th.textContent = hdr;
                    th.style.border = '1px solid #ccc';
                    th.style.padding = '4px';
                    trHead.append(th);
                });
                thead.append(trHead);
                table.append(thead);

                // TBODY
                const tbody = document.createElement('tbody');
                objs.forEach(obj => {
                    const tr = document.createElement('tr');
                    tr.dataset.objectId = obj.id;

                    // ID cell
                    const idCell = document.createElement('td');
                    idCell.dataset.prop = 'ID';
                    idCell.style.border = '1px solid #ccc';
                    idCell.style.padding = '4px';
                    idCell.style.cursor = 'pointer';
                    idCell.style.whiteSpace = 'nowrap';
                    const dot = document.createElement('span');
                    dot.style.display = 'inline-block';
                    dot.style.width = '10px';
                    dot.style.height = '10px';
                    dot.style.borderRadius = '50%';
                    dot.style.backgroundColor = obj.color || '#000';
                    dot.style.marginRight = '6px';
                    dot.style.verticalAlign = 'middle';
                    idCell.append(dot, document.createTextNode(obj.name));
                    idCell.addEventListener('click', e => {
                        e.stopPropagation();
                        let x, y;
                        if (typeof obj.x === 'number' && typeof obj.y === 'number') {
                            [x, y] = [obj.x, obj.y];
                        } else if (Array.isArray(obj.position)) {
                            [x, y] = obj.position;
                        } else if (Array.isArray(obj.mid)) {
                            [x, y] = obj.mid;
                        } else if (Array.isArray(obj.origin)) {
                            [x, y] = obj.origin;
                        } else if (Array.isArray(obj.start) && Array.isArray(obj.end)) {
                            // for lines, focus on the midpoint
                            x = (obj.start[0] + obj.end[0]) / 2;
                            y = (obj.start[1] + obj.end[1]) / 2;
                        } else {
                            // ultimate fallback: world-origin
                            x = 0;
                            y = 0;
                        }
                        gridMap.centerOn(x, y);
                        gridMap.selectObjectById(obj.id);
                    });


                    tr.append(idCell);

                    // basic columns
                    typeDef.basicCols.slice(1).forEach(col => {
                        const td = document.createElement('td');
                        td.dataset.prop = col;
                        td.style.border = '1px solid #ccc';
                        td.style.padding = '4px';
                        switch (col) {
                            case 'x':
                                td.textContent = formatNum(obj.x ?? obj.position?.[0]);
                                break;
                            case 'y':
                                td.textContent = formatNum(obj.y ?? obj.position?.[1]);
                                break;
                            case 'Psi':
                                td.textContent = formatNum(((obj.psi * 180 / Math.PI) + 360) % 360);
                                break;
                            case 'Rad':
                                td.textContent = formatNum(obj.visionRadius);
                                break;
                            case 'FOV':
                                td.textContent = formatNum(obj.visionFov);
                                break;
                            case 'Origin':
                                td.textContent = formatArr(obj.origin);
                                break;
                            case 'Vec':
                                td.textContent = formatArr(obj.vec);
                                break;
                            case 'Start':
                                td.textContent = formatArr(obj.start);
                                break;
                            case 'End':
                                td.textContent = formatArr(obj.end);
                                break;
                            case 'Mid':
                                td.textContent = formatArr(obj.mid);
                                break;
                            case 'Diameter':
                                td.textContent = formatNum(obj.diameter);
                                break;
                            case 'Visible': {
                                const cb = document.createElement('input');
                                cb.type = 'checkbox';
                                cb.checked = !!obj.visible;
                                cb.addEventListener('click', e => e.stopPropagation());
                                cb.addEventListener('change', () => {
                                    obj.visible = cb.checked;
                                    gridMap.redraw();
                                    saveObjectState(obj);
                                    buildOverlay();               // ← rebuild the table so headers update
                                });
                                td.append(cb);
                                break;
                            }
                            default:
                                td.textContent = obj.text || '';
                        }
                        tr.append(td);
                    });

                    // ⚙️ settings column
                    const tdSet = document.createElement('td');
                    tdSet.style.border = '1px solid #ccc';
                    tdSet.style.padding = '4px';
                    const btn = document.createElement('button');
                    btn.textContent = '⚙️';
                    btn.style.cursor = 'pointer';
                    btn.addEventListener('click', e => {
                        e.stopPropagation();
                        const next = tr.nextSibling;
                        if (next && next.classList.contains('advanced-settings')) {
                            next.remove();
                        } else {
                            const advTr = document.createElement('tr');
                            advTr.className = 'advanced-settings';
                            const advTd = document.createElement('td');
                            advTd.colSpan = typeDef.basicCols.length + 1;
                            advTd.style.padding = '8px';
                            advTd.style.backgroundColor = '#f9f9f9';

                            const idLabel = document.createElement('span');
                            idLabel.textContent = `ID: ${obj.id}`;
                            idLabel.style.marginRight = '12px';
                            advTd.append(idLabel);

                            typeDef.advCols.forEach(col => {
                                const label = document.createElement('label');
                                label.style.marginRight = '12px';
                                if (col === 'Note') {
                                    const inp = document.createElement('input');
                                    inp.type = 'text';
                                    inp.value = obj.text || '';
                                    inp.placeholder = 'Note…';
                                    inp.style.marginRight = '8px';
                                    inp.addEventListener('change', () => {
                                        obj.text = inp.value;
                                        gridMap.redraw();
                                    });
                                    label.append(`${col}: `, inp);
                                } else if (col === 'Rad' || col === 'FOV') {
                                    // non‐editable numeric display
                                    const span = document.createElement('span');
                                    span.textContent = col === 'Rad'
                                        ? formatNum(obj.visionRadius)
                                        : formatNum(obj.visionFov);
                                    label.append(`${col}: `, span);
                                } else {
                                    const cb = document.createElement('input');
                                    cb.type = 'checkbox';
                                    cb.checked = !!obj[propMap[col]];
                                    cb.addEventListener('change', () => {
                                        obj[propMap[col]] = cb.checked;
                                        gridMap.redraw();
                                        saveObjectState(obj);
                                    });
                                    label.append(cb, ` ${col}`);
                                }
                                advTd.append(label);
                            });

                            // ── delete-trails button for moving objects ──
                            if (['PointObject', 'AgentObject', 'VisionAgentObject']
                                .includes(obj.constructor.name)) {
                                const delBtn = document.createElement('button');
                                delBtn.textContent = 'Delete Trails';
                                delBtn.style.marginLeft = '12px';
                                delBtn.addEventListener('click', e => {
                                    e.stopPropagation();
                                    obj.trailHistory = [];
                                    gridMap.redraw();
                                });
                                advTd.append(delBtn);
                            }


                            advTr.append(advTd);
                            tr.parentNode.insertBefore(advTr, tr.nextSibling);
                        }
                    });
                    tdSet.append(btn);
                    tr.append(tdSet);

                    tbody.append(tr);
                });

                table.append(tbody);
                tblContainer.append(table);

                // collapse/expand section
                tblHeader.addEventListener('click', () => {
                    const nowHidden = tblContainer.style.display === 'none';
                    tblContainer.style.display = nowHidden ? 'block' : 'none';
                    arrow2.style.transform = nowHidden ? 'rotate(180deg)' : 'rotate(90deg)';
                    typeOpenStates[sectionKey] = nowHidden;
                    saveTypeStates();
                });

            });

            // recurse into sub‐groups
            Object.values(group.groups).forEach(sub =>
                content.append(createGroupPanel(sub))
            );

            return panel;
        }

        Object.values(gridMap.groups).forEach(root =>
            overlay.appendChild(createGroupPanel(root))
        );
        highlightRowInOverlay(gridMap.selectedObjectId);
    }

    // ─────────────────────────────────────────────────────────────────────────
// Helpers to count all objects (and hidden ones) in a group & its sub-groups
// ─────────────────────────────────────────────────────────────────────────
    function countGroupObjects(group) {
        let count = Object.values(group.objects).length;
        for (let sub of Object.values(group.groups)) {
            count += countGroupObjects(sub);
        }
        return count;
    }

    function countHiddenGroupObjects(group) {
        let count = Object.values(group.objects).filter(o => !o.visible).length;
        for (let sub of Object.values(group.groups)) {
            count += countHiddenGroupObjects(sub);
        }
        return count;
    }


// —————————————————————————————————————————————————————————————————————
// 2) Add this new helper right *below* buildOverlay.
//    It will gently patch only the changed cells & checkboxes.
// —————————————————————————————————————————————————————————————————————
    function updateOverlay() {
        if (overlay.style.display !== 'block') return;

        // same formatters as in buildOverlay:
        const formatNum = v => (typeof v === 'number' ? v.toFixed(2) : '');
        const formatArr = arr =>
            '[' +
            (Array.isArray(arr)
                ? arr.map(n => (typeof n === 'number' ? n.toFixed(2) : '')).join(',')
                : '') +
            ']';

        // walk every row, look at its data-prop tags and update in place
        overlay.querySelectorAll('tbody tr').forEach(tr => {
            const id = tr.dataset.objectId;
            const obj = gridMap.objects[id]
                || gridMap._getFlattenedGroupObjects().find(o => o.id === id);
            if (!obj) return;

            Array.from(tr.children).forEach(td => {
                const prop = td.dataset.prop;
                switch (prop) {
                    case 'x':
                        td.textContent = formatNum(obj.x ?? obj.position?.[0]);
                        break;
                    case 'y':
                        td.textContent = formatNum(obj.y ?? obj.position?.[1]);
                        break;
                    case 'Psi':
                        td.textContent = formatNum(((obj.psi * 180 / Math.PI) + 360) % 360) + '°';
                        break;
                    case 'Rad':
                        td.textContent = formatNum(obj.visionRadius);
                        break;
                    case 'FOV':
                        td.textContent = formatNum(obj.visionFov);
                        break;
                    case 'Origin':
                        td.textContent = formatArr(obj.origin);
                        break;
                    case 'Vec':
                        td.textContent = formatArr(obj.vec);
                        break;
                    case 'Start':
                        td.textContent = formatArr(obj.start);
                        break;
                    case 'End':
                        td.textContent = formatArr(obj.end);
                        break;
                    case 'Mid':
                        td.textContent = formatArr(obj.mid);
                        break;
                    case 'Diameter':
                        td.textContent = formatNum(obj.diameter);
                        break;
                    case 'Visible': {
                        const cb = td.querySelector('input[type=checkbox]');
                        if (cb) cb.checked = !!obj.visible;
                        break;
                    }
                    // ID, Note, etc. you probably don’t need to update here
                }
            });
        });
    }

    // ── helper: append one trail‐sample + expire by memory length ──
    function recordTrail(obj, x, y) {
        const now = Date.now();
        // store with timestamp
        obj.trailHistory.push({x, y, t: now});
        // prune old
        const mem = gridMap.trailsMemoryLength;
        if (mem != null) {
            const cutoff = now - mem * 1000;
            while (obj.trailHistory.length && obj.trailHistory[0].t < cutoff) {
                obj.trailHistory.shift();
            }
        }
    }


    toggleBtn.addEventListener('click', () => {
        if (overlay.style.display === 'none') {
            buildOverlay();
            overlay.style.display = 'block';
            toggleBtn.innerText = 'Hide';
        } else {
            overlay.style.display = 'none';
            toggleBtn.innerText = 'Table';
        }
    });

    // ——— selection on single‐click, but never deselect on empty click ———
    gridMap.mapContainer.addEventListener('click', e => {
        // ignore clicks inside the table overlay or on the toggle button
        if (overlay.style.display === 'block' && overlay.contains(e.target)) return;
        if (toggleBtn.contains(e.target)) return;

        const rect = canvas.getBoundingClientRect();
        const cx = e.clientX - rect.left;
        const cy = e.clientY - rect.top;

        // check objects from topmost down
        const all = Object.values(gridMap.objects)
            .concat(gridMap._getFlattenedGroupObjects())
            .sort((a, b) => a.layer - b.layer)
            .reverse();

        for (let o of all) {
            // only Point, Agent or VisionAgent are clickable
            if (
                o instanceof PointObject ||
                o instanceof AgentObject ||
                o instanceof VisionAgentObject
            ) {
                const worldX = (o.x !== undefined) ? o.x : o.position[0];
                const worldY = (o.y !== undefined) ? o.y : o.position[1];
                const pos = gridMap.worldToCanvas(worldX, worldY);
                const r = (o.size || 5) + 3;  // hit radius
                const dx = cx - pos.x, dy = cy - pos.y;

                if (Math.hypot(dx, dy) <= r) {
                    // select only — do NOT center
                    gridMap.selectObjectById(o.id);
                    return;
                }
            }
        }
        // clicked empty → do nothing (leave the current selection intact)
    });

// ——— clear selection only on double‐click ———
    gridMap.mapContainer.addEventListener('dblclick', e => {
        // ignore double‐clicks inside the overlay or on the toggle button
        if (overlay.style.display === 'block' && overlay.contains(e.target)) return;
        if (toggleBtn.contains(e.target)) return;

        // clear any selection
        gridMap.selectObjectById(null);
    });


    // —— WebSocket listener for Python backend ——
    // ——— Replace your WebSocket setup block with this auto-reconnect version ———
    let ws;

    function connect() {
        ws = new WebSocket('ws://localhost:8091');

        ws.addEventListener('open', () => {
            console.log('Map WS connected');
        });

        ws.addEventListener('message', evt => {
            const msg = JSON.parse(evt.data);
            switch (msg.command) {
                case 'init':
                    handleInit(msg);
                    break;
                case 'add':
                    handleAdd(msg.data);
                    break;
                case 'remove':
                    handleRemove(msg.data);
                    break;
                case 'update':
                    handleUpdate(msg.data);
                    break;
                case 'stop':
                case 'close':
                    ws.close();
                    break;
                default:
                    console.warn('WS unknown cmd', msg.command);
            }
        });

        ws.addEventListener('close', () => {
            console.log('Map WS closed');
            // clear everything on disconnect
            gridMap.objects = {};
            gridMap.groups = {};
            gridMap.redraw();
            // try again in 1s
            setTimeout(connect, 1000);
        });

        ws.addEventListener('error', e => {
            console.error('Map WS error', e);
            ws.close();
        });
    }

    connect();


    function handleInit(initMsg) {
        // unpack the server’s init
        const {options, data: rootPayload} = initMsg;
        const {
            size,
            center,
            initial_display,
            background_color,
            grid,
            grid_color,
            ticks_color,
            coordinate_system_size,
            trails_size,
            trails_alpha,
            trails_memory_length
        } = options;

        // store for drawGrid
        gridMap.serverOptions = options;

        // determine worldW/worldH & centerX/centerY from initial_display if present
        let worldW, worldH, centerX, centerY;
        if (Array.isArray(initial_display) && initial_display.length === 4) {
            [worldW, worldH, centerX, centerY] = initial_display;
        } else {
            [worldW, worldH] = size;
            [centerX, centerY] = center;
        }

        // 1) override world dims + recalc zoom/pan
        gridMap.worldW = worldW;
        gridMap.worldH = worldH;
        gridMap.coordinate_system_size = coordinate_system_size;
        gridMap.updateSize();
        gridMap.centerOn(centerX, centerY);

        // 2) trails
        gridMap.globalTrailSize = trails_size;
        gridMap.trailsAlpha = trails_alpha;
        gridMap.trailsMemoryLength = trails_memory_length;

        // 3) grid cell size
        gridMap.gridSize = grid;

        // 4) background + grid/tick colors
        gridMap.canvas.style.backgroundColor = arrayToColor(background_color);
        gridMap.gridLineColor = arrayToColor(grid_color);
        gridMap.tickLabelColor = arrayToColor(ticks_color);

        // 5) preserve any “hidden” toggles the user set
        const oldVisibility = {};
        gridMap._getFlattenedGroupObjects().forEach(o => {
            oldVisibility[o.id] = o.visible;
        });

        // 6) wipe & rebuild
        gridMap.objects = {};
        gridMap.groups = {};
        buildGroupRecursively(rootPayload);

        // 7) re-apply local overrides
        gridMap._getFlattenedGroupObjects().forEach(o => {
            if (oldVisibility[o.id] === false) o.visible = false;
        });

        // 8) apply persisted object‐visible/trail states
        gridMap._getFlattenedGroupObjects().forEach(o => {
            const ps = savedObjStates[o.id];
            if (ps) {
                if (ps.visible !== undefined) o.visible = ps.visible;
                if (ps.showTrail !== undefined) o.showTrail = ps.showTrail;
            }
        });

        // ── apply persisted group‐visibility flags ──
        Object.entries(groupVisibilityStates).forEach(([path, vis]) => {
            const g = gridMap.getGroup(path);
            if (g) g.visible = vis;
        });


        // 9) final redraw
        gridMap.redraw();

    }


    function buildGroupRecursively(groupPayload) {
        // strip leading slashes, e.g. "/root/foo" → "root/foo"
        const fullPath = groupPayload.path.replace(/^\/+/, '');
        // ensure the group exists in JS
        gridMap.createGroup(fullPath);

        // first recurse into sub‐groups
        Object.values(groupPayload.data.groups || {})
            .forEach(buildGroupRecursively);

        // then collect *all* object‐payloads (points, agents, etc.)
        const allObjs = [
            ...Object.values(groupPayload.data.points || {}),
            ...Object.values(groupPayload.data.agents || {}),
            ...Object.values(groupPayload.data.vision_agents || {}),
            ...Object.values(groupPayload.data.vectors || {}),
            ...Object.values(groupPayload.data.coordinate_systems || {}),
            ...Object.values(groupPayload.data.lines || {}),
            ...Object.values(groupPayload.data.rectangles || {}),
            ...Object.values(groupPayload.data.circles || {}),
        ];

        // add each one
        allObjs.forEach(handleAdd);
    }


// add either a group or object
    // ——— Replaces your old handleAdd ———
    function handleAdd(payload) {
        const fullPath = payload.path.replace(/^\/+/, '');
        const parts = fullPath.split('/');
        const id = parts.pop();
        const parentPath = parts.join('/');

        switch (payload.type) {
            case 'group':
                gridMap.createGroup(fullPath);
                break;

            case 'point': {
                const d = payload.data;
                gridMap.addPointToGroup(
                    parentPath,
                    id,
                    {
                        x: d.x,
                        y: d.y,
                        size: d.size,
                        shape: d.shape,
                        color: arrayToColor(d.color),
                        alpha: d.alpha,
                        dim: d.dim,
                        layer: d.zindex,     // ← use Python’s zindex
                        showName: d.show_name,
                        name: d.name,
                        showTrail: d.show_trails,
                    }
                );
                break;
            }

            case 'agent': {
                const d = payload.data;
                gridMap.addAgentToGroup(
                    parentPath,
                    id,
                    {
                        position: [d.x, d.y],
                        psi: d.psi,
                        size: d.size,
                        shape: d.shape,
                        color: arrayToColor(d.color),
                        alpha: d.alpha,
                        dim: d.dim,
                        text: d.text,
                        layer: d.zindex,
                        showName: d.show_name,
                        name: d.name,
                        showTrail: d.show_trails,
                    }
                );
                break;
            }

            case 'vision_agent': {
                const d = payload.data;
                gridMap.addVisionAgentToGroup(
                    parentPath,
                    id,
                    {
                        position: [d.x, d.y],
                        psi: d.psi,
                        visionRadius: d.vision_radius,
                        visionFov: d.vision_fov,
                        size: d.size,
                        shape: d.shape,
                        color: arrayToColor(d.color),
                        alpha: d.alpha,
                        dim: d.dim,
                        text: d.text,
                        layer: d.zindex,
                        showName: d.show_name,
                        name: d.name,
                        showTrail: d.show_trails,
                    }
                );
                break;
            }

            case 'vector': {
                const d = payload.data;
                gridMap.addVectorToGroup(
                    parentPath,
                    id,
                    {
                        origin: d.origin,
                        vec: d.vec,
                        thickness: d.width,
                        color: arrayToColor(d.color),
                        alpha: d.alpha,
                        dim: d.dim,
                        layer: d.zindex,
                        showName: d.show_name,
                        name: d.name,
                    }
                );
                break;
            }

            case 'coordinate_system': {
                const d = payload.data;
                gridMap.addCoordinateSystemToGroup(
                    parentPath,
                    id,
                    {
                        origin: d.origin,
                        ex: d.x_axis,
                        ey: d.y_axis,
                        thickness: d.width,
                        colors: {
                            ex: arrayToColor(d.colors.ex),
                            ey: arrayToColor(d.colors.ey)
                        },
                        alpha: d.alpha,
                        dim: d.dim,
                        layer: d.zindex,
                        showName: d.show_name,
                        name: d.name,
                    }
                );
                break;
            }

            case 'line': {
                const d = payload.data;
                gridMap.addLineToGroup(
                    parentPath,
                    id,
                    {
                        start: d.start,
                        end: d.end,
                        thickness: d.width,
                        color: arrayToColor(d.color),
                        alpha: d.alpha,
                        dim: d.dim,
                        style: d.style,
                        layer: d.zindex,
                        showName: d.show_name,
                        name: d.name,
                    }
                );
                break;
            }

            case 'rectangle': {
                const d = payload.data;
                const w = Array.isArray(d.size) ? d.size[0] : d.size;
                const h = Array.isArray(d.size) ? d.size[1] : d.size;
                gridMap.addRectangleToGroup(
                    parentPath,
                    id,
                    {
                        mid: d.origin,
                        width: w,
                        height: h,
                        fill: arrayToColor(d.color),
                        lineColor: arrayToColor(d.linecolor),
                        thickness: 1,
                        alpha: d.alpha,
                        dim: d.dim,
                        layer: d.zindex,
                        showName: d.show_name,
                        name: d.name,
                    }
                );
                break;
            }

            case 'circle': {
                const d = payload.data;
                gridMap.addCircleToGroup(
                    parentPath,
                    id,
                    {
                        mid: d.origin,
                        diameter: d.diameter,
                        fill: arrayToColor(d.color),
                        lineColor: arrayToColor(d.linecolor),
                        thickness: 1,
                        alpha: d.alpha,
                        dim: d.dim,
                        layer: d.zindex,
                        showName: d.show_name,
                        name: d.name,
                    }
                );
                break;
            }

            default:
                console.warn('Unhandled add type', payload.type);
        }

        gridMap.redraw();
    }


// remove a group or object
    function handleRemove(payload) {
        const fullPath = payload.path.replace(/^\/+/, '');
        const parts = fullPath.split('/');
        const id = parts.pop();
        const parentPath = parts.join('/');

        if (payload.type === 'group') {
            if (!parentPath) {
                delete gridMap.groups[id];
            } else {
                const parent = gridMap.getGroup(parentPath);
                parent && parent.removeGroup(id);
            }
        } else {
            const parent = gridMap.getGroup(parentPath);
            parent && parent.removeObject(id);
        }
        gridMap.redraw();
    }

    /**
     * Recursively update or add every group/object in the incoming payload,
     * without clearing out your existing MapObjects.
     */
    function updateGroupRecursively(groupPayload) {
        const fullPath = groupPayload.path.replace(/^\/+/, '');
        // ensure group exists
        gridMap.createGroup(fullPath);

        // recurse into sub-groups
        Object.values(groupPayload.data.groups || {}).forEach(updateGroupRecursively);

        // collect all object payloads
        const allObjs = [
            ...Object.values(groupPayload.data.points || {}),
            ...Object.values(groupPayload.data.agents || {}),
            ...Object.values(groupPayload.data.vision_agents || {}),
            ...Object.values(groupPayload.data.vectors || {}),
            ...Object.values(groupPayload.data.coordinate_systems || {}),
            ...Object.values(groupPayload.data.lines || {}),
            ...Object.values(groupPayload.data.rectangles || {}),
            ...Object.values(groupPayload.data.circles || {}),
        ];

        allObjs.forEach(payload => {
            const objPath = payload.path.replace(/^\/+/, '');
            const d = payload.data;
            // try to find existing JS object
            let obj = gridMap.getObjectByPath(objPath);
            if (!obj) {
                // brand-new object → add it
                handleAdd(payload);
                return;
            }
            // otherwise update its live properties:
            switch (payload.type) {
                case 'point':
                    obj.x = d.x;
                    obj.y = d.y;
                    obj.size = d.size;
                    obj.shape = d.shape;
                    obj.color = arrayToColor(d.color);
                    obj.alpha = d.alpha;
                    // obj.dim = d.dim;
                    obj.layer = d.zindex;
                    break;
                case 'agent':
                    obj.position = [d.x, d.y];
                    obj.psi = d.psi;
                    obj.size = d.size;
                    obj.shape = d.shape;
                    obj.color = arrayToColor(d.color);
                    obj.alpha = d.alpha;
                    // obj.dim = d.dim;
                    obj.text = d.text;
                    obj.layer = d.zindex;
                    break;
                case 'vision_agent':
                    obj.position = [d.x, d.y];
                    obj.psi = d.psi;
                    obj.visionRadius = d.vision_radius;
                    obj.visionFov = d.vision_fov;
                    obj.size = d.size;
                    obj.shape = d.shape;
                    obj.color = arrayToColor(d.color);
                    obj.alpha = d.alpha;
                    // obj.dim = d.dim;
                    obj.text = d.text;
                    obj.layer = d.zindex;
                    break;
                case 'vector':
                    obj.origin = d.origin;
                    obj.vec = d.vec;
                    obj.thickness = d.width;
                    obj.color = arrayToColor(d.color);
                    obj.alpha = d.alpha;
                    // obj.dim = d.dim;
                    obj.layer = d.zindex;
                    break;
                case 'coordinate_system':
                    obj.origin = d.origin;
                    obj.ex = d.x_axis;
                    obj.ey = d.y_axis;
                    obj.thickness = d.width;
                    obj.colors = {
                        ex: arrayToColor(d.colors.ex),
                        ey: arrayToColor(d.colors.ey)
                    };
                    obj.alpha = d.alpha;
                    // obj.dim = d.dim;
                    obj.text = d.text;
                    obj.layer = d.zindex;
                    break;
                case 'line':
                    obj.start = d.start;
                    obj.end = d.end;
                    obj.thickness = d.width;
                    obj.color = arrayToColor(d.color);
                    obj.alpha = d.alpha;
                    // obj.dim = d.dim;
                    obj.layer = d.zindex;
                    break;
                case 'rectangle':
                    obj.mid = d.origin;
                    // unpack size array or scalar
                {
                    const w = Array.isArray(d.size) ? d.size[0] : d.size;
                    const h = Array.isArray(d.size) ? d.size[1] : d.size;
                    obj.width = w;
                    obj.height = h;
                }
                    obj.fill = arrayToColor(d.color);
                    obj.lineColor = arrayToColor(d.linecolor);
                    obj.alpha = d.alpha;
                    // obj.dim = d.dim;
                    obj.layer = d.zindex;
                    break;
                case 'circle':
                    obj.mid = d.origin;
                    obj.diameter = d.diameter;
                    obj.fill = arrayToColor(d.color);
                    obj.lineColor = arrayToColor(d.linecolor);
                    obj.alpha = d.alpha;
                    // obj.dim = d.dim;
                    obj.layer = d.zindex;
                    break;
            }
        });
    }

    function handleUpdate(rootPayload) {
        // 1) sync all object positions, etc.
        updateGroupRecursively(rootPayload);

        // 2) record a new sample for moving objects
        const now = Date.now();
        gridMap._getFlattenedGroupObjects().forEach(o => {
            let x, y;
            if (o instanceof PointObject) {
                x = o.x;
                y = o.y;
            } else if (o instanceof AgentObject) {
                x = o.position[0];
                y = o.position[1];
            } else {
                return;
            }
            o.trailHistory.push({x, y, t: now});
            // prune old
            const mem = gridMap.trailsMemoryLength;
            if (mem != null) {
                const cutoff = now - mem * 1000;
                while (o.trailHistory.length && o.trailHistory[0].t < cutoff) {
                    o.trailHistory.shift();
                }
            }
        });

        // 3) redraw the map & overlay table
        gridMap.redraw();
        updateOverlay();

        // 4) **only** update the position span in the infoBar—
        //    don’t rebuild its innerHTML or reattach handlers
        // 4) **only** update the position & psi spans in the infoBar
        const sel = gridMap.selectedObjectId;
        if (sel) {
            // re-grab the selected object
            const obj = gridMap.objects[sel]
                || gridMap._getFlattenedGroupObjects().find(o => o.id === sel);
            if (!obj) return;

            // build a fresh [x,y]
            const posArr = (typeof obj.x === 'number')
                ? [obj.x, obj.y]
                : (obj.position || obj.mid || obj.origin || [NaN, NaN]);

            // update position *with* your markup (innerHTML, not textContent)
            const posSpan = document.getElementById('map-info-position');
            if (posSpan) {
                posSpan.innerHTML = `<strong>x:</strong> ${posArr[0].toFixed(2)}&nbsp;`
                    + `<strong>y:</strong> ${posArr[1].toFixed(2)}`;
            }

            // update Ψ
            const psiSpan = document.getElementById('map-info-psi');
            if (psiSpan && typeof obj.psi === 'number') {
                const deg = ((obj.psi * 180 / Math.PI) + 360) % 360;
                psiSpan.textContent = deg.toFixed(2) + '°';
            }
        }

    }


    return gridMap;
}

// Export classes
export {
    MapObject,
    PointObject,
    AgentObject,
    VisionAgentObject,
    VectorObject,
    CoordinateSystemObject,
    LineObject,
    RectangleObject,
    CircleObject,
    MapObjectGroup
};
