const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function formatApiError(detail, fallback) {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail.map((issue) => {
      const field = Array.isArray(issue.loc) ? issue.loc.at(-1) : null;
      return field ? `${field}: ${issue.msg}` : issue.msg;
    });
    return messages.filter(Boolean).join("; ") || fallback;
  }
  return fallback;
}

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    let detail;
    try {
      const body = await response.json();
      detail = body.detail;
    } catch (error) {
      if (!(error instanceof SyntaxError)) {
        throw error;
      }
    }
    throw new Error(
      formatApiError(detail, `The request failed (${response.status}).`),
    );
  }
  return response.status === 204 ? null : response.json();
}

async function requestBlob(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    let detail;
    try {
      const body = await response.json();
      detail = body.detail;
    } catch (error) {
      if (!(error instanceof SyntaxError)) {
        throw error;
      }
    }
    throw new Error(
      formatApiError(detail, `The request failed (${response.status}).`),
    );
  }
  return response.blob();
}

export function fetchTransactions() {
  return request("/api/v1/transactions");
}

export function fetchTransactionSummary() {
  return request("/api/v1/transactions/summary");
}

export function updateTransaction(id, transaction) {
  return request(`/api/v1/transactions/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(transaction),
  });
}

export function deleteTransaction(id) {
  return request(`/api/v1/transactions/${id}`, { method: "DELETE" });
}

export function createTransaction(transaction) {
  return request("/api/v1/transactions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(transaction),
  });
}

export function importTransactions(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/v1/transactions/import", {
    method: "POST",
    body: formData,
  });
}

export function exportTransactions() {
  return requestBlob("/api/v1/transactions/export");
}
