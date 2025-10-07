const inputBox = document.getElementById("q");
const solveBtn = document.getElementById("solveBtn");
const fmtSelect = document.getElementById("fmtSelect");
const stepsBox = document.getElementById("stepsBox");
const resultBox = document.getElementById("resultBox");

let lastResponse = null;

async function solveNow() {
  const q = inputBox.value.trim();
  if (!q) {
    resultBox.innerHTML = '<div class="err">الرجاء كتابة مسألة.</div>';
    return;
  }

  stepsBox.innerHTML = '<div class="note">⏳ جارٍ الحل...</div>';
  resultBox.innerHTML = '';

  try {
    const res = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q })
    });
    const data = await res.json();

    if (!data.ok) {
      stepsBox.innerHTML = '';
      resultBox.innerHTML = `<div class="err">❌ ${data.error}</div>`;
      return;
    }

    lastResponse = data;
    stepsBox.innerHTML = data.steps_html;
    renderResult();
  } catch {
    stepsBox.innerHTML = '';
    resultBox.innerHTML = `<div class="err">❌ فشل الاتصال بالخادم.</div>`;
  }
}

function renderResult() {
  if (!lastResponse) return;
  const mode = fmtSelect.value;
  const pretty = lastResponse.pretty;
  const numeric = lastResponse.numeric_value;

  if (mode === "en") {
    resultBox.innerHTML = `
      <h4 class="section-title">النتيجة (إنجليزي نصّي)</h4>
      <div class="result-line">${pretty.en_text}</div>
      ${numeric ? `<div class="note">القيمة العددية: <b>${numeric}</b></div>` : ""}
    `;
  } else {
    resultBox.innerHTML = `
      <h4 class="section-title">النتيجة (رياضي مُنسّق)</h4>
      <div class="result-line">\\(${pretty.ar_latex}\\)</div>
      ${numeric ? `<div class="note">القيمة العددية: <b>${numeric}</b></div>` : ""}
    `;
    if (window.MathJax && MathJax.typesetPromise)
      MathJax.typesetPromise([resultBox]);
  }
}

solveBtn.addEventListener("click", solveNow);
fmtSelect.addEventListener("change", renderResult);
inputBox.addEventListener("keydown", e => {
  if (e.key === "Enter") solveNow();
});
