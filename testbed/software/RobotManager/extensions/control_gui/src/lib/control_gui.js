import {mountTerminal} from './terminal/terminal.js';
import {GUI_Object, ButtonWidget, SliderWidget, MultiStateButtonWidget} from './objects.js'

export class ControlGui {

    grid = null;
    head_bar = null;
    head_bar_grid = null;
    navigation_bar = null;
    application_bar = null;
    terminal_container = null;
    rows = 0;
    cols = 0;

    grid_widgets = {};

    constructor(container_ids, wsUrl) {
        this.grid = document.getElementById(container_ids.grid);
        this.head_bar = document.getElementById(container_ids.head_bar);
        this.head_bar_grid = document.getElementById(container_ids.head_bar_grid);
        this.navigation_bar = document.getElementById(container_ids.navigation_bar);
        this.navigation_bar_grid = document.getElementById(container_ids.navigation_bar_grid);
        this.application_bar = document.getElementById(container_ids.application_bar);
        this.application_bar_grid = document.getElementById(container_ids.application_bar_grid);
        this.terminal_container = document.getElementById(container_ids.terminal_container);

        this.rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--grid-rows');
        this.cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--grid-cols');

        this.headbar_rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--headbar-rows');
        this.headbar_cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--headbar-cols');

        this.navigation_bar_rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--navigation_bar-rows');
        this.navigation_bar_cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--navigation_bar-cols');

        this.application_bar_rows = +getComputedStyle(document.documentElement)
            .getPropertyValue('--application_bar-rows');
        this.application_bar_cols = +getComputedStyle(document.documentElement)
            .getPropertyValue('--application_bar-cols');

        this.occupied_grid_cells = new Set(); // Store "row,col" strings for a quick lookup


        const testButton = new ButtonWidget({
            id: 'btn-test',
            configuration: {
                text: 'Button 1',
                color: 'rgba(79,170,108,0.81)',
                textColor: '#ffffff',
                // visible: true,
            },
            callbacks: {
                event: this.onWidgetEvent
            }
        })

        const testButton2 = new ButtonWidget({
            id: 'btn-test2',
            configuration: {
                text: 'Button 2',
                color: 'rgba(79,170,108,0.81)',
                textColor: '#ffffff',
                // visible: true,
            },
            callbacks: {
                event: this.onWidgetEvent
            }
        })


        const testSlider = new SliderWidget({
            id: 'slider-test',
            configuration: {
                text: 'Slider 1',
                title: "Hallo",
                min: 0,
                max: 100,
                value: 50,
                increment: 10,
                ticks: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                // limitToTicks: true,
                direction: 'vertical',
                color: 'rgba(79,170,108,0.81)',
                textColor: '#ffffff',

            },
            callbacks: {
                event: this.onWidgetEvent
            }
        })

        const testslider2 = new SliderWidget({
            id: 'slider-test2',
            configuration: {
                text: 'Slider 2',
                title: "Hallo",
                min: 0,
                max: 1,
                value: 0.5,
                increment: 0.1,
                direction: 'horizontal',
                automaticReset: 0.5,
                continuousUpdates: true,
                color: 'rgba(79,170,108,0.81)',
            },
            callbacks: {
                event: this.onWidgetEvent
            }
        })

        const msb1 = new MultiStateButtonWidget({
            id: 'msb-test',
            configuration: {
                text: 'State',
                states: ['A', 'B', 'C'],
                currentState: 0,
                color: ['rgba(79,170,108,0.81)', 'rgb(191,0,0, 0.9)', 'rgba(88,125,179,0.81)'],
                textColor: '#ffffff',
            },
            callbacks: {
                event: this.onWidgetEvent
            }
        })

        this._addObjectToGrid(msb1, 0, 0, 1, 1);


        this._addObjectToGrid(testSlider, 0, 10, 3, 3);
        this._addObjectToGrid(testslider2, 6, 10, 3, 2);

        // 3) Add it to the grid
        this._addObjectToGrid(testButton, 2, 2, 1, 1);
        this._addObjectToGrid(testButton2, 0, 2, 1, 1);

        this._initializeHeadBarGrid()
        this._initializeNavigationBarGrid()
        this._initializeApplicationBarGrid()

        this._initializeTerminal();

        this._connect(wsUrl);
    }


    _initializeTerminal() {
        mountTerminal('#' + this.terminal_container.id);
    }


    onWidgetEvent(event) {
        console.log("Widget Event")
        console.log(event)
    }


    _initializeApplicationBarGrid() {
        for (let row = 0; row < this.application_bar_rows; row++) {
            for (let col = 0; col < this.application_bar_cols; col++) {
                const gridItem = document.createElement('div');
                gridItem.className = 'application_bar_cell';
                gridItem.textContent = `${row},${col}`;  // Optional: for debugging
                this.application_bar_grid.appendChild(gridItem);
            }
        }
    }

    _initializeHeadBarGrid() {
        for (let row = 0; row < this.headbar_rows; row++) {
            for (let col = 0; col < this.headbar_cols; col++) {
                const gridItem = document.createElement('div');
                gridItem.className = 'headbar_cell';
                gridItem.textContent = `${row},${col}`;  // Optional: for debugging
                this.head_bar_grid.appendChild(gridItem);
            }
        }
    }

    _initializeNavigationBarGrid() {
        for (let row = 0; row < this.navigation_bar_rows; row++) {
            for (let col = 0; col < this.navigation_bar_cols; col++) {
                const gridItem = document.createElement('div');
                gridItem.className = 'navigation_bar_cell';
                gridItem.textContent = `${row},${col}`;  // Optional: for debugging
                this.navigation_bar_grid.appendChild(gridItem);
            }
        }
    }

    /**
     * Replace your old stub with this:
     * @param {GUI_Object} widget  — any widget subclass
     * @param {int} row
     * @param {int} col
     * @param {int} width
     * @param {int} height
     */
    _addObjectToGrid(widget, row, col, width, height) {
        if (!(widget instanceof GUI_Object)) {
            console.warn('Expected a GUI_Object, got:', widget);
            return;
        }

        if (!widget.id) {
            console.warn('Widget must have an ID');
            return;
        }

        if (this.grid_widgets[widget.id]) {
            console.warn(`Widget with ID "${widget.id}" already exists in the grid.`);
            return;
        }

        if (row < 0 || col < 0 || row >= this.rows || col >= this.cols) {
            console.warn(`Invalid grid coordinates: row=${row}, col=${col}`);
            return;
        }

        if (row + height > this.rows || col + width > this.cols) {
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

        this.grid_widgets[widget.id] = widget;
    }

    _getOccupiedCells(row, col, width, height) {
        const cells = [];
        for (let r = row; r < row + height; r++) {
            for (let c = col; c < col + width; c++) {
                cells.push(`${r},${c}`);
            }
        }
        return cells;
    }

    _initializeGrid(grid) {


        console.log('Initializing grid with', rows, 'rows and', cols, 'cols');

        for (let row = 0; row < rows; row++) {
            for (let col = 0; col < cols; col++) {
                const gridItem = document.createElement('div');
                gridItem.className = 'grid-item';
                gridItem.textContent = `${row},${col}`;  // Optional: for debugging
                grid.appendChild(gridItem);
            }
        }

    }

    _connect(wsUrl) {
        this.socket = new WebSocket(wsUrl);
        this.socket.addEventListener('open', () => {
            console.log('WebSocket connected');
        });
        this.socket.addEventListener('message', (ev) => this._onMessage(ev));
        this.socket.addEventListener('close', () => {

            if (this.plot) {
                this.plot.destroy();
                this.plot = null;
            }
            // clear any leftover queues
            this._queue = {};
            console.log('WebSocket closed, retrying in 3s');
            setTimeout(() => this._connect(wsUrl), 3000);
        });
        this.socket.addEventListener('error', (err) => {
            console.error('WebSocket error', err);
            this.socket.close();
        });
    }

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
    }

    _initialize(msg) {
        console.log('Initializing control GUI');
        console.log(msg);
    }

    _update(msg) {
        console.log('Updating control GUI');
        console.log(msg);
    }

}