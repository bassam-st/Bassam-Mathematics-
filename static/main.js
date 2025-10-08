/* Bassam Math Pro v8 — Smart Auto Mode
   واجهة ذكية تعرض النتيجة مثل ChatGPT
   إعداد: بسّام الذكي 💜
*/

const qEl = document.getElementById("q");
const solveBtn = document.getElementById("solveBtn");
const stepsBox = document.getElementById("steps");
const resBox = document.getElementById("result");
const statusBox = document.getElementById("status");

function showStatus(msg, type = "info") {
  statusBox.className = "status " + type;
  statusBox.textContent = msg;
  statusBox.classList.remove("none");
}

function clearStatus() {
  statusBox.className = "status none";
  statusBox.textContent = "";
}

function renderSteps(steps) {
  stepsBox.innerHTML = "";
  if (!steps || !steps.length) return;
  let html = "";
  for (let i = 0; i < steps.length; i++) {
    html += `
      <div class="step">
        <div class="step-num">الخطوة ${i + 1}:</div>
        <div class="step-text">${steps[i]}</div>
      </div>
    `;
  }
  stepsBox.innerHTML = html;
  if (window.MathJax) MathJax.typesetPromise();
}

function renderResult(result) {
  resBox.innerHTML = result ? `\\(${result}\\)` : "—";
  if (window.MathJax) MathJax.typesetPromise();
}

async function solveNow() {
  clearStatus();
  stepsBox.innerHTML = "";
  resBox.innerHTML = "";

  const text = qEl.value.trim();
  if (!text) {
    showStatus("⚠️ يرجى كتابة مسألة.", "warn");
    return;
  }

  showStatus("⏳ جاري التحليل والحل، يرجى الانتظار...", "info");

  try {
    const r = await fetch("/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    if (!r.ok) {
      const t = await r.text();
      throw new Error(t || "فشل الاتصال بالخادم.");
    }

    const data = await r.json();
    if (!data.ok) {
      showStatus("❌ " + (data.error || "حدث خطأ أثناء الحل."), "err");
      return;
    }

    showStatus("✅ تم الحل بنجاح.", "ok");
    renderSteps(data.steps);
    renderResult(data.result);

  } catch (err) {
    console.error(err);
    showStatus("❌ خطأ في الاتصال أو في تحليل المسألة.", "err");
  }
}

solveBtn.addEventListener("click", solveNow);
qEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") solveNow();
});
