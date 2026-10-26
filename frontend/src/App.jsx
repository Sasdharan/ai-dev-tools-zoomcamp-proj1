import { useEffect, useState } from "react";
import { createTransaction, fetchTransactions } from "./api.js";

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
      await createTransaction({
        date: `${form.date}T00:00:00`,
        amount: normalizedAmount,
        merchant: form.merchant.trim(),
        category: form.category.trim(),
      });
      setForm(EMPTY_FORM);
      setFormMessage({ type: "success", text: "Transaction saved." });
      await loadTransactions();
    } catch (error) {
      setFormMessage({ type: "error", text: error.message });
    } finally {
      setIsSubmitting(false);
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
              <h2 id="new-transaction">New transaction</h2>
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
            <button className="submit-button" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Saving..." : "Save transaction"}
            </button>
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
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
