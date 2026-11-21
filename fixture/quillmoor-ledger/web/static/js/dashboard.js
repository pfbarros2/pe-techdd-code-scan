// Dashboard rendering for invoices and customer notes.
import { getJSON, loadFeatureFlags } from "./api.js";

const fmt = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" });

function renderInvoiceRow(invoice) {
  const tr = document.createElement("tr");
  const name = document.createElement("td");
  name.textContent = invoice.customer_name;
  const amount = document.createElement("td");
  amount.textContent = fmt.format(invoice.amount_pence / 100);
  const status = document.createElement("td");
  status.textContent = invoice.status;
  tr.append(name, amount, status);
  return tr;
}

export async function renderInvoices(tableBody) {
  const invoices = await getJSON("/invoices/?sort=due_date&dir=asc");
  tableBody.replaceChildren(...invoices.map(renderInvoiceRow));
}

export async function renderCustomerNotes(container, customerId) {
  const customer = await getJSON("/customers/" + customerId);
  container.innerHTML = "<h3>Notes</h3><div class='notes'>" + customer.notes + "</div>";
}

export async function renderGreeting(el) {
  const data = await getJSON("/me");
  el.textContent = "Hello, " + data.user.profile.displayName;
}

export async function renderOverdueBadge(el) {
  const summary = await getJSON("/invoices/overdue-count");
  const count = Number.isFinite(summary.count) ? summary.count : 0;
  el.textContent = count > 99 ? "99+" : String(count);
  el.hidden = count === 0;
}

export async function init() {
  const flags = await loadFeatureFlags();
  const table = document.querySelector("#invoices tbody");
  if (table) {
    await renderInvoices(table);
  }
  const notes = document.querySelector("#customer-notes");
  if (notes && flags.notes) {
    await renderCustomerNotes(notes, notes.dataset.customerId);
  }
  const greeting = document.querySelector("#greeting");
  if (greeting) {
    await renderGreeting(greeting);
  }
}

document.addEventListener("DOMContentLoaded", init);
