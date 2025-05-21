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
                    id,
                    configuration,
                    type,
                    callbacks
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
            visible: true,
            color: 'rgba(79,170,108,0.81)',
            textColor: '#ffffff',
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
            id: this.id,
            event: 'click',
            data: {},
        })
    }
}

// =====================================================================================================================
// ====================================================================
// SliderWidget
// ====================================================================
export class SliderWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'slider'});
        const d = this.configuration;
        const defaults = {
            visible: true, color: '#333', textColor: '#fff',
            min: 0, max: 100, value: 0, precision: 0,
            direction: 'horizontal', continuousUpdates: false,
            limitToTicks: false, ticks: [], automaticReset: null
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

        // set-up dataset for listener code
        el.dataset.min = c.min;
        el.dataset.max = c.max;
        el.dataset.precision = c.precision;
        el.dataset.valueType = c.valueType || (c.precision === 0 ? 'int' : 'float');
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
      <div class="sliderFill" style="${c.direction === 'vertical'
            ? `height:${pct}%`
            : `width:${pct}%`}"></div>
      <span class="sliderValue">${Number(c.value).toFixed(c.precision)}</span>
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
        // backend pushes {value}
        if (data.value == null) return;
        const el = this.element;
        el.dataset.currentValue = data.value;
        const vSpan = el.querySelector('.sliderValue');
        vSpan.textContent = Number(data.value).toFixed(parseInt(el.dataset.precision, 10));

        const min = parseFloat(el.dataset.min);
        const max = parseFloat(el.dataset.max);
        const pct = ((data.value - min) / (max - min)) * 100;
        const fill = el.querySelector('.sliderFill');
        if (el.dataset.direction === 'vertical') fill.style.height = pct + '%';
        else fill.style.width = pct + '%';
    }

    assignListeners(el) {
        // very similar to inline attachSliderListeners
        let drag = false, startVal, startX, timer;
        const wsEvent = id => evt => {
            this.callbacks.event({id: this.id, event: evt, data: {}});
        };

        // long-press
        el.addEventListener('pointerdown', e => {
            timer = setTimeout(() => wsEvent(this.id)('slider_long_click'), 500);
            drag = true;
            startX = e.clientX;
            startVal = parseFloat(el.dataset.currentValue);
            el.setPointerCapture(e.pointerId);
        });
        el.addEventListener('pointermove', e => {
            if (!drag) return;
            clearTimeout(timer);
            const dx = e.clientX - startX;
            const min = parseFloat(el.dataset.min), max = parseFloat(el.dataset.max);
            let raw = startVal + (dx / 150) * (max - min);
            // snap...
            if (el.dataset.limitToTicks === 'true') {
                const ticks = JSON.parse(el.dataset.ticks);
                if (ticks.length) raw = ticks.reduce((p, c) =>
                    Math.abs(c - raw) < Math.abs(p - raw) ? c : p, ticks[0]);
            } else if (el.dataset.valueType === 'int') raw = Math.round(raw);
            else raw = parseFloat(raw.toFixed(parseInt(el.dataset.precision, 10)));
            raw = Math.max(min, Math.min(max, raw));
            // update UI
            el.dataset.currentValue = raw;
            el.querySelector('.sliderValue').textContent =
                Number(raw).toFixed(el.dataset.valueType === 'int' ? 0 : parseInt(el.dataset.precision, 10));
            const pct = ((raw - min) / (max - min)) * 100;
            if (el.dataset.direction === 'vertical') el.querySelector('.sliderFill').style.height = pct + '%';
            else el.querySelector('.sliderFill').style.width = pct + '%';

            // continuous
            if (el.dataset.continuousUpdates === 'true') {
                this.callbacks.event({id: this.id, event: 'slider_change', data: {value: raw}});
            }
        });
        el.addEventListener('pointerup', e => {
            clearTimeout(timer);
            drag = false;
            el.releasePointerCapture(e.pointerId);
            this.callbacks.event({id: this.id, event: 'slider_change', data: {value: el.dataset.currentValue}});
            // auto-reset?
            if (el.dataset.automaticReset != null) {
                el.dataset.currentValue = el.dataset.automaticReset;
                this.update({value: parseFloat(el.dataset.automaticReset)});
            }
        });
    }
}
