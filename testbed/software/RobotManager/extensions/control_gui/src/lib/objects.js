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
// export class SliderWidget extends GUI_Object {
//     constructor(opts) {
//         super({...opts, type: 'slider'});
//         const d = this.configuration;
//         const defaults = {
//             visible: true, color: '#333', textColor: '#fff',
//             min: 0, max: 100, value: 0, increment: 1,
//             direction: 'horizontal', continuousUpdates: false,
//             limitToTicks: false, ticks: [], automaticReset: null
//         };
//         this.configuration = {...defaults, ...d};
//     }
//
//     getHTML() {
//         const c = this.configuration;
//         const el = document.createElement('div');
//         el.id = this.id;
//         el.classList.add('gridItem', 'sliderWidget');
//         if (!c.visible) el.style.display = 'none';
//         el.style.backgroundColor = c.color;
//         el.style.color = c.textColor;
//
//         // set-up dataset for listener code
//         el.dataset.min = c.min;
//         el.dataset.max = c.max;
//         el.dataset.precision = c.precision;
//         el.dataset.valueType = c.valueType || (c.precision === 0 ? 'int' : 'float');
//         el.dataset.direction = c.direction;
//         el.dataset.continuousUpdates = c.continuousUpdates;
//         el.dataset.limitToTicks = c.limitToTicks;
//         el.dataset.ticks = JSON.stringify(c.ticks);
//         if (c.automaticReset != null) el.dataset.automaticReset = c.automaticReset;
//
//         // initial fill & value
//         const pct = ((c.value - c.min) / (c.max - c.min)) * 100;
//         el.dataset.currentValue = c.value;
//
//         el.innerHTML = `
//   <span class="sliderTitle">${c.title || ''}</span>
//   <div class="sliderFill" style="${
//             c.direction === 'vertical'
//                 ? `height:${pct}%; width:100%; bottom:0; top:auto;`
//                 : `width:${pct}%; height:100%;`
//         }"></div>
//       <span class="sliderValue">${Number(c.value).toFixed(c.precision)}</span>
//     `;
//         // ticks
//         if (c.ticks.length) {
//             c.ticks.forEach(v => {
//                 const tick = document.createElement('div');
//                 tick.className = 'sliderTick';
//                 const tPct = ((v - c.min) / (c.max - c.min)) * 100;
//                 if (c.direction === 'vertical') {
//                     tick.style.top = `${100 - tPct}%`;
//                     tick.style.width = '100%';
//                 } else {
//                     tick.style.left = `${tPct}%`;
//                     tick.style.height = '100%';
//                 }
//                 el.appendChild(tick);
//             });
//         }
//
//         this.element = el;
//         return el;
//     }
//
//     update(data) {
//         // backend pushes {value}
//         if (data.value == null) return;
//         const el = this.element;
//         el.dataset.currentValue = data.value;
//         const vSpan = el.querySelector('.sliderValue');
//         vSpan.textContent = Number(data.value).toFixed(parseInt(el.dataset.precision, 10));
//
//         const min = parseFloat(el.dataset.min);
//         const max = parseFloat(el.dataset.max);
//         const pct = ((data.value - min) / (max - min)) * 100;
//         const fill = el.querySelector('.sliderFill');
//         if (el.dataset.direction === 'vertical') fill.style.height = pct + '%';
//         else fill.style.width = pct + '%';
//     }
//
//     assignListeners(el) {
//         let dragging = false, startVal, trackLength, direction = el.dataset.direction;
//         let rect, startPos;
//
//         const getPointerPos = e => direction === 'vertical'
//             ? (rect.bottom - e.clientY)    // distance from bottom = pct
//             : (e.clientX - rect.left);
//
//         const updateFromPointer = e => {
//             // grab constants
//             const min = parseFloat(el.dataset.min),
//                 max = parseFloat(el.dataset.max),
//                 prec = parseInt(el.dataset.precision, 10),
//                 valueType = el.dataset.valueType,
//                 fill = el.querySelector('.sliderFill');
//
//             // 1) pct from raw pointer pos
//             const pos = direction === 'vertical'
//                 ? (rect.bottom - e.clientY)
//                 : (e.clientX - rect.left);
//             const rawPct = Math.max(0, Math.min(1, pos / trackLength));
//
//             // 2) raw value before snapping
//             let raw = min + rawPct * (max - min);
//
//             // 3) snap raw
//             if (el.dataset.limitToTicks === 'true') {
//                 const ticks = JSON.parse(el.dataset.ticks);
//                 if (ticks.length) {
//                     raw = ticks.reduce((p, c) =>
//                             Math.abs(c - raw) < Math.abs(p - raw) ? c : p,
//                         ticks[0]);
//                 }
//             } else if (valueType === 'int') {
//                 raw = Math.round(raw);
//             } else {
//                 raw = parseFloat(raw.toFixed(prec));
//             }
//
//             // 4) write back
//             el.dataset.currentValue = raw;
//             el.querySelector('.sliderValue').textContent =
//                 raw.toFixed(valueType === 'int' ? 0 : prec);
//
//             // 5) recompute pct on the snapped value
//             const snappedPct = (raw - min) / (max - min);
//
//             // 6) draw fill at snappedPct
//             if (direction === 'vertical') {
//                 fill.style.height = (snappedPct * 100) + '%';
//             } else {
//                 fill.style.width = (snappedPct * 100) + '%';
//             }
//
//             return raw;
//         };
//
//
//         el.addEventListener('pointerdown', e => {
//
//             if (el.dataset.continuousUpdates === 'true') {
//                 el.classList.add('dragging');
//             }
//             e.preventDefault();
//             rect = el.getBoundingClientRect();
//             trackLength = direction === 'vertical'
//                 ? rect.height
//                 : rect.width;
//             startVal = parseFloat(el.dataset.currentValue);
//             startPos = getPointerPos(e);
//             dragging = true;
//             el.setPointerCapture(e.pointerId);
//
//             // *** this line gives you click-to-set ***
//             const newValue = updateFromPointer(e);
//             if (el.dataset.continuousUpdates === 'true')
//                 this.callbacks.event({id: this.id, event: 'slider_change', data: {value: newValue}});
//         });
//
//         el.addEventListener('pointermove', e => {
//             if (!dragging) return;
//             const newValue = updateFromPointer(e);
//             if (el.dataset.continuousUpdates === 'true')
//                 this.callbacks.event({id: this.id, event: 'slider_change', data: {value: newValue}});
//         });
//
//         el.addEventListener('pointerup', e => {
//             dragging = false;
//             el.releasePointerCapture(e.pointerId);
//             const finalValue = parseFloat(el.dataset.currentValue);
//             this.callbacks.event({id: this.id, event: 'slider_change', data: {value: finalValue}});
//
//             if (el.dataset.automaticReset != null) {
//                 el.dataset.currentValue = el.dataset.automaticReset;
//                 this.update({value: parseFloat(el.dataset.automaticReset)});
//             }
//
//             if (el.dataset.continuousUpdates !== 'true') {
//                 el.classList.add('accepted');
//                 // remove so the blink can re-trigger next time
//                 el.addEventListener('animationend', () => {
//                     el.classList.remove('accepted');
//                 }, {once: true});
//             }
//             // always clear dragging
//             el.classList.remove('dragging');
//
//         });
//     }
//
// }
export class SliderWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'slider'});
        const d = this.configuration;
        const defaults = {
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
  <div class="sliderFill" style="${
            c.direction === 'vertical'
                ? `height:${pct}%; width:100%; bottom:0; top:auto;`
                : `width:${pct}%; height:100%;`
        }"></div>
      <span class="sliderValue">${Number(c.value).toFixed(decimals)}</span>
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
        if (el.dataset.direction === 'vertical') fill.style.height = pct + '%';
        else fill.style.width = pct + '%';
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

            const pos = direction === 'vertical'
                ? (rect.bottom - e.clientY)
                : (e.clientX - rect.left);
            const rawPct = Math.max(0, Math.min(1, pos / trackLength));
            let raw = min + rawPct * (max - min);

            // snapping
            if (el.dataset.limitToTicks === 'true') {
                const ticks = JSON.parse(el.dataset.ticks);
                if (ticks.length) {
                    raw = ticks.reduce((p, c) =>
                            Math.abs(c - raw) < Math.abs(p - raw) ? c : p,
                        ticks[0]
                    );
                }
            } else {
                raw = Math.round(raw / inc) * inc;
                if (valueType === 'int') raw = Math.round(raw);
                else raw = parseFloat(raw.toFixed(decimals));
            }

            el.dataset.currentValue = raw;
            el.querySelector('.sliderValue').textContent =
                valueType === 'int' ? raw.toFixed(0) : raw.toFixed(decimals);

            const snappedPct = (raw - min) / (max - min);
            if (direction === 'vertical') fill.style.height = (snappedPct * 100) + '%';
            else fill.style.width = (snappedPct * 100) + '%';

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
            if (el.dataset.continuousUpdates === 'true')
                this.callbacks.event({id: this.id, event: 'slider_change', data: {value: newValue}});
        });

        el.addEventListener('pointermove', e => {
            if (!dragging) return;
            const newValue = updateFromPointer(e);
            if (el.dataset.continuousUpdates === 'true')
                this.callbacks.event({id: this.id, event: 'slider_change', data: {value: newValue}});
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


// ====================================================================
// MultiStateButtonWidget
// ====================================================================
// export class MultiStateButtonWidget extends GUI_Object {
//     constructor(opts) {
//         super({...opts, type: 'multi_state_button'});
//         const d = this.configuration;
//         const defaults = {
//             visible: true, color: 'rgba(79,170,108,0.81)', textColor: '#fff',
//             states: [], currentState: 0, text: '', state: ''
//         };
//         this.configuration = {...defaults, ...d};
//     }
//
//     getHTML() {
//         const c = this.configuration;
//         const btn = document.createElement('button');
//         btn.id = this.id;
//         btn.classList.add('gridItem', 'buttonItem', 'multiStateButtonMain');
//         if (!c.visible) btn.style.display = 'none';
//         btn.style.backgroundColor = c.color;
//         btn.style.color = c.textColor;
//         let html = `<span class="msbTitle">${c.text}</span>
//                 <span class="msbState">${c.state}</span>
//                 <div class="msbIndicators">`;
//         c.states.forEach((_, i) => {
//             html += `<span class="msbIndicator${i === c.currentState ? ' active' : ''}"></span>`;
//         });
//         html += '</div>';
//         btn.innerHTML = html;
//         this.element = btn;
//         return btn;
//     }
//
//     update(data) {
//         const btn = this.element;
//         btn.style.backgroundColor = data.color || btn.style.backgroundColor;
//         btn.style.color = data.textColor || btn.style.color;
//         // rebuild indicators
//         let html = `<span class="msbTitle">${data.text || ''}</span>
//                 <span class="msbState">${data.state || ''}</span>
//                 <div class="msbIndicators">`;
//         data.states.forEach((_, i) => {
//             html += `<span class="msbIndicator${i === data.currentState ? ' active' : ''}"></span>`;
//         });
//         html += '</div>';
//         btn.innerHTML = html;
//     }
//
//     assignListeners(el) {
//         el.addEventListener('click', () => this.callbacks.event({
//             id: this.id, event: 'multi_state_button_click', data: {}
//         }));
//         el.addEventListener('contextmenu', e => {
//             e.preventDefault();
//             this.callbacks.event({id: this.id, event: 'multi_state_button_long_click', data: {}});
//         });
//     }
// }
//
// export class MultiStateButtonWidget extends GUI_Object {
//     constructor(opts) {
//         super({...opts, type: 'multi_state_button'});
//         const d = this.configuration;
//         const defaults = {
//             visible: true,
//             color: 'rgba(79,170,108,0.81)',
//             textColor: '#fff',
//             states: [],
//             currentState: 0,
//             text: '',
//         };
//         this.configuration = {...defaults, ...d};
//
//         this.configuration.currentState = Math.max(0, Math.min(this.configuration.states.length - 1, this.configuration.currentState));
//         // derive the actual label from the array:
//         this.configuration.state = this.configuration.states.length ? this.configuration.states[this.configuration.currentState] : '';
//     }
//
//     // helper to build the innerHTML for title, state label and indicators
//     _renderContent() {
//         const c = this.configuration;
//         let html = `
//       <span class="msbTitle">${c.text}</span>
//       <span class="msbState">${c.state}</span>
//       <div class="msbIndicators">
//     `;
//         c.states.forEach((_, i) => {
//             html += `<span class="msbIndicator${i === c.currentState ? ' active' : ''}" data-index="${i}"></span>`;
//         });
//         html += `</div>`;
//         return html;
//     }
//
//     getHTML() {
//         const c = this.configuration;
//         const btn = document.createElement('button');
//         btn.id = this.id;
//         btn.classList.add('gridItem', 'buttonItem', 'multiStateButtonMain');
//         if (!c.visible) btn.style.display = 'none';
//         btn.style.backgroundColor = c.color;
//         btn.style.color = c.textColor;
//         btn.innerHTML = this._renderContent();
//         this.element = btn;
//         return btn;
//     }
//
//     update(data) {
//         // merge in any new data
//         if (data.states) this.configuration.states = data.states;
//         if (typeof data.currentState === 'number') this.configuration.currentState = data.currentState;
//         if (data.text !== undefined) this.configuration.text = data.text;
//         if (data.state !== undefined) this.configuration.state = data.state;
//         if (data.color) this.configuration.color = data.color;
//         if (data.textColor) this.configuration.textColor = data.textColor;
//
//         // restyle & rebuild
//         this.element.style.backgroundColor = this.configuration.color;
//         this.element.style.color = this.configuration.textColor;
//         this.element.innerHTML = this._renderContent();
//
//         // re-attach the little-dot click handlers
//         this._attachIndicatorListeners();
//     }
//
//     assignListeners(el) {
//         // click anywhere (outside of the little dots) → advance
//         el.addEventListener('click', () => this._advanceState());
//
//         // right-click → long click event
//         el.addEventListener('contextmenu', e => {
//             e.preventDefault();
//             this.callbacks.event({
//                 id: this.id,
//                 event: 'multi_state_button_long_click',
//                 data: {}
//             });
//         });
//
//         // attach the dot listeners
//         this._attachIndicatorListeners();
//     }
//
//     _attachIndicatorListeners() {
//         this.element.querySelectorAll('.msbIndicator').forEach(dot => {
//             dot.addEventListener('click', e => {
//                 e.stopPropagation();
//                 const idx = parseInt(dot.getAttribute('data-index'), 10);
//                 this._setState(idx);
//             });
//         });
//     }
//
//     _advanceState() {
//         const len = this.configuration.states.length;
//         if (len === 0) return;
//         const next = (this.configuration.currentState + 1) % len;
//         this._setState(next);
//     }
//
//     _setState(index) {
//         if (index < 0 || index >= this.configuration.states.length) return;
//
//         // update our config
//         this.configuration.currentState = index;
//         this.configuration.state = this.configuration.states[index];
//
//         // rebuild UI
//         this.element.innerHTML = this._renderContent();
//         this._attachIndicatorListeners();
//
//         // notify
//         this.callbacks.event({
//             id: this.id,
//             event: 'multi_state_button_click',
//             data: {
//                 currentState: index,
//                 state: this.configuration.state
//             }
//         });
//     }
// }

export class MultiStateButtonWidget extends GUI_Object {
    constructor(opts) {
        super({...opts, type: 'multi_state_button'});
        const d = this.configuration;
        const defaults = {
            visible: true,
            color: 'rgba(79,170,108,0.81)',  // can also be an array of colors
            textColor: '#fff',
            states: [],
            currentState: 0,
            text: '',
        };
        this.configuration = {...defaults, ...d};

        // clamp index
        this.configuration.currentState = Math.max(
            0,
            Math.min(
                this.configuration.states.length - 1,
                this.configuration.currentState
            )
        );
        // derive label
        this.configuration.state = this.configuration.states.length
            ? this.configuration.states[this.configuration.currentState]
            : '';
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
        this.configuration.currentState = Math.max(
            0,
            Math.min(
                this.configuration.states.length - 1,
                this.configuration.currentState
            )
        );
        // derive label if needed
        this.configuration.state = this.configuration.states.length
            ? this.configuration.states[this.configuration.currentState]
            : '';

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
                id: this.id,
                event: 'multi_state_button_long_click',
                data: {}
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
            id: this.id,
            event: 'multi_state_button_click',
            data: {
                currentState: index,
                state: this.configuration.state
            }
        });
    }
}

