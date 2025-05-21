class JSPlot {
    constructor(canvasId, wsUrl) {
        this.ctx = document.getElementById(canvasId).getContext('2d');

        // connect websocket
        this._connect(wsUrl);
    }

    _connect(wsUrl) {
        this.socket = new WebSocket(wsUrl);
        this.socket.addEventListener('open', () => {
            console.log('WebSocket connected');
        });
        this.socket.addEventListener('message', (ev) => this._onMessage(ev));
        this.socket.addEventListener('close', () => {
            console.log('WebSocket closed, retrying in 1s');
            setTimeout(() => this._connect(wsUrl), 1000);
        });
        this.socket.addEventListener('error', (err) => {
            console.error('WebSocket error', err);
            this.socket.close();
        });
    }

    _onMessage(event) {
        // let msg;
        // try {
        //   msg = JSON.parse(event.data);
        // } catch (e) {
        //   console.error('Invalid JSON:', event.data);
        //   return;
        // }
        //
        // switch (msg.type) {
        //   case 'init':
        //     this.storageTime = msg.options.storage_time;
        //     this.windowTime = msg.options.window_time;
        //     this._createAllSeries(msg.data);
        //     break;
        //
        //   case 'add':
        //     this._addSeries(msg.data);
        //     break;
        //
        //   case 'remove':
        //     this._removeSeries(msg.data);
        //     break;
        //
        //   case 'clear':
        //     this._clearAll();
        //     break;
        //
        //   case 'close':
        //     this.socket.close();
        //     break;
        //
        //   case 'update':
        //     this._updateData(msg.time, msg.data);
        //     break;
        //
        //   default:
        //     console.warn('Unknown message type', msg.type);
        // }
    }
}

// _createAllSeries(data) {
//   // initial payload contains all series definitions
//   this.chart.data.datasets = [];
//   this.datasets = {};
//   Object.values(data).forEach(payload => this._addSeries(payload));
//   this.chart.update();
// }
//
// _addSeries(payload) {
//   const {
//     id,name,unit,color,fill,fill_color,width,visible,precision
//   } = payload;
//
//   const borderColor = `rgba(${color[0]},${color[1]},${color[2]},1)`;
//   const backgroundColor = fill
//     ? `rgba(${fill_color[0]},${fill_color[1]},${fill_color[2]},${fill_color[3]})`
//     : 'transparent';
//
//   const ds = {
//     label: name + (unit? ` (${unit})`:''),
//     data: [],
//     borderColor,
//     backgroundColor,
//     borderWidth: width,
//     hidden: !visible,
//     fill: fill,
//     parsing: false,
//     tension: 0.2,
//   };
//
//   this.chart.data.datasets.push(ds);
//   this.datasets[id] = ds;
// }
//
// _removeSeries(id) {
//   this.chart.data.datasets = this.chart.data.datasets.filter(ds => ds.label !== this.datasets[id].label);
//   delete this.datasets[id];
//   this.chart.update();
// }
//
// _clearAll() {
//   Object.values(this.datasets).forEach(ds => ds.data = []);
//   this.chart.update();
// }
//
// _updateData(time, data) {
//   const t = time * 1000; // ms
//   Object.entries(data).forEach(([id, payload]) => {
//     const ds = this.datasets[id];
//     if (!ds) return;
//     ds.data.push({ x: t, y: payload.value });
//     // drop old points beyond storageTime
//     const cutoff = t - this.storageTime*1000;
//     ds.data = ds.data.filter(pt => pt.x >= cutoff);
//   });
//
//   // update x-axis range
//   const now = Date.now();
//   this.chart.options.scales.x.min = now - this.windowTime*1000;
//   this.chart.options.scales.x.max = now;
//
//   this.chart.update('none');
// }
//
// setWindowTime(seconds) {
//   this.windowTime = seconds;
//   // redefine viewport
//   const now = Date.now();
//   this.chart.options.scales.x.min = now - seconds*1000;
//   this.chart.options.scales.x.max = now;
//   this.chart.update();
// }
//
// // placeholder for future interfaces
// // setSeriesVisibility(id, visible) { ... }
// // setYAxisRange(min, max) { ... }
// }