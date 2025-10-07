// عناصر الواجهة
const inputBox  = document.getElementById('q');
const solveBtn  = document.getElementById('solveBtn');
const fmtSelect = document.getElementById('fmtSelect');
const stepsBox  = document.getElementById('stepsBox');
const resultBox = document.getElementById('resultBox');

let lastResponse = null;

async function solveNow() {
  const q = (inputBox.value || '').trim();
  if (!q) {
    stepsBox.innerHTML = '';
    resultBox.innerHTML = `<div class="err">الرجاء كتابة مسألة.</div>`;
    return;
  }

  stepsBox.innerHTML = `<div class="muted">⏳ جارٍ الحل...</div>`;
  resultBox.innerHTML = '';

  try {
    const res = await fetch('/api/solve', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ q })
    });
    const data = await res.json();
    if (!data.ok) {
      stepsBox.innerHTML = '';
      resultBox.innerHTML = `<div class="err">❌ ${data.error || 'حدث خطأ غير متوقع'}</div>`;
      return;
    }

    lastResponse = data;

    // الشرح العربي
    stepsBox.innerHTML = data.steps_html || '';

    // عرض النتيجة وفق التنسيق
    renderResult();

  } catch (e) {
    stepsBox.innerHTML = '';
    resultBox.innerHTML = `<div class="err">❌ فشل الاتصال بالخادم.</div>`;
  }
}

function renderResult() {
  if (!lastResponse) return;
  const mode = fmtSelect.value;            // 'ar' | 'en'
  const pretty = lastResponse.pretty || {};
  const numeric = lastResponse.numeric_value;

  if (mode === 'en') {
    // إنجليزي نصّي (x^3 - 5x^2 + ...)
    let html = `
      <h4 class="section-title">النتيجة (إنجليزي نصّي)</h4>
      <div class="result-line">${pretty.en_text || ''}</div>
    `;
    if (numeric) {
      html += `<div class="muted" style="margin-top:.5rem">قيمة عددية (إن كان التعبير عدديًا): <b>${numeric}</b></div>`;
    }
    resultBox.innerHTML = html;
  } else {
    // عربي مُنسّق — LaTeX via MathJax
    let html = `
      <h4 class="section-title">النتيجة (رياضي مُنسّق)</h4>
      <div class="result-line">\\(${pretty.ar_latex || ''}\\)</div>
    `;
    if (numeric) {
      html += `<div class="muted" style="margin-top:.5rem">قيمة عددية (إن كان التعبير عدديًا): <b>${numeric}</b></div>`;
    }
    resultBox.innerHTML = html;

    // نطلب من MathJax إعادة التنضيد
    if (window.MathJax && MathJax.typesetPromise) {
      MathJax.typesetPromise([resultBox]).catch(()=>{});
    }
  }
}

// أحداث
if (solveBtn) solveBtn.addEventListener('click', solveNow);
if (fmtSelect) fmtSelect.addEventListener('change', renderResult);

// الحل عند الضغط Enter
inputBox?.addEventListener('keydown', (e)=>{
  if (e.key === 'Enter') solveNow();
});
