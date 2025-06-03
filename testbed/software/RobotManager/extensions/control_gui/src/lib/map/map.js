import './map.css';

import {
    AgentObject,
    arrayToColor,
    CircleObject,
    CoordinateSystemObject,
    LineObject,
    MapObject,
    MapObjectGroup,
    PointObject,
    RectangleObject,
    VectorObject,
    VisionAgentObject
} from './map_objects'


// ——————————————————————————————————————————————————————————————————————————————————
// DEFAULTS
// ——————————————————————————————————————————————————————————————————————————————————
const DEFAULT_CLIENT_CONFIG = {
    websocket_url: 'ws://localhost:8001',
};

const DEFAULT_MAP_OPTIONS = {
    size: [10, 10],
    origin: [0, 0],
    initial_display: [12, 12, 0, 0],
    grid_size: 1,
    coordinate_system_size: 1,
    background_color: [255, 255, 255, 1],
    text_color: [0, 0, 0, 1],
    button_color: [85, 85, 85, 1],
    grid_background_color: [238, 238, 238, 1],
    grid_line_color: [51, 51, 51, 1],
    grid_ticks_color: [0, 0, 0, 1],
    grid_line_width: 1,
    grid_border_width: 3,
    major_grid_style: 'solid',
    minor_grid_style: 'dotted',
    trails_size: 5,
    trails_alpha: 0.3,
    trails_memory_length: 100,

    labelFont: '12px Roboto',
    labelMargin: 40,
    minLabelPx: 50,
    globalPointSize: 1,
    globalAgentSize: 1,
    globalVectorSize: 1,
    globalTrailSize: 1,
    globalTextSize: 12,
    globalLineThickness: 2
};


// =====================================================================================================================
// =====================================================================================================================
class GridMap {
    constructor(mapContainer, config = {}, rootPayload = null) {

        if (!mapContainer) {
            console.error('GridMap: missing container or canvas');
            return;
        }

        this.config = {...DEFAULT_MAP_OPTIONS, ...config};

        this.mapContainer = mapContainer;

        // 1) create the canvas element internally
        const canvas = document.createElement('canvas');
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.display = 'block';
        canvas.style.background = 'rgba(255, 0, 255, 0.9)';
        this.mapContainer.appendChild(canvas);

        this.canvas = canvas;
        this.ctx = this.canvas.getContext('2d');

        console.log("[GridMap] ctor: container size =",
            this.mapContainer.clientWidth, "×", this.mapContainer.clientHeight,
            "–– canvas size =", this.canvas.width, "×", this.canvas.height);


        this.selectedObjectId = null;

        this.objects = {};
        this.groups = {};


        // Assign some initial drawing parameters
        this.labelFont = this.config.labelFont;
        this.labelMargin = this.config.labelMargin;
        this.minLabelPx = this.config.minLabelPx;
        this.globalPointSize = this.config.globalPointSize;
        this.globalAgentSize = this.config.globalAgentSize;
        this.globalVectorSize = this.config.globalVectorSize;
        this.globalTrailSize = this.config.globalTrailSize;
        this.globalTextSize = this.config.globalTextSize;
        this.globalLineThickness = this.config.globalLineThickness;
        this.gridLineColor = arrayToColor(this.config.grid_line_color);
        this.tickLabelColor = arrayToColor(this.config.ticks_color);

        // // 4) background and grid/tick colors
        this.canvas.style.backgroundColor = arrayToColor(this.config.background_color);


        // START DRAWING
        let worldW, worldH, centerX, centerY;
        if (Array.isArray(this.config.initial_display) && this.config.initial_display.length === 4) {
            [worldW, worldH, centerX, centerY] = this.config.initial_display;
        } else {
            [worldW, worldH] = size;
            [centerX, centerY] = origin;
        }

        console.log("Creating map with world size: ", worldW, worldH, " and origin: ", centerX, centerY, "")

        this.coordinate_system_size = this.config.coordinate_system_size;


        // apply initial view + styling
        this.worldW = worldW;
        this.worldH = worldH;
        this.gridSize = this.config.grid_size;


        // // 5) preserve any “hidden” toggles the user set
        const oldVisibility = {};
        this._getFlattenedGroupObjects().forEach(o => {
            oldVisibility[o.id] = o.visible;
        });


        this.updateSize();

        this._savedView = null;

        this.centerOn(centerX, centerY);


        // Trails
        this.globalTrailSize = this.config.trails_size;
        this.trailsAlpha = this.config.trails_alpha;
        this.trailsMemoryLength = this.config.trails_memory_length;


        // Panning
        this.dragging = false;
        this.startX = 0;
        this.startY = 0;
        this.startOX = 0;
        this.startOY = 0;
        this.mapContainer.style.cursor = 'grab';


        this.attachListeners();


        // Build the map objects
        this.buildGroupRecursively(rootPayload);


        // Apply local overrides
        this._getFlattenedGroupObjects().forEach(o => {
            if (oldVisibility[o.id] === false) o.visible = false;
        });


        // size and first draw
        this.updateSize();
        this.redraw();

        {
            const origUpdate = this.updateSize.bind(this);
            this.updateSize = () => {
                origUpdate();

                // only re-apply if we actually have a non-zero canvas
                if (this.canvas.width > 0 && this._savedView) {
                    Object.assign(this, this._savedView);
                }

                this.redraw();
            };
        }

        // {
        //     const origUpdate = this.updateSize.bind(this);
        //     let first = true;
        //     this.updateSize = () => {
        //         // call the original (centers to initial)
        //         origUpdate();
        //
        //         // after that, if we’ve got a saved view, and it's not the very first call,
        //         // re-apply it
        //         if (!first && this._savedView) {
        //             Object.assign(this, this._savedView);
        //         }
        //
        //         // redraw
        //         this.redraw();
        //         first = false;
        //     };
        // }
    }

    // -----------------------------------------------------------------------------------------------------------------
    attachListeners() {

        this.mapContainer.addEventListener('mouseup', () => this.saveCurrentView());
        this.mapContainer.addEventListener('wheel', () => this.saveCurrentView());

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

        new ResizeObserver(() => {
            this.updateSize();
            this.redraw();
        }).observe(this.mapContainer);


        window.addEventListener('resize', () => {
            {
                this.updateSize();
                this.redraw();
            }
        });
    }

    saveCurrentView() {
        if (this.canvas.width === 0 || this.canvas.height === 0) return;

        this._savedView = {
            scaleX: this.scaleX,
            scaleY: this.scaleY,
            offsetX: this.offsetX,
            offsetY: this.offsetY
        };
    };

    // -----------------------------------------------------------------------------------------------------------------
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

    // -----------------------------------------------------------------------------------------------------------------
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

    // -----------------------------------------------------------------------------------------------------------------
    addObjectToGroup(path, obj) {
        const group = this.createGroup(path);
        group.addObject(obj);
        this.redraw();
    }

    // -----------------------------------------------------------------------------------------------------------------
    addPointToGroup(path, id, options = {}) {
        const obj = new PointObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    // -----------------------------------------------------------------------------------------------------------------
    addAgentToGroup(path, id, options = {}) {
        const obj = new AgentObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    // -----------------------------------------------------------------------------------------------------------------
    addVisionAgentToGroup(path, id, options = {}) {
        const obj = new VisionAgentObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    // -----------------------------------------------------------------------------------------------------------------
    addVectorToGroup(path, id, options = {}) {
        const obj = new VectorObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    // -----------------------------------------------------------------------------------------------------------------
    addCoordinateSystemToGroup(path, id, options = {}) {
        const obj = new CoordinateSystemObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    // -----------------------------------------------------------------------------------------------------------------
    addLineToGroup(path, id, options = {}) {
        const obj = new LineObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    // -----------------------------------------------------------------------------------------------------------------
    addRectangleToGroup(path, id, options = {}) {
        const obj = new RectangleObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    // -----------------------------------------------------------------------------------------------------------------
    addCircleToGroup(path, id, options = {}) {
        const obj = new CircleObject(id, options);
        this.addObjectToGroup(path, obj);
        return obj;
    }

    // -----------------------------------------------------------------------------------------------------------------
    getObjectByPath(fullPath) {
        const parts = fullPath.split('/');
        const id = parts.pop();
        const group = this.getGroup(parts);
        return group ? group.getObject(id) : null;
    }

    // -----------------------------------------------------------------------------------------------------------------
    setGroupVisibility(path, visible) {
        const group = this.getGroup(path);
        if (group) {
            group.visible = visible;
            this.redraw();
        }
    }

    // -----------------------------------------------------------------------------------------------------------------
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

    // -----------------------------------------------------------------------------------------------------------------
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

    // -----------------------------------------------------------------------------------------------------------------
    worldToCanvas(x, y) {
        return {
            x: (x + this.worldW / 2 + this.offsetX) * this.scaleX,
            y: (this.worldH / 2 - (y + this.offsetY)) * this.scaleY
        };
    }

    // -----------------------------------------------------------------------------------------------------------------
    drawGrid() {
        // this.ctx = this.canvas.getContext('2d');
        const ctx = this.ctx;

        // 1) viewport in world coords
        const wMinX = -this.worldW / 2 - this.offsetX;
        const wMaxX = wMinX + this.cw / this.scaleX;
        const wMaxY = this.worldH / 2 - this.offsetY;
        const wMinY = wMaxY - this.ch / this.scaleY;

        // 2) finite bounds?
        const hasBounds = (
            this.config.size[0] != null &&
            this.config.size[1] != null
        );
        const gridMinX = hasBounds ? -this.config.size[0] / 2 : wMinX;
        const gridMaxX = hasBounds ? this.config.size[0] / 2 : wMaxX;
        const gridMinY = hasBounds ? -this.config.size[1] / 2 : wMinY;
        const gridMaxY = hasBounds ? this.config.size[1] / 2 : wMaxY;

        // ▷ fill grid-area background
        if (this.config.grid_background_color) {
            const bg = arrayToColor(this.config.grid_background_color);
            const topLeft = this.worldToCanvas(gridMinX, gridMaxY);
            const bottomRight = this.worldToCanvas(gridMaxX, gridMinY);
            ctx.save();
            ctx.fillStyle = bg;
            ctx.fillRect(
                topLeft.x,
                topLeft.y,
                bottomRight.x - topLeft.x,
                bottomRight.y - topLeft.y
            );
            ctx.restore();
        }


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
                    ? (this.config.major_grid_style === 'dotted' ? [2, 2] : [])
                    : (this.config.minor_grid_style === 'dotted' ? [2, 2] : [])
            );
            ctx.lineWidth = this.config.grid_line_width;
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
                    ? (this.config.major_grid_style === 'dotted' ? [2, 2] : [])
                    : (this.config.minor_grid_style === 'dotted' ? [2, 2] : [])
            );
            ctx.lineWidth = this.config.grid_line_width;
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
            const halfW = this.config.size[0] / 2;
            const halfH = this.config.size[1] / 2;
            const tl = this.worldToCanvas(-halfW, +halfH);
            const br = this.worldToCanvas(+halfW, -halfH);
            ctx.save();
            ctx.setLineDash([]);
            ctx.lineWidth = this.config.grid_border_width;
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

    // -----------------------------------------------------------------------------------------------------------------
    drawOriginMarker() {

        const ctx = this.ctx;
        const p0 = this.worldToCanvas(0, 0);  // TODO: Here I have to use the origin
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

    // -----------------------------------------------------------------------------------------------------------------
    addObject(obj) {
        this.objects[obj.id] = obj;
        this.redraw();
    }

    // -----------------------------------------------------------------------------------------------------------------
    removeObject(id) {
        delete this.objects[id];
        this.redraw();
    }

    // -----------------------------------------------------------------------------------------------------------------
    clearObjects() {
        this.objects = {};
        this.redraw();
    }

    // -----------------------------------------------------------------------------------------------------------------
    redraw() {
        // this.ctx = this.canvas.getContext('2d');
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.cw, this.ch);

        // 1) draw grid, border & tick labels underneath everything
        this.drawGrid();

        // 2) flatten legacy and grouped objects and sort by layer
        const legacyArr = Object.values(this.objects);
        const groupArr = this._getFlattenedGroupObjects();
        const allObjs = legacyArr.concat(groupArr)
            .sort((a, b) => a.layer - b.layer);

        // 3) draw all objects on top of the grid
        allObjs.forEach(o => o.draw(ctx, this));

        // 4) finally, draw your origin marker on top as well
        this.drawOriginMarker();
    };

    // -----------------------------------------------------------------------------------------------------------------
    centerOn(x, y) {
        this.offsetX = this.cw / (2 * this.scaleX) - this.worldW / 2 - x;
        this.offsetY = this.worldH / 2 - this.ch / (2 * this.scaleY) - y;

        this.saveCurrentView();
        this.redraw();
    };

    // -----------------------------------------------------------------------------------------------------------------
    handleAdd(payload) {
        const fullPath = payload.path.replace(/^\/+/, '');
        const parts = fullPath.split('/');
        const id = parts.pop();
        const parentPath = parts.join('/');

        switch (payload.type) {
            case 'group':
                this.createGroup(fullPath);
                break;

            case 'point':
                const d = payload.data;
                console.log("Adding a point to the group:")
                console.log(this);
                this.addPointToGroup(
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


            case 'agent': {
                const d = payload.data;
                this.addAgentToGroup(
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
                this.addVisionAgentToGroup(
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
                this.addVectorToGroup(
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
                this.addCoordinateSystemToGroup(
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
                this.addLineToGroup(
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
                this.addRectangleToGroup(
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
                this.addCircleToGroup(
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

        this.redraw();
    }

    // -----------------------------------------------------------------------------------------------------------------
    handleRemove(payload) {
        const fullPath = payload.path.replace(/^\/+/, '');
        const parts = fullPath.split('/');
        const id = parts.pop();
        const parentPath = parts.join('/');

        if (payload.type === 'group') {
            if (!parentPath) {
                delete this.groups[id];
            } else {
                const parent = this.getGroup(parentPath);
                parent && parent.removeGroup(id);
            }
        } else {
            const parent = this.getGroup(parentPath);
            parent && parent.removeObject(id);
        }
        this.redraw();
    }

    // -----------------------------------------------------------------------------------------------------------------

    handleUpdate(rootPayload) {
        // this.updateSize();
        // 1) sync all object positions, etc.
        this.updateGroupRecursively(rootPayload);

        this.recordTrails();

        this.ctx = this.canvas.getContext('2d');

        // 3) redraw the map & overlay table
        this.redraw();

    }

    // -----------------------------------------------------------------------------------------------------------------
    updateGroupRecursively(groupPayload) {
        const fullPath = groupPayload.path.replace(/^\/+/, '');
        // ensure group exists
        this.createGroup(fullPath);

        Object
            .values(groupPayload.data.groups || {})
            .forEach(sub => this.updateGroupRecursively(sub));

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
            let obj = this.getObjectByPath(objPath);
            if (!obj) {
                // brand-new object → add it
                this.handleAdd(payload);
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

    // -----------------------------------------------------------------------------------------------------------------
    buildGroupRecursively(groupPayload) {
        // strip leading slashes, e.g. "/root/foo" → "root/foo"
        const fullPath = groupPayload.path.replace(/^\/+/, '');
        // ensure the group exists in JS
        this.createGroup(fullPath);

        // first recurse into sub‐groups using arrow function to preserve `this`
        Object.values(groupPayload.data.groups || {}).forEach(group => {
            this.buildGroupRecursively(group);
        });

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

        // add each one using arrow function to ensure correct `this`
        allObjs.forEach(obj => {
            this.handleAdd(obj);
        });
    }


    // -----------------------------------------------------------------------------------------------------------------
    selectObjectById(id) {
        this.selectedObjectId = id;
        this.redraw();
    }

    // -----------------------------------------------------------------------------------------------------------------
    recordTrails() {
        // 2) record a new sample for moving objects
        const now = Date.now();
        this._getFlattenedGroupObjects().forEach(o => {
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
            const mem = this.trailsMemoryLength;
            if (mem != null) {
                const cutoff = now - mem * 1000;
                while (o.trailHistory.length && o.trailHistory[0].t < cutoff) {
                    o.trailHistory.shift();
                }
            }
        });
    }

    // -----------------------------------------------------------------------------------------------------------------
    deleteAllTrails() {
        Object.values(this.objects)
            .concat(this._getFlattenedGroupObjects())
            .forEach(o => {
                o.trailHistory = [];
            });
        this.redraw();
    }
}


class GridMapContainer {
    constructor(mapContainer, config = {}) {

        this.mapContainer = mapContainer;
        this.options = {...DEFAULT_CLIENT_CONFIG, ...config};
        this.map = null;

        // Build Buttons
        this.buildButtons();

        // Prepare Overlay
        this.prepareOverlay();


        this.groupOpenStates = {};
        this.typeOpenStates = {};

        // ── persistent‐storage keys & loader/saver ──
        this.STORAGE_KEY_GROUP = 'map_groupOpenStates';
        this.STORAGE_KEY_TYPE = 'map_typeOpenStates';
        this.STORAGE_KEY_OBJECT = 'map_objectStates';
        this.STORAGE_KEY_GROUPVIS = 'map_groupVisibilityStates';

        // Object.assign(this.groupOpenStates, JSON.parse(localStorage.getItem(this.STORAGE_KEY_GROUP) || '{}'));
        // Object.assign(this.typeOpenStates, JSON.parse(localStorage.getItem(this.STORAGE_KEY_TYPE) || '{}'));

        this.groupOpenStates = JSON.parse(localStorage.getItem(this.STORAGE_KEY_GROUP) || '{}');
        this.typeOpenStates = JSON.parse(localStorage.getItem(this.STORAGE_KEY_TYPE) || '{}');
        this.savedObjStates = JSON.parse(localStorage.getItem(this.STORAGE_KEY_OBJECT) || '{}');
        this.groupVisibilityStates = JSON.parse(localStorage.getItem(this.STORAGE_KEY_GROUPVIS) || '{}');

        this.connect();
    }

    // -----------------------------------------------------------------------------------------------------------------
    buildButtons() {
        const ctrlCol = document.createElement('div');
        Object.assign(ctrlCol.style, {
            position: 'absolute',
            top: '3px',
            right: '5px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            gap: '2px',
            zIndex: '1000',
            userSelect: 'none'
        });
        this.mapContainer.appendChild(ctrlCol);

        // 1) Connection indicator
        this.connIndicator = document.createElement('div');
        Object.assign(this.connIndicator.style, {
            width: '12px',
            height: '12px',
            borderRadius: '50%',
            backgroundColor: 'red',
            border: '1px solid #000',
        });
        this.connIndicator.title = 'Disconnected';
        ctrlCol.appendChild(this.connIndicator);

        // 2) Table toggle
        this.toggleBtn = document.createElement('button');
        this.toggleBtn.innerText = 'Table';
        Object.assign(this.toggleBtn.style, {
            padding: '4px 8px',
            fontSize: '12px',
            cursor: 'pointer',
            opacity: '0.8',
            width: '60px',
        });
        ctrlCol.appendChild(this.toggleBtn);

        this.toggleBtn.addEventListener('click', () => {
            if (this.overlay.style.display === 'none') {
                this.buildOverlay();
                this.overlay.style.display = 'block';
                this.toggleBtn.innerText = 'Hide';
            } else {
                this.overlay.style.display = 'none';
                this.toggleBtn.innerText = 'Table';
            }
        });

        // 3) Reset button
        const resetBtn = document.createElement('button');
        resetBtn.innerText = 'Reset';
        Object.assign(resetBtn.style, {
            padding: '4px 8px',
            fontSize: '12px',
            cursor: 'pointer',
            opacity: '0.8',
            width: '60px',
        });
        ctrlCol.appendChild(resetBtn);

        resetBtn.addEventListener('click', () => {
            if (this.map) {
                this.map.deleteAllTrails();
            }
        })
    }

    // -----------------------------------------------------------------------------------------------------------------
    prepareOverlay() {
        this.overlay = document.createElement('div');
        Object.assign(this.overlay.style, {
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
        this.mapContainer.appendChild(this.overlay);

        this.overlay.addEventListener('wheel', e => {
            e.stopPropagation();
        });

        this.infoBar = document.createElement('div');
        this.infoBar.id = 'map-info-bar';
        Object.assign(this.infoBar.style, {
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
        this.mapContainer.appendChild(this.infoBar);
    }

    // -----------------------------------------------------------------------------------------------------------------
    saveGroupStates() {
        localStorage.setItem(this.STORAGE_KEY_GROUP, JSON.stringify(this.groupOpenStates));
    }

    // -----------------------------------------------------------------------------------------------------------------
    saveTypeStates() {
        localStorage.setItem(this.STORAGE_KEY_TYPE, JSON.stringify(this.typeOpenStates));
    }

    // -----------------------------------------------------------------------------------------------------------------
    saveObjectState(obj) {
        const states = JSON.parse(localStorage.getItem(this.STORAGE_KEY_OBJECT) || '{}');
        states[obj.id] = {visible: obj.visible, showTrail: obj.showTrail, showName: obj.showName};
        localStorage.setItem(this.STORAGE_KEY_OBJECT, JSON.stringify(states));
    }

    // -----------------------------------------------------------------------------------------------------------------
    saveGroupVisibilityStates() {
        localStorage.setItem(
            this.STORAGE_KEY_GROUPVIS,
            JSON.stringify(this.groupVisibilityStates)
        );
    }

    // -----------------------------------------------------------------------------------------------------------------
    highlightRowInOverlay(id) {
        const rows = this.overlay.querySelectorAll('tbody tr');
        rows.forEach(r => {
            // match against the data‐attribute we’ll set below
            r.style.backgroundColor = (r.dataset.objectId === id) ? 'lightblue' : '';
        });
    }

    // -----------------------------------------------------------------------------------------------------------------
    groupContainsSelected(group) {
        const sel = this.map.selectedObjectId;
        if (!sel) return false;
        if (group.objects[sel]) return true;
        return Object.values(group.groups).some(sub => this.groupContainsSelected(sub));
    }

    // -----------------------------------------------------------------------------------------------------------------
    buildOverlay() {
        this.overlay.innerHTML = '';

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

        const createGroupPanel = (group) => {
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

            const containsSelected = this.groupContainsSelected(group);
            const expanded = containsSelected || this.groupOpenStates[group.fullPath] !== false;

            const arrow = createArrow(expanded);

            // visibility checkbox
            const visCb = document.createElement('input');
            visCb.type = 'checkbox';
            visCb.checked = group.visible;
            visCb.addEventListener('click', e => e.stopPropagation());
            visCb.addEventListener('change', () => {
                this.map.setGroupVisibility(group.fullPath, visCb.checked);
                this.groupVisibilityStates[group.fullPath] = visCb.checked;
                this.saveGroupVisibilityStates();
                this.buildOverlay();               // ← rebuild so the “(n hidden)” count updates

            });

            // label with counts
            const total = this.countGroupObjects(group);
            const hidden = this.countHiddenGroupObjects(group);
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
                const recurse = (g) => {
                    Object.values(g.objects).forEach(o => {
                        if (!o.visible) {
                            o.visible = true;
                            this.saveObjectState(o);
                        }
                    });
                    Object.values(g.groups).forEach(recurse);
                }

                recurse(group);
                this.map.redraw();
                this.updateOverlay();
                this.buildOverlay();
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
                this.groupOpenStates[group.fullPath] = !isOpen;
                this.saveGroupStates();
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
                const containsTypeSelected = objs.some(o => o.id === this.map.selectedObjectId);
                const isExpanded = containsTypeSelected || this.typeOpenStates[sectionKey] !== false;

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
                        this.map.centerOn(x, y);
                        this.onSelectObject(obj.id);
                        // this.map.selectObjectById(obj.id);
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
                                    this.map.redraw();
                                    this.saveObjectState(obj);
                                    this.buildOverlay();               // ← rebuild the table so headers update
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
                                        this.map.redraw();
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
                                        this.map.redraw();
                                        this.saveObjectState(obj);
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
                                    this.map.redraw();
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
                    this.typeOpenStates[sectionKey] = nowHidden;
                    this.saveTypeStates();
                });

            });

            // recurse into sub‐groups
            Object.values(group.groups).forEach(sub =>
                content.append(createGroupPanel(sub))
            );

            return panel;
        }

        Object.values(this.map.groups).forEach(root =>
            this.overlay.appendChild(createGroupPanel(root))
        );
        this.highlightRowInOverlay(this.map.selectedObjectId);
    }

    // -----------------------------------------------------------------------------------------------------------------
    countGroupObjects(group) {
        let count = Object.values(group.objects).length;
        for (let sub of Object.values(group.groups)) {
            count += this.countGroupObjects(sub);
        }
        return count;
    }

    // -----------------------------------------------------------------------------------------------------------------
    countHiddenGroupObjects(group) {
        let count = Object.values(group.objects).filter(o => !o.visible).length;
        for (let sub of Object.values(group.groups)) {
            count += this.countHiddenGroupObjects(sub);
        }
        return count;
    }

    // -----------------------------------------------------------------------------------------------------------------
    updateOverlay() {
        if (this.overlay.style.display !== 'block') return;

        // same formatters as in buildOverlay:
        const formatNum = v => (typeof v === 'number' ? v.toFixed(2) : '');
        const formatArr = arr =>
            '[' +
            (Array.isArray(arr)
                ? arr.map(n => (typeof n === 'number' ? n.toFixed(2) : '')).join(',')
                : '') +
            ']';

        // walk every row, look at its data-prop tags and update in place
        this.overlay.querySelectorAll('tbody tr').forEach(tr => {
            const id = tr.dataset.objectId;
            const obj = this.map.objects[id]
                || this.map._getFlattenedGroupObjects().find(o => o.id === id);
            if (!obj) return;

            Array.from(tr.objects).forEach(td => {
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

    // -----------------------------------------------------------------------------------------------------------------
    addMapHandler() {
        this.mapContainer.addEventListener('click', e => {
            // ignore clicks inside the table overlay or on the toggle button
            if (this.overlay.style.display === 'block' && this.overlay.contains(e.target)) return;
            if (this.toggleBtn.contains(e.target)) return;

            const rect = this.map.canvas.getBoundingClientRect();
            const cx = e.clientX - rect.left;
            const cy = e.clientY - rect.top;

            // check objects from topmost down
            const all = Object.values(this.map.objects)
                .concat(this.map._getFlattenedGroupObjects())
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
                    const pos = this.map.worldToCanvas(worldX, worldY);
                    const r = (o.size || 5) + 3;  // hit radius
                    const dx = cx - pos.x, dy = cy - pos.y;

                    if (Math.hypot(dx, dy) <= r) {
                        // select only — do NOT center
                        this.onSelectObject(o.id);
                        // this.map.selectObjectById(o.id);
                        return;
                    }
                }
            }
            // clicked empty → do nothing (leave the current selection intact)
        });

        // ——— clear selection only on double‐click ———
        this.mapContainer.addEventListener('dblclick', e => {
            // ignore double‐clicks inside the overlay or on the toggle button
            if (this.overlay.style.display === 'block' && this.overlay.contains(e.target)) return;
            if (this.toggleBtn.contains(e.target)) return;

            // clear any selection
            this.onSelectObject(null);
            // this.map.selectObjectById(null);
        });

    }

    // -----------------------------------------------------------------------------------------------------------------
    connect() {
        this.ws = new WebSocket(this.options.websocket_url);

        this.ws.addEventListener('open', () => {
            console.log('Map WS connected');
            this.connIndicator.style.backgroundColor = 'green';
            this.connIndicator.title = 'Connected';
        });

        this.ws.addEventListener('message', evt => {
            const msg = JSON.parse(evt.data);
            switch (msg.command) {
                case 'init':
                    this.handleInit(msg);
                    break;
                case 'add':
                    this.handleAdd(msg.data);
                    break;
                case 'remove':
                    this.handleRemove(msg.data);
                    break;
                case 'update':
                    this.handleUpdate(msg.data);
                    break;
                case 'stop':
                case 'close':
                    ws.close();
                    break;
                default:
                    console.warn('WS unknown cmd', msg.command);
            }
        });

        this.ws.addEventListener('close', () => {
            this.connIndicator.style.backgroundColor = 'red';
            this.connIndicator.title = 'Disconnected';
            this.map.objects = {};
            this.map.groups = {};
            this.map.redraw();
            // try again in 1s
            setTimeout(this.connect, 3000);
        });

        this.ws.addEventListener('error', e => {
            // console.error('Map WS error', e);
            this.ws.close();
        });
    }

    // -----------------------------------------------------------------------------------------------------------------
    handleInit(initMsg) {
        // unpack the server’s init
        const {options, data: rootPayload} = initMsg;

        const map_options = {...DEFAULT_MAP_OPTIONS, ...options};

        this.map = new GridMap(this.mapContainer, map_options, rootPayload);

        this.loadObjectStates();

        // redraw to pick up those flags before we attach handlers


        this.addMapHandler();


    }

    // -----------------------------------------------------------------------------------------------------------------
    loadObjectStates() {
        // ——— re-apply any saved object visibility / trail settings ———
        Object.entries(this.savedObjStates).forEach(([id, state]) => {
            // try both top-level and grouped objects
            const obj =
                this.map.objects[id] ||
                this.map._getFlattenedGroupObjects().find(o => o.id === id);
            if (!obj) return;
            if (state.visible !== undefined) obj.visible = state.visible;
            if (state.showTrail !== undefined) obj.showTrail = state.showTrail;
            if (state.showName !== undefined) obj.showName = state.showName;
        });

        // ——— re-apply any saved group-visibility flags ———
        Object.entries(this.groupVisibilityStates).forEach(([path, vis]) => {
            const g = this.map.getGroup(path);
            if (g) g.visible = vis;
        });


        this.map.redraw();
    }

    // -----------------------------------------------------------------------------------------------------------------
    handleAdd(data) {
        this.map.handleAdd(data);
    }

    // -----------------------------------------------------------------------------------------------------------------
    handleRemove(data) {
        this.map.handleRemove(data);
    }

    // -----------------------------------------------------------------------------------------------------------------
    handleUpdate(data) {
        this.map.handleUpdate(data);

        this.updateOverlay();

        // 4) **only** update the position span in the infoBar—
        //    don’t rebuild its innerHTML or reattach handlers
        // 4) **only** update the position & psi spans in the infoBar
        const sel = this.map.selectedObjectId;
        if (sel) {
            // re-grab the selected object
            const obj = this.map.objects[sel]
                || this.map._getFlattenedGroupObjects().find(o => o.id === sel);
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

    // -----------------------------------------------------------------------------------------------------------------
    onSelectObject(id) {
        // 1) update map selection + redraw
        this.map.selectObjectById(id);

        // 2) highlight the overlay row
        this.highlightRowInOverlay(id);

        // 3) update the info bar
        const infoBar = document.getElementById('map-info-bar');
        if (!id) {
            infoBar.style.display = 'none';
            return;
        }
        const obj = this.map.objects[id]
            || this.map._getFlattenedGroupObjects().find(o => o.id === id);
        if (!obj) return;

        // compute position and psi
        let [x, y] = typeof obj.x === 'number'
            ? [obj.x, obj.y]
            : obj.position || obj.mid || obj.origin || [0, 0];
        let psiText = '';
        if (typeof obj.psi === 'number') {
            const deg = ((obj.psi * 180 / Math.PI) + 360) % 360;
            psiText = `&nbsp;&nbsp;<strong>Psi:</strong> <span id="map-info-psi">${deg.toFixed(2)}°</span>`;
        }

        infoBar.innerHTML = `
  <div>
    <strong>${obj.name || obj.id}</strong>
    &nbsp;
    <span id="map-info-position">
      <strong>x:</strong> ${x.toFixed(2)}&nbsp;<strong>y:</strong> ${y.toFixed(2)}
    </span>
    ${psiText}
  </div>
  <div style="margin-top:4px;">
    <label>
      <input id="infovisible" type="checkbox" ${obj.visible ? 'checked' : ''}/>
      Visible
    </label>
    <label style="margin-left:12px">
      <input id="infotrails" type="checkbox" ${obj.showTrail ? 'checked' : ''}/>
      Trails
    </label>
    <label style="margin-left:12px">
      <input id="infoname" type="checkbox" ${obj.showName ? 'checked' : ''}/>
      Name
    </label>
    <span style="margin-left:12px"><strong>ID:</strong> ${id}</span>
    <button id="infodeltrails" style="margin-left:12px">↩️</button>
  </div>
`;


        infoBar.style.display = 'block';

        // wire up the controls (stopPropagation(), redraw, save states…)
        document.getElementById('infovisible')
            .addEventListener('change', e => {
                obj.visible = e.target.checked;
                this.map.redraw();
                this.updateOverlay();
                this.saveObjectState(obj);
            });
        document.getElementById('infotrails')
            .addEventListener('change', e => {
                obj.showTrail = e.target.checked;
                this.map.redraw();
                this.updateOverlay();
                this.saveObjectState(obj);
            });
        document.getElementById('infodeltrails')
            .addEventListener('click', () => {
                obj.trailHistory = [];
                this.map.redraw();
                this.updateOverlay();
            });
        document.getElementById('infoname').addEventListener('change', e => {
            obj.showName = e.target.checked;
            this.map.redraw();
            this.updateOverlay();
            this.saveObjectState(obj);
        });

    }

    // -----------------------------------------------------------------------------------------------------------------

    // -----------------------------------------------------------------------------------------------------------------
}


export function createGridMapContainer(mapContainer, container_config = {}) {
    container_config = {...DEFAULT_CLIENT_CONFIG, ...container_config};
    return new GridMapContainer(mapContainer, container_config);
}

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
