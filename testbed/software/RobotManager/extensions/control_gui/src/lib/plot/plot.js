import Chart from "chart.js/auto";
import 'chartjs-adapter-moment';
import streamingPlugin from 'chartjs-plugin-streaming';


import './plot.css';
import {getColor, interpolateColors} from "../helpers";

// Register the streaming plugin
Chart.register(streamingPlugin);

const backgroundcolor_plugin = {
    id: 'customCanvasBackgroundColor',
    beforeDraw: (chart, args, options) => {
        const ctx = chart.ctx;
        ctx.save();
        ctx.globalCompositeOperation = 'destination-over';
        ctx.fillStyle = options.color || '#99ffff';
        ctx.fillRect(0, 0, chart.width, chart.height);
        ctx.restore();
    }
};

const defaultLegendClick = Chart.defaults.plugins.legend.onClick;
const defaultGenerateLabels = Chart.defaults.plugins.legend.labels.generateLabels;


const DEFAULT_CONFIG = {
    host: 'localhost',
    port: 8080,
    // websocket_url: 'ws://localhost:8080',
    standalone: true,  // If standalone=true, then the plot has its own websocket. If false, it gets fed via an external update
}

const DEFAULT_PLOT_CONFIG = {
    window_time: 10,
    pre_delay: 0.1,
    update_time: 0.1,
    background_color: [1, 1, 1, 0],
    time_ticks_color: [0.5, 0.5, 0.5],
    y_grid_color: [0.5, 0.5, 0.5, 0.5],

    time_display_format: 'HH:mm:ss',

    time_step_display: null,
    highlight_zero: true,

    y_axis_font_size: 10,

    y_axis_show_label: false,

    show_title: true,
    title_position: 'top',  // Options: 'top', 'left', 'bottom', 'right''
    title_font_size: 11,
    title_color: [0.8, 0.8, 0.8],

    show_legend: true,
    legend_position: 'bottom',  // Options: 'top', 'left', 'bottom', 'right', 'chartArea'
    legend_align: 'start',  // Options: 'start', 'center', 'end'
    legend_fullsize: false,
    legend_label_type: 'point', // Options: 'box', 'point'
    legend_label_size: 5,

    use_queue: false
}


export class JSPlot {
    constructor(container, config, plot_config) {

        this.config = {...DEFAULT_CONFIG, ...config};
        this.plot_config = {...DEFAULT_PLOT_CONFIG, ...plot_config};
        this.container = container;

        const canvas = document.createElement('canvas');
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.display = 'block';
        canvas.style.background = 'rgba(255, 255, 255, 0)';
        this.container.appendChild(canvas);
        this.canvas = canvas;


        // in your JSPlot constructor, after `this.container.appendChild(canvas)`
        this.container.style.position = 'relative';

        const btn = document.createElement('button');
        btn.classList.add('plot-settings-button');
        btn.innerHTML = '⚙️';


        btn.addEventListener('click', () => {
            if (this.config.onSettingsClick) {
                this.config.onSettingsClick();
            }
        });

        this.container.appendChild(btn);


        this.ctx = this.canvas.getContext('2d');
        this._queue = {}; // TODO: Not used
        this._lastValue = {};

        if (this.config.standalone) {
            const websocket_url = `ws://${this.config.host}:${this.config.port}`;
            this._connect(websocket_url);
        }

    }

    /* -------------------------------------------------------------------------------------------------------------- */
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
            // this._queue = {};
            this._lastValue = {};
            console.log('WebSocket closed, retrying in 3s');
            setTimeout(() => this._connect(wsUrl), 3000);
        });
        this.socket.addEventListener('error', (err) => {
            console.error('WebSocket error', err);
            this.socket.close();
        });
    }

    /* -------------------------------------------------------------------------------------------------------------- */
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
                this.initializePlot(msg);
                break;
            case 'update':
                this.update(msg);
                break;
            case 'clear':
                this._clearData();
                break;
            case 'add':
                this._addSeries(msg.data);
                break;
            case 'remove':
                this._removeSeries(msg.data);
                break;
            default:
                console.warn('Unknown message type', msg.type);
        }
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    initializePlot(msg) {

        if (this.plot) {
            this.plot.destroy();
            this.plot = null;
            this._queue = {};    // and reset all your queues
        }

        this.plot_config = {...this.plot_config, ...msg.config};

        const tsDef = msg.timeseries;

        const datasets = [];
        const yAxes = {};

        // Convert background color
        const bg = this.plot_config.background_color;
        const bgColor = `rgba(${Math.round(bg[0] * 255)}, ${Math.round(bg[1] * 255)}, ${Math.round(bg[2] * 255)}, ${bg[3]})`;

        // Setup datasets and axes
        Object.values(tsDef).forEach(cfg => {
            // Convert colors
            const rgb = cfg.color.map(c => Math.round(c * 255));
            const borderColor = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 1)`;
            let fillColor;
            if (cfg.fill) {
                const fc = cfg.fill_color;
                fillColor = `rgba(${Math.round(fc[0] * 255)}, ${Math.round(fc[1] * 255)}, ${Math.round(fc[2] * 255)}, ${fc[3]})`;
            }

            // Initialize queue for this series
            this._queue[cfg.id] = [];
            this._lastValue[cfg.id] = null;

            // Create dataset
            datasets.push({
                label: cfg.name,
                unit: cfg.unit,
                seriesId: cfg.id,
                borderColor,
                backgroundColor: fillColor,
                borderWidth: cfg.width,
                fill: cfg.fill,
                tension: cfg.tension,
                data: [],
                yAxisID: cfg.id,
                hidden: !cfg.visible,
                precision: cfg.precision
            });

            // Create corresponding Y axis
            yAxes[cfg.id] = {
                type: 'linear',
                position: cfg.y_axis_side,
                title: {
                    display: this.plot_config.y_axis_show_label,
                    text: cfg.y_axis_label || (cfg.unit || '')
                },
                ticks: {
                    color: borderColor,
                    font: {
                        size: this.plot_config.y_axis_font_size,
                    },
                    callback: (value) => value.toFixed(cfg.precision)
                },
                grid: {
                    display: cfg.y_axis_grid,
                    drawOnChartArea: cfg.y_axis_grid,
                    // borderColor: getColor(this.plot_config.y_grid_color),
                    borderColor: interpolateColors(this.plot_config.y_grid_color, borderColor, 0.5),
                    lineWidth: ctx => this.plot_config.highlight_zero && ctx.tick.value === 0 ? 2 : 1,
                    color: ctx => {
                        const isZero = this.plot_config.highlight_zero && ctx.tick.value === 0;
                        // parse your existing borderColor to RGBA components:
                        const [r, g, b] = this.plot_config.y_grid_color
                            .slice(0, 3)
                            .map(c => Math.round(c * 255));
                        const alpha = isZero ? 1 : 0.4;
                        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
                    }
                },
            };
            if (cfg.min !== null && cfg.min !== undefined) yAxes[cfg.id].min = cfg.min;
            if (cfg.max !== null && cfg.max !== undefined) yAxes[cfg.id].max = cfg.max;
        });

        // Convert time ticks color
        const timeTickColor = getColor(this.plot_config.time_ticks_color);

        // Create chart
        this.plot = new Chart(this.ctx, {
            type: 'line',
            data: {datasets},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                normalized: true,
                scales: {
                    x: {
                        type: 'realtime',
                        realtime: {
                            duration: Math.floor(this.plot_config.window_time * 1000),
                            refresh: Math.floor(this.plot_config.update_time * 1000),
                            delay: Math.floor(this.plot_config.pre_delay * 1000),
                            onRefresh: chart => {
                                chart.data.datasets.forEach(ds => {

                                    if (this.plot_config.use_queue) {
                                        const q = this._queue[ds.seriesId] || [];
                                        if (q.length) {
                                            ds.data.push(...q);
                                            this._queue[ds.seriesId] = [];
                                        }
                                    } else {

                                        const last = this._lastValue[ds.seriesId];
                                        if (last !== null) {
                                            ds.data.push(last);
                                        }
                                    }

                                });

                            }
                        },
                        time: {
                            displayFormats: {
                                second: this.plot_config.time_display_format,
                                minute: this.plot_config.time_display_format,
                                hour: this.plot_config.time_display_format
                            },
                            tooltipFormat: this.plot_config.time_display_format,
                            unit: 'second',
                            stepSize: this.plot_config.time_step_display,
                        },
                        ticks: {color: timeTickColor},
                        grid: {color: timeTickColor}
                    },
                    ...yAxes
                },
                elements: {point: {radius: 0}},
                plugins: {
                    decimation: {
                        enabled: true,
                        algorithm: 'lttb',      // “largest triangle” algorithm
                        samples: 500         // keep at most 500 points on‐screen
                    },
                    customCanvasBackgroundColor: {color: bgColor},
                    legend: {
                        display: this.plot_config.show_legend,
                        position: this.plot_config.legend_position,
                        align: this.plot_config.legend_align,
                        fullSize: this.plot_config.legend_fullsize,
                        font: {
                            size: 11
                        },
                        labels: {
                            font: {family: 'monospace'},
                            usePointStyle: this.plot_config.legend_label_type === 'point', // true if this.config.legend_label_type === 'point'
                            boxWidth: this.plot_config.legend_label_size,
                            boxHeight: this.plot_config.legend_label_size,
                            padding: 3,
                            generateLabels: chart => {
                                const items = defaultGenerateLabels(chart);
                                items.forEach(item => {
                                    const ds = chart.data.datasets[item.datasetIndex];
                                    const last = ds.data.length ? ds.data[ds.data.length - 1].y : 0;
                                    const value = last.toFixed(ds.precision).padStart(6, ' ');
                                    const suffix = ds.unit && !this.plot_config.y_axis_show_label
                                        ? ` (${ds.unit})`
                                        : '';
                                    item.text = `${ds.label}${suffix} ${value}`;
                                });
                                return items;
                            },
                        },
                        onClick: defaultLegendClick
                    },
                    title: {
                        display: this.plot_config.show_title,
                        position: this.plot_config.title_position,
                        text: this.plot_config.title || '',
                        color: getColor(this.plot_config.title_color),
                        font: {
                            size: this.plot_config.title_font_size,
                        },
                        padding: {
                            top: 2,
                            bottom: 2
                        }
                    },
                }
            },
            plugins: [backgroundcolor_plugin]
        });

        const ro = new ResizeObserver(() => this.plot.resize());
        ro.observe(this.container);
    }

    /* -------------------------------------------------------------------------------------------------------------- */

    /* -------------------------------------------------------------------------------------------------------------- */
    update(msg) {
        const t = msg.time * 1000;
        // const t = Date.now();
        Object.values(msg.data).forEach(item => {
                const sid = item.id;

                if (this.plot_config.use_queue) {
                    if (this._queue[sid]) {
                        this._queue[sid].push({x: t, y: item.value});
                        if (this._queue[sid].length > 2000) {
                            // drop the oldest to avoid runaway memory
                            this._queue[sid].shift();
                        }
                    }
                } else {
                    if (sid in this._lastValue) {
                        // overwrite the last‐value for this series
                        this._lastValue[sid] = {x: t, y: item.value};
                    }
                }
            }
        )
        ;
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    _clearData() {
        if (!this.plot) return;
        this.plot.data.datasets.forEach(ds => {
            ds.data = [];
        });
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    _addSeries(cfg) {
        // handle dynamic addition if needed
    }

    /* -------------------------------------------------------------------------------------------------------------- */
    _removeSeries(id) {
        // handle dynamic removal if needed
    }
}
