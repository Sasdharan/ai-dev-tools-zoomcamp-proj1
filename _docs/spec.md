# MVP Scope: Personal Expense Tracker

## Goal

Build a local-first personal expense tracker for managing transactions, importing and exporting CSV files, and reviewing basic spending summaries. SMS-based transaction tracking is not part of this MVP.

## Users and deployment

- One user on a private, local installation; no sign-in or multi-user support.
- The app is a simple, installable Progressive Web App (PWA).
- Support local deployment with SQLite and PostgreSQL. Use SQLAlchemy so the database can be configured without changing application behavior.
- The PWA is read-only while the backend is unavailable: users may view cached transactions, but changes require a connection. Offline edits and later synchronization are out of scope.

## Transactions

Support these transaction types:

- **Expense**
- **Income**
- **Transfer** between two accounts

Users can maintain multiple accounts, but the app does not track or reconcile account balances. All transactions use one configured currency; multi-currency storage and currency conversion are out of scope.

Transactions have a category. Provide common editable categories, and allow users to create and edit categorization rules. Categorization uses local rules matching transaction descriptions or merchants; it does not call an external AI or other service. Users can correct the assigned category.

## CSV import

- Accept CSV files.
- Detect common column names and layouts, then let the user review and correct the column mapping.
- Preview parsed transactions and obtain confirmation before saving.
- Import valid rows when other rows are invalid, and report invalid rows with enough information to correct them.
- Skip likely duplicates when date, amount, description, and account all match. Report skipped duplicates in the import results.

## CSV export

- Export all transactions or a user-selected filtered/date-range subset.
- Use one stable, app-defined CSV format rather than preserving the layout of an imported file.
- Include the fields needed to represent the supported transaction types, including both accounts for a transfer.

## PWA availability

- Provide an installable app shell and read-only access to cached transactions when the backend is unavailable.
- Require the backend for creating, editing, deleting, importing, and other data-changing actions.
- Do not queue offline changes.

## Summaries

Provide basic summaries of transactions by month, category, and account. Include a pie chart showing each category's share of spending. Income and transfers must not be counted as spending in that chart.

## Out of scope

- SMS ingestion, SMS parsing, and MacroDroid/Tasker webhook integration.
- Multiple users, authentication, and shared household ledgers.
- Account balance tracking or reconciliation.
- Multiple currencies or currency conversion.
- AI-based categorization and external categorization services.
- Offline editing and synchronization of queued changes.
- Advanced budgeting, forecasting, or detailed analytics beyond the summaries above.
