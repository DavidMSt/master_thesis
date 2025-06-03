import {getColor, shadeColor, splitPath} from "./helpers";
import {createGridMapContainer} from "./map/map.js";
import {JSPlot} from "./plot/plot.js"

export class GUI_Object {

    /** @type {string|null} */
    id = null;

    /** @type {HTMLElement|null} */
    element = null;  // will hold the DOM element

    /** @type {Object} */
    configuration = null;

    /** @type {Object} */
    callbacks = {};

    /**

     * @param {string} id            – unique id
     * @param {Object} configuration

     */
    constructor(
        id, configuration
    ) {

        this.id = id;
        this.configuration = configuration;
        // this.callbacks = {};
    }

    configureElement(config = {}) {
        config = {...config, ...this.configuration};
        this.configuration = config;

    }

    /**
     * @param {Array<number>} grid_position - [column, row] start positions
     * @param {Array<number>} grid_size - [columnSpan, rowSpan] sizes
     * @returns {HTMLElement}
     */
    render(grid_position = null, grid_size = null) {
        if (!this.checkGridSize(grid_size)) {
            const errorEl = document.createElement('div');
            errorEl.classList.add('gridItem');
            errorEl.style.display = 'flex';
            errorEl.style.alignItems = 'center';
            errorEl.style.justifyContent = 'center';
            errorEl.style.backgroundColor = '#c00';
            errorEl.style.color = '#fff';
            errorEl.style.fontWeight = 'bold';
            errorEl.style.fontSize = '0.7em';
            errorEl.textContent = `Layout!`;

            if (grid_position && grid_size) {
                errorEl.style.gridColumnStart = String(grid_position[1]);
                errorEl.style.gridColumnEnd = `span ${grid_size[0]}`;
                errorEl.style.gridRowStart = String(grid_position[0]);
                errorEl.style.gridRowEnd = `span ${grid_size[1]}`;
            }

            return errorEl;
        }

        const element = this.getElement();
        if (grid_position && grid_size) {
            element.style.gridColumnStart = String(grid_position[1]);
            element.style.gridColumnEnd = `span ${grid_size[0]}`;
            element.style.gridRowStart = String(grid_position[0]);
            element.style.gridRowEnd = `span ${grid_size[1]}`;
        }
        return element;
    }

    /**
     * @abstract
     * @returns {HTMLElement}
     */
    getElement() {
        throw new Error('getHTML() must be implemented by subclass');
    }


    /**
     *
     */
    checkGridSize() {
        return true;
    }

    /**
     * @abstract
     * @param {Object} data
     * @returns {void}
     */
    update(data) {
        throw new Error('update() must be implemented by subclass');
    }

    /**
     *
     */
    destroy() {
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        this.element = null;
    }

    /**
     * @abstract
     * @param {HTMLElement} element
     * @returns {void}
     */
    assignListeners(element) {
        throw new Error('assignListeners() must be implemented by subclass');
    }
}

/* ================================================================================================================== */
export class ObjectGroup extends GUI_Object {
    _occupiedSet = new Set();

    constructor(opts) {
        super({...opts, type: 'group'});

        // ── Defaults ─────────────────────────────────────────────────────────
        const defaults = {
            rows: 1,
            cols: 1,
            fit: true,
            title: '',
            titleFontSize: '1em',
            titleColor: '#000',
            titlePosition: 'center',
            tabs: false,
            backgroundColor: 'transparent',
            borderColor: '#444',
            borderWidth: 1,
            fillEmpty: true,
        };
        this.configuration = {...defaults, ...this.configuration};
        this.objects = [];


        // ── Container & Title/Tabs ───────────────────────────────────────────
        this.container = document.createElement('div');
        this.container.id = this.id;
        this.container.classList.add('gridItem', 'object-group');
        Object.assign(this.container.style, {
            backgroundColor: this.configuration.backgroundColor,
            border: `${this.configuration.borderWidth}px solid ${this.configuration.borderColor}`,
            display: 'flex',
            flexDirection: 'column',
            boxSizing: 'border-box',
            width: '100%',
            height: '100%',
            overflow: 'hidden',
        });

        if (this.configuration.title) {
            this.titleBar = document.createElement('div');
            this.titleBar.classList.add('object-group__titlebar');
            this.titleBar.textContent = this.configuration.title;
            this.titleBar.style.fontSize = this.configuration.titleFontSize;
            this.titleBar.style.color = this.configuration.titleColor;
            this.titleBar.style.textAlign = this.configuration.titlePosition;
            this.container.appendChild(this.titleBar);
        }

        if (this.configuration.tabs) {
            this.tabsBar = document.createElement('div');
            this.tabsBar.classList.add('object-group__tabs');
            this.tabsBar.textContent = this.configuration.tabs === true ? 'Tabs' : this.configuration.tabs;
            this.container.appendChild(this.tabsBar);
        }

        // ── Inner grid ───────────────────────────────────────────────────────
        this.gridDiv = document.createElement('div');
        this.gridDiv.classList.add('object-group__grid');
        this.gridDiv.dataset.fit = String(this.configuration.fit);

        // base grid styles
        Object.assign(this.gridDiv.style, {
            display: 'grid', width: '100%', gap: '2px', minHeight: '0',      // allow flex children to shrink properly
        });

        // always set columns
        this.gridDiv.style.gridTemplateColumns = `repeat(${this.configuration.cols}, 1fr)`;
        // store a gap and cols in CSS vars for our cell-size calc
        this.gridDiv.style.setProperty('--og-gap', '2px');
        this.gridDiv.style.setProperty('--og-cols', `${this.configuration.cols}`);

        if (this.configuration.fit) {
            // no scrolling, non‐square grid
            this.gridDiv.style.gridTemplateRows = `repeat(${this.configuration.rows}, 1fr)`;
            this.gridDiv.style.flex = '1';
            this.gridDiv.style.overflowY = 'hidden';
        } else {
            // square cells, scroll if too tall
            // compute: (100% − total gaps) / cols
            const gapPx = 2;
            const cols = this.configuration.cols;
            const totalGap = gapPx * (cols - 1);

            // this.gridDiv.style.setProperty('--og-cell-size', `calc((100% - ${totalGap}px) / ${cols})`);

            requestAnimationFrame(() => {
                const gridWidth = this.gridDiv.clientWidth;
                const cellSize = (gridWidth - totalGap) / cols;
                this.gridDiv.style.setProperty('--og-cell-size', `${cellSize}px`);
            });

            // each implicit AND explicit row is exactly one cell‐height:
            this.gridDiv.style.removeProperty('gridTemplateRows');
            this.gridDiv.style.gridAutoRows = 'var(--og-cell-size)';

            this.gridDiv.style.flex = '1';
            this.gridDiv.style.overflowY = 'auto';
            this.gridDiv.style.alignContent = 'start';
        }

        this.container.appendChild(this.gridDiv);
    }

    /* ===============================================================================================================*/
    getObjectByPath(path) {
        // Example:
        //   If this.id = "/category1/page1/groupG", and path = "subWidget"
        //   → childKey = "/category1/page1/groupG/subWidget"
        //   or path = "subGroupA/innermostWidget" → first pass childKey = "/category1/page1/groupG/subGroupA"
        //                                            then recurse with "innermostWidget"
        const [firstSegment, remainder] = (function (path) {
            const trimmed = path.replace(/^\/+|\/+$/g, '');
            if (trimmed === '') return ["", ""];
            const parts = trimmed.split('/');
            return [parts[0], parts.slice(1).join('/')];
        })(path);

        if (!firstSegment) {
            return null;
        }

        // Build the full‐UID key for this group’s direct child:
        //   this.id is "/category1/page1/groupG"
        //   firstSegment might be "subWidget" or "subGroupA"
        const childKey = `${this.id}/${firstSegment}`;

        // Now search this.objects (an array of { child, row, col, … })
        for (const entry of this.objects) {
            const child = entry.child; // child.id is full UID, e.g. "/category1/page1/groupG/subWidget"
            if (child.id === childKey) {
                if (!remainder) {
                    // No more path → return that child
                    return child;
                }
                // Otherwise, we must descend further—but only if it’s another ObjectGroup
                if (child instanceof ObjectGroup) {
                    return child.getObjectByPath(remainder);
                } else {
                    return null;
                }
            }
        }

        // If we never found a matching childKey, return null
        return null;
    }

    /* ===============================================================================================================*/
    /**
     * @param {Array<number>} grid_position - [column, row] start positions
     * @param {Array<number>} grid_size - [columnSpan, rowSpan] sizes
     * @returns {HTMLElement}
     */
    render(grid_position = null, grid_size = null) {
        if (grid_position && grid_size) {
            this.container.style.gridRowStart = `${grid_position[0] + 1}`;
            this.container.style.gridRowEnd = `span ${grid_size[1]}`;
            this.container.style.gridColumnStart = `${grid_position[1] + 1}`;
            this.container.style.gridColumnEnd = `span ${grid_size[0]}`;
        }
        this.element = this.container;

        this._recomputeOccupied();
        if (this.configuration.fillEmpty) {
            this._fillEmptySlots();
        }
        return this.container;
    }

    /* ===============================================================================================================*/
    addObject(child, row, col, width, height) {
        if (!(child instanceof GUI_Object)) {
            console.warn('ObjectGroup can only contain GUI_Object instances');
            return;
        }

        this.objects.push({child, row, col, width, height});

        const el = child.render([row, col], [width, height]);
        child.callbacks.event = (payload) => this._onChildEvent(payload);

        this.gridDiv.appendChild(el);

        child.callbacks.event = this._onChildEvent

        this._recomputeOccupied();
        if (this.configuration.fillEmpty) {
            this._fillEmptySlots();
        }
    }

    /* ===============================================================================================================*/
    removeObject(child) {
        const idx = this.objects.findIndex((c) => c.child === child);
        if (idx < 0) return;
        this.objects.splice(idx, 1);
        child.destroy();

        this._recomputeOccupied();
        if (this.configuration.fillEmpty) {
            this._fillEmptySlots();
        }
    }

    /* ===============================================================================================================*/
    _recomputeOccupied() {
        this._occupiedSet.clear();
        this.objects.forEach(({row, col, width, height}) => {
            for (let r = row; r < row + height; r++) {
                for (let c = col; c < col + width; c++) {
                    this._occupiedSet.add(`${r},${c}`);
                }
            }
        });
    }

    /* ===============================================================================================================*/
    _fillEmptySlots() {
        this.gridDiv
            .querySelectorAll('.placeholder')
            .forEach((el) => el.remove());

        for (let r = 0; r < this.configuration.rows; r++) {
            for (let c = 0; c < this.configuration.cols; c++) {
                const cellKey = `${r},${c}`;
                if (!this._occupiedSet.has(cellKey)) {
                    const ph = document.createElement('div');
                    ph.classList.add('placeholder');
                    ph.style.gridRowStart = `${r + 1}`;
                    ph.style.gridColumnStart = `${c + 1}`;
                    ph.style.zIndex = '0'; // behind real objects
                    this.gridDiv.appendChild(ph);
                }
            }
        }
    }

    /* ===============================================================================================================*/
    _onChildEvent(payload) {
        console.log('ObjectGroup received event:', payload);
        // this.groupEventHandler({groupId: this.id, ...payload});
    }

    getElement() {
        return undefined;
    }

    update(data) {
        return undefined;
    }

    assignListeners(element) {
    }
}

// =====================================================================================================================
export class MapWidget extends GUI_Object {
    constructor(id, config = {}) {
        super(id, config);

        const default_configuration = {}

        this.configuration = {...default_configuration, ...this.configuration};
        // const map_configuration = this.configuration.map_configuration;

        // Try to add the map
        const map_container = document.createElement('div');
        map_container.id = 'map_container';
        map_container.className = 'map-wrapper';
        this.map_container = map_container;
        createGridMapContainer(this.map_container, this.configuration);
    }

    assignListeners(element) {
    }

    getElement() {
        return this.map_container;
    }

    update(data) {
    }
}

// =====================================================================================================================
export class PlotWidget extends GUI_Object {
    constructor(id, config = {}) {
        super(id, config);

        const default_configuration = {}

        this.configuration = {...default_configuration, ...this.configuration};

        this.plot_container = document.createElement('div');
        this.plot_container.id = 'plot_container';
        this.plot_container.className = 'plot-wrapper';


        this.plot = new JSPlot(this.plot_container, this.configuration.config, this.configuration.plot_config);

    }

    assignListeners(element) {
    }

    configureElement(config = {}) {
        super.configureElement(config);
    }

    getElement() {
        return this.plot_container;
    }

    update(data) {

    }
}

// =====================================================================================================================
export class ButtonWidget extends GUI_Object {
    constructor(id, config = {}) {
        super(id, config);

        const default_configuration = {
            visible: true,
            color: 'rgba(79,170,108,0.81)',
            textColor: '#ffffff',
            fontSize: 12,
        }

        this.configuration = {...default_configuration, ...this.configuration};

        // State for long-click detection
        this.longClickTimer = null;
        this.longClickThreshold = 800; // ms
        this.longClickFired = false;

        // State for single-vs-double-click distinction
        this.clickTimer = null;
        this.clickDelay = 200; // ms

        // State for minimum “pressed” feedback duration
        this.minPressDuration = 100; // ms (adjust as needed)
        this._pressedTimestamp = 0;
        this._removePressedTimeout = null;

        this.element = document.createElement('button');
        this.element.id = this.id;

        this.configureElement(this.configuration);
        this.assignListeners(this.element);
    }

    configureElement(config = {}) {
        super.configureElement(config);

        const {text = '', icon = '', iconPosition = 'top'} = this.configuration;
        let html = '';
        if (icon && iconPosition === 'top') {
            html += `<div class="buttonIcon top">${icon}</div>`;
        }
        html += `<div class="buttonLabel${!icon ? ' full' : ''}">${text}</div>`;
        if (icon && iconPosition === 'center') {
            html += `<div class="buttonIcon center">${icon}</div>`;
        }

        this.element.classList.add('gridItem', 'buttonItem');
        this.element.style.backgroundColor = getColor(this.configuration.color);
        this.element.style.color = getColor(this.configuration.textColor);
        this.element.style.fontSize = `${this.configuration.fontSize}px`;

        if (!this.configuration.visible) {
            this.element.style.display = 'none';
        }
        this.element.innerHTML = html;
    }

    getElement() {
        return this.element;
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    update(data) {
        console.log('ButtonWidget update', data);
        this.configuration = {...this.configuration, ...data};
        this.configureElement(this.configuration);
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    assignListeners(element) {
        // SINGLE vs. DOUBLE CLICK
        element.addEventListener('click', (event) => {
            // If a long-click just fired, skip any click
            if (this.longClickFired) {
                this.longClickFired = false;
                return;
            }

            // event.detail === 1 for first click; === 2 for second click
            if (event.detail === 1) {
                // Start a timer to treat this as a single click unless a second click arrives
                this.clickTimer = setTimeout(() => {
                    this.handleClick();
                    this.clickTimer = null;
                }, this.clickDelay);
            } else if (event.detail === 2) {
                // Second click arrived quickly → cancel single-click timer
                if (this.clickTimer) {
                    clearTimeout(this.clickTimer);
                    this.clickTimer = null;
                }
            }
        });

        element.addEventListener('dblclick', () => {
            // If a single-click timer is pending, cancel it
            if (this.clickTimer) {
                clearTimeout(this.clickTimer);
                this.clickTimer = null;
            }
            this.handleDoubleClick();
        });

        // RIGHT CLICK (contextmenu)
        element.addEventListener('contextmenu', (event) => {
            event.preventDefault();
            this.handleRightClick();
        });

        // LONG CLICK (press-and-hold)
        element.addEventListener('mousedown', () => {
            this.longClickFired = false;
            this.longClickTimer = setTimeout(() => {
                this.handleLongClick();
                this.longClickFired = true;
            }, this.longClickThreshold);
        });

        element.addEventListener('mouseup', () => {
            if (this.longClickTimer) {
                clearTimeout(this.longClickTimer);
                this.longClickTimer = null;
            }
        });

        element.addEventListener('mouseleave', () => {
            if (this.longClickTimer) {
                clearTimeout(this.longClickTimer);
                this.longClickTimer = null;
            }
        });

        // UNIVERSAL “pressed” feedback with minimum duration
        element.addEventListener('pointerdown', (evt) => {
            // only care about the primary button/touch
            if (!evt.isPrimary) return;

            // record when we “pressed in”
            this._pressedTimestamp = performance.now();

            // clear any pending removal (in case a previous tap was still pending)
            if (this._removePressedTimeout) {
                clearTimeout(this._removePressedTimeout);
                this._removePressedTimeout = null;
            }

            element.classList.add('pressed');
        });

        element.addEventListener('pointerup', (evt) => {
            // compute how long it’s been “pressed”
            const now = performance.now();
            const elapsed = now - this._pressedTimestamp;
            const remaining = this.minPressDuration - elapsed;

            if (remaining > 0) {
                // still “too soon” to remove the class → wait the rest of the time
                this._removePressedTimeout = setTimeout(() => {
                    element.classList.remove('pressed');
                    this._removePressedTimeout = null;
                }, remaining);
            } else {
                // enough time has passed → remove immediately
                element.classList.remove('pressed');
            }
        });

        element.addEventListener('pointerleave', (evt) => {
            // If the pointer leaves before timeout, clear any pending removal
            if (this._removePressedTimeout) {
                clearTimeout(this._removePressedTimeout);
                this._removePressedTimeout = null;
            }
            element.classList.remove('pressed');
        });
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    handleClick() {
        this.callbacks.event({
            id: this.id,
            event: 'click',
            data: {},
        });
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    handleDoubleClick() {
        this.callbacks.event({
            id: this.id,
            event: 'doubleClick',
            data: {},
        });
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    handleLongClick() {
        this.callbacks.event({
            id: this.id,
            event: 'longClick',
            data: {},
        });
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    handleRightClick() {
        this.callbacks.event({
            id: this.id,
            event: 'rightClick',
            data: {},
        });
    }
}


// === MULTI STATE BUTTON =============================================================================================
// =====================================================================================================================
export class MultiStateButtonWidget extends GUI_Object {
    constructor(id, config = {}) {
        super(id, config);

        const defaults = {
            visible: true,
            color: [0.2, 0.3, 0.4],
            textColor: '#fff',
            states: [],
            state_index: 0,
            text: '',
            title: '',
        };
        this.configuration = {...defaults, ...this.configuration};


        this.element = this._initializeElement();

        this.configureElement(this.configuration);

        this.assignListeners(this.element);

    }

    /* ============================================================================================================== */
    _initializeElement() {
        const btn = document.createElement('button');
        btn.id = this.id;
        btn.classList.add('gridItem', 'buttonItem', 'multiStateButtonMain');
        btn.innerHTML = this._renderContent();
        return btn;
    }

    /* ============================================================================================================== */
    configureElement(config = {}) {
        super.configureElement(config);

        // clamp index
        this.configuration.state_index = Math.max(0, Math.min(this.configuration.states.length - 1, this.configuration.state_index));
        // derive label
        this.configuration.state = this.configuration.states.length ? this.configuration.states[this.configuration.state_index] : '';

        if (!this.configuration.visible) this.element.style.display = 'none';
        this.element.style.color = getColor(this.configuration.textColor);
        this.element.style.backgroundColor = getColor(this._getCurrentColor());
        this.element.innerHTML = this._renderContent();
    }

    /* ============================================================================================================== */
    /** returns either a single color or the per-state color */
    _getCurrentColor() {
        const {color, state_index, states} = this.configuration;

        if (!Array.isArray(color)) {
            return color;
        }

        // Check if it's an array of strings (like ['#fff', '#000'])
        if (typeof color[0] === 'string') {
            return color[state_index % color.length];
        }

        // Check if it's an array of arrays (like [[r,g,b], [r,g,b]])
        if (Array.isArray(color[0])) {
            return color[state_index % color.length];
        }

        // If it's just a single color as array of floats (like [r, g, b])
        if (typeof color[0] === 'number') {
            return color;
        }

        // Fallback (should not happen)
        return [0.5, 0.5, 0.5]; // default grey
    }

    /* ============================================================================================================== */

    // build inner HTML
    _renderContent() {
        const c = this.configuration;
        let html = `
      <span class="msbTitle">${c.title}</span>
      <span class="msbState">${c.state}</span>
      <div class="msbIndicators">
    `;

        c.states.forEach((stateName, i) => {
            const activeClass = (i === c.state_index) ? ' active' : '';
            // note: here we set data-tooltip="${stateName}" (not title)
            html += `
            <span
              class="msbIndicator${activeClass}"
              data-index="${i}"
              data-tooltip="${stateName}"
            ></span>
        `;
        });

        html += `</div>`;
        return html;
    }

    /* ============================================================================================================== */
    getElement() {
        return this.element;
    }

    /* ============================================================================================================== */
    update(data) {
        this.configuration = {...this.configuration, ...data};
        this.configureElement(this.configuration);

        // dot clickers
        this._attachIndicatorListeners();

    }

    /* ============================================================================================================== */
    assignListeners(el) {

        el.addEventListener('click', () => this._handleClick());

        // right-click → long click
        el.addEventListener('contextmenu', e => {
            e.preventDefault();
            this._handleRightClick();
        });

    }

    /* ============================================================================================================== */
    _attachIndicatorListeners() {
        this.element.querySelectorAll('.msbIndicator').forEach(dot => {
            dot.addEventListener('click', e => {
                e.stopPropagation();
                const idx = parseInt(dot.getAttribute('data-index'), 10);
                this._handleIndicatorClick(idx);
            });
        });
    }

    /* ============================================================================================================== */
    _handleClick() {
        this.callbacks.event({
            id: this.id,
            event: 'click',
            data: {},
        });
    }

    /* ============================================================================================================== */
    _handleRightClick() {
        this.callbacks.event({
            id: this.id,
            event: 'rightClick',
            data: {},
        });
    }

    /* ============================================================================================================== */
    _handleIndicatorClick(idx) {
        this.callbacks.event({
            id: this.id,
            event: 'indicatorClick',
            data: {index: idx},
        });
    }


    /* ============================================================================================================== */
    _advanceState(num) {
        const len = this.configuration.states.length;
        if (len === 0) return;
        const rawNext = (this.configuration.currentState + num) % len;
        const next = (rawNext + len) % len; // ensures result is non-negative
        this._setState(next);
    }

    /* ============================================================================================================== */
    _setState(index) {
        // if (index < 0 || index >= this.configuration.states.length) return;
        //
        // // update config
        // this.configuration.currentState = index;
        // this.configuration.state = this.configuration.states[index];
        //
        // // rebuild UI + restyle
        // this.element.style.backgroundColor = this._getCurrentColor();
        // this.element.innerHTML = this._renderContent();
        // this._attachIndicatorListeners();
        //
        // // notify
        // this.callbacks.event({
        //     id: this.id, event: 'multi_state_button_click', data: {
        //         currentState: index, state: this.configuration.state
        //     }
        // });
    }
}

// === SLIDER WIDGET ===================================================================================================
// =====================================================================================================================
export class SliderWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'slider'});
        const d = this.configuration;
        const defaults = {
            title: '',
            visible: true,
            color: '#333',
            textColor: '#fff',
            min: 0,
            max: 100,
            value: 0,
            increment: 1,
            direction: 'horizontal',
            continuousUpdates: false,
            limitToTicks: false,
            ticks: [],
            automaticReset: null
        };
        this.configuration = {...defaults, ...d};
    }

    getElement() {
        const c = this.configuration;
        const el = document.createElement('div');
        el.id = this.id;
        el.classList.add('gridItem', 'sliderWidget');
        if (!c.visible) el.style.display = 'none';
        el.style.backgroundColor = c.color;
        el.style.color = c.textColor;

        const inc = parseFloat(c.increment);
        const decimals = Math.max(0, (inc.toString().split('.')[1] || '').length);
        //
        // // — after “const decimals = …” in getHTML()
        // const minStr = Number(c.min).toFixed(decimals);
        // const maxStr = Number(c.max).toFixed(decimals);
        // const maxLen = Math.max(minStr.length, maxStr.length);
        // // expose e.g. “5th” if your longest label is 5 characters
        // el.style.setProperty('--value-width', `${maxLen}ch`);

        const valueType = inc % 1 === 0 ? 'int' : 'float';

        // dataset
        el.dataset.min = c.min;
        el.dataset.max = c.max;
        el.dataset.increment = inc;
        el.dataset.decimals = decimals;
        el.dataset.valueType = valueType;
        el.dataset.direction = c.direction;
        el.dataset.continuousUpdates = c.continuousUpdates;
        el.dataset.limitToTicks = c.limitToTicks;
        el.dataset.ticks = JSON.stringify(c.ticks);
        if (c.automaticReset != null) el.dataset.automaticReset = c.automaticReset;

        // initial fill & value
        const pct = ((c.value - c.min) / (c.max - c.min)) * 100;
        el.dataset.currentValue = c.value;

        el.innerHTML = `
  <span class="sliderTitle">${c.title || ''}</span>
  <div class="sliderFill" style="${c.direction === 'vertical' ? `height:${pct}%; width:100%; bottom:0; top:auto;` : `width:${pct}%; height:100%;`}"></div>
      <span class="sliderValue">${Number(c.value).toFixed(decimals)}</span>
      ${c.continuousUpdates ? '<div class="continuousIcon">🔄</div>' : ''}
    `;

        // ticks
        if (c.ticks.length) {
            c.ticks.forEach(v => {
                const tick = document.createElement('div');
                tick.className = 'sliderTick';
                const tPct = ((v - c.min) / (c.max - c.min)) * 100;
                if (c.direction === 'vertical') {
                    tick.style.top = `${100 - tPct}%`;
                    tick.style.width = '100%';
                } else {
                    tick.style.left = `${tPct}%`;
                    tick.style.height = '100%';
                }
                el.appendChild(tick);
            });
        }

        this.element = el;
        return el;
    }

    update(data) {
        if (data.value == null) return;
        const el = this.element;
        el.dataset.currentValue = data.value;
        const decimals = parseInt(el.dataset.decimals, 10);
        const vSpan = el.querySelector('.sliderValue');
        vSpan.textContent = Number(data.value).toFixed(decimals);

        const min = parseFloat(el.dataset.min);
        const max = parseFloat(el.dataset.max);
        const pct = ((data.value - min) / (max - min)) * 100;
        const fill = el.querySelector('.sliderFill');
        if (el.dataset.direction === 'vertical') fill.style.height = pct + '%'; else fill.style.width = pct + '%';
    }

    assignListeners(el) {
        let dragging = false, trackLength, direction = el.dataset.direction;
        let rect;

        const updateFromPointer = e => {
            const min = parseFloat(el.dataset.min);
            const max = parseFloat(el.dataset.max);
            const inc = parseFloat(el.dataset.increment);
            const decimals = parseInt(el.dataset.decimals, 10);
            const valueType = el.dataset.valueType;
            const fill = el.querySelector('.sliderFill');

            const pos = direction === 'vertical' ? (rect.bottom - e.clientY) : (e.clientX - rect.left);
            const rawPct = Math.max(0, Math.min(1, pos / trackLength));
            let raw = min + rawPct * (max - min);

            // snapping
            if (el.dataset.limitToTicks === 'true') {
                const ticks = JSON.parse(el.dataset.ticks);
                if (ticks.length) {
                    raw = ticks.reduce((p, c) => Math.abs(c - raw) < Math.abs(p - raw) ? c : p, ticks[0]);
                }
            } else {
                raw = Math.round(raw / inc) * inc;
                if (valueType === 'int') raw = Math.round(raw); else raw = parseFloat(raw.toFixed(decimals));
            }

            el.dataset.currentValue = raw;
            el.querySelector('.sliderValue').textContent = valueType === 'int' ? raw.toFixed(0) : raw.toFixed(decimals);

            const snappedPct = (raw - min) / (max - min);
            if (direction === 'vertical') fill.style.height = (snappedPct * 100) + '%'; else fill.style.width = (snappedPct * 100) + '%';

            return raw;
        };

        el.addEventListener('pointerdown', e => {
            if (el.dataset.continuousUpdates === 'true') {
                el.classList.add('dragging');
            }
            e.preventDefault();
            rect = el.getBoundingClientRect();
            trackLength = direction === 'vertical' ? rect.height : rect.width;
            dragging = true;
            el.setPointerCapture(e.pointerId);

            const newValue = updateFromPointer(e);
            if (el.dataset.continuousUpdates === 'true') this.callbacks.event({
                id: this.id, event: 'slider_change', data: {value: newValue}
            });
        });

        el.addEventListener('pointermove', e => {
            if (!dragging) return;
            const newValue = updateFromPointer(e);
            if (el.dataset.continuousUpdates === 'true') this.callbacks.event({
                id: this.id, event: 'slider_change', data: {value: newValue}
            });
        });

        el.addEventListener('pointerup', e => {
            dragging = false;
            el.releasePointerCapture(e.pointerId);
            const finalValue = parseFloat(el.dataset.currentValue);
            this.callbacks.event({id: this.id, event: 'slider_change', data: {value: finalValue}});

            if (el.dataset.automaticReset != null) {
                el.dataset.currentValue = el.dataset.automaticReset;
                this.update({value: parseFloat(el.dataset.automaticReset)});
            }

            if (el.dataset.continuousUpdates !== 'true') {
                el.classList.add('accepted');
                el.addEventListener('animationend', () => {
                    el.classList.remove('accepted');
                }, {once: true});
            }
            el.classList.remove('dragging');
        });
    }
}


// =====================================================================================================================
// MultiSelectWidget
// =====================================================================================================================
export class MultiSelectWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'multi_select'});

        const defaults = {
            visible: true, color: '#333',      // or an array of colors, matching options.length
            textColor: '#fff', title: '', options: [],        // [{ value, label }, …]
            value: null,        // the selected value
            lockable: false, locked: false, titlePosition: 'top',  // 'top' or 'left'
            titleStyle: 'bold'     // 'bold' or 'normal'
        };
        this.configuration = {...defaults, ...this.configuration};
        if (!this.configuration.lockable) {
            this.configuration.locked = false;
        }
    }

    /* ============================================================================================================== */
    _getCurrentColor() {
        const {color, options, value} = this.configuration;
        if (Array.isArray(color) && color.length === options.length) {
            const idx = options.findIndex(opt => opt.value === value);
            if (idx >= 0) return color[idx];
        }
        return color;
    }

    /* ============================================================================================================== */
    _getCurrentLabel() {
        const {options, value} = this.configuration;
        const found = options.find(opt => opt.value === value);
        return found ? found.label : '';
    }

    /* ============================================================================================================== */
    getElement() {
        const c = this.configuration;
        const container = document.createElement('div');
        container.id = this.id;
        container.classList.add('gridItem', 'multiSelectWidget');
        // expose position so CSS can pick it up
        container.dataset.titlePosition = c.titlePosition;

        if (!c.visible) container.style.display = 'none';
        container.style.backgroundColor = this._getCurrentColor();
        container.style.color = c.textColor;
        container.dataset.lockable = c.lockable;
        container.dataset.locked = c.locked;

        // build inner HTML
        let html = '';
        if (c.title) {
            html += `<span class="msSelectTitle">${c.title}</span>`;
        }
        html += `
          <span class="msSelectValue">${this._getCurrentLabel()}</span>
          <select></select>
          <span class="msSelectDropdown">&#x25BC;</span>
        `;
        container.innerHTML = html;

        // populate <select>
        const select = container.querySelector('select');
        c.options.forEach(opt => {
            const o = document.createElement('option');
            o.value = opt.value;
            o.textContent = opt.label;
            if (opt.value === c.value) o.selected = true;
            select.appendChild(o);
        });
        if (c.locked) select.disabled = true;

        // stretch the select invisibly
        Object.assign(select.style, {
            position: 'absolute',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            opacity: '0',
            cursor: 'pointer',
            zIndex: '1',
        });

        // arrow
        const arrow = container.querySelector('.msSelectDropdown');
        Object.assign(arrow.style, {
            position: 'absolute', bottom: '1px', right: '1px', pointerEvents: 'none', zIndex: '2',
        });

        // apply titleStyle (font‐weight) – font‐size and layout handled by CSS
        const titleEl = container.querySelector('.msSelectTitle');
        if (titleEl) {
            titleEl.style.fontWeight = (c.titleStyle === 'bold' ? 'bold' : 'normal');
        }

        this.element = container;
        return container;
    }

    /* ============================================================================================================== */
    update(data) {
        const c = this.configuration;
        const container = this.element;
        const select = container.querySelector('select');
        const valueEl = container.querySelector('.msSelectValue');

        // options
        if (data.options) {
            c.options = data.options;
            select.innerHTML = '';
            c.options.forEach(opt => {
                const o = document.createElement('option');
                o.value = opt.value;
                o.textContent = opt.label;
                select.appendChild(o);
            });
        }

        // value
        if (data.value !== undefined) {
            c.value = data.value;
            select.value = data.value;
            valueEl.textContent = this._getCurrentLabel();
        }

        // lock state
        if (data.locked !== undefined && c.lockable) {
            c.locked = data.locked;
            select.disabled = c.locked;
            container.dataset.locked = c.locked;
        }

        // colors
        if (data.color) c.color = data.color;
        if (data.textColor) c.textColor = data.textColor;
        container.style.backgroundColor = this._getCurrentColor();
        container.style.color = c.textColor;

        // title text
        let titleEl = container.querySelector('.msSelectTitle');
        if (data.title !== undefined) {
            c.title = data.title;
            if (c.title) {
                if (!titleEl) {
                    titleEl = document.createElement('span');
                    titleEl.classList.add('msSelectTitle');
                    container.insertBefore(titleEl, container.firstChild);
                }
                titleEl.textContent = c.title;
            } else if (titleEl) {
                titleEl.remove();
                titleEl = null;
            }
        }

        // titlePosition
        if (data.titlePosition && data.titlePosition !== c.titlePosition) {
            c.titlePosition = data.titlePosition;
            container.dataset.titlePosition = c.titlePosition;
        }

        // titleStyle
        if (data.titleStyle && data.titleStyle !== c.titleStyle) {
            c.titleStyle = data.titleStyle;
        }

        // reapply titleStyle only (layout via CSS)
        if (titleEl) {
            titleEl.style.cssText = '';
            titleEl.classList.add('msSelectTitle');
            titleEl.style.fontWeight = (c.titleStyle === 'bold' ? 'bold' : 'normal');
        }
    }

    /* ============================================================================================================== */
    assignListeners(container) {
        const select = container.querySelector('select');
        const c = this.configuration;
        const valueEl = container.querySelector('.msSelectValue');

        select.addEventListener('change', () => {
            c.value = select.value;
            valueEl.textContent = this._getCurrentLabel();
            this.callbacks.event({
                id: this.id, event: 'multi_select_change', data: {value: c.value},
            });
            container.style.backgroundColor = this._getCurrentColor();
            container.classList.add('accepted');
            container.addEventListener('animationend', () => {
                container.classList.remove('accepted');
            }, {once: true});
        });

        select.addEventListener('contextmenu', e => {
            if (c.lockable) e.preventDefault();
        });

        // long-press → long-click
        let longPressTimer;
        const LP = 500;
        const startPress = () => {
            longPressTimer = setTimeout(() => {
                this.callbacks.event({
                    id: this.id, event: 'multi_select_long_click', data: {},
                });
            }, LP);
        };
        const clearPress = () => clearTimeout(longPressTimer);

        container.addEventListener('mousedown', startPress);
        container.addEventListener('mouseup', clearPress);
        container.addEventListener('mouseleave', clearPress);
        container.addEventListener('touchstart', startPress, {passive: true});
        container.addEventListener('touchend', clearPress);
        container.addEventListener('touchcancel', clearPress);
    }
}

/* ============================================================================================================== */
/* ============================================================================================================== */

/* ============================================================================================================== */
export class RotaryDialWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'rotary_dial'});

        const d = this.configuration;
        const defaults = {
            visible: true,
            color: '#333',
            dialColor: '#3399FF',
            textColor: '#fff',
            title: '',
            titlePosition: 'top',   // only 'top' or 'left'
            min: 0,
            max: 100,
            value: 0,
            ticks: [],
            increment: 1,
            continuousUpdates: false,
            limitToTicks: false,
            dialWidth: 5           // <— new: thickness of the dial arc
        };

        // enforce only 'top' or 'left'
        const pos = d.titlePosition === 'left' ? 'left' : 'top';
        this.configuration = {...defaults, ...d, titlePosition: pos};
    }

    /* ============================================================================================================== */
    _deg2rad(deg) {
        return (deg * Math.PI) / 180;
    }

    /* ============================================================================================================== */
    _drawDial(el) {
        const canvas = el.querySelector('canvas');
        const ctx = canvas.getContext('2d');
        const w = canvas.clientWidth, h = canvas.clientHeight;
        const cx = w / 2, cy = h / 2;
        const radius = Math.min(w, h) / 2 * 0.8;

        const minVal = +el.dataset.min;
        const maxVal = +el.dataset.max;
        const curVal = +el.dataset.value;
        const ticks = JSON.parse(el.dataset.ticks);
        const clr = el.dataset.dialColor;
        const dialWidth = +el.dataset.dialWidth;

        const gapDeg = 20;
        const startAngle = this._deg2rad(90 + gapDeg / 2);
        const endAngle = this._deg2rad(450 - gapDeg / 2);
        const totalAngle = endAngle <= startAngle ? endAngle + 2 * Math.PI - startAngle : endAngle - startAngle;

        ctx.clearRect(0, 0, w, h);

        // — background arc
        ctx.lineWidth = dialWidth;
        ctx.strokeStyle = '#555';
        ctx.beginPath();
        ctx.arc(cx, cy, radius, startAngle, startAngle + totalAngle);
        ctx.stroke();

        // — filled arc
        const pct = (curVal - minVal) / (maxVal - minVal);
        ctx.strokeStyle = clr;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, startAngle, startAngle + totalAngle * pct);
        ctx.stroke();

        // — tick marks
        ctx.lineWidth = 1;
        ctx.strokeStyle = clr;
        ticks.forEach(v => {
            const tPct = (v - minVal) / (maxVal - minVal);
            const ang = startAngle + totalAngle * tPct;
            const x1 = cx + Math.cos(ang) * (radius + 2);
            const y1 = cy + Math.sin(ang) * (radius + 2);
            const x2 = cx + Math.cos(ang) * (radius - 4);
            const y2 = cy + Math.sin(ang) * (radius - 4);
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
        });
    }

    /* ============================================================================================================== */
    _valueFromAngle(el, e) {
        const canvas = el.querySelector('canvas');
        const r = canvas.getBoundingClientRect();
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        let dx = e.clientX - cx, dy = e.clientY - cy;
        let ang = Math.atan2(dy, dx);
        if (ang < 0) ang += 2 * Math.PI;

        const minVal = +el.dataset.min;
        const maxVal = +el.dataset.max;
        const inc = +el.dataset.increment;
        const dec = +el.dataset.decimals;
        const ticks = JSON.parse(el.dataset.ticks);
        const limit = el.dataset.limitToTicks === 'true';

        const gapDeg = 20;
        const startAngle = this._deg2rad(90 + gapDeg / 2);
        const endAngle = this._deg2rad(450 - gapDeg / 2);
        const totalAngle = endAngle <= startAngle ? endAngle + 2 * Math.PI - startAngle : endAngle - startAngle;

        let delta = ang - startAngle;
        if (delta < 0) delta += 2 * Math.PI;
        delta = Math.min(delta, totalAngle);

        let raw = minVal + (delta / totalAngle) * (maxVal - minVal);

        if (limit && ticks.length) {
            raw = ticks.reduce((p, c) => Math.abs(c - raw) < Math.abs(p - raw) ? c : p, ticks[0]);
        } else {
            raw = Math.round(raw / inc) * inc;
            raw = parseFloat(raw.toFixed(dec));
        }

        return Math.max(minVal, Math.min(maxVal, raw));
    }

    /* ============================================================================================================== */
    checkGridSize(grid_size) {
        const {titlePosition} = this.configuration;
        return !(titlePosition === 'left' && (!grid_size || grid_size[0] < 2));
    }

    /* ============================================================================================================== */
    getElement() {

        const c = this.configuration;
        // if left‐title but not wide enough, bail out with an empty container

        const el = document.createElement('div');
        el.id = this.id;
        el.classList.add('gridItem', 'rotaryDialWidget');
        if (!c.visible) el.style.display = 'none';
        el.style.backgroundColor = c.color;
        el.style.color = c.textColor;

        const inc = +c.increment;
        const dec = Math.max(0, (inc.toString().split('.')[1] || '').length);


        el.dataset.min = c.min;
        el.dataset.max = c.max;
        el.dataset.value = c.value;
        el.dataset.ticks = JSON.stringify(c.ticks);
        el.dataset.dialColor = c.dialColor;
        el.dataset.increment = inc;
        el.dataset.decimals = dec;
        el.dataset.continuousUpdates = c.continuousUpdates;
        el.dataset.limitToTicks = c.limitToTicks;
        el.dataset.titlePosition = c.titlePosition;
        el.dataset.dialWidth = c.dialWidth;

        const disp = (inc % 1 === 0) ? c.value : Number(c.value).toFixed(dec);

        el.innerHTML = `
      <span class="rotaryTitle">${c.title}</span>
      <div class="dialWrapper">
        <canvas></canvas>
        <div class="value">${disp}</div>
      </div>
      ${c.continuousUpdates ? '<div class="continuousIcon">🔄</div>' : ''}
    `;

        this.element = el;
        return el;
    }

    /* ============================================================================================================== */
    update(data) {
        if (data.value == null) return;
        const el = this.element;
        el.dataset.value = data.value;
        const dec = +el.dataset.decimals;
        const inc = +el.dataset.increment;

        el.querySelector('.value').textContent = (inc % 1 === 0) ? parseInt(data.value, 10) : Number(data.value).toFixed(dec);

        this._drawDial(el);
    }

    /* ============================================================================================================== */
    assignListeners(el) {
        // initial draw
        requestAnimationFrame(() => {
            const canvas = el.querySelector('canvas');
            const r = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            canvas.width = r.width * dpr;
            canvas.height = r.height * dpr;
            canvas.getContext('2d').scale(dpr, dpr);
            this._drawDial(el);
        });

        const canvas = el.querySelector('canvas');
        const inc = +el.dataset.increment;
        const cont = el.dataset.continuousUpdates === 'true';
        let startX = null, startVal = null, moved = false;

        const onDown = e => {
            moved = false;
            startX = e.clientX;
            startVal = +el.dataset.value;
            el.classList.add('dragging');
            // if (cont) el.classList.add('dragging');
            canvas.setPointerCapture(e.pointerId);
        };
        const onMove = e => {
            if (startX == null) return;
            moved = true;
            const dx = e.clientX - startX;
            const minVal = +el.dataset.min, maxVal = +el.dataset.max;
            const ticks = JSON.parse(el.dataset.ticks);
            const limit = el.dataset.limitToTicks === 'true';

            let raw = startVal + (dx / 150) * (maxVal - minVal);
            if (limit && ticks.length) {
                raw = ticks.reduce((p, c) => Math.abs(c - raw) < Math.abs(p - raw) ? c : p, ticks[0]);
            } else {
                raw = Math.round(raw / inc) * inc;
                raw = parseFloat(raw.toFixed(+el.dataset.decimals));
            }
            raw = Math.max(minVal, Math.min(maxVal, raw));

            el.dataset.value = raw;
            el.querySelector('.value').textContent = (inc % 1 === 0) ? raw : raw.toFixed(+el.dataset.decimals);
            this._drawDial(el);

            if (cont && raw !== el._last) {
                this.callbacks.event({id: this.id, event: 'rotary_dial_change', data: {value: raw}});
                el._last = raw;
            }
        };
        const onUp = e => {
            canvas.releasePointerCapture(e.pointerId);
            startX = null;
            const final = +el.dataset.value;
            this.callbacks.event({id: this.id, event: 'rotary_dial_change', data: {value: final}});
            if (!cont) {
                el.classList.add('accepted');
                el.addEventListener('animationend', () => el.classList.remove('accepted'), {once: true});
            }
            el.classList.remove('dragging');
        };

        canvas.addEventListener('pointerdown', onDown);
        canvas.addEventListener('pointermove', onMove);
        canvas.addEventListener('pointerup', onUp);
        canvas.addEventListener('pointercancel', onUp);

        // click‐to‐set
        canvas.addEventListener('click', e => {
            if (moved) return;
            const v = this._valueFromAngle(el, e);
            el.dataset.value = v;
            el.querySelector('.value').textContent = (inc % 1 === 0) ? v : v.toFixed(+el.dataset.decimals);
            this._drawDial(el);
            this.callbacks.event({id: this.id, event: 'rotary_dial_change', data: {value: v}});
        });
    }
}

/* ============================================================================================================== */
/* ============================================================================================================== */

/* ============================================================================================================== */
export class ClassicSliderWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'classic_slider'});
        const d = this.configuration;
        const defaults = {
            title: '',
            titlePosition: 'top',
            valuePosition: 'center',
            visible: true,
            backgroundColor: '#444',
            stemColor: '#888',
            handleColor: '#ccc',
            textColor: '#fff',
            min: 0,
            max: 100,
            value: 0,
            increment: 1,
            direction: 'horizontal',
            continuousUpdates: false,
            limitToTicks: false,
            ticks: [],
            automaticReset: null
        };
        this.configuration = {...defaults, ...d};
    }

    getElement() {
        const c = this.configuration;
        const el = document.createElement('div');
        el.id = this.id;
        el.classList.add('gridItem', 'classicSliderWidget');
        if (!c.visible) el.style.display = 'none';
        el.style.backgroundColor = c.backgroundColor;
        el.style.color = c.textColor;
        el.style.setProperty('--stem-color', c.stemColor);
        el.style.setProperty('--handle-color', c.handleColor);

        // layout flags
        el.dataset.titlePosition = c.titlePosition;
        el.dataset.valuePosition = c.valuePosition;
        el.dataset.direction = c.direction;
        el.dataset.continuousUpdates = c.continuousUpdates;
        el.dataset.limitToTicks = c.limitToTicks;

        // numeric metadata
        const inc = parseFloat(c.increment);
        const decimals = Math.max(0, (inc.toString().split('.')[1] || '').length);
        el.dataset.min = c.min;
        el.dataset.max = c.max;
        el.dataset.increment = inc;
        el.dataset.decimals = decimals;
        el.dataset.ticks = JSON.stringify(c.ticks);
        if (c.automaticReset != null) el.dataset.automaticReset = c.automaticReset;

        // compute max label width
        const minStr = Number(c.min).toFixed(decimals);
        const maxStr = Number(c.max).toFixed(decimals);
        const maxLen = Math.max(minStr.length, maxStr.length);
        el.style.setProperty('--value-width', `${maxLen}ch`);

        // initial fill/handle pos
        const pct = ((c.value - c.min) / (c.max - c.min)) * 100;

        el.innerHTML = `
    <span class="csTitle">${c.title}</span>
    <div class="csMain">
      <div class="csSliderContainer">
        <div class="csStem"></div>
        <div class="csFill" style="${c.direction === 'vertical' ? `height:${pct}%;` : `width:${pct}%;`}"></div>
        <div class="csHandle" style="${c.direction === 'vertical' ? `bottom:${pct}%;` : `left:${pct}%;`}"></div>
      </div>
      <span class="csValue">${Number(c.value).toFixed(decimals)}</span>
      ${c.continuousUpdates ? '<div class="continuousIcon">🔄</div>' : ''}
    </div>
  `;

        // ticks
        if (c.ticks.length) {
            const track = el.querySelector('.csSliderContainer');
            c.ticks.forEach(v => {
                const t = document.createElement('div');
                t.className = 'csTick';
                const tPct = ((v - c.min) / (c.max - c.min)) * 100;
                if (c.direction === 'vertical') {
                    t.style.bottom = `${tPct}%`;
                } else {
                    t.style.left = `${tPct}%`;
                }
                track.appendChild(t);
            });
        }

        this.element = el;
        return el;
    }


    /* ============================================================================================================== */
    update(data) {
        if (data.value == null) return;
        const el = this.element;
        const raw = parseFloat(data.value);
        el.dataset.value = raw;

        const min = +el.dataset.min, max = +el.dataset.max, decimals = +el.dataset.decimals,
            pct = ((raw - min) / (max - min)) * 100;

        const fill = el.querySelector('.csFill'), handle = el.querySelector('.csHandle'),
            vSpan = el.querySelector('.csValue');

        vSpan.textContent = Number(raw).toFixed(decimals);

        if (el.dataset.direction === 'vertical') {
            fill.style.height = `${pct}%`;
            handle.style.bottom = `${pct}%`;
        } else {
            fill.style.width = `${pct}%`;
            handle.style.left = `${pct}%`;
        }
    }

    /* ============================================================================================================== */
    assignListeners(el) {
        let dragging = false, trackLength, rect;
        const dir = el.dataset.direction;
        const trackEl = el.querySelector('.csSliderContainer');

        const updateFromPointer = e => {
            const min = +el.dataset.min, max = +el.dataset.max, inc = +el.dataset.increment,
                decimals = +el.dataset.decimals;

            let raw = dir === 'vertical' ? ((rect.bottom - e.clientY) / trackLength) * (max - min) + min : ((e.clientX - rect.left) / trackLength) * (max - min) + min;

            if (el.dataset.limitToTicks === 'true') {
                const ticks = JSON.parse(el.dataset.ticks);
                if (ticks.length) {
                    raw = ticks.reduce((p, c) => Math.abs(c - raw) < Math.abs(p - raw) ? c : p, ticks[0]);
                }
            } else {
                raw = Math.round(raw / inc) * inc;
                raw = parseFloat(raw.toFixed(decimals));
            }
            raw = Math.max(min, Math.min(max, raw));
            this.update({value: raw});
            if (el.dataset.continuousUpdates === 'true') {
                this.callbacks.event({id: this.id, event: 'slider_change', data: {value: raw}});
            }
            return raw;
        };

        // only start drag when clicking on the bar
        trackEl.addEventListener('pointerdown', e => {
            e.preventDefault();
            rect = trackEl.getBoundingClientRect();
            trackLength = dir === 'vertical' ? rect.height : rect.width;
            dragging = true;
            el.setPointerCapture?.(e.pointerId);
            el.classList.add('dragging')
            // if (el.dataset.continuousUpdates === 'true') el.classList.add('dragging');
            updateFromPointer(e);
        });

        // continue anywhere over the widget
        el.addEventListener('pointermove', e => {
            if (!dragging) return;
            updateFromPointer(e);
        });

        el.addEventListener('pointerup', e => {
            if (!dragging) return;
            dragging = false;
            el.releasePointerCapture?.(e.pointerId);
            const final = +el.dataset.value;
            this.callbacks.event({id: this.id, event: 'slider_change', data: {value: final}});
            if (el.dataset.automaticReset != null) {
                this.update({value: +el.dataset.automaticReset});
            }
            el.classList.remove('dragging');
            if (el.dataset.continuousUpdates !== 'true') {
                el.classList.add('accepted');
                el.addEventListener('animationend', () => el.classList.remove('accepted'), {once: true});
            }
        });
    }
}


// =====================================================================================================================
// DigitalNumberWidget
// =====================================================================================================================
export class DigitalNumberWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'digital_number'});
        const d = this.configuration;
        const defaults = {
            title: '',
            visible: true,
            color: '#333',
            textColor: '#fff',
            min: 0,
            max: 100,
            value: 0,
            increment: 1,
            titlePosition: 'top',     // 'top' or 'left'
            valueColor: null,
            showUnusedDigits: true
        };
        this.configuration = {...defaults, ...d};
    }

    /* ============================================================================================================== */
    getElement() {
        const c = this.configuration;
        const el = document.createElement('div');
        el.id = this.id;
        el.classList.add('gridItem', 'digitalNumberWidget');
        el.dataset.titlePosition = c.titlePosition;
        if (!c.visible) el.style.display = 'none';
        el.style.backgroundColor = c.color;
        el.style.color = c.textColor;

        // compute decimals & maxLen (including sign if any)
        const inc = +c.increment;
        const decimals = Math.max(0, (inc.toString().split('.')[1] || '').length);
        const minStr = Number(c.min).toFixed(decimals);
        const maxStr = Number(c.max).toFixed(decimals);
        const maxLen = Math.max(minStr.length, maxStr.length);

        // numeric width excludes a minus if min<0
        const numericMaxLen = (c.min < 0) ? maxLen - 1 : maxLen;

        // store metadata
        el.dataset.increment = inc;
        el.dataset.decimals = decimals;
        el.dataset.maxLength = maxLen;
        el.dataset.numericMaxLength = numericMaxLen;

        // base font‐size
        let baseFs = Math.max(12, 30 - 2 * maxLen);
        if (c.titlePosition === 'left') baseFs += 4;

        // format (with optional zero padding)
        const formatInner = raw => {
            const s = decimals === 0 ? parseInt(raw, 10).toString() : Number(raw).toFixed(decimals);
            if (!c.showUnusedDigits) return s;
            // split sign from digits
            const sign = s[0] === '-' ? '-' : '';
            const digits = sign ? s.slice(1) : s;
            const pad = numericMaxLen - digits.length;
            const zeros = pad > 0 ? '0'.repeat(pad) : '';
            return sign + `<span class="leadingZero">${zeros}</span>${digits}`;
        };

        const initialRaw = Math.round(c.value / inc) * inc;
        const inner = formatInner(initialRaw);

        // valueColor or fallback
        const vc = c.valueColor || c.textColor;

        el.innerHTML = `
      <span class="digitalNumberTitle">${c.title}</span>
      <span
        class="digitalNumberValue"
        style="
          font-size:${baseFs}px;
          width:${maxLen}ch;
          color:${vc};
        ">${inner}
      </span>
    `;

        this.element = el;
        return el;
    }

    /* ============================================================================================================== */
    update(data) {
        if (data.value == null) return;
        const el = this.element;
        const inc = +el.dataset.increment;
        const dec = +el.dataset.decimals;
        // const maxLen = +el.dataset.maxLength;
        const numericMaxLen = +el.dataset.numericMaxLength;
        const c = this.configuration;

        let raw = Math.round(data.value / inc) * inc;
        const s = dec === 0 ? parseInt(String(raw), 10).toString() : Number(raw).toFixed(dec);

        let html;
        if (!c.showUnusedDigits) {
            html = s;
        } else {
            const sign = s[0] === '-' ? '-' : '';
            const digits = sign ? s.slice(1) : s;
            const pad = numericMaxLen - digits.length;
            const zeros = pad > 0 ? '0'.repeat(pad) : '';
            html = sign + `<span class="leadingZero">${zeros}</span>${digits}`;
        }

        el.querySelector('.digitalNumberValue').innerHTML = html;
    }

    /* ============================================================================================================== */
    assignListeners() {
        // display‐only
    }
}

/* ============================================================================================================== */
/* ============================================================================================================== */

/* ============================================================================================================== */
export class TextWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'text'});
        const d = this.configuration;
        const defaults = {
            visible: true,
            color: 'transparent',
            textColor: '#000',
            title: '',
            text: '',
            fontSize: '1em',
            fontFamily: 'inherit',
            verticalAlignment: 'center',   // top | center | bottom
            horizontalAlignment: 'center', // left | center | right
            fontWeight: 'normal',
            fontStyle: 'normal',
        };
        this.configuration = {...defaults, ...d};
    }

    /* ============================================================================================================== */
    getElement() {
        const c = this.configuration;
        const el = document.createElement('div');
        el.id = this.id;
        el.classList.add('gridItem', 'textWidget');
        if (!c.visible) el.style.display = 'none';

        // container‐level styling
        el.style.backgroundColor = c.color;
        el.style.color = c.textColor;
        el.style.fontSize = c.fontSize;
        el.style.fontFamily = c.fontFamily;
        el.style.fontWeight = c.fontWeight;
        el.style.fontStyle = c.fontStyle;

        // flex to align content
        el.style.display = 'flex';
        el.style.flexDirection = 'column';
        // vertical
        el.style.justifyContent = {
            top: 'flex-start', center: 'center', bottom: 'flex-end'
        }[c.verticalAlignment] || 'center';
        // horizontal
        el.style.alignItems = {
            left: 'flex-start', center: 'center', right: 'flex-end'
        }[c.horizontalAlignment] || 'center';

        // build inner HTML (title and formatted text)
        let html = '';
        if (c.title) {
            html += `<span class="textTitle">${c.title}</span>`;
        }
        html += `<div class="textContent">${c.text}</div>`;

        el.innerHTML = html;
        this.element = el;
        return el;
    }

    /* ============================================================================================================== */
    update(data) {
        // merge in new properties
        Object.assign(this.configuration, data);
        const c = this.configuration;
        const el = this.element;
        if (!el) return;

        // visibility
        el.style.display = c.visible ? '' : 'none';
        // styling
        el.style.backgroundColor = c.color;
        el.style.color = c.textColor;
        el.style.fontSize = c.fontSize;
        el.style.fontFamily = c.fontFamily;
        el.style.fontWeight = c.fontWeight;
        el.style.fontStyle = c.fontStyle;
        el.style.justifyContent = {
            top: 'flex-start', center: 'center', bottom: 'flex-end'
        }[c.verticalAlignment] || 'center';
        el.style.alignItems = {
            left: 'flex-start', center: 'center', right: 'flex-end'
        }[c.horizontalAlignment] || 'center';

        // content
        const titleEl = el.querySelector('.textTitle');
        if (c.title) {
            if (titleEl) titleEl.textContent = c.title; else {
                const span = document.createElement('span');
                span.className = 'textTitle';
                span.textContent = c.title;
                el.insertBefore(span, el.firstChild);
            }
        } else if (titleEl) {
            titleEl.remove();
        }

        const contentEl = el.querySelector('.textContent');
        contentEl.innerHTML = c.text;
    }

    /* ============================================================================================================== */
    assignListeners() {
        // no interactions
    }
}

/* ============================================================================================================== */
/* ============================================================================================================== */

/* ============================================================================================================== */
export class TextInputWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'text_input'});
        const d = this.configuration;
        const defaults = {
            visible: true,
            color: 'transparent',
            textColor: '#000',
            textInputFieldColor: '#fff',
            inputTextColor: '#000',
            title: '',
            titlePosition: 'top',   // 'top' or 'left'
            datatype: null,         // 'int' | 'float' | null
            value: '',
            validator: null
        };
        this.configuration = {...defaults, ...d};
        this._prevValue = this.configuration.value;
    }

    /* ============================================================================================================== */
    getElement() {
        const c = this.configuration;
        const el = document.createElement('div');
        el.id = this.id;
        el.classList.add('gridItem', 'textInputWidget');
        el.dataset.titlePosition = c.titlePosition;
        if (!c.visible) el.style.display = 'none';

        // container & CSS variable styling
        el.style.backgroundColor = c.color;
        el.style.color = c.textColor;
        el.style.setProperty('--ti-field-bg', c.textInputFieldColor);
        el.style.setProperty('--ti-field-color', c.inputTextColor);

        // inner HTML
        let html = '';
        if (c.title) {
            html += `<span class="tiTitle">${c.title}</span>`;
        }
        html += `<input
      class="tiInput"
      type="text"
      value="${c.value}"
      autocomplete="off"
      autocapitalize="none"
      spellcheck="false"
    />`;

        el.innerHTML = html;
        this.element = el;
        return el;
    }

    /* ============================================================================================================== */
    update(data) {
        // handle external updates and color changes
        const c = this.configuration;
        Object.assign(c, data);
        const el = this.element;
        const input = el.querySelector('.tiInput');

        if (data.event === 'revert') {
            input.value = this._prevValue;
            return this._animateError();
        }

        if (data.textInputFieldColor) {
            el.style.setProperty('--ti-field-bg', data.textInputFieldColor);
        }
        if (data.inputTextColor) {
            el.style.setProperty('--ti-field-color', data.inputTextColor);
        }
        if (data.textColor) {
            el.style.color = data.textColor;
        }

        if (data.value !== undefined) {
            input.value = data.value;
            this._prevValue = data.value;
            this._animateAccepted();
        }
    }

    /* ============================================================================================================== */
    assignListeners(el) {
        const input = el.querySelector('.tiInput');

        const commit = () => {
            const v = input.value.trim();
            const dt = this.configuration.datatype;

            // validate
            if (dt === 'int' && !/^[-+]?\d+$/.test(v)) {
                input.value = this._prevValue;
                this._animateError();
                return;
            }
            if (dt === 'float' && !/^[-+]?\d+(\.\d+)?$/.test(v)) {
                input.value = this._prevValue;
                this._animateError();
                return;
            }

            if (this.configuration.validator) {
                const valid = this.configuration.validator(v);
                if (!valid) {
                    input.value = this._prevValue;
                    this._animateError();
                    return;
                }
            }

            // accept
            this._prevValue = v;
            this.callbacks.event({
                id: this.id, event: 'text_input_change', data: {value: v}
            });
            this._animateAccepted();
        };

        // ENTER: try to commit
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                commit();
                input.blur();
            }
        });

        // BLUR: always revert silently
        input.addEventListener('blur', () => {
            input.value = this._prevValue;
        });
    }

    /* ============================================================================================================== */
    _animateAccepted() {
        const el = this.element;
        el.classList.add('accepted');
        el.addEventListener('animationend', () => el.classList.remove('accepted'), {once: true});
    }

    /* ============================================================================================================== */
    _animateError() {
        const el = this.element;
        el.classList.add('error');
        el.addEventListener('animationend', () => el.classList.remove('error'), {once: true});
    }
}


/**
 * StatusWidget
 *
 * Displays a simple table of status markers, names, and status texts.
 *
 * Configuration parameters (via constructor opts. Configuration):
 *   - visible      {boolean}   : show/hide widget (default: true)
 *   - color        {string}    : background color (default: 'transparent')
 *   - textColor    {string}    : default text color (default: '#000')
 *   - items        {Array}     : list of rows; each is an object:
 *       • markerColor {string} : circle color
 *       • name        {string} : label text
 *       • nameColor   {string} : (optional) label color
 *       • status      {string} : status text
 *       • statusColor {string} : (optional) status text color
 *   - nameLength   {number|null}: fixes name-column width in “ch” (or null for auto)
 *   - fontSize     {string}    : base font size (e.g. '1em', '14px')
 *
 * Example instantiation:
 *   const statusWidget = new StatusWidget({
 *     id: 'sys-status',
 *     configuration: {
 *       color: '#222',
 *       textColor: '#eee',
 *       fontSize: '0.9em',
 *       nameLength: 12,
 *       items: [
 *         { markerColor:'#0f0', name:'Sensor A', status:'OK',   statusColor:'#0f0' },
 *         { markerColor:'#fa0', name:'Sensor B', status:'WARN', statusColor:'#fa0' },
 *         { markerColor:'#f00', name:'Sensor C', status:'DOWN', statusColor:'#f00' }
 *       ]
 *     },
 *     callbacks: { event: () => {} }
 *   });
 *
 * Two ways to update:
 *
 * 1) Change a single row in place:
 *    statusWidget.update({
 *      updatedItem: {
 *        index: 1,
 *        status: 'OFFLINE',
 *        statusColor: '#f00'
 *      }
 *    });
 *
 * 2) Replace the entire table:
 *    statusWidget.update({
 *      items: [
 *        { markerColor:'#0f0', name: 'Sensor A', status:'OK', statusColor:'#0f0' },
 *        { markerColor:'#f00', name: 'Sensor B', status:'DOWN', statusColor:'#f00' }
 *      ]
 *    });
 */
export class StatusWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'status'});
        const defaults = {
            visible: true, color: 'transparent', textColor: '#000', items: [],                   // [{ markerColor, name, nameColor, status, statusColor }, …]
            nameLength: null,            // number (ch) or null
            fontSize: '1em'              // new: base font size
        };
        this.configuration = {...defaults, ...this.configuration};
    }

    getElement() {
        const c = this.configuration;
        const container = document.createElement('div');
        container.id = this.id;
        container.classList.add('gridItem', 'statusWidget');
        if (!c.visible) container.style.display = 'none';
        container.style.backgroundColor = c.color;
        container.style.color = c.textColor;
        container.style.fontSize = c.fontSize;      // apply fontSize

        this._buildTable(container);
        this.element = container;
        return container;
    }

    _buildTable(container) {
        const {items, nameLength} = this.configuration;
        container.innerHTML = '';
        const table = document.createElement('table');
        const tbody = document.createElement('tbody');
        table.appendChild(tbody);

        if (items.length) {
            const rowHeight = 100 / items.length + '%';
            items.forEach(it => {
                const tr = document.createElement('tr');
                tr.style.height = rowHeight;

                const tdM = document.createElement('td');
                const mark = document.createElement('div');
                mark.classList.add('statusMarker');
                mark.style.backgroundColor = it.markerColor || '#fff';
                tdM.appendChild(mark);

                const tdN = document.createElement('td');
                tdN.textContent = it.name;
                if (it.nameColor) tdN.style.color = it.nameColor;
                if (nameLength != null) tdN.style.width = `${nameLength}ch`;

                const tdS = document.createElement('td');
                tdS.textContent = it.status;
                if (it.statusColor) tdS.style.color = it.statusColor;

                tr.append(tdM, tdN, tdS);
                tbody.appendChild(tr);
            });
        }

        container.appendChild(table);
    }

    update(data) {
        // merge global settings
        if (data.color) this.configuration.color = data.color;
        if (data.textColor) this.configuration.textColor = data.textColor;
        if (data.fontSize) this.configuration.fontSize = data.fontSize;
        if (data.nameLength !== undefined) this.configuration.nameLength = data.nameLength;

        // item array or single‐item update
        if (data.items) {
            this.configuration.items = data.items;
        } else if (data.updatedItem) {
            const {index, ...fields} = data.updatedItem;
            Object.assign(this.configuration.items[index], fields);
        }

        // restyle
        const el = this.element;
        el.style.backgroundColor = this.configuration.color;
        el.style.color = this.configuration.textColor;
        el.style.fontSize = this.configuration.fontSize;

        // rebuild
        this._buildTable(el);
    }

    assignListeners() {
        // no interactions
    }
}


// === TABLE WIDGET ===================================================================
export class TableWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'table'});
        const d = this.configuration;
        const defaults = {
            columns: [],                // { id, name, width?, fontSize?, textColor?, columnColor?,
                                        //   headerFontSize?, headerColor?, headerTextColor? }
            showHeader: true, fit: true,                  // true = no scroll; false = vertical scroll
            lineWidth: 1,               // px; 0 = no lines
            lineColor: '#ccc', cellColor: 'transparent',   // default cell bg
            rows: [],

            // new globals ↓
            fontSize: '1em',            // default cell font-size
            headerFontSize: '1em',      // default header font-size
            color: 'transparent',       // widget background
            textColor: '#000',          // default cell text color
            headerColor: '#f5f5f5',     // default header bg
            headerTextColor: '#000'     // default header text color
        };
        this.configuration = {...defaults, ...d};
    }

    getElement() {
        const c = this.configuration;
        const container = document.createElement('div');
        container.id = this.id;
        container.classList.add('gridItem', 'tableWidget');
        // widget styling
        container.style.backgroundColor = c.color;
        container.style.overflowY = c.fit ? 'hidden' : 'auto';
        container.style.fontSize = c.fontSize;
        container.style.color = c.textColor;

        const track = c.scrollbarTrackColor || c.color;
        const thumb = c.scrollbarThumbColor || shadeColor(c.color, -10);
        container.style.setProperty('--scrollbar-track', track);
        container.style.setProperty('--scrollbar-thumb', thumb);

        this._buildTable(container);
        this.element = container;
        return container;
    }

    _buildTable(container) {
        const c = this.configuration;
        container.innerHTML = '';

        const table = document.createElement('table');
        table.style.width = '100%';
        table.style.borderCollapse = 'collapse';
        table.style.tableLayout = 'fixed';

        // ─── HEADER ─────────────────────────────────────────────
        if (c.showHeader) {
            const thead = document.createElement('thead');
            const tr = document.createElement('tr');
            c.columns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col.name || col.id;
                if (col.width) th.style.width = col.width;
                // header font-size: column override or global
                th.style.fontSize = col.headerFontSize || c.headerFontSize;
                // header bg & text-color: column override or global
                th.style.backgroundColor = col.headerColor || c.headerColor;
                th.style.color = col.headerTextColor || c.headerTextColor;
                this._styleCellBorder(th);
                tr.appendChild(th);
            });
            thead.appendChild(tr);
            table.appendChild(thead);
        }

        // ─── BODY ────────────────────────────────────────────────
        const tbody = document.createElement('tbody');
        c.rows.forEach(row => {
            tbody.appendChild(this._createRow(row));
        });
        table.appendChild(tbody);

        container.appendChild(table);
    }

    _createRow(rowData) {
        const c = this.configuration;
        const tr = document.createElement('tr');
        c.columns.forEach(col => {
            const td = document.createElement('td');
            td.textContent = rowData[col.id] != null ? rowData[col.id] : '';
            // cell background: column override or global
            td.style.backgroundColor = col.columnColor || c.cellColor;
            // font-size: column override or global
            td.style.fontSize = col.fontSize || c.fontSize;
            // text color: column override or global
            td.style.color = col.textColor || c.textColor;
            this._styleCellBorder(td);
            tr.appendChild(td);
        });
        return tr;
    }

    _styleCellBorder(cell) {
        const c = this.configuration;
        if (c.lineWidth > 0) {
            cell.style.border = `${c.lineWidth}px solid ${c.lineColor}`;
        } else {
            cell.style.border = 'none';
        }
    }

    /* ===============================================================================================================*/
    update(data) {
        // replace the entire table
        if (data.rows) {
            this.configuration.rows = data.rows;
            this._buildTable(this.element);
            return;
        }

        const tbody = this.element.querySelector('tbody');

        // update a single row
        if (data.updatedRow) {
            const {index, row} = data.updatedRow;
            this.configuration.rows[index] = row;
            const oldTr = tbody.objects[index];
            if (oldTr) tbody.replaceChild(this._createRow(row), oldTr);
        }

        // add a row
        if (data.addedRow) {
            const {index, row} = data.addedRow;
            if (index != null && index < this.configuration.rows.length) {
                this.configuration.rows.splice(index, 0, row);
                tbody.insertBefore(this._createRow(row), tbody.objects[index]);
            } else {
                this.configuration.rows.push(row);
                tbody.appendChild(this._createRow(row));
            }
        }

        // remove a row
        if (data.removedRow != null) {
            const i = data.removedRow;
            this.configuration.rows.splice(i, 1);
            const tr = tbody.objects[i];
            if (tr) tbody.removeChild(tr);
        }
    }

    /* ===============================================================================================================*/
    assignListeners() {
        // no default interactions
    }
}

/* ================================================================================================================== */
/* ================================================================================================================== */


