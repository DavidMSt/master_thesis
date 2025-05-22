export class GUI_Object {

    /** @type {string|null} */
    id = null;

    /** @type {HTMLElement|null} */
    element = null;  // will hold the DOM element

    /** @type {Object} */
    configuration = null;

    /** @type {Object} */
    callbacks = null;

    /**
     * @param {Object} opts
     * @param {string} opts.id            – unique id
     * @param {Object} opts.configuration
     * @param {Object} opts.callbacks
     * @param {string} opts.type
     */
    constructor({
                    id, configuration, type, callbacks
                }) {

        this.id = id;
        this.type = type;
        this.configuration = configuration;
        this.callbacks = callbacks;
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
                errorEl.style.gridColumnStart = String(grid_position[1] + 1);
                errorEl.style.gridColumnEnd = `span ${grid_size[0]}`;
                errorEl.style.gridRowStart = String(grid_position[0] + 1);
                errorEl.style.gridRowEnd = `span ${grid_size[1]}`;
            }

            this.element = errorEl;
            return errorEl;
        }

        const element = this.getHTML();
        if (grid_position && grid_size) {
            element.style.gridColumnStart = String(grid_position[1] + 1);
            element.style.gridColumnEnd = `span ${grid_size[0]}`;
            element.style.gridRowStart = String(grid_position[0] + 1);
            element.style.gridRowEnd = `span ${grid_size[1]}`;
        }
        this.assignListeners(element);
        return element;
    }

    /**
     * @abstract
     * @returns {HTMLElement}
     */
    getHTML() {
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
     * @param {HTMLElement} element
     */
    assignListeners(element) {
        throw new Error('assignListeners() must be implemented by subclass');
    }
}

// =====================================================================================================================
export class ButtonWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'button'});

        const default_configuration = {
            visible: true, color: 'rgba(79,170,108,0.81)', textColor: '#ffffff',
        }

        this.configuration = {...default_configuration, ...this.configuration};
    }

    getHTML() {

        const {text = '', icon = '', iconPosition = 'top'} = this.configuration;
        let html = '';
        if (icon && iconPosition === 'top') {
            html += `<div class="buttonIcon top">${icon}</div>`;
        }
        html += `<div class="buttonLabel${!icon ? ' full' : ''}">${text}</div>`;
        if (icon && iconPosition === 'center') {
            html += `<div class="buttonIcon center">${icon}</div>`;
        }

        const btn = document.createElement('button');
        btn.id = this.id;
        btn.classList.add('gridItem', 'buttonItem');
        btn.style.backgroundColor = this.configuration.color;
        btn.style.color = this.configuration.textColor;
        if (!this.configuration.visible) btn.style.display = 'none';

        btn.innerHTML = html;

        this.element = btn;

        return this.element;
    }


    update(data) {
        return undefined;
    }


    assignListeners(element) {
        element.addEventListener("click", (e) => {
            this.handleClick();
        });
    }

    handleClick() {
        this.callbacks.event({
            id: this.id, event: 'click', data: {},
        })
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

    getHTML() {
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
        // // expose e.g. “5ch” if your longest label is 5 characters
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
                id: this.id,
                event: 'slider_change',
                data: {value: newValue}
            });
        });

        el.addEventListener('pointermove', e => {
            if (!dragging) return;
            const newValue = updateFromPointer(e);
            if (el.dataset.continuousUpdates === 'true') this.callbacks.event({
                id: this.id,
                event: 'slider_change',
                data: {value: newValue}
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


export class MultiStateButtonWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'multi_state_button'});
        const d = this.configuration;
        const defaults = {
            visible: true, color: 'rgba(79,170,108,0.81)',  // can also be an array of colors
            textColor: '#fff', states: [], currentState: 0, text: '',
        };
        this.configuration = {...defaults, ...d};

        // clamp index
        this.configuration.currentState = Math.max(0, Math.min(this.configuration.states.length - 1, this.configuration.currentState));
        // derive label
        this.configuration.state = this.configuration.states.length ? this.configuration.states[this.configuration.currentState] : '';
    }

    /** returns either a single color or the per-state color */
    _getCurrentColor() {
        const {color, states, currentState} = this.configuration;
        if (Array.isArray(color) && color.length === states.length) {
            return color[currentState];
        }
        return color;
    }

    // build inner HTML
    _renderContent() {
        const c = this.configuration;
        let html = `
      <span class="msbTitle">${c.text}</span>
      <span class="msbState">${c.state}</span>
      <div class="msbIndicators">
    `;
        c.states.forEach((_, i) => {
            html += `<span class="msbIndicator${i === c.currentState ? ' active' : ''}" data-index="${i}"></span>`;
        });
        html += `</div>`;
        return html;
    }

    getHTML() {
        const c = this.configuration;
        const btn = document.createElement('button');
        btn.id = this.id;
        btn.classList.add('gridItem', 'buttonItem', 'multiStateButtonMain');
        if (!c.visible) btn.style.display = 'none';
        btn.style.backgroundColor = this._getCurrentColor();
        btn.style.color = c.textColor;
        btn.innerHTML = this._renderContent();
        this.element = btn;
        return btn;
    }

    update(data) {
        // merge new data
        if (data.states) this.configuration.states = data.states;
        if (typeof data.currentState === 'number') this.configuration.currentState = data.currentState;
        if (data.text !== undefined) this.configuration.text = data.text;
        if (data.state !== undefined) this.configuration.state = data.state;
        if (data.color) this.configuration.color = data.color;
        if (data.textColor) this.configuration.textColor = data.textColor;

        // clamp index again in case states changed
        this.configuration.currentState = Math.max(0, Math.min(this.configuration.states.length - 1, this.configuration.currentState));
        // derive label if needed
        this.configuration.state = this.configuration.states.length ? this.configuration.states[this.configuration.currentState] : '';

        // restyle & rebuild
        this.element.style.backgroundColor = this._getCurrentColor();
        this.element.style.color = this.configuration.textColor;
        this.element.innerHTML = this._renderContent();

        // re-attach dot clickers
        this._attachIndicatorListeners();
    }

    assignListeners(el) {
        // click anywhere (outside dots) → advance
        el.addEventListener('click', () => this._advanceState());

        // right-click → long click
        el.addEventListener('contextmenu', e => {
            e.preventDefault();
            this.callbacks.event({
                id: this.id, event: 'multi_state_button_long_click', data: {}
            });
        });

        // dot clickers
        this._attachIndicatorListeners();
    }

    _attachIndicatorListeners() {
        this.element.querySelectorAll('.msbIndicator').forEach(dot => {
            dot.addEventListener('click', e => {
                e.stopPropagation();
                const idx = parseInt(dot.getAttribute('data-index'), 10);
                this._setState(idx);
            });
        });
    }

    _advanceState() {
        const len = this.configuration.states.length;
        if (len === 0) return;
        const next = (this.configuration.currentState + 1) % len;
        this._setState(next);
    }

    _setState(index) {
        if (index < 0 || index >= this.configuration.states.length) return;

        // update config
        this.configuration.currentState = index;
        this.configuration.state = this.configuration.states[index];

        // rebuild UI + restyle
        this.element.style.backgroundColor = this._getCurrentColor();
        this.element.innerHTML = this._renderContent();
        this._attachIndicatorListeners();

        // notify
        this.callbacks.event({
            id: this.id, event: 'multi_state_button_click', data: {
                currentState: index, state: this.configuration.state
            }
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

    _getCurrentColor() {
        const {color, options, value} = this.configuration;
        if (Array.isArray(color) && color.length === options.length) {
            const idx = options.findIndex(opt => opt.value === value);
            if (idx >= 0) return color[idx];
        }
        return color;
    }

    _getCurrentLabel() {
        const {options, value} = this.configuration;
        const found = options.find(opt => opt.value === value);
        return found ? found.label : '';
    }

    getHTML() {
        const c = this.configuration;
        const container = document.createElement('div');
        container.id = this.id;
        container.classList.add('gridItem', 'multiSelectWidget');
        if (!c.visible) container.style.display = 'none';

        // base styling
        container.style.position = 'relative';
        container.style.backgroundColor = this._getCurrentColor();
        container.style.color = c.textColor;
        container.dataset.lockable = c.lockable;
        container.dataset.locked = c.locked;

        // make room for left‐positioned title if needed
        if (c.titlePosition === 'left') {
            container.style.display = 'flex';
            container.style.alignItems = 'center';
            container.style.justifyContent = 'space-between';
            container.style.padding = '0 8px';
        }

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

        // position arrow bottom-right
        const arrow = container.querySelector('.msSelectDropdown');
        Object.assign(arrow.style, {
            position: 'absolute', bottom: '1px', right: '1px', pointerEvents: 'none', zIndex: '2',
        });

        // now apply titlePosition & titleStyle
        const titleEl = container.querySelector('.msSelectTitle');
        if (titleEl) {
            // font‐weight
            titleEl.style.fontWeight = (c.titleStyle === 'bold' ? 'bold' : 'normal');

            if (c.titlePosition === 'left') {
                // override default absolute‐center CSS
                titleEl.style.position = 'static';
                titleEl.style.top = '';
                titleEl.style.left = '';
                titleEl.style.right = '';
                titleEl.style.textAlign = 'left';
                // value right-aligned
                const valueEl = container.querySelector('.msSelectValue');
                valueEl.style.flex = '1';
                valueEl.style.textAlign = 'right';
                valueEl.style.padding = '0 8px';
            } else {
                // top (default): absolute‐center
                titleEl.style.position = 'absolute';
                titleEl.style.top = '5px';
                titleEl.style.left = '0';
                titleEl.style.right = '0';
                titleEl.style.textAlign = 'center';
            }
        }

        this.element = container;
        return container;
    }

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
        }

        // titleStyle
        if (data.titleStyle && data.titleStyle !== c.titleStyle) {
            c.titleStyle = data.titleStyle;
        }

        // reapply title layout if it exists
        if (titleEl) {
            // clear previous inline overrides
            titleEl.style.cssText = '';
            // font‐weight
            titleEl.style.fontWeight = (c.titleStyle === 'bold' ? 'bold' : 'normal');

            if (c.titlePosition === 'left') {
                container.style.display = 'flex';
                container.style.alignItems = 'center';
                container.style.justifyContent = 'space-between';
                container.style.padding = '0 8px';

                titleEl.style.position = 'static';
                titleEl.style.textAlign = 'left';

                valueEl.style.flex = '1';
                valueEl.style.textAlign = 'right';
                valueEl.style.padding = '0 8px';
            } else {
                // top
                container.style.display = '';
                container.style.justifyContent = '';
                container.style.padding = '';

                titleEl.style.position = 'absolute';
                titleEl.style.top = '5px';
                titleEl.style.left = '0';
                titleEl.style.right = '0';
                titleEl.style.textAlign = 'center';

                valueEl.style.flex = '';
                valueEl.style.textAlign = '';
                valueEl.style.padding = '';
            }
        }
    }

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

        // long‐press → long-click
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

    _deg2rad(deg) {
        return (deg * Math.PI) / 180;
    }

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

    checkGridSize(grid_size) {
        const {titlePosition} = this.configuration;
        if (titlePosition === 'left' && (!grid_size || grid_size[0] < 2)) {
            return false;
        }
        return true;
    }

    getHTML() {

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

    update(data) {
        if (data.value == null) return;
        const el = this.element;
        el.dataset.value = data.value;
        const dec = +el.dataset.decimals;
        const inc = +el.dataset.increment;

        el.querySelector('.value').textContent = (inc % 1 === 0) ? parseInt(data.value, 10) : Number(data.value).toFixed(dec);

        this._drawDial(el);
    }

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
            if (cont) el.classList.add('dragging');
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
            const disp = (inc % 1 === 0) ? raw : raw.toFixed(+el.dataset.decimals);
            el.querySelector('.value').textContent = disp;
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
            const disp = (inc % 1 === 0) ? v : v.toFixed(+el.dataset.decimals);
            el.querySelector('.value').textContent = disp;
            this._drawDial(el);
            this.callbacks.event({id: this.id, event: 'rotary_dial_change', data: {value: v}});
        });
    }
}


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

    // getHTML() {
    //     const c = this.configuration;
    //     const el = document.createElement('div');
    //     el.id = this.id;
    //     el.classList.add('gridItem', 'classicSliderWidget');
    //     if (!c.visible) el.style.display = 'none';
    //     el.style.backgroundColor = c.backgroundColor;
    //     el.style.color = c.textColor;
    //     el.style.setProperty('--stem-color', c.stemColor);
    //     el.style.setProperty('--handle-color', c.handleColor);
    //
    //     // layout flags
    //     el.dataset.titlePosition = c.titlePosition;
    //     el.dataset.valuePosition = c.valuePosition;
    //     el.dataset.direction = c.direction;
    //     el.dataset.continuousUpdates = c.continuousUpdates;
    //     el.dataset.limitToTicks = c.limitToTicks;
    //
    //     // numeric metadata
    //     const inc = parseFloat(c.increment);
    //     const decimals = Math.max(0, (inc.toString().split('.')[1] || '').length);
    //     el.dataset.min = c.min;
    //     el.dataset.max = c.max;
    //     el.dataset.increment = inc;
    //     el.dataset.decimals = decimals;
    //     el.dataset.ticks = JSON.stringify(c.ticks);
    //     if (c.automaticReset != null) el.dataset.automaticReset = c.automaticReset;
    //
    //     // initial fill/handle pos
    //     const pct = ((c.value - c.min) / (c.max - c.min)) * 100;
    //
    //     el.innerHTML = `
    //   <span class="csTitle">${c.title}</span>
    //   <div class="csMain">
    //     <div class="csSliderContainer">
    //       <div class="csStem"></div>
    //       <div class="csFill" style="${c.direction === 'vertical' ? `height:${pct}%;` : `width:${pct}%;`}"></div>
    //       <div class="csHandle" style="${c.direction === 'vertical' ? `bottom:${pct}%;` : `left:${pct}%;`}"></div>
    //     </div>
    //     <span class="csValue">${Number(c.value).toFixed(decimals)}</span>
    //     ${c.continuousUpdates ? '<div class="continuousIcon">🔄</div>' : ''}
    //   </div>
    // `;
    //
    //     // ticks
    //     if (c.ticks.length) {
    //         const track = el.querySelector('.csSliderContainer');
    //         c.ticks.forEach(v => {
    //             const t = document.createElement('div');
    //             t.className = 'csTick';
    //             const tPct = ((v - c.min) / (c.max - c.min)) * 100;
    //             if (c.direction === 'vertical') {
    //                 t.style.bottom = `${tPct}%`;
    //             } else {
    //                 t.style.left = `${tPct}%`;
    //             }
    //             track.appendChild(t);
    //         });
    //     }
    //
    //     this.element = el;
    //     return el;
    // }

    // replace your existing ClassicSliderWidget.getHTML() with this:

    getHTML() {
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
            if (el.dataset.continuousUpdates === 'true') el.classList.add('dragging');
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



