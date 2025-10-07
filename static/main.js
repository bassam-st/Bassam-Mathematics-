const inputBox  = document.getElementById("q");
const solveBtn  = document.getElementById("solveBtn");
const fmtSelect = document.getElementById("fmtSelect");
const stepsBox  = document.getElementById("stepsBox");
const resultBox = document.getElementById("resultBox");
const pickFile  = document.getElementById("pickFile");
const openCam   = document.getElementById("openCam");
const fileInput = document.getElementById("fileInput");
const camInput  = document.getElementById("camInput");
const kbd       = document.getElementById("kbd");

let lastResponse = null;

// أرقام عربية -> إنجليزية
function toEnDigits(s){
  const ar='٠١٢٣٤٥٦٧٨٩'; return (s||'').replace(/[٠-٩]/g, d => String(ar.indexOf(d)));
}

// تطبيع مبسّط للنص
function normalizeText(raw){
  if(!raw) return "";
  let t = toEnDigits(raw)
    .replace(/×/g,'*').replace(/÷/g,'/')
    .replace(/√/g,'sqrt').replace(/π/g,'pi')
    .replace(/\^/g,'**').replace(/–|—|−/g,'-')
    .replace(/\|x\|/g,'Abs(x)').replace(/\|([a-zA-Z])\|/g,'Abs($1)')
    .replace(/\s+/g,' ').trim();

  // دعم الضرب الضمني: 2x, 3(x+1), )x
  t = t.replace(/([0-9])([a-zA-Z])/g,'$1*$2')
       .replace(/([a-zA-Z])\(/g,'$1*(')
       .replace(/\)([a-zA-Z0-9])/g,')*$1');

  // كلمات عربية شائعة
  t = t.replace(/تفاضل\s+/i,'d/dx ')
       .replace(/تكامل\s+/i,'integral ')
       .replace(/جي?يب/gi,'sin')
       .replace(/جيب تمام/gi,'cos')
       .replace(/ظل/gi,'tan');

  // sin 60 → اعتبرها درجات؟ (للطلبة الصغار غالباً يكتبون أرقام)
  t = t.replace(/\b(sin|cos|tan)\s+([+\-]?\d+(\.\d+)?)/g,'$1($2)');

  return t;
}

async function solveNow(){
  const raw = inputBox.value || "";
  const q = normalizeText(raw);
  if(!q){
    resultBox.innerHTML = '<div class="err">الرجاء كتابة مسألة.</div>'; return;
  }
  stepsBox.innerHTML = '<div class="note">⏳ جارٍ الحل...</div>';
  resultBox.innerHTML = '';

  try{
    const res = await fetch('/api/solve', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ q })
    });
    const data = await res.json();

    if(!data.ok){
      stepsBox.innerHTML = '';
      resultBox.innerHTML = `<div class="err">❌ ${data.error}</div>`;
      return;
    }

    lastResponse = data;
    stepsBox.innerHTML = data.steps_html || '';
    renderResult();
  }catch(e){
    stepsBox.innerHTML = '';
    resultBox.innerHTML = `<div class="err">❌ فشل الاتصال بالخادم.</div>`;
  }
}

function renderResult(){
  if(!lastResponse) return;
  const mode = fmtSelect.value;
  const { en_text, ar_latex } = lastResponse.pretty || {};
  const numeric = lastResponse.numeric_value;

  if(mode === 'en'){
    resultBox.innerHTML = `
      <h4 class="section-title">النتيجة (إنجليزي نصّي)</h4>
      <div class="result-line">${en_text || ''}</div>
      ${numeric ? `<div class="note">القيمة العددية: <b>${numeric}</b></div>` : ""}
    `;
  } else {
    resultBox.innerHTML = `
      <h4 class="section-title">النتيجة (رياضي مُنسّق)</h4>
      <div class="result-line">\\(${ar_latex || ''}\\)</div>
      ${numeric ? `<div class="note">القيمة العددية: <b>${numeric}</b></div>` : ""}
    `;
    if(window.MathJax && MathJax.typesetPromise){ MathJax.typesetPromise([resultBox]); }
  }
}

// OCR من صورة
async function ocrFromFile(file){
  if(!file) return;
  stepsBox.innerHTML = '<div class="note">🧠 قراءة النص من الصورة…</div>';
  resultBox.innerHTML = '';
  try{
    const { data: { text } } = await Tesseract.recognize(file, 'ara+eng', {
      tessedit_char_whitelist: '0123456789+-*/()xXyY^.,=|[]π sincostan√'
    });
    const cleaned = (text||'').replace(/\n+/g,' ').replace(/\s{2,}/g,' ').trim();
    inputBox.value = cleaned;
    solveNow();
  }catch(e){
    stepsBox.innerHTML = '';
    resultBox.innerHTML = `<div class="err">تعذّر قراءة النص من الصورة.</div>`;
  }
}

pickFile.addEventListener('click', ()=> fileInput.click());
fileInput.addEventListener('change', ()=> {
  if(fileInput.files && fileInput.files[0]) ocrFromFile(fileInput.files[0]);
});
openCam.addEventListener('click', ()=> camInput.click());
camInput.addEventListener('change', ()=> {
  if(camInput.files && camInput.files[0]) ocrFromFile(camInput.files[0]);
});

// كيبورد مصغّر
kbd.addEventListener('click', (e)=>{
  const b = e.target;
  if(!b.classList.contains('k')) return;
  if(b.id==='clr'){ inputBox.value=''; inputBox.focus(); return; }
  let v = b.textContent.trim();
  if(v==='×') v='*';
  if(v==='÷') v='/';
  if(v==='√') v='sqrt(';
  if(v==='|x|') v='Abs(x)';
  inputBox.setRangeText(v, inputBox.selectionStart, inputBox.selectionEnd, 'end');
  inputBox.focus();
});

// أحداث
solveBtn.addEventListener('click', solveNow);
fmtSelect.addEventListener('change', renderResult);
inputBox.addEventListener('keydown', e=>{ if(e.key==='Enter') solveNow(); });
