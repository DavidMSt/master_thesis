import Chart from "chart.js/auto";
import 'chartjs-adapter-moment';
import streamingPlugin from 'chartjs-plugin-streaming';

// Register the streaming plugin
Chart.register(streamingPlugin);

const UPDATE_INTERVAL_MS = 100;      // how often to fetch new data (in ms)
let WINDOW_DURATION_MS = 15 * 1000;  // initial time window size (in ms)


const backgroundcolor_plugin = {
    id: 'customCanvasBackgroundColor',
    beforeDraw: (chart, args, options) => {
        const {ctx} = chart;
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

    plot = null;
    ctx = null;

    constructor(canvasId, wsUrl) {
        this.ctx = document.getElementById(canvasId).getContext('2d');
        this._connect(wsUrl);

    }

    _connect(wsUrl) {
        this.socket = new WebSocket(wsUrl);
        this.socket.addEventListener('open', () => {
            console.log('WebSocket connected');
        });
        this.socket.addEventListener('message', (ev) => this._onMessage(ev));
        this.socket.addEventListener('close', () => {
            console.log('WebSocket closed, retrying in 3s');
            setTimeout(() => this._connect(wsUrl), 3000);
        });
        this.socket.addEventListener('error', (err) => {
            // console.error('WebSocket error', err);
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
                this._updateData(msg);
                break;
            case 'clear':
                break;
            case 'add':
                // Do not handle that for now
                break;
            case 'remove':
                // Do not handle that for now
                break;
            default:
                console.warn('Unknown message type', msg.type);
        }

    }

    // -----------------------------------------------------------------------------------------------------------------
    _initializePlot(msg) {
        console.log('Initializing plot');

        const plot_options = msg.options;
        const timeseries_definition = msg.timeseries;
        console.log('Plot options:');
        console.log(plot_options);
        console.log('Timeseries definition:');
        console.log(timeseries_definition);


        this.plot = new Chart(this.ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Down',
                        borderColor: 'rgb(237,18,237)',
                        borderWidth: 2,
                        fill: false,
                        data: [],          // streaming plugin manages this
                        yAxisID: 'yDownload',
                        tension: 0.1,
                    }
                ]
            },
            options: {
                animation: false,
                normalized: true,
                scales: {
                    x: {
                        type: 'realtime',
                        realtime: {
                            duration: WINDOW_DURATION_MS,
                            refresh: UPDATE_INTERVAL_MS,
                            delay: 100,
                            onRefresh: chart => {
                                const now = Date.now();
                                chart.data.datasets[0].data.push({x: now, y: Math.random() * 200 - 100});
                                // chart.data.datasets[1].data.push({x: now, y: Math.random() * 20 - 10});
                            }
                        },
                        time: {
                            displayFormats: {second: 'HH:mm:ss', minute: 'HH:mm:ss', hour: 'HH:mm:ss',},
                            tooltipFormat: 'HH:mm:ss',
                            unit: 'second',
                        },
                        ticks: {
                            autoSkip: true,
                            maxRotation: 0,
                            source: 'auto',
                            color: 'rgba(0,0,0,0.8)',
                        },
                        grid: {
                            drawOnChartArea: true,
                            color: 'rgba(0,0,0,0.2)',
                            lineWidth: 1,
                            borderColor: 'rgba(0,0,0,0.2)',
                            borderWidth: 1,
                        }
                    },
                    yDownload: {
                        position: 'left',
                        title: {display: true, text: 'Download (Mbps)', color: 'rgb(237,18,237)'},
                        ticks: {color: 'rgb(237,18,237)'},
                        grid: {
                            drawOnChartArea: true,
                            lineWidth: ctx => ctx.tick.value === 0 ? 2 : 1,
                            color: ctx => ctx.tick.value === 0
                                ? 'rgba(237,18,237,1)'
                                : 'rgba(237,18,237,0.4)',
                        },
                        min: -100,
                        max: 100,
                    },
                    // yUpload: {
                    //     position: 'right',
                    //     title: {display: true, text: 'Upload (Mbps)', color: 'rgb(0,115,255)'},
                    //     ticks: {color: 'rgb(0,115,255)'},
                    //     grid: {drawOnChartArea: false, color: 'rgba(0,115,255,0.2)', lineWidth: 2},
                    //     min: -12,
                    //     max: 12,
                    // }
                },
                elements: {
                    point: {radius: 0}
                },
                plugins: {
                    customCanvasBackgroundColor: {
                        color: 'rgba(255,255,255, 0.8)',
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            // Use monospace font so numbers don't jump
                            font: {family: 'monospace'},
                            // Custom label generator that appends the latest value
                            generateLabels: chart => {
                                const items = defaultGenerateLabels(chart);
                                items.forEach(item => {
                                    const ds = chart.data.datasets[item.datasetIndex];
                                    const data = ds.data;
                                    // get last value or zero if none
                                    const last = data.length ? data[data.length - 1].y : 0;
                                    // one decimal, pad to width 6 (reserving space for minus)
                                    const formatted = last.toFixed(1).padStart(6, ' ');
                                    item.text = `${ds.label} ${formatted}`;
                                });
                                return items;
                            }
                        },
                        // preserve toggle behavior
                        onClick: defaultLegendClick
                    }
                }
            },
            plugins: [backgroundcolor_plugin]
        })
    }

    // -----------------------------------------------------------------------------------------------------------------
    _updateData(msg) {
        console.log('Updating plot');
        console.log(msg)
    }
}