const webview = {
    api: new Proxy({}, {
        get(target, name) {
            return (...args) => {
                return new Promise((resolve, reject) => {
                    const callId = webview._uuid();

                    webview._promiseMap[callId] = {
                        resolve,
                        reject
                    };
                    chrome.webview.postMessage([0, [callId, name, args]]);
                });
            };
        },
    }),

    _promiseMap: {},

    _uuid() {
        const temp_url = URL.createObjectURL(new Blob());
        const result = temp_url.toString();
        URL.revokeObjectURL(temp_url);
        return result.substring(result.lastIndexOf("/") + 1);
    },

    _callJs(callId, func) {
        func()
            .then((result) => chrome.webview.postMessage([1, [callId, JSON.stringify(result), false]]))
            .catch((error) => chrome.webview.postMessage([1, [callId, JSON.stringify(error), true]]));
    },

    _resultOk(callId, result, isError) {
        const promise = this._promiseMap[callId];
        if (isError) {
            const error = new Error(result.message);
            error.name = result.name;
            error.stack = result.stack;
            promise.reject(error);
        } else {
            promise.resolve(result);
        }
        delete this._promiseMap[callId];
    },

    _fetchJs(url) {
        return new Promise((resolve) => {
            const script = document.createElement("script");
            script.onload = resolve;
            script.src = url;
            document.body.appendChild(script);
        });
    },
};
dispatchEvent(new CustomEvent("webviewready"));