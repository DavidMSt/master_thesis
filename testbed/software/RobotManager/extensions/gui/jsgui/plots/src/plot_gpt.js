import Chart from "chart.js/auto";
import 'chartjs-adapter-moment';
import streamingPlugin from 'chartjs-plugin-streaming';

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

export class JSPlot {
    constructor(canvasId, wsUrl) {
        this.ctx = document.getElementById(canvasId).getContext('2d');
        this._queue = {};
        this._connect(wsUrl);
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
                this._initializePlot(msg);
                break;
            case 'update':
                this._queueUpdate(msg);
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

    _initializePlot(msg) {

        if (this.plot) {
            this.plot.destroy();
            this.plot = null;
            this._queue = {};    // and reset all your queues
        }

        const plotOptions = msg.options;
        const tsDef = msg.timeseries;
        const datasets = [];
        const yAxes = {};

        // Convert background color
        const bg = plotOptions.background_color;
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

            // Create dataset
            datasets.push({
                label: cfg.name,
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
                    display: Boolean(cfg.y_axis_label || cfg.unit),
                    text: cfg.y_axis_label || (cfg.unit || '')
                },
                ticks: {
                    color: borderColor,
                    callback: (value) => value.toFixed(cfg.precision)
                },
                grid: {
                    display: cfg.y_axis_grid,
                    drawOnChartArea: cfg.y_axis_grid
                }
            };
            if (cfg.min !== null && cfg.min !== undefined) yAxes[cfg.id].min = cfg.min;
            if (cfg.max !== null && cfg.max !== undefined) yAxes[cfg.id].max = cfg.max;
        });

        // Convert time ticks color
        const tc = plotOptions.time_ticks_color.map(c => Math.round(c * 255));
        const timeTickColor = `rgba(${tc[0]}, ${tc[1]}, ${tc[2]}, ${tc[3] || 1})`;

        // Create chart
        this.plot = new Chart(this.ctx, {
            type: 'line',
            data: {datasets},
            options: {
                animation: false,
                normalized: true,
                scales: {
                    x: {
                        type: 'realtime',
                        realtime: {
                            duration: Math.floor(plotOptions.window_time * 1000),
                            refresh: Math.floor(plotOptions.update_time*1000),
                            delay: Math.floor(plotOptions.pre_delay*1000),
                            onRefresh: chart => {
                                chart.data.datasets.forEach(ds => {
                                    const queue = this._queue[ds.seriesId] || [];
                                    if (queue.length) {
                                        const latest = queue[queue.length - 1];
                                        this._queue[ds.seriesId] = [];
                                        ds.data.push(latest);
                                    }
                                });
                            }
                        },
                        time: {
                            displayFormats: {
                                second: plotOptions.time_display_format,
                                minute: plotOptions.time_display_format,
                                hour: plotOptions.time_display_format
                            },
                            tooltipFormat: plotOptions.time_display_format,
                            unit: 'second'
                        },
                        ticks: {color: timeTickColor},
                        grid: {color: timeTickColor}
                    },
                    ...yAxes
                },
                elements: {point: {radius: 0}},
                plugins: {
                    customCanvasBackgroundColor: {color: bgColor},
                    legend: {
                        position: 'top',
                        labels: {
                            font: {family: 'monospace'},
                            generateLabels: chart => {
                                const items = defaultGenerateLabels(chart);
                                items.forEach(item => {
                                    const ds = chart.data.datasets[item.datasetIndex];
                                    const data = ds.data;
                                    const last = data.length ? data[data.length - 1].y : 0;
                                    const formatted = last.toFixed(ds.precision).padStart(6, ' ');
                                    item.text = `${ds.label} ${formatted}`;
                                });
                                return items;
                            }
                        },
                        onClick: defaultLegendClick
                    }
                }
            },
            plugins: [backgroundcolor_plugin]
        });
    }

    _queueUpdate(msg) {
        const t = msg.time * 1000;
        Object.values(msg.data).forEach(item => {
            const sid = item.id;
            if (this._queue[sid]) {
                this._queue[sid].push({x: t, y: item.value});
            }
        });
    }

    _clearData() {
        if (!this.plot) return;
        this.plot.data.datasets.forEach(ds => {
            ds.data = [];
        });
    }

    _addSeries(cfg) {
        // handle dynamic addition if needed
    }

    _removeSeries(id) {
        // handle dynamic removal if needed
    }
}
