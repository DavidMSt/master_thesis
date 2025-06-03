import {mountTerminal} from './terminal/terminal.js';
import {
    GUI_Object,
    ButtonWidget,
    SliderWidget,
    MultiStateButtonWidget,
    MultiSelectWidget,
    RotaryDialWidget,
    ClassicSliderWidget,
    DigitalNumberWidget,
    TextWidget,
    TextInputWidget,
    StatusWidget,
    TableWidget,
    ObjectGroup, MapWidget, PlotWidget
} from './objects.js'

import {simulateSine, splitPath} from './helpers.js';

const OBJECT_MAPPING = {
    'button': ButtonWidget,
    'slider': SliderWidget,
    'rotary_dial': RotaryDialWidget,
    'multi_state_button': MultiStateButtonWidget,
    'multi_select': MultiSelectWidget,
    'classic_slider': ClassicSliderWidget,
    'digital_number': DigitalNumberWidget,
    'text': TextWidget,
    'text_input': TextInputWidget,
    'status': StatusWidget,
    'table': TableWidget,
    'object_group': ObjectGroup,
    'map': MapWidget,
    'plot': PlotWidget,
}

const DEFAULT_BACKGROUND_COLOR = 'rgb(31,32,35)'
const DEBUG = true;

class ControlGUI_Page {

    /** @type {Object} */
    objects = {};

    /** @type {Object} */
    callbacks = {};

    /** @type {Object} */
    configuration = {};

    /** @type {string} */
    id = '';


    /** @type {HTMLElement | null} */
    grid = null;


    /** @type {HTMLElement | null} */
    button = null;

    constructor(id, configuration = {}, objects = {}) {
        this.id = id;

        const default_configuration = {
            rows: 18,
            columns: 50,
            fillEmptyCells: true,
            color: 'rgba(40,40,40,0.7)',
            backgroundColor: DEFAULT_BACKGROUND_COLOR,
            textColor: 'rgba(255,255,255,0.7)',
            name: id,
        }

        this.configuration = {...default_configuration, ...configuration};
        this.callbacks = {};
        this.objects = {};

        this.occupied_grid_cells = new Set();

        // Create the main grid container for this page that gets later swapped into the content container
        this.grid = document.createElement('div');
        this.grid.id = `page_${this.id}_grid`;
        this.grid.className = 'grid';

        // Make the number of rows and columns based on the configuration
        this.grid.style.gridTemplateRows = `repeat(${this.configuration.rows}, 1fr)`;
        this.grid.style.gridTemplateColumns = `repeat(${this.configuration.columns}, 1fr)`;

        this.grid.style.display = 'grid';

        // Fill the grid with empty cells
        if (this.configuration.fillEmptyCells) {
            this._fillContentGrid();
        }

        // Generate the button for this page that the category will later attach to the page bar
        this.button = this._generateButton();

        if (Object.keys(objects).length > 0) {
            this.buildObjectsFromDefinition(objects);
        }

    }

    /* ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯ */
    getObjectByPath(path) {
        // Example invocations:
        //   path = "button1"            → childKey = "/category1/page1/button1"
        //   path = "groupG/widgetX"     → childKey = "/category1/page1/groupG"
        //                                        then recurse with "widgetX"
        const [firstSegment, remainder] = splitPath(path);
        if (!firstSegment) {
            return null;
        }

        // Build the full‐UID key for the direct child:
        //   this.id is "/category1/page1"
        //   firstSegment might be "button1" or "groupG"
        const childKey = `${this.id}/${firstSegment}`;

        // Look up the widget or group in this.objects, which is keyed by full UID
        const child = this.objects[childKey];
        if (!child) {
            return null;
        }

        if (!remainder) {
            // No deeper path → return the widget or group itself
            return child;
        }

        // If there is more path to consume, the child must be an ObjectGroup
        if (child instanceof ObjectGroup) {
            return child.getObjectByPath(remainder);
        } else {
            // Cannot descend further if it’s not a group
            return null;
        }
    }

    /* ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯ */
    buildObjectsFromDefinition(objects) {
        for (const [id, config] of Object.entries(objects)) {
            this.buildObjectFromConfig(config);
        }
    }

    /* ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯ */
    buildObjectFromConfig(config) {
        const id = config.id;
        const type = config.type;
        const width = config.width;
        const height = config.height;
        const row = config.row;
        const col = config.column;
        const object_config = config.config;

        console.log(`Adding object ${id} of type ${type} at (${row},${col}) with config: ${object_config}`);

        // Check if the type is in the object mapping variable
        if (!OBJECT_MAPPING[type]) {
            console.warn(`Object type "${type}" is not defined.`);
            return;
        }

        const object_class = OBJECT_MAPPING[type];

        const object = new object_class(id, object_config);
        console.log(object);
        this.addObject(object, row, col, width, height);
    }

    /* ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯ */
    /**
     * Replace your old stub with this:
     * @param {GUI_Object} widget  — any widget subclass
     * @param {int} row
     * @param {int} col
     * @param {int} width
     * @param {int} height
     */
    addObject(widget, row, col, width, height) {
        if (!(widget instanceof GUI_Object)) {
            console.warn('Expected a GUI_Object, got:', widget);
            return;
        }

        if (!widget.id) {
            console.warn('Widget must have an ID');
            return;
        }

        if (this.objects[widget.id]) {
            console.warn(`Widget with ID "${widget.id}" already exists in the grid.`);
            return;
        }

        if (row < 0 || col < 0 || row >= this.configuration.rows || col >= this.configuration.columns) {
            console.warn(`Invalid grid coordinates: row=${row}, col=${col}`);
            return;
        }

        if (row + height - 1 > this.configuration.rows || col + width - 1 > this.configuration.columns) {
            console.warn(`Invalid grid dimensions: row=${row}, col=${col}, width=${width}, height=${height}`);
        }

        const newCells = this._getOccupiedCells(row, col, width, height);

        // Check for cell conflicts
        for (const cell of newCells) {
            if (this.occupied_grid_cells.has(cell)) {
                console.warn(`Grid cell ${cell} is already occupied. Cannot place widget "${widget.id}".`);
                return;
            }
        }

        // Mark the cells as occupied
        newCells.forEach(cell => this.occupied_grid_cells.add(cell));

        // Render the widget’s DOM and append into the main grid container
        const el = widget.render([row, col], [width, height]);
        this.grid.appendChild(el);
        this.objects[widget.id] = widget;

        widget.callbacks.event = this.onEvent.bind(this);

        if (this.configuration.fillEmptyCells) {
            this._fillContentGrid();
        }

    }

    /* -------------------------------------------------------------------------------------------------------------- */
    _generateButton() {
        let button = document.createElement('button');
        button.className = 'page_button';
        button.textContent = this.configuration.name;
        // button.style.backgroundColor = this.configuration.color;
        button.style.color = this.configuration.textColor;
        button.classList.add('not-selected');

        return button;
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    _getOccupiedCells(row, col, width, height) {
        const cells = [];
        for (let r = row; r < row + height; r++) {
            for (let c = col; c < col + width; c++) {
                cells.push(`${r},${c}`);
            }
        }
        return cells;
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    // _fillContentGrid() {
    //     let occupied_cells = 0;
    //     this.grid
    //         .querySelectorAll('.placeholder')
    //         .forEach((el) => el.remove());
    //
    //     for (let row = 1; row < this.configuration.rows + 1; row++) {
    //         for (let col = 1; col < this.configuration.columns + 1; col++) {
    //             if (!this.occupied_grid_cells.has(`${row},${col}`)) {
    //                 const gridItem = document.createElement('div');
    //                 gridItem.className = 'placeholder';
    //                 // gridItem.textContent = `${row},${col}`;
    //                 gridItem.style.fontSize = '6px';
    //                 gridItem.style.color = 'rgba(255,255,255,0.5)';
    //                 this.grid.appendChild(gridItem);
    //             } else {
    //                 occupied_cells++;
    //             }
    //         }
    //     }
    //
    //     console.log(`Page "${this.id}" has ${occupied_cells} occupied cells.`);
    // }

    /* -------------------------------------------------------------------------------------------------------------- */
    _fillContentGrid() {
        let occupied_cells = 0;

        // Remove any existing placeholders
        this.grid
            .querySelectorAll('.placeholder')
            .forEach((el) => el.remove());

        for (let row = 1; row < this.configuration.rows + 1; row++) {
            for (let col = 1; col < this.configuration.columns + 1; col++) {
                if (!this.occupied_grid_cells.has(`${row},${col}`)) {
                    const gridItem = document.createElement('div');
                    gridItem.className = 'placeholder';

                    // Set a tooltip showing the 1-based row and column
                    gridItem.title = `Row ${row}, Column ${col}`;

                    gridItem.style.fontSize = '6px';
                    gridItem.style.color = 'rgba(255,255,255,0.5)';
                    this.grid.appendChild(gridItem);
                } else {
                    occupied_cells++;
                }
            }
        }

        // console.log(`Page "${this.id}" has ${occupied_cells} occupied cells.`);
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    onEvent(event) {
        // Check if there is an 'event' callback for this page
        if (DEBUG) {
            console.log(`[Page ID: ${this.id}] Event received:`, event);
        }
        if (this.callbacks.event) {
            this.callbacks.event(event);
        }
    }
}

/* ================================================================================================================== */
class ControlGUI_Category {

    /** @type {Object} */
    pages = {};

    /** @type {ControlGUI_Page | null} */
    page = null;

    /** @type {Object} */
    callbacks = {};

    /** @type {Object} */
    configuration = {};

    /** @type {string} */
    id = '';

    /** @type {HTMLElement | null} */
    button = null;

    /** @type{Object} */
    page_buttons = {};

    /** @type {HTMLElement | null} */
    page_grid = null

    /** @type {HTMLElement | null} */
    content_grid = null


    /* -------------------------------------------------------------------------------------------------------------- */
    constructor(id, configuration = {}, pages = {}) {
        this.id = id;

        const default_configuration = {
            name: id,
            color: 'rgba(40,40,40,0.7)',
            textColor: 'rgba(255,255,255,0.7)',
            number_of_pages: +getComputedStyle(document.documentElement).getPropertyValue('--page_bar-cols'),
        }

        this.configuration = {...default_configuration, ...configuration};

        this.callbacks = {};
        this.pages = {};
        this.page = null;

        this.button = this._generateButton();

        this.page_buttons = {};
        for (let i = 0; i < this.configuration.number_of_pages; i++) {
            this.page_buttons[i] = null;
        }

        // Create this category's page grid that can later be attached to the page bar
        this._createPageGrid();

        // Initialize pages if any pages are given
        if (Object.keys(pages).length > 0) {
            this.buildPagesFromDefinition(pages);
        }
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    getObjectByPath(path) {
        // Example: path = "page1"             → pageKey = "/category1/page1"
        //          path = "page1/groupG/widgetX"
        const [firstSegment, remainder] = splitPath(path);
        if (!firstSegment) {
            return null;
        }

        // Build the full‐UID key for the page:
        //   this.id is "/category1", the firstSegment might be "page1"
        const pageKey = `${this.id}/${firstSegment}`;

        // Look up that ControlGUI_Page, which was stored under full UID
        const page = this.pages[pageKey];
        if (!page) {
            return null;
        }

        if (!remainder) {
            // No deeper path → return the page itself
            return page;
        }

        // Otherwise, descend into the page
        return page.getObjectByPath(remainder);
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    buildPagesFromDefinition(pages) {
        for (const [id, config] of Object.entries(pages)) {
            this.buildPageFromDefinition(config);
        }
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    buildPageFromDefinition(page_definition) {
        const new_page = new ControlGUI_Page(page_definition.id, page_definition.config, page_definition.objects);
        this.addPage(new_page, page_definition.position);
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    _generateButton() {
        let button = document.createElement('button');
        button.className = 'category_button';
        button.textContent = this.configuration.name;
        // button.style.backgroundColor = this.configuration.color;
        button.style.color = this.configuration.textColor;

        return button
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    _createPageGrid() {
        this.page_grid = document.createElement('div');
        this.page_grid.id = `page_${this.id}_grid`;
        this.page_grid.className = 'page_bar_grid';
    }


    /* -------------------------------------------------------------------------------------------------------------- */
    _renderEmpty(container, content_grid) {
        content_grid.innerHTML = '';
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    /**
     *
     * @param {ControlGUI_Page} page
     * @param {int|null} position
     */

    addPage(page, position = null) {
        // Check if there is a page with the same ID
        if (this.pages[page.id]) {
            console.warn(`Page with ID "${page.id}" already exists in the category.`);
            return;
        }

        // Add the button. First check if position is not null and if the desired spot is free
        if (position !== null) {
            if (this.page_buttons[position - 1] !== null) {
                console.warn(`Page button with position ${position} already exists in the category ${this.id}`);
                return;
            }
        } else {
            // Find the first free position
            for (let i = 1; i < this.configuration.number_of_pages + 1; i++) {
                if (this.page_buttons[i - 1] === null) {
                    position = i;
                    break;
                }
            }
            if (position === null) {
                console.warn(`${this.id}: No free page button positions.`);
                return;
            }
        }

        this.page_buttons[position - 1] = page.button;

        // Add the button to the page grid with the height and width of 1
        page.button.style.gridRow = '1'
        page.button.style.gridColumn = String(position);
        page.button.style.gridRowEnd = 'span 1';
        page.button.style.gridColumnEnd = 'span 1';

        // Add an event listener that calls setPage with the page's id
        page.button.addEventListener('click', () => this.setPage(page.id));

        this.page_grid.appendChild(page.button);

        this.pages[page.id] = page;

        page.callbacks.event = this.onEvent.bind(this);

        // If the current page is empty, set this page
        if (this.page === null) {
            console.log('Setting initial page to: ', page.id);
            this.setPage(page.id);
        }
    }

    /* -------------------------------------------------------------------------------------------------------------- */

    /**
     *
     * @param {string | ControlGUI_Page} page
     */


    /**
     * Render the page-bar buttons and stash each page.grid absolutely in the content area.
     *
     * @param {HTMLElement} container    – the page-bar container
     * @param {HTMLElement} content_grid – the main content container
     */
    buildCategory(container, content_grid) {
        console.log('Building category:', this.id);

        // 1) rebuild your page-bar
        container.innerHTML = '';
        container.appendChild(this.page_grid);

        // 2) make content_grid a positioning context
        this.content_grid = content_grid;
        this.content_grid.style.position = 'relative';

        // 3) for each page: append once, absolutely position, hide it
        Object.values(this.pages).forEach(page => {
            if (page.grid.parentNode !== this.content_grid) {
                // pull out of the normal flow
                this.content_grid.appendChild(page.grid);

                Object.assign(page.grid.style, {
                    position: 'absolute',
                    top: '0',
                    left: '0',
                    width: '100%',
                    height: '100%',
                    // make it a grid itself
                    display: 'none',
                });
            } else {
                page.grid.style.display = 'none';
            }
        });

        // 4) show the active (or first) page
        const start = this.page ? this.page.id : Object.keys(this.pages)[0];
        if (start) this.setPage(start);
        else this._renderEmpty(container, content_grid);
    }

    /**
     * Hide all pages, then absolutely show the selected one.
     *
     * @param {string|ControlGUI_Page} pageOrId – the page to activate
     */
    setPage(pageOrId) {
        // normalize to an ID
        const id = pageOrId instanceof ControlGUI_Page ? pageOrId.id : pageOrId;
        const page = this.pages[id];
        if (!page) {
            console.warn(`Page "${id}" not found in category "${this.id}".`);
            return;
        }

        console.log('Switching to page:', id);

        // hide everything + dim buttons
        Object.values(this.pages).forEach(p => {
            p.grid.style.display = 'none';
            p.button.classList.remove('selected');
        });

        // reveal the chosen page + highlight its button
        page.grid.style.display = 'grid';
        page.button.classList.add('selected');
        window.dispatchEvent(new Event('resize'));
        this.page = page;
    }


    /* -------------------------------------------------------------------------------------------------------------- */
    onEvent(event) {
        console.log(`[Category ID: ${this.id}] Event received:`, event);
        // Check if there is an 'event' callback for this category
        if (this.callbacks.event) {
            this.callbacks.event(event);
        }
    }
}


/* ================================================================================================================== */
export class ControlGui {

    grid = null;
    content = null;
    head_bar = null;
    head_bar_grid = null;
    page_bar = null;
    category_bar = null;
    terminal_container = null;
    rows = 0;
    cols = 0;

    /** @type {Object} */
    category_buttons = {};

    /** @type {Object} */
    configuration = {};

    /** @type {boolean} */
    connected = false;

    /* ===============================================================================================================*/
    constructor(container_ids, configuration = {}, wsUrl) {

        const default_configuration = {
            'number_of_categories': 10
        }
        this.configuration = {...default_configuration, ...configuration};

        this.wsURL = wsUrl;

        this.containers = {}

        this._readContainers(container_ids);

        // this.drawHeadBarGrid()
        this.drawStatusBarGrid()


        this._initializeTerminal();


        this.category = null;
        this.categories = {}
        this.category_buttons = {}

        for (let i = 0; i < this.configuration.number_of_categories; i++) {
            this.category_buttons[i] = null;
        }


        this.addLogo();
        this.addConnectionIndicator();
        // this.resetGUI();

        this._connect(wsUrl);
    }

    /* ===============================================================================================================*/
    getObjectByUID(uid) {
        // e.g. uid = "/category1/page1/groupG/widgetX"
        if (!uid) {
            return null;
        }

        // Trim leading/trailing slashes → "category1/page1/groupG/widgetX"
        const trimmed = uid.replace(/^\/+|\/+$/g, '');
        const [categorySegment, remainder] = splitPath(trimmed);
        if (!categorySegment) {
            return null;
        }

        // Rebuild the full‐UID key for the category:
        //   "category1"  → "/category1"
        const categoryKey = `/${categorySegment}`;
        const category = this.categories[categoryKey];
        if (!category) {
            return null;
        }

        if (!remainder) {
            // If the path was only "/category1", return the category object
            return category;
        }

        // Otherwise, delegate into that category
        return category.getObjectByPath(remainder);
    }

    /* ===============================================================================================================*/
    resetGUI() {
        // Empty the content
        this.content.innerHTML = '';
        this.category_bar_grid.innerHTML = '';
        this.page_bar.innerHTML = '';

        // Delete all categories that are currently stored
        this.categories = {};
        this.category = null;

        for (let i = 0; i < this.configuration.number_of_categories; i++) {
            this.category_buttons[i] = null;
        }


        // Add the placeholder in the middle of the content area
        const placeholder = document.createElement('div');
        placeholder.className = 'content_placeholder';
        placeholder.innerHTML = `
            <span class="placeholder_title">Not connected</span>
            <span class="placeholder_info">${this.wsURL}</span>
            `;
        this.content.appendChild(placeholder);

        this.msgRateDisplay.textContent = '-----';
    }

    /* ===============================================================================================================*/
    addLogo() {

        const logoLink = document.createElement('a')
        logoLink.href = 'https://github.com/dustin-lehmann/bilbolab' // Change to your desired URL
        logoLink.className = 'logo_link'
        logoLink.target = '_blank' // Opens in a new tab
        logoLink.rel = 'noopener noreferrer' // Security best practice

        const logo = document.createElement('img')
        logo.src = new URL('./symbols/bilbolab_logo.png', import.meta.url).href
        logo.alt = 'Logo'
        logo.className = 'bilbolab_logo'

        logoLink.appendChild(logo)
        this.head_bar_grid.appendChild(logoLink)

    }

    /* ===============================================================================================================*/
    addConnectionIndicator() {

        // ——— websocket status & rate indicator ———
        this.msgTimestamps = [];
        this.msgRateWindow = 1;
        this.blinkThrottle = 100;      // ms between blinks
        this._lastBlinkTime = 0;

        // create a container in the head_bar_grid
        const statusContainer = document.createElement('div');
        statusContainer.style.gridRow = '1 / span 2';                       // top row
        statusContainer.style.gridColumn = `${String(this.headbar_cols - 1)} / span 2`; // far right
        statusContainer.style.justifySelf = 'end';
        statusContainer.style.marginRight = '10px';
        statusContainer.style.paddingRight = '10px';
        statusContainer.style.display = 'flex';
        statusContainer.style.alignItems = 'center';
        statusContainer.style.gap = '8px';


        // the little circle
        this.statusIndicator = document.createElement('div');
        this.statusIndicator.className = 'status-indicator';

        // the “X M/s” text
        this.msgRateDisplay = document.createElement('span');
        this.msgRateDisplay.className = 'msg-rate';
        this.msgRateDisplay.textContent = '-----';

        statusContainer.appendChild(this.statusIndicator);
        statusContainer.appendChild(this.msgRateDisplay);
        this.head_bar_grid.appendChild(statusContainer);
    }

    /* ===============================================================================================================*/
    /**
     *
     * @param {ControlGUI_Category} category
     * @param {int|null} position
     */
    addCategory(category, position = null) {
        if (this.categories[category.id]) {
            console.warn(`Category with ID "${category.id}" already exists in the control GUI.`);
            return;
        }


        // Add the button. First check if position is not null and if the desired spot is free
        if (position !== null) {
            if (this.category_buttons[position] !== null) {
                console.warn(`Category button with position ${position} already exists in the control GUI.`);
                return;
            }
        } else {
            // Find the first free position
            for (let i = 1; i < this.configuration.number_of_categories + 1; i++) {
                if (this.category_buttons[i] === null) {
                    position = i;
                    break;
                }
            }
            if (position === null) {
                console.warn('No free category button positions.');
                return;
            }
        }

        this.category_buttons[position] = category.button;

        // Add the button to the category grid with the height and width of 1
        category.button.style.gridRow = String(position);
        category.button.style.gridColumn = '1';
        category.button.style.gridRowEnd = 'span 1';
        category.button.style.gridColumnEnd = 'span 1';

        // Add an event listener that calls setCategory with the category's id
        category.button.addEventListener('click', () => this.setCategory(category.id));

        this.category_bar_grid.appendChild(category.button);

        // Make the button faint
        category.button.classList.add('not-selected')

        category._position = position;
        this.categories[category.id] = category;
        category.callbacks.event = this._onEvent.bind(this);

        // Set this category as initial if the category is not set
        if (this.category === null) {
            console.log('Setting initial category to: ', category.id);
            this.setCategory(category.id);
        }
    }

    /* ===============================================================================================================*/
    setCategory(category_id) {
        // 1) sanity check
        if (!this.categories[category_id]) {
            console.warn(`Category "${category_id}" does not exist.`);
            return;
        }

        // 2) hide every single page.grid from *all* categories
        Object.values(this.categories).forEach(cat => {
            Object.values(cat.pages).forEach(pg => {
                pg.grid.style.display = 'none';
                // dim their page buttons too, just in case
            });
        });

        // 3) update the category-bar button styles
        Object.values(this.categories).forEach(cat => {
            cat.button.classList.remove('selected');
        });
        this.categories[category_id].button.classList.add('selected');

        console.log('Setting category to:', category_id);

        // 4) stash the new category
        this.category = this.categories[category_id];

        // 5) rebuild that category (which will re-hide & position its own pages,
        //    then call its own setPage to show the first/active one)
        this.category.buildCategory(this.page_bar, this.content);
    }

    /* ===============================================================================================================*/
    _initializeTerminal() {
        mountTerminal('#' + this.terminal_container.id);
    }

    /* ===============================================================================================================*/
    drawStatusBarGrid() {
        for (let row = 0; row < this.robot_status_bar_rows; row++) {
            for (let col = 0; col < this.robot_status_bar_cols; col++) {
                const gridItem = document.createElement('div');
                gridItem.className = 'robot_status_bar_cell';
                // gridItem.textContent = `${row},${col}`;  // Optional: for debugging
                this.robot_status_bar_grid.appendChild(gridItem);
            }
        }
    }


    /* ===============================================================================================================*/
    drawHeadBarGrid() {
        for (let row = 0; row < this.headbar_rows; row++) {
            for (let col = 0; col < this.headbar_cols; col++) {
                const gridItem = document.createElement('div');
                gridItem.className = 'headbar_cell';
                // gridItem.textContent = `${row},${col}`;  // Optional: for debugging
                this.head_bar_grid.appendChild(gridItem);
            }
        }
    }


    /* ===============================================================================================================*/
    _readContainers(container_ids) {
        // this.grid = document.getElementById(container_ids.grid);

        this.content = document.getElementById(container_ids.content);

        this.head_bar = document.getElementById(container_ids.head_bar);
        this.head_bar_grid = document.getElementById(container_ids.head_bar_grid);

        this.page_bar = document.getElementById(container_ids.page_bar);
        this.page_bar_grid = document.getElementById(container_ids.page_bar_grid);

        this.category_bar = document.getElementById(container_ids.category_bar);
        this.category_bar_grid = document.getElementById(container_ids.category_bar_grid);

        this.terminal_container = document.getElementById(container_ids.terminal_container);
        this.robot_status_bar = document.getElementById(container_ids.robot_status_bar);
        this.robot_status_bar_grid = document.getElementById(container_ids.robot_status_bar_grid);

        this.containers.side_placeholder = document.getElementById(container_ids.side_placeholder);

        this.rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--grid-rows');
        this.cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--grid-cols');

        this.headbar_rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--headbar-rows');
        this.headbar_cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--headbar-cols');

        this.page_bar_rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--page_bar-rows');
        this.page_bar_cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--page_bar-cols');

        this.category_bar_rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--category_bar-rows');
        this.category_bar_cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--category_bar-cols');

        this.robot_status_bar_rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--robot_status_bar-rows');
        this.robot_status_bar_cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--robot_status_bar-cols');
    }

    /* ===============================================================================================================*/
    _connect(wsUrl) {
        this.socket = new WebSocket(wsUrl);

        this.socket.addEventListener('open', () => {
            console.log('WebSocket connected');
            this.connected = true;
            this.setConnectionStatus(true);
        });
        this.socket.addEventListener('message', (ev) => this._onMessage(ev));
        this.socket.addEventListener('close', () => {
            this.connected = false;
            this.setConnectionStatus(false);
            delete this.socket;
            this.resetGUI();
            // console.log('WebSocket closed, retrying in 3 s');
            setTimeout(() => this._connect(wsUrl), 3000);
        });
        this.socket.addEventListener('error', (err) => {
            // console.error('WebSocket error', err);
            this.socket.close();
        });
    }

    /* ===============================================================================================================*/
    _onMessage(event) {
        let msg;
        try {
            msg = JSON.parse(event.data);
        } catch (e) {
            console.error('Invalid JSON:', event.data);
            return;
        }
        switch (msg.type) {
            case 'init':
                this._initialize(msg);
                break;
            case 'update':
                this._update(msg);
                break;
            default:
                console.warn('Unknown message type', msg.type);
        }

        this._recordMessage();
    }

    /* ===============================================================================================================*/
    _onEvent(event) {
        console.log('GUI Event received: ', event)
        const message = {
            'type': 'event', 'id': event.id, 'data': event,
        }
        if (this.connected) {
            this.socket.send(JSON.stringify(message));
        }
    }

    /* ===============================================================================================================*/
    _initialize(msg) {
        console.log('Initializing control GUI');

        // Check if msg has a field name configuration, if yes extract it
        if (msg.configuration) {
            const config = msg.configuration;
            console.log('Configuration received: ', config);

            if (config.categories) {
                for (let id in config.categories) {
                    console.log("Adding category: ", id);
                    console.log("Configuration:", config.categories[id].config)
                    console.log(config.categories[id])
                    const category = new ControlGUI_Category(id, config.categories[id].config, config.categories[id].pages);

                    this.addCategory(category);
                }
            }

        }
    }

    /* ===============================================================================================================*/
    _update(msg) {
        const object = this.getObjectByUID(msg.id);
        object.update(msg.data);
    }

    /* ===============================================================================================================*/
    /**
     * Call on WebSocket open/close
     */
    setConnectionStatus(connected) {
        if (connected) {
            this.statusIndicator.classList.add('connected');
            const placeholder = this.content.querySelector('.content_placeholder');
            if (placeholder) placeholder.remove();
        } else {
            this.statusIndicator.classList.remove('connected');
            this.msgRateDisplay.textContent = '---';
        }
    }

    /* ===============================================================================================================*/
    /**
     * Call this for every incoming message event
     */
    _recordMessage() {
        const now = Date.now();
        this.msgTimestamps.push(now);
        // drop anything older than the window
        const cutoff = now - this.msgRateWindow * 1000;
        while (this.msgTimestamps.length && this.msgTimestamps[0] < cutoff) {
            this.msgTimestamps.shift();
        }
        this._updateMessageRate();
        this._maybeBlink();
    }

    /* ===============================================================================================================*/
    /**
     * Recompute and display the messages/sec
     */
    _updateMessageRate() {
        const count = this.msgTimestamps.length;
        const rate = count / this.msgRateWindow;
        this.msgRateDisplay.textContent = rate.toFixed(1) + ' M/s';
    }

    /* ===============================================================================================================*/
    /**
     * Blink the status indicator at most once per blinkThrottle ms
     */
    _maybeBlink() {
        const now = Date.now();
        if (now - this._lastBlinkTime < this.blinkThrottle) return;
        this._lastBlinkTime = now;
        this.statusIndicator.classList.add('blink');
        this.statusIndicator.addEventListener(
            'animationend',
            () => this.statusIndicator.classList.remove('blink'),
            {once: true}
        );
    }


    /* ===============================================================================================================*/
    _demoObjects() {
        const category_1 = new ControlGUI_Category('category_1', {name: 'First', color: 'rgb(19,40,0)'})
        const category_2 = new ControlGUI_Category('category_2', {name: 'Second', color: 'rgb(0,0,40)'})
        const category_3 = new ControlGUI_Category('category_3', {name: 'Third', color: 'rgb(40,0,37)'})

        this.addCategory(category_1, 1);
        this.addCategory(category_2, 2);
        this.addCategory(category_3, 3);


        const page_1 = new ControlGUI_Page('page_1', {name: 'Page 1.1'})
        const page_2 = new ControlGUI_Page('page_2', {name: 'Page 1.2'})
        const page_3 = new ControlGUI_Page('page_3', {name: 'Page 1.3'})
        const page_4 = new ControlGUI_Page('page_4', {name: 'Page 1.4'})
        const page_5 = new ControlGUI_Page('page_5', {name: 'Page 1.5'})
        const page_6 = new ControlGUI_Page('page_6', {name: 'Page 1.6'})
        const page_7 = new ControlGUI_Page('page_7', {name: 'Page 1.7'})
        const page_8 = new ControlGUI_Page('page_8', {name: 'Page 1.8'})
        const page_9 = new ControlGUI_Page('page_9', {name: 'Page 1.9'})
        const page_10 = new ControlGUI_Page('page_10', {name: 'Page 1.10'})
        category_1.addPage(page_1, 1)
        category_1.addPage(page_2, 2)
        category_1.addPage(page_3, 3)
        category_1.addPage(page_4, 4)
        category_1.addPage(page_5, 5)
        category_1.addPage(page_6, 6)
        category_1.addPage(page_7, 7)
        category_1.addPage(page_8, 8)
        category_1.addPage(page_9, 9)
        category_1.addPage(page_10, 10)

        return;


        const page_2_1 = new ControlGUI_Page('page_2_1', {name: 'Page 2.1'})
        const page_2_2 = new ControlGUI_Page('page_2_2', {name: 'Page 2.2'})
        const page_2_3 = new ControlGUI_Page('page_2_3', {name: 'Page 2.3'})
        const page_2_4 = new ControlGUI_Page('page_2_4', {name: 'Page 2.4'})
        const page_2_5 = new ControlGUI_Page('page_2_5', {name: 'Page 2.5'})
        const page_2_6 = new ControlGUI_Page('page_2_6', {name: 'Page 2.6'})
        const page_2_7 = new ControlGUI_Page('page_2_7', {name: 'Page 2.7'})

        // category_2.addPage(page_2_1, 1)
        // category_2.addPage(page_2_2, 2)
        // category_2.addPage(page_2_3, 3)
        // category_2.addPage(page_2_4, 4)
        // category_2.addPage(page_2_5, 5)
        // category_2.addPage(page_2_6, 6)
        // category_2.addPage(page_2_7, 7)


        const page_3_1 = new ControlGUI_Page('page_3_1', {name: 'Page 3.1'})
        const page_3_2 = new ControlGUI_Page('page_3_2', {name: 'Page 3.2'})
        // category_3.addPage(page_3_1, 1)
        // category_3.addPage(page_3_2, 2)


        const btn_1_1 = new ButtonWidget({
            id: 'btn_1_1', configuration: {
                text: 'Button A', color: 'rgba(79,170,108,0.81)', textColor: '#ffffff', // visible: true,
            },
        })

        const msb1 = new MultiStateButtonWidget({
            id: 'msb-test', configuration: {
                text: 'State',
                states: ['A', 'B', 'C'],
                currentState: 0,
                color: ['rgba(79,170,108,0.81)', 'rgb(191,0,0, 0.9)', 'rgba(88,125,179,0.81)'],
                textColor: '#ffffff',
            },
        })

        page_1.addObject(btn_1_1, 1, 1, 2, 2);
        page_1.addObject(msb1, 1, 4, 2, 2);

        const cs2 = new ClassicSliderWidget({
            id: 'mySlider2', configuration: {
                title: 'Volume',
                titlePosition: 'left',      // or 'top'
                valuePosition: 'right',     // or 'center'
                backgroundColor: 'rgba(255,255,255,0.05)',
                stemColor: '#555',
                handleColor: '#cc0085',
                textColor: '#fff',
                min: -1,
                max: 1,
                value: 0,
                increment: 0.1,
                direction: 'horizontal',      // or 'horizontal'
                continuousUpdates: true,
            },
        });

        page_2.addObject(cs2, 1, 1, 10, 2);
    }

}