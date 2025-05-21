export class GUI_Object {
    /**
     * @param {Object} opts
     * @param {string} opts.id            – unique DOM id
     * @param {string} opts.type          – widget_type (e.g. "button", "slider", …)
     * @param {number[]} opts.gridSize    – [cols, rows]
     * @param {Object} opts.position      – { column, row }
     * @param {string} opts.color         – background color
     * @param {string} opts.textColor     – text / forecolor
     * @param {boolean} opts.lockable     – can be locked/unlocked
     * @param {boolean} opts.locked       – initial locked state
     * @param {boolean} opts.visible      – initial visibility
     * @param {Object} opts.data          – any widget-specific data
     */
    constructor({
                    id,
                    type,
                    gridSize,
                    position,
                    color,
                    textColor,
                    lockable = false,
                    locked = false,
                    visible = true,
                    data = {}
                }) {
        this.id = id;
        this.type = type;
        this.gridSize = gridSize;
        this.position = position;
        this.color = color;
        this.textColor = textColor;
        this.lockable = lockable;
        this.locked = locked;
        this.visible = visible;
        this.data = data;
        this.element = null;  // will hold the DOM node after render()
    }

    /**
     * Render this widget into its DOM element and return it.
     * Handles wrapper creation, grid positioning, styling, and wiring up listeners.
     */
    render() {
        const el = document.createElement('div');
        el.id = this.id;
        el.className = `gridItem ${this.type}`;
        // grid placement (CSS grid row/column are 1-based)
        el.style.gridColumnStart = this.position.column + 1;
        el.style.gridColumnEnd = `span ${this.gridSize[0]}`;
        el.style.gridRowStart = this.position.row + 1;
        el.style.gridRowEnd = `span ${this.gridSize[1]}`;

        // styling
        el.style.backgroundColor = this.color;
        el.style.color = this.textColor;
        if (!this.visible) el.style.display = 'none';

        // lockable state
        el.dataset.lockable = this.lockable;
        el.dataset.locked = this.locked;

        // inject the widget-specific inner HTML
        el.innerHTML = this.getInnerHTML();

        // keep reference and wire up
        this.element = el;
        this.attachCommonListeners();
        this.attachCustomListeners();

        return el;
    }

    /**
     * Subclasses must override to return the inner HTML fragment
     * (e.g. `<button>…</button>`, `<canvas>…</canvas>`, etc.)
     */
    getInnerHTML() {
        throw new Error('getInnerHTML() must be implemented by subclass');
    }

    /**
     * Attach any listeners that are common to all widgets
     * (lock/unlock, visibility toggles, etc.)
     */
    attachCommonListeners() {
        if (this.lockable) {
            // e.g. click on lock-icon to toggle locked state
            this.element.addEventListener('dblclick', () => {
                this.locked = !this.locked;
                this.element.dataset.locked = this.locked;
                // optionally re-render a lock icon…
            });
        }
    }

    /**
     * Subclasses override to wire up click, drag, change, etc.
     */
    attachCustomListeners() {
        // default no-op
    }

    /**
     * Update this widget’s data (e.g. new value, new ticks)
     * and re-render only the necessary parts.
     *
     * @param {Object} newData
     */
    update(newData) {
        Object.assign(this.data, newData);
        this.onDataUpdate();
    }

    /**
     * Subclasses override to reflect data changes in the DOM
     */
    onDataUpdate() {
        // default no-op
    }

    show() {
        this.visible = true;
        if (this.element) this.element.style.display = '';
    }

    hide() {
        this.visible = false;
        if (this.element) this.element.style.display = 'none';
    }

    /**
     * Remove this widget entirely
     */
    destroy() {
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        this.element = null;
    }
}


// ——— Subclass for simple buttons ———
export class ButtonWidget extends GUI_Object {
    /**
     * You can pass any of the GUI_Object opts plus:
     * @param {string} data.text        – button label
     * @param {string} [data.icon]      – optional emoji/icon
     * @param {'top'|'center'} [data.iconPosition]
     */
    constructor(opts) {
        // force type to “button”
        super({...opts, type: 'button'});
    }

    /**
     * Returns the inner HTML for a button:
     *  - .buttonIcon if you passed an icon
     *  - .buttonLabel always
     */
    getInnerHTML() {
        const {text = '', icon = '', iconPosition = 'top'} = this.data;
        let html = '';
        if (icon && iconPosition === 'top') {
            html += `<div class="buttonIcon top">${icon}</div>`;
        }
        html += `<div class="buttonLabel${!icon ? ' full' : ''}">${text}</div>`;
        if (icon && iconPosition === 'center') {
            html += `<div class="buttonIcon center">${icon}</div>`;
        }
        return html;
    }

    render() {
        const btn = document.createElement('button');
        btn.id = this.id;
        // Notice we use 'buttonItem' here, to match your CSS
        btn.classList.add('gridItem', 'buttonItem');
        // grid placement
        btn.style.gridColumnStart = this.position.column + 1;
        btn.style.gridColumnEnd = `span ${this.gridSize[0]}`;
        btn.style.gridRowStart = this.position.row + 1;
        btn.style.gridRowEnd = `span ${this.gridSize[1]}`;
        // styling
        btn.style.backgroundColor = this.color;
        btn.style.color = this.textColor;
        if (!this.visible) btn.style.display = 'none';
        btn.innerHTML = this.getInnerHTML();

        this.element = btn;
        this.attachCommonListeners();
        this.attachCustomListeners();
        return btn;
    }

    /**
     * Wire up click / double-click / long-press events
     */
    attachCustomListeners() {
        // uses your global helper from the original code
        attachCustomListeners(this.element, this.id, 'button');
    }

    /**
     * If you call widget.update({ text: 'New', color: '#0f0' })
     * this will patch the label and styling in place.
     */
    onDataUpdate() {
        // update text
        const labelEl = this.element.querySelector('.buttonLabel');
        if (labelEl && this.data.text !== undefined) {
            labelEl.textContent = this.data.text;
        }
        // update icon (if you ever change it dynamically)
        const iconEl = this.element.querySelector('.buttonIcon');
        if (iconEl && this.data.icon !== undefined) {
            iconEl.textContent = this.data.icon;
        }
        // update styles
        if (this.data.color) this.element.style.backgroundColor = this.data.color;
        if (this.data.textColor) this.element.style.color = this.data.textColor;
    }
}


function attachCustomListeners(element, id, baseType) {
    return;
    let clickTimer;
    let lastClickTime = 0;
    let longPressTimer;
    const longPressThreshold = 500, clickDelay = 250;
    let touchHandled = false;

    // function handleClick() {
    //     const now = Date.now();
    //     if (now - lastClickTime < clickDelay) {
    //         clearTimeout(clickTimer);
    //         if (ws && ws.readyState === WebSocket.OPEN) {
    //             ws.send(JSON.stringify({type: 'widget', event_type: baseType + "_double_click", id: id}));
    //         }
    //         lastClickTime = 0;
    //     } else {
    //         lastClickTime = now;
    //         clickTimer = setTimeout(function () {
    //             if (ws && ws.readyState === WebSocket.OPEN) {
    //                 ws.send(JSON.stringify({type: 'widget', event_type: baseType + "_click", id: id}));
    //             }
    //         }, clickDelay);
    //     }
    // }
    function handleClick() {
        // if it's editable_value, focus the input (leave current value)
        if (baseType === 'editable_value' && element.dataset.locked === 'false') {
            const inp = element.querySelector('.evInput');
            if (inp) inp.focus();
        }

        const now = Date.now();
        if (now - lastClickTime < clickDelay) {
            clearTimeout(clickTimer);
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'widget',
                    event_type: baseType + "_double_click",
                    id: id
                }));
            }
            lastClickTime = 0;
        } else {
            lastClickTime = now;
            clickTimer = setTimeout(function () {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'widget',
                        event_type: baseType + "_click",
                        id: id
                    }));
                }
            }, clickDelay);
        }
    }

    element.addEventListener("mousedown", function (e) {
        longPressTimer = setTimeout(function () {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'widget', event_type: baseType + "_long_click", id: id}));
            }
            element.dataset.longPressed = "true";
            // VISUAL FEEDBACK: blink just like the rotary-dial “accepted” animation
            element.classList.add('accepted');

            element.addEventListener('animationend', () => {
                element.classList.remove('accepted');
            }, {once: true});


            // If this is an editable_value, clear + focus the input
            if (baseType === 'editable_value' && element.dataset.locked === 'false') {
                const inp = element.querySelector('.evInput');
                if (inp) {
                    inp.value = '';
                    inp.focus();
                }
            }
        }, longPressThreshold);
    });
    element.addEventListener("mouseup", function (e) {
        clearTimeout(longPressTimer);
    });
    element.addEventListener("touchstart", function (e) {
        touchHandled = true;
        longPressTimer = setTimeout(function () {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'widget', event_type: baseType + "_long_click", id: id}));
            }
            element.dataset.longPressed = "true";

            // VISUAL FEEDBACK: blink just like the rotary-dial “accepted” animation
            element.classList.add('accepted');

            element.addEventListener('animationend', () => {
                element.classList.remove('accepted');
            }, {once: true});


            // If this is an editable_value, clear + focus the input
            if (baseType === 'editable_value' && element.dataset.locked === 'false') {
                const inp = element.querySelector('.evInput');
                if (inp) {
                    inp.value = '';
                    inp.focus();
                }
            }
        }, longPressThreshold);
    }, {passive: true});
    element.addEventListener("touchend", function (e) {
        clearTimeout(longPressTimer);
        if (isSwiping) {
            element.dataset.longPressed = "";
            return;
        }
        if (element.dataset.longPressed === "true") {
            element.dataset.longPressed = "";
            return;
        }
        handleClick();
    });
    element.addEventListener("touchcancel", function (e) {
        clearTimeout(longPressTimer);
    });
    element.addEventListener("click", function (e) {
        if (touchHandled) {
            touchHandled = false;
            return;
        }
        if (element.dataset.longPressed === "true") {
            element.dataset.longPressed = "";
            return;
        }
        handleClick();
    });
}