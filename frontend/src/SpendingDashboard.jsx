const MAX_CATEGORIES = 6;
const MAX_MONTHS = 6;

const amountFormatter = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatMoney(value) {
  const amount = Number(value);
  return Number.isFinite(amount) ? amountFormatter.format(amount) : value;
}

function formatMonth(month) {
  const [year, monthIndex] = month.split("-").map(Number);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    year: "2-digit",
  }).format(new Date(year, monthIndex - 1, 1));
}

function percentOf(value, max) {
  const amount = Number(value);
  if (!(max > 0) || !(amount > 0)) {
    return "0%";
  }
  return `${Math.max((amount / max) * 100, 2)}%`;
}

export default function SpendingDashboard({ summary, isLoading, error, onRetry }) {
  if (isLoading && !summary) {
    return (
      <section className="panel summary-panel" aria-labelledby="spending-overview">
        <h2 id="spending-overview" className="visually-hidden">
          Spending overview
        </h2>
        <p className="state-message" role="status">
          Loading overview...
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel summary-panel" aria-labelledby="spending-overview">
        <h2 id="spending-overview" className="visually-hidden">
          Spending overview
        </h2>
        <div className="state-message error-state" role="alert">
          <p>{error}</p>
          <button className="retry-button" onClick={onRetry} type="button">
            Try again
          </button>
        </div>
      </section>
    );
  }

  if (!summary) {
    return null;
  }

  const categories = summary.by_category.slice(0, MAX_CATEGORIES);
  const months = summary.by_month.slice(-MAX_MONTHS);
  const maxCategorySpending = Math.max(
    0,
    ...categories.map((item) => Number(item.spending)),
  );
  const maxMonthlyValue = Math.max(
    0,
    ...months.flatMap((item) => [Number(item.income), Number(item.spending)]),
  );
  const net = Number(summary.net);

  return (
    <section className="panel summary-panel" aria-labelledby="spending-overview">
      <div className="section-heading">
        <div>
          <p className="eyebrow">At a glance</p>
          <h2 id="spending-overview">Spending overview</h2>
        </div>
      </div>

      <dl className="stat-grid">
        <div className="stat-card">
          <dt>Total spent</dt>
          <dd className="stat-spending">{formatMoney(summary.total_spending)}</dd>
        </div>
        <div className="stat-card">
          <dt>Total income</dt>
          <dd className="stat-income">{formatMoney(summary.total_income)}</dd>
        </div>
        <div className="stat-card">
          <dt>Net balance</dt>
          <dd className={net < 0 ? "stat-spending" : "stat-income"}>
            {formatMoney(summary.net)}
          </dd>
        </div>
        <div className="stat-card">
          <dt>Transactions</dt>
          <dd>{summary.transaction_count}</dd>
        </div>
      </dl>

      {summary.transaction_count === 0 ? (
        <p className="state-message empty-state">
          Add or import transactions to see your spending breakdown.
        </p>
      ) : (
        <div className="chart-grid">
          <div className="chart-card">
            <h3>Spending by category</h3>
            {categories.length === 0 ? (
              <p className="chart-empty">No spending recorded yet.</p>
            ) : (
              <ul className="category-bars">
                {categories.map((item) => (
                  <li key={item.category}>
                    <div className="bar-label">
                      <span>{item.category}</span>
                      <strong>{formatMoney(item.spending)}</strong>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: percentOf(item.spending, maxCategorySpending),
                        }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="chart-card">
            <h3>Monthly trend</h3>
            <div className="chart-legend" aria-hidden="true">
              <span className="legend-spending">Spent</span>
              <span className="legend-income">Income</span>
            </div>
            <ul className="month-bars">
              {months.map((item) => (
                <li
                  key={item.month}
                  aria-label={`${formatMonth(item.month)}: spent ${formatMoney(
                    item.spending,
                  )}, income ${formatMoney(item.income)}`}
                >
                  <div className="month-columns" aria-hidden="true">
                    <div
                      className="month-column spending"
                      style={{ height: percentOf(item.spending, maxMonthlyValue) }}
                      title={`Spent ${formatMoney(item.spending)}`}
                    />
                    <div
                      className="month-column income"
                      style={{ height: percentOf(item.income, maxMonthlyValue) }}
                      title={`Income ${formatMoney(item.income)}`}
                    />
                  </div>
                  <span>{formatMonth(item.month)}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}
