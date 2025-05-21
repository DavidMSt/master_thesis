// const {createApp, ref, reactive, computed, onMounted, nextTick} = Vue;
console.log("__VUE_OPTIONS_API__ is", __VUE_OPTIONS_API__);

import {createApp, ref, reactive, computed, onMounted, nextTick} from 'vue'

export function mountTerminal(elSelector) {
    const app = createApp({
        template: `
         <!-- terminal.html -->
        <div id="terminal-window" style="display:flex; flex-direction:column; height:100%; width: 100%">
            <div
                    id="terminalLogContainer"
                    ref="terminalLogContainer"
                    style="flex:1; overflow-y:auto; background-color:#333; padding:10px; font-family:monospace;"
            >
                <div v-for="(log, index) in terminalLogs" :key="index">
                    <span :style="{ color: log.color }">{{ log.text }}</span>
                </div>
            </div>

            <div id="terminal-path">Current Path: {{ currentPath }}</div>
            <div id="terminal-suggestions" v-html="suggestions"></div>

            <div style="display:flex; border-top:1px solid #333;">
                <input
                        v-model="terminalInput"
                        @input="updateSuggestions"
                        @keydown="handleKeydown"
                        @keydown.enter.prevent="handleTerminalSubmit"
                        style="flex:1; padding:5px; font-family:monospace;"
                        placeholder="Enter command…"
                />
                <button @click="handleTerminalSubmit" style="padding:5px;">Send</button>
            </div>
        </div>`,
        setup()
    {
        // — state —
        const terminalLogs = ref([]);
        const terminalInput = ref("");
        const suggestions = ref("");
        const commandSets = ref({});
        const activeSet = ref([]);
        const currentPath = computed(() => activeSet.value.join(" / ") || "");
        const terminalLogContainer = ref(null);

        // Websocket status + counters
        const terminalWsStatus = reactive({connected: false, frequency: 0, count: 0});
        let terminalWs = null;
        const commandHistory = ref([]);
        const historyIndex = ref(null);

        function isNegativeNumber(str) {
            return /^-\d+(\.\d+)?$/.test(str);
        }

        function castValue(val) {
            if (/^-?\d+$/.test(val)) return parseInt(val, 10);
            if (/^-?\d+\.\d+$/.test(val)) return parseFloat(val);
            if (val.toLowerCase() === "true") return true;
            if (val.toLowerCase() === "false") return false;
            return val;
        }

        function splitTokens(text) {
            return text.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
        }

        function getSetByPath(pathArr) {
            let current = commandSets.value;
            for (let i = 1; i < pathArr.length; i++) {
                if (current.child_sets && current.child_sets[pathArr[i]]) {
                    current = current.child_sets[pathArr[i]];
                } else {
                    return null;
                }
            }
            return current;
        }

        function getSuggestions(inputText) {
            const tokens = splitTokens(inputText);
            const completeToken = inputText.endsWith(" ");
            let path = activeSet.value.length ? [...activeSet.value] : (commandSets.value.name ? [commandSets.value.name] : []);
            let currentSetLocal = getSetByPath(path) || commandSets.value;
            let tokensCopy = [...tokens];
            if (tokensCopy.length > 0) {
                if (tokensCopy[0] === "..") {
                    if (path.length > 1) {
                        path.pop();
                        currentSetLocal = getSetByPath(path);
                    }
                    tokensCopy.shift();
                } else if (tokensCopy[0] === ".") {
                    path = [commandSets.value.name];
                    currentSetLocal = commandSets.value;
                    tokensCopy.shift();
                }
            }
            let recognizedCommand = null;
            let tokensToTraverse = completeToken ? tokensCopy : tokensCopy.slice(0, tokensCopy.length - 1);
            let partialToken = completeToken ? "" : (tokensCopy[tokensCopy.length - 1] || "");
            for (let token of tokensToTraverse) {
                if (currentSetLocal.child_sets && currentSetLocal.child_sets[token]) {
                    path.push(token);
                    currentSetLocal = currentSetLocal.child_sets[token];
                } else if (currentSetLocal.commands && currentSetLocal.commands[token]) {
                    recognizedCommand = currentSetLocal.commands[token];
                    break;
                } else {
                    break;
                }
            }
            if (recognizedCommand) {
                const args = recognizedCommand.arguments;
                if (args) {
                    let argSuggestions = [];
                    for (let argName in args) {
                        let argDef = args[argName];
                        let argType = argDef.type || "str";
                        if (argType.toLowerCase() === "flag" || argType.toLowerCase() === "bool") {
                            argType = "FLAG";
                        }
                        if (argDef.short_name) {
                            argSuggestions.push("--" + argName + " (-" + argDef.short_name + ", " + argType + ")");
                        } else {
                            argSuggestions.push("--" + argName + " (" + argType + ")");
                        }
                    }
                    return "Inputs: " + argSuggestions.join(" ");
                }
                return "Inputs: none";
            } else {
                let extras = [];
                if (path.length > 1 && (!partialToken || "..".startsWith(partialToken))) {
                    extras.push("..");
                }
                if (!partialToken || ".".startsWith(partialToken)) {
                    extras.push(".");
                }
                let sets = [];
                if (currentSetLocal.child_sets) {
                    for (let s in currentSetLocal.child_sets) {
                        if (!partialToken || s.toLowerCase().startsWith(partialToken.toLowerCase())) {
                            sets.push(s);
                        }
                    }
                }
                let cmds = [];
                if (currentSetLocal.commands) {
                    for (let c in currentSetLocal.commands) {
                        if (!partialToken || c.toLowerCase().startsWith(partialToken.toLowerCase())) {
                            cmds.push(c);
                        }
                    }
                }
                const extrasFormatted = extras.map(x => "<span>" + x + "</span>");
                const setsFormatted = sets.map(x => "<span style=\"color: orange;\">" + x + "</span>");
                const cmdsFormatted = cmds.map(x => "<span style=\"color: cyan;\">" + x + "</span>");
                const allFormatted = extrasFormatted.concat(setsFormatted).concat(cmdsFormatted);
                return "Commands: " + (allFormatted.length ? allFormatted.join(" ") : "none");
            }
        }

        function parseCommand(inputText) {
            const tokens = splitTokens(inputText);
            if (tokens.length === 0) {
                return {success: false, error: "Empty command"};
            }
            let path = activeSet.value.length ? [...activeSet.value] : (commandSets.value.name ? [commandSets.value.name] : []);
            let currentSetLocal = getSetByPath(path) || commandSets.value;
            let i = 0;
            while (i < tokens.length && (tokens[i] === "." || tokens[i] === "..")) {
                if (tokens[i] === ".") {
                    path = [commandSets.value.name];
                    currentSetLocal = commandSets.value;
                } else if (tokens[i] === "..") {
                    if (path.length > 1) {
                        path.pop();
                        currentSetLocal = getSetByPath(path);
                    } else {
                        return {success: false, error: "Already at root, cannot exit further."};
                    }
                }
                i++;
            }
            let cmdName = null;
            for (; i < tokens.length; i++) {
                let token = tokens[i];
                if (currentSetLocal.child_sets && currentSetLocal.child_sets[token]) {
                    path.push(token);
                    currentSetLocal = currentSetLocal.child_sets[token];
                } else if (currentSetLocal.commands && currentSetLocal.commands[token]) {
                    cmdName = token;
                    i++;
                    break;
                } else {
                    return {success: false, error: "Token '" + token + "' not recognized in set " + path.join("/")};
                }
            }
            if (!cmdName) {
                activeSet.value = path;
                return {success: true, type: "change_set", active_set: path};
            }
            const cmdDef = currentSetLocal.commands[cmdName];
            let positional = [];
            let keyword = {};
            while (i < tokens.length) {
                let token = tokens[i];
                if (token.startsWith("--")) {
                    if (token.includes("=")) {
                        let eqIndex = token.indexOf("=");
                        let key = token.slice(2, eqIndex);
                        let value = token.slice(eqIndex + 1);
                        keyword[key] = value;
                    } else {
                        let key = token.slice(2);
                        if (i + 1 < tokens.length && !tokens[i + 1].startsWith("-")) {
                            keyword[key] = tokens[i + 1];
                            i++;
                        } else {
                            keyword[key] = true;
                        }
                    }
                } else if (token.startsWith("-") && !token.startsWith("--")) {
                    let short = token.slice(1);
                    let matchedLong = null;
                    if (cmdDef && cmdDef.arguments) {
                        for (let argName in cmdDef.arguments) {
                            let argDef = cmdDef.arguments[argName];
                            if (argDef.short_name === short) {
                                matchedLong = argName;
                                break;
                            }
                        }
                    }
                    if (matchedLong) {
                        if (i + 1 < tokens.length && (!tokens[i + 1].startsWith("-") || isNegativeNumber(tokens[i + 1]))) {
                            keyword[matchedLong] = tokens[i + 1];
                            i++;
                        } else {
                            keyword[matchedLong] = true;
                        }
                    } else {
                        positional.push(token);
                    }
                } else {
                    positional.push(token);
                }
                i++;
            }
            positional = positional.map(castValue);
            for (let key in keyword) {
                if (cmdDef && cmdDef.arguments && cmdDef.arguments[key] && cmdDef.arguments[key].type) {
                    let argType = cmdDef.arguments[key].type.toLowerCase();
                    if (argType === "int") {
                        keyword[key] = parseInt(keyword[key], 10);
                    } else if (argType === "float") {
                        keyword[key] = parseFloat(keyword[key]);
                    } else if (argType === "bool" || argType === "flag") {
                        keyword[key] = (keyword[key] === true || keyword[key].toString().toLowerCase() === "true");
                    } else {
                        keyword[key] = keyword[key];
                    }
                } else {
                    keyword[key] = castValue(keyword[key]);
                }
            }
            return {
                success: true,
                type: "command",
                command: {name: cmdName, path: path, arguments: {positional: positional, keyword: keyword}},
                active_set: activeSet.value
            };
        }

        function addLog(text, color) {
            const ts = new Date().toLocaleTimeString();
            terminalLogs.value.push({text: `[${ts}] ${text}`, color});
            nextTick(() => {
                if (terminalLogContainer.value)
                    terminalLogContainer.value.scrollTop = terminalLogContainer.value.scrollHeight;
            });
        }

        function updateSuggestions() {
            suggestions.value = getSuggestions(terminalInput.value);
        }

        function handleTerminalSubmit() {
            const txt = terminalInput.value.trim();
            if (!txt) return;
            if (txt.toLowerCase() === "clear") {
                terminalLogs.value = [];
                terminalInput.value = "";
                updateSuggestions();
                return;
            }
            addLog(">> " + txt, "cyan");
            commandHistory.value.push(txt);
            historyIndex.value = null;
            const res = parseCommand(txt);
            if (!res.success) {
                addLog(res.error, "red");
            } else if (res.type === "change_set") {
                activeSet.value = res.active_set;
                addLog("Changed set to: " + activeSet.value.join(" / "), "yellow");
            } else { // a real command
                if (terminalWs && terminalWs.readyState === WebSocket.OPEN) {
                    terminalWs.send(JSON.stringify({type: 'command', data: res.command}));
                } else {
                    addLog("WebSocket not connected", "red");
                }
            }
            terminalInput.value = "";
            updateSuggestions();
        }

        function handleKeydown(e) {
            if (e.key === "ArrowUp" && commandHistory.value.length) {
                historyIndex.value = historyIndex.value === null
                    ? commandHistory.value.length - 1
                    : Math.max(0, historyIndex.value - 1);
                terminalInput.value = commandHistory.value[historyIndex.value];
                updateSuggestions();
                e.preventDefault();
            }
            if (e.key === "ArrowDown" && commandHistory.value.length) {
                if (historyIndex.value === null) return;
                historyIndex.value = historyIndex.value < commandHistory.value.length - 1
                    ? historyIndex.value + 1
                    : null;
                terminalInput.value = historyIndex.value === null
                    ? ""
                    : commandHistory.value[historyIndex.value];
                updateSuggestions();
                e.preventDefault();
            }
        }

        // — WebSocket hookup —
        function connectTerminalWebSocket() {
            terminalWs = new WebSocket("ws://localhost:8090");
            terminalWs.onopen = () => {
                addLog("Terminal Websocket connected", "green");
                terminalWsStatus.connected = true;
            };
            terminalWs.onmessage = ev => {
                const data = JSON.parse(ev.data);
                terminalWsStatus.count++;
                if (data.type === 'log' && data.data?.text) {
                    addLog(data.data.text, data.data.color || '#d3d3d3');
                }
                if (data.type === 'commands' && data.data) {
                    commandSets.value = data.data;
                    activeSet.value = data.data.name ? [data.data.name] : [];
                    updateSuggestions();
                }
            };
            terminalWs.onerror = err => console.error("Terminal WS error:", err);
            terminalWs.onclose = () => {
                terminalWsStatus.connected = false;
                setTimeout(connectTerminalWebSocket, 3000);
            };
        }

        onMounted(() => {
            updateSuggestions()
            connectTerminalWebSocket();
            setInterval(() => {
                terminalWsStatus.frequency = terminalWsStatus.count;
                terminalWsStatus.count = 0;
            }, 1000);
        });

        return {
            terminalLogs,
            terminalInput,
            suggestions,
            currentPath,
            terminalLogContainer,
            terminalWsStatus,
            updateSuggestions,
            handleTerminalSubmit,
            handleKeydown
        };
    }
})
    ;

    app.mount(elSelector);
}
