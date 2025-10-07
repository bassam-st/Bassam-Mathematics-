const $ = (s) => document.querySelector(s);

const qEl = $("#q");
const modeEl = $("#mode");
const fmtEl = $("#fmt");
const outEl = $("#out");
const solveBtn = $("#solve");

function renderSteps(steps, result) {
  if (!steps || !steps.length) {
    outEl.innerHTML = `<div class="res">النتيجة: <b>${result ?? ""}</b></div>`;
    return;
  }
  let html = "";
  for (const [title, body] of steps) {
    html += `
      <div class="step">
        <div class="step-title">${title}:</div>
        <div class="step-body">${body}</div>
      </div>
    `;
  }
  html += `<div class="result-box"><div class="result-title">النتيجة:</div><div class="result-val">${result ?? ""}</div></div>`;
  outEl.innerHTML = html;
}

async function solve() {
  outEl.innerHTML = `<div class="loading">... جاري الحل</div>`;
  const body = {
    q: qEl.value,
    mode: modeEl.value,
    fmt: fmtEl.value,
  };

  try {
    const res = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!data.ok) {
      outEl.innerHTML = `<div class="err">❌ ${data.error || "حدث خطأ غير متوقع."}</div>`;
      return;
    }
    renderSteps(data.steps, data.result);
  } catch (e) {
    outEl.innerHTML = `<div class="err">❌ فشل الاتصال بالخادم.</div>`;
  }
}

solveBtn.addEventListener("click", solve);
qEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") solve();
});
