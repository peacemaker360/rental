// Retry only explicitly selected reads. Never replay writes or system requests.
export async function requestJson(fetcher, url, options = {}, {recover = false, translate = key => key, wait = ms => new Promise(resolve => setTimeout(resolve, ms))} = {}) {
  const attempts = recover && (options.method || "GET").toUpperCase() === "GET" ? 2 : 1;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      let response;
      try {
        response = await fetcher(url, options);
      } catch (error) {
        // Auth-provider failures are system failures, not retryable data transport.
        if (error?.data?.errorCode) throw error;
        if (options.signal?.aborted) throw Object.assign(new Error(translate("messages.request_failed")), {retryable: false});
        throw Object.assign(new Error(translate("messages.connection_unavailable")), {status: 0, retryable: true});
      }
      const data = await response.json().catch(() => null);
      if (response.ok && data !== null) return data;
      const status = response.ok ? 502 : response.status;
      const serverFailure = status >= 500;
      const integrity = data?.errorCode === "DATA_INTEGRITY_ERROR";
      const configuration = ["AUTH_CONFIGURATION_ERROR", "CONTEXT_CONFIGURATION_ERROR"].includes(data?.errorCode);
      const requestId = /^[a-f0-9]{32}$/.test(data?.requestId || "") ? data.requestId : "";
      let message = serverFailure
        ? translate(integrity ? "messages.data_unavailable" : configuration ? "messages.configuration_unavailable" : "messages.service_unavailable")
        : data?.error || translate("messages.request_failed");
      if (serverFailure && requestId) message += ` ${translate("messages.error_reference", {reference: requestId})}`;
      const error = Object.assign(new Error(message), {
        status,
        data: serverFailure ? {errorCode: integrity ? "DATA_INTEGRITY_ERROR" : configuration ? "AUTH_CONFIGURATION_ERROR" : "BACKEND_UNAVAILABLE", requestId} : data || {},
        retryable: serverFailure && !integrity && !configuration && data?.retryable !== false
      });
      throw error;
    } catch (error) {
      if (!error.retryable || attempt + 1 === attempts) throw error;
      await wait(750);
    }
  }
}
