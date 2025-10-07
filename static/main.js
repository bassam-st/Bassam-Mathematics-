// عناصر DOM
const inputBox  = document.getElementById("q");
const solveBtn  = document.getElementById("solveBtn");
const fmtSelect = document.getElementById("fmtSelect");
const degChk    = document.getElementById("degChk");
const stepsBox  = document.getElementById("stepsBox");
const resultBox = document.getElementById("resultBox");
const pickFile  = document.getElementById("pickFile");
const openCam   = document.getElementById("openCam");
const fileInput = document.getElementById("fileInput");
const camInput  = document.getElementById("camInput");
const kbd       = document.getElementById("kbd");

let lastResponse = null;

// ---------- 1) تحويل عربي/رموز إلى صيغة مفهومة لـ Sympy ----------
function normalizeText(raw) {
  if (!raw) return "";

  // أرقام عربية -> إنجليزية
  const arabicDigits = '٠١٢٣٤٥٦٧٨٩';
  raw = raw.replace(/[٠-٩]/g, d => String(arabicDigits.indexOf(d)));

  // مسافات زائدة
  raw = raw.replace(/\s+/g, ' ').trim();

  // رموز شائعة
  raw = raw
    .replace(/[×xX]\s*\(/g, '1*(')      // x( → 1*(  (سنتعامل مع x لاحقاً)
    .replace(/×/g, '*')
    .replace(/÷/g, '/')
    .replace(/·/g, '*')
    .replace(/–|—|−/g, '-')            // شرطات
    .replace(/π/g, 'pi')
    .replace(/\|x\|/g, 'Abs(x)')
    .replace(/\|([a-zA-Z])\|/g, 'Abs($1)')
    .replace(/√/g, 'sqrt')
    .replace(/\^/g, '**')
    .replace(/,/g, ','); // للفصل بين الدوال إن وُجد

  // كلمات عربية شائعة
  raw = raw
    .replace(/جي?يب/gi, 'sin')
    .replace(/جيب تمام/gi, 'cos')
    .replace(/ظل/gi, 'tan')
    .replace(/اس/g, '**');  // (أس) → قوة

  // implicit multiplication:  2x → 2*x  ،  )x → )*x  ،  x( → x*(  ،  رقم( → رقم*(  ،  )( → )*(
  raw = raw
    .replace(/([0-9])([a-zA-Z])/g, '$1*$2')
    .replace(/([a-zA-Z])\(/g, '$1*(')
    .replace(/\)([a-zA-Z0-9])/g, ')*$1');

  // تأمين الدرجات: سنحوّل sin(60°) أو sin(60) إلى راديان إن كانت الدرجات مفعّلة
  if (degChk.checked) {
    raw = raw.replace(/(sin|cos|tan)\s*\(\s*([\-]?\d+(\.\d+)?)\s*°?\s*\)/g, (_, fn, d) => {
      const rad = (parseFloat(d) * Math.PI / 180).toString();
      return `${fn}(${rad})`;
    });
  } else {
    // إزالة رمز درجة فقط
    raw = raw.replace(/°/g, '');
  }

  return raw;
}

// ---------- 2) حلّ المسألة عبر الخادم ----------
async function solveNow() {
  const raw = inputBox.value;
  const q = normalizeText(raw);
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
  } catch (e) {
    stepsBox.innerHTML = '';
    resultBox.innerHTML = `<div class="err">❌ فشل الاتصال بالخادم.</div>`;
  }
}

// ---------- 3) عرض النتيجة حسب التنسيق ----------
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

// ---------- 4) OCR: قراءة من صورة (استوديو/كاميرا) ----------
async function ocrFromFile(file) {
  if (!file) return;
  stepsBox.innerHTML = '<div class="note">🧠 قراءة النص من الصورة (OCR)...</div>';
  resultBox.innerHTML = '';

  try {
    const { data: { text } } = await Tesseract.recognize(file, 'ara+eng', {
      tessedit_char_whitelist: '0123456789+-*/()xXyY^.,=|[]π sincostan√'
    });
    // تنظيف وتطبيع
    const cleaned = text.replace(/\n+/g, ' ').replace(/\s{2,}/g, ' ').trim();
    inputBox.value = cleaned;
    solveNow();
  } catch (e) {
    stepsBox.innerHTML = '';
    resultBox.innerHTML = `<div class="err">تعذّر قراءة النص من الصورة: ${e}</div>`;
  }
}

// اختيار من الاستوديو
pickFile.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  if (fileInput.files && fileInput.files[0]) ocrFromFile(fileInput.files[0]);
});

// التقاط صورة بالكاميرا
openCam.addEventListener('click', () => camInput.click());
camInput.addEventListener('change', () => {
  if (camInput.files && camInput.files[0]) ocrFromFile(camInput.files[0]);
});

// ---------- 5) لوحة المفاتيح المصغّرة ----------
kbd.addEventListener('click', (e) => {
  const t = e.target;
  if (!t.classList.contains('k')) return;
  if (t.id === 'clr') { inputBox.value = ''; inputBox.focus(); return; }

  let v = t.textContent;
  // تحويل بعض الرموز للآلة
  if (v === '×') v = '*';
  if (v === '÷') v = '/';
  if (v === '√') v = 'sqrt(';
  if (v === '|x|') v = 'Abs(x)';
  inputBox.setRangeText(v, inputBox.selectionStart, inputBox.selectionEnd, 'end');
  inputBox.focus();
});

// أحداث عامة
solveBtn.addEventListener("click", solveNow);
fmtSelect.addEventListener("change", renderResult);
inputBox.addEventListener("keydown", e => { if (e.key === "Enter") solveNow(); });
degChk.addEventListener("change", () => {
  // لا نعيد الحل تلقائيا حتى لا نزعج المستخدم؛ فقط غيّر النتيجة إذا كانت موجودة.
  renderResult();
});
