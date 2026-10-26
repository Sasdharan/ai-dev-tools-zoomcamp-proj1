import { useEffect, useState } from "react";
import {
  createTransaction,
  deleteTransaction,
  exportTransactions,
  fetchTransactions,
  importTransactions,
  updateTransaction,
} from "./api.js";

const EMPTY_FORM = {
  date: "",
  amount: "",
  merchant: "",
  category: "",
};

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function formatAmount(value) {
  const amount = Number(value);
  return Number.isFinite(amount) ? amount.toFixed(2) : value;
}

export default function App() {
  const [transactions, setTransactions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formMessage, setFormMessage] = useState(null);
  const [editingTransactionId, setEditingTransactionId] = useState(null);
  const [deletingTransactionId, setDeletingTransactionId] = useState(null);
  const [transactionActionError, setTransactionActionError] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [importMessage, setImportMessage] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState("");

  async function loadTransactions() {
    setIsLoading(true);
    setLoadError("");
    try {
      setTransactions(await fetchTransactions());
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadTransactions();
  }, []);

  function updateForm(event) {
    const { name, value } = event.target;
    setForm((currentForm) => ({ ...currentForm, [name]: value }));
    setFormMessage(null);
  }

  function cancelEditing() {
    setEditingTransactionId(null);
    setForm(EMPTY_FORM);
    setFormMessage(null);
  }

  function startEditing(transaction) {
    setEditingTransactionId(transaction.id);
    setForm({
      date: transaction.date.slice(0, 10),
      amount: String(transaction.amount),
      merchant: transaction.merchant,
      category: transaction.category,
    });
    setFormMessage(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const normalizedAmount = form.amount.trim();
    if (!/^-?\d{1,10}(?:\.\d{1,2})?$/.test(normalizedAmount)) {
      setFormMessage({
        type: "error",
        text: "Enter an amount with up to 10 digits and 2 decimal places.",
      });
      return;
    }
    if (!form.merchant.trim() || !form.category.trim()) {
      setFormMessage({
        type: "error",
        text: "Merchant and category cannot be blank.",
      });
      return;
    }

    setIsSubmitting(true);
    setFormMessage(null);
    try {
      const transaction = {
        date: `${form.date}T00:00:00`,
        amount: normalizedAmount,
        merchant: form.merchant.trim(),
        category: form.category.trim(),
      };
      if (editingTransactionId === null) {
        await createTransaction(transaction);
      } else {
        await updateTransaction(editingTransactionId, transaction);
      }
      setEditingTransactionId(null);
      setForm(EMPTY_FORM);
      setFormMessage({
        type: "success",
        text:
          editingTransactionId === null
            ? "Transaction saved."
            : "Transaction updated.",
      });
      await loadTransactions();
    } catch (error) {
      setFormMessage({ type: "error", text: error.message });
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(transaction) {
    if (
      !window.confirm(
        `Delete the transaction for ${transaction.merchant}? This cannot be undone.`,
      )
    ) {
      return;
    }

    setDeletingTransactionId(transaction.id);
    setTransactionActionError("");
    try {
      await deleteTransaction(transaction.id);
      setTransactions((currentTransactions) =>
        currentTransactions.filter((item) => item.id !== transaction.id),
      );
      if (editingTransactionId === transaction.id) {
        cancelEditing();
      }
    } catch (error) {
      setTransactionActionError(error.message);
    } finally {
      setDeletingTransactionId(null);
    }
  }

  async function handleImport(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const file = formElement.elements.namedItem("csv-file").files[0];
    if (!file) {
      setImportMessage({ type: "error", text: "Choose a CSV file to import." });
      return;
    }

    setIsImporting(true);
    setImportMessage(null);
    try {
      const result = await importTransactions(file);
      const rejectedRows = result.rejected
        .map(
          (row) =>
            `Row ${row.row_number}: ${row.errors.join(", ")}`,
        )
        .join("\n");
      setImportMessage({
        type: result.rejected.length > 0 ? "error" : "success",
        text: `Imported ${result.imported} ${
          result.imported === 1 ? "transaction" : "transactions"
        }.${
          rejectedRows
            ? ` ${result.rejected.length} row(s) were rejected:\n${rejectedRows}`
            : ""
        }`,
      });
      formElement.reset();
      await loadTransactions();
    } catch (error) {
      setImportMessage({ type: "error", text: error.message });
    } finally {
      setIsImporting(false);
    }
  }

  async function handleExport() {
    setIsExporting(true);
    setExportError("");
    try {
      const blob = await exportTransactions();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "transactions.csv";
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      setExportError(error.message);
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">Personal finance</p>
          <h1>Expense Tracker</h1>
          <p className="description">
            Keep your everyday spending in one clear place.
          </p>
        </div>
        <div className="header-mark" aria-hidden="true">
          $
        </div>
      </header>

      <div className="dashboard-grid">
        <section className="panel form-panel" aria-labelledby="new-transaction">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Add to your records</p>
              <h2 id="new-transaction">
                {editingTransactionId === null
                  ? "New transaction"
                  : "Edit transaction"}
              </h2>
            </div>
          </div>
          <form onSubmit={handleSubmit}>
            <label>
              Date
              <input
                autoComplete="off"
                name="date"
                onChange={updateForm}
                required
                type="date"
                value={form.date}
              />
            </label>
            <label>
              Amount
              <input
                inputMode="decimal"
                max="9999999999.99"
                min="-9999999999.99"
                name="amount"
                onChange={updateForm}
                placeholder="0.00"
                required
                step="0.01"
                type="number"
                value={form.amount}
              />
            </label>
            <label>
              Merchant
              <input
                maxLength={255}
                name="merchant"
                onChange={updateForm}
                placeholder="e.g. Coffee House"
                required
                type="text"
                value={form.merchant}
              />
            </label>
            <label>
              Category
              <input
                maxLength={100}
                name="category"
                onChange={updateForm}
                placeholder="e.g. Food & Drinks"
                required
                type="text"
                value={form.category}
              />
            </label>
            {formMessage && (
              <p
                className={`form-message ${formMessage.type}`}
                role={formMessage.type === "error" ? "alert" : "status"}
              >
                {formMessage.text}
              </p>
            )}
            <div className="form-actions">
              <button
                className="submit-button"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting
                  ? editingTransactionId === null
                    ? "Saving..."
                    : "Updating..."
                  : editingTransactionId === null
                    ? "Save transaction"
                    : "Update transaction"}
              </button>
              {editingTransactionId !== null && (
                <button
                  className="secondary-button"
                  disabled={isSubmitting}
                  onClick={cancelEditing}
                  type="button"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </section>

        <section className="panel transactions-panel" aria-labelledby="transactions">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Your activity</p>
              <h2 id="transactions">Transactions</h2>
            </div>
            {!isLoading && !loadError && (
              <span className="transaction-count">
                {transactions.length}{" "}
                {transactions.length === 1 ? "record" : "records"}
              </span>
            )}
          </div>

          <div className="data-tools">
            <button
              className="secondary-button"
              disabled={isExporting}
              onClick={handleExport}
              type="button"
            >
              {isExporting ? "Preparing CSV..." : "Export CSV"}
            </button>
            <form className="import-form" onSubmit={handleImport}>
              <label htmlFor="csv-file">Import CSV</label>
              <div className="import-controls">
                <input
                  accept=".csv,text/csv"
                  id="csv-file"
                  name="csv-file"
                  required
                  type="file"
                />
                <button
                  className="secondary-button"
                  disabled={isImporting}
                  type="submit"
                >
                  {isImporting ? "Importing..." : "Import"}
                </button>
              </div>
            </form>
          </div>
          {importMessage && (
            <p
              className={`form-message ${importMessage.type} import-message`}
              role={importMessage.type === "error" ? "alert" : "status"}
            >
              {importMessage.text}
            </p>
          )}
          {exportError && (
            <p className="form-message error" role="alert">
              {exportError}
            </p>
          )}
          {transactionActionError && (
            <p className="form-message error" role="alert">
              {transactionActionError}
            </p>
          )}

          {isLoading ? (
            <p className="state-message" role="status">
              Loading transactions...
            </p>
          ) : loadError ? (
            <div className="state-message error-state" role="alert">
              <p>{loadError}</p>
              <button className="retry-button" onClick={loadTransactions} type="button">
                Try again
              </button>
            </div>
          ) : transactions.length === 0 ? (
            <p className="state-message empty-state">
              No transactions yet. Add your first one using the form.
            </p>
          ) : (
            <ul className="transaction-list">
              {transactions.map((transaction) => (
                <li className="transaction-item" key={transaction.id}>
                  <div className="transaction-details">
                    <strong>{transaction.merchant}</strong>
                    <span>
                      {transaction.category} · {formatDate(transaction.date)}
                    </span>
                  </div>
                  <span className="transaction-amount">
                    {formatAmount(transaction.amount)}
                  </span>
                  <div className="transaction-actions">
                    <button
                      className="text-button"
                      aria-label={`Edit ${transaction.merchant}`}
                      disabled={
                        isSubmitting || deletingTransactionId !== null
                      }
                      onClick={() => startEditing(transaction)}
                      type="button"
                    >
                      Edit
                    </button>
                    <button
                      className="text-button danger-button"
                      aria-label={`Delete ${transaction.merchant}`}
                      disabled={
                        isSubmitting || deletingTransactionId !== null
                      }
                      onClick={() => handleDelete(transaction)}
                      type="button"
                    >
                      {deletingTransactionId === transaction.id
                        ? "Deleting..."
                        : "Delete"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
