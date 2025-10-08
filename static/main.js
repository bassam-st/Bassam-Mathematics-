/* Bassam Math Pro v8.1 — Smart Auto Mode + OCR
   - خانة واحدة فقط
   - عرض مثل ChatGPT
   - OCR عبر Tesseract.js (ara+eng) مع تنظيف تلقائي
*/

const qEl = document.getElementById("q");
const solveBtn = document.getElementById("solveBtn");
const stepsBox = document.getElementById("steps");
const resBox = document.getElementById("result");
const statusBox = document.getElementById("status");

// OCR elements
const pickImgBtn = document.getElementById("pickImg");
const takeImgBtn = document.getElementById("takeImg");
const imgInput = document.getElementById("imgInput");
const ocrBox = document.getElementById("ocrBox");
const ocrText = document.getElementById("ocrText");
const ocrHint = document.getElementById("ocrHint");
const applyOcrBtn = document.getElementById("applyOcr");
const clearOcrBtn = document.getElementById("clearOcr");

/* ----------------- حالة/تنبيه ----------------- */
function showStatus(msg, type = "info") {
  statusBox.className = "status " + type;
  statusBox.textContent = msg;
  statusBox.classList.remove("none");
}
function clearStatus() {
  statusBox.className = "status none";
  statusBox.textContent = "";
}

/* ----------------- عرض الخطوات/النتيجة ----------------- */
function renderSteps(steps) {
  stepsBox.innerHTML = "";
  if (!steps || !steps.length) return;
  let html = "";
  for (let i = 0; i < steps.length; i++) {
    const line = steps[i];
    html += `
      <div class="step">
        <div class="step-num">الخطوة ${i + 1}:</div>
        <div class="step-text">${line}</div>
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

/* ----------------- حل الآن ----------------- */
async function solveNow() {
  clearStatus();
  stepsBox.innerHTML = "";
  resBox.innerHTML = "";

  const text = (qEl.value || "").trim();
  if (!text) {
    showStatus("⚠️ يرجى كتابة مسألة أو استخدام الكاميرا/الاستوديو.", "warn");
    return;
  }

  showStatus("⏳ جارٍ التحليل والحل…", "info");

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
qEl.addEventListener("keydown", (e) => { if (e.key === "Enter") solveNow(); });

/* ----------------- OCR: تنظيف وتحويل ----------------- */
function toEnDigits(s){
  const ar='٠١٢٣٤٥٦٧٨٩';
  return (s||'').replace(/[٠-٩]/g, d => String(ar.indexOf(d)));
}

function normalizeMath(s){
  if(!s) return "";
  let t = toEnDigits(s);

  // بدائل الرموز الشائعة
  t = t
    .replace(/×/g,'*').replace(/·/g,'*').replace(/•/g,'*')
    .replace(/÷/g,'/')
    .replace(/[–—−]/g,'-')
    .replace(/√/g,'sqrt')
    .replace(/π/gi,'pi')
    .replace(/\^/g,'^'); // نترك ^ لأن الخادم يحوله داخليًا

  // مسافات/سطور
  t = t.replace(/\n+/g,' ').replace(/\s{2,}/g,' ').trim();

  // دعم ضرب ضمني بسيط: 2x -> 2*x ، 3(x+1) -> 3*(x+1)
  t = t.replace(/(\d)\s*([a-zA-Z])/g, '$1*$2');
  t = t.replace(/([a-zA-Z])\s*\(/g, '$1*(');
  t = t.replace(/\)\s*([a-zA-Z0-9])/g, ')*$1');

  // دوال مثلثية/لوغاريتم كما هي
  // sin, cos, tan, log, ln, sqrt — لا تغيير إضافي

  return t;
}

/* ----------------- OCR: اختيار/التقاط صورة ----------------- */
function pickImage(fromCamera=false){
  if(fromCamera){
    // بعض المتصفحات تدعم capture عبر input عام؛ نستخدم مسار موحد
    imgInput.removeAttribute("capture");
  } else {
    imgInput.removeAttribute("capture");
  }
  imgInput.click();
}

pickImgBtn.addEventListener("click", ()=> pickImage(false));
takeImgBtn.addEventListener("click", ()=> pickImage(true));

imgInput.addEventListener("change", async ()=>{
  const f = imgInput.files && imgInput.files[0];
  if(!f) return;

  ocrBox.style.display = "block";
  ocrText.value = "";
  ocrHint.textContent = "⏳ جارٍ قراءة النص من الصورة… تأكد من الإضاءة ووضوح المعادلة.";

  try{
    // Tesseract: لغتان معًا ara+eng
    const { data: { text } } = await Tesseract.recognize(f, 'ara+eng', {
      tessedit_char_whitelist: '0123456789+-*/()xXyY^.,=|[]πsqrtcostaingelogSINCOStan',
    });

    const raw = (text || '').trim();
    const cleaned = normalizeMath(raw);
    ocrText.value = cleaned;
    ocrHint.textContent = "✅ تم استخراج النص. يمكنك تعديله ثم الضغط على (إرسال للنص أعلاه).";
  }catch(e){
    console.error(e);
    ocrHint.textContent = "❌ تعذّر قراءة النص. حاول صورة أوضح أو قُم بقصّ المنطقة حول المسألة.";
  }finally{
    imgInput.value = "";
  }
});

applyOcrBtn.addEventListener("click", ()=>{
  const t = (ocrText.value || "").trim();
  if(!t){ ocrHint.textContent = "⚠️ لا يوجد نص مستخرج."; return; }
  qEl.value = t;
  showStatus("📋 تم لصق النص المستخرج في خانة السؤال. اضغط (حل الآن).", "info");
});

clearOcrBtn.addEventListener("click", ()=>{
  ocrText.value = "";
  ocrBox.style.display = "none";
  ocrHint.textContent = "";
});
