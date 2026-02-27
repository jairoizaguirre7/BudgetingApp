const form = document.getElementById("upload-form");
const statusEl = document.getElementById("status");

const render = (payload) => {
  const { transactions, summary } = payload;

  const totals = summary.totals;
  document.getElementById("totals").innerHTML = `
    <div class="card"><strong>Income</strong><div>$${totals.income.toFixed(2)}</div></div>
    <div class="card"><strong>Expenses</strong><div>$${totals.expenses.toFixed(2)}</div></div>
    <div class="card"><strong>Net</strong><div>$${totals.net.toFixed(2)}</div></div>
  `;

  document.getElementById("category-list").innerHTML = Object.entries(summary.by_category)
    .map(([category, amount]) => `<li>${category}: $${amount.toFixed(2)}</li>`)
    .join("");

  document.getElementById("month-list").innerHTML = Object.entries(summary.by_month)
    .map(([month, amount]) => `<li>${month}: $${amount.toFixed(2)}</li>`)
    .join("");

  document.getElementById("transactions").innerHTML = transactions
    .map(
      (transaction) => `
      <tr>
        <td>${transaction.date}</td>
        <td>${transaction.description}</td>
        <td>${transaction.category}</td>
        <td>$${Number(transaction.amount).toFixed(2)}</td>
      </tr>
    `
    )
    .join("");
};

const loadSummary = async () => {
  const response = await fetch("/summary");
  const payload = await response.json();
  render(payload);
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById("file");
  if (!fileInput.files.length) {
    statusEl.className = "error";
    statusEl.textContent = "Please choose a CSV file.";
    return;
  }

  const body = new FormData();
  body.append("file", fileInput.files[0]);

  const response = await fetch("/upload", {
    method: "POST",
    body,
  });

  const payload = await response.json();
  if (!response.ok) {
    statusEl.className = "error";
    statusEl.textContent = payload.error;
    return;
  }

  statusEl.className = "success";
  statusEl.textContent = "Upload successful.";
  await loadSummary();
  form.reset();
});

loadSummary();
