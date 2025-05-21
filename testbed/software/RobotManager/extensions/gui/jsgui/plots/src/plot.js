import Chart from 'chart.js/auto';
import 'chartjs-adapter-moment';             // Time adapter
import streamingPlugin from 'chartjs-plugin-streaming';

// Register the streaming plugin
Chart.register(streamingPlugin);

// Keep a reference to the default legend onClick and generateLabels
const defaultLegendClick = Chart.defaults.plugins.legend.onClick;
const defaultGenerateLabels = Chart.defaults.plugins.legend.labels.generateLabels;

// Configuration constants
const UPDATE_INTERVAL_MS = 100;      // how often to fetch new data (in ms)
let WINDOW_DURATION_MS = 15 * 1000;  // initial time window size (in ms)

// Get canvas context
const ctx = document.getElementById('plot').getContext('2d');

const plugin = {
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

// Create the chart instance
export const streamingChart = new Chart(ctx, {
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
            },
            {
                label: 'Up',
                borderColor: 'rgb(0,115,255)',
                borderWidth: 2,
                data: [],
                yAxisID: 'yUpload'
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
                        chart.data.datasets[1].data.push({x: now, y: Math.random() * 20 - 10});
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
            yUpload: {
                position: 'right',
                title: {display: true, text: 'Upload (Mbps)', color: 'rgb(0,115,255)'},
                ticks: {color: 'rgb(0,115,255)'},
                grid: {drawOnChartArea: false, color: 'rgba(0,115,255,0.2)', lineWidth: 2},
                min: -12,
                max: 12,
            }
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
    plugins: [plugin]
});

// Slider logic
const slider = document.getElementById('windowSize');
const sliderValue = document.getElementById('windowSizeValue');
slider.addEventListener('input', () => {
    const seconds = parseInt(slider.value, 10);
    sliderValue.textContent = seconds;
    // update the realtime window
    streamingChart.options.scales.x.realtime.duration = seconds * 1000;
    streamingChart.update('none');
});
