/* بسّام ماث — Frontend v7.1
   - يرسل الطلب إلى /solve
   - تنسيق الناتج عربي/إنجليزي
   - كيبورد مدمج مبسّط
*/

const $ = (s, r=document)=>r.querySelector(s);
const qEl = $("#q");
const solveBtn = $("#solveBtn");
const fmtSel = $("#fmt");
const modeSel = $("#mode");
const verboseChk = $("#verbose");
const stepsBox = $("#steps");
const resBox = $("#result");
const statusBox = $("#status");
const kbdBox = $("#kbd");
const pickImgBtn = $("#pickImg");
const takeImgBtn = $("#takeImg");
const imgInput = $("#imgInput");

/* -------------------- كيبورد مبسّط -------------------- */
const keys = [
  ["+", "-", "×", "÷", "^", "(", ")", "x"],
  ["y", "=", "π", "√", "sin(", "cos(", "tan(", "Abs("],
  ["d/dx", ",", "0", "1", "2", "3", "4", "5"],
  ["6", "7", "8", "9", ".", "CLR", "←", "↵"]
];
function insertText(txt){
  const el = qEl;
  const start = el.selectionStart ?? el.value.length;
  const end = el.selectionEnd ?? el.value.length;
  const before = el.value.slice(0, start);
  const after  = el.value.slice(end);
  el.value = before + txt + after;
  const pos = start + txt.length;
  el.setSelectionRange(pos, pos);
  el.focus();
}
function buildKeyboard(){
  kbdBox.innerHTML = "";
  keys.flat().forEach(k=>{
    const b=document.createElement("button");
    b.textContent = k;
    if(k==="CLR") b.classList.add("warn");
    if(k==="↵") b.classList.add("ok");
    b.onclick = ()=>{
      if(k==="CLR"){ qEl.value=""; return; }
      if(k==="←"){ qEl.value = qEl.value.slice(0,-1); return; }
      if(k==="×") return insertText("*");
      if(k==="÷") return insertText("/");
      if(k==="^") return insertText("^");
      if(k==="↵") return solveNow();
      if(k==="d/dx") return insertText("تفاضل ");
      insertText(k);
    };
    kbdBox.appendChild(b);
  });
}
buildKeyboard();

/* -------------------- تنسيق عرض رياضي -------------------- */
function humanize(expr, lang){
  // تبسيط للطباعة: استبدال ** بـ ^ وإخفاء * بين العدد والمتغير
  let s = String(expr ?? "").trim();

  // لو كان المخرج من الخادم فيه نجوم Python
  s = s.replace(/\*\*/g, "^");

  // إخفاء الضرب 3*x -> 3x ، و (-1)*x -> -x
  s = s.replace(/(\b\d+)\s*\*\s*([a-zA-Z])/g, "$1$2");
  s = s.replace(/(^|[^a-zA-Z0-9_])-?1\*([a-zA-Z])/g, (m,p1,p2)=> `${p1}-${p2}`);

  // cos(x) + sin(x) تبقى كما هي
  // fractions a/b تبقى كما هي

  if(lang==="ar"){
    s = s.replace(/\bpi\b|π/gi,"π");
  }
  return s;
}

/* -------------------- عرض الحالة/النتيجة -------------------- */
function setStatus(ok, msg){
  statusBox.className = "status " + (ok?"ok":"err");
  statusBox.textContent = msg;
  statusBox.classList.remove("none");
}
function clearStatus(){ statusBox.className="status none"; statusBox.textContent=""; }

function renderSteps(stepsArr){
  stepsBox.innerHTML = "";
  if(!Array.isArray(stepsArr) || !stepsArr.length) return;
  stepsArr.forEach((st,i)=>{
    const box = document.createElement("div");
    box.className="step";
    const t = document.createElement("div");
    t.className="t";
    t.textContent = `الخطوة ${i+1}:`;
    const b = document.createElement("div");
    b.textContent = st;
    box.append(t,b);
    stepsBox.appendChild(box);
  });
}

/* -------------------- الطلب للخادم -------------------- */
async function solveNow(){
  clearStatus();
  stepsBox.innerHTML = "";
  resBox.textContent = "";

  const text = qEl.value.trim();
  if(!text){ setStatus(false,"يرجى كتابة مسألة."); return; }

  // نرسل بصيغة بسيطة وواضحة للخادم
  const payload = {
    text,
    mode: modeSel.value,
    verbose: !!verboseChk.checked,
    format: fmtSel.value // يُستخدم فقط في الواجهة، الخادم يعيد نص خام
  };

  try{
    const r = await fetch("/solve", {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(payload)
    });

    // إذا الخادم يصحى ببطء (خطة مجانية) قد يرجع 502 أول مرة
    if(!r.ok){ 
      const t = await r.text();
      throw new Error(`(${r.status}) ${t}`);
    }

    const data = await r.json();

    if(data.error){
      setStatus(false, data.error);
      return;
    }

    // data.expected structure:
    // { result: "...", steps: ["...", "..."] }
    const lang = fmtSel.value === "en" ? "en" : "ar";
    const pretty = humanize(data.result ?? "", lang);

    renderSteps(data.steps || []);
    resBox.textContent = pretty || "—";
    setStatus(true,"تم الحل بنجاح.");

  }catch(err){
    setStatus(false, "فشل الاتصال بالخادم أو خطأ في المعالجة.");
    console.error(err);
  }
}

solveBtn.addEventListener("click", solveNow);
qEl.addEventListener("keydown", (e)=>{ if(e.key==="Enter"){ e.preventDefault(); solveNow(); } });

/* -------------------- أزرار الصور (تحضير لـ OCR الخادم) -------------------- */
function pickImage(fromCamera=false){
  // هذه النسخة الأمامية لا تقوم بـ OCR من المتصفح.
  // عند دمج OCR في الخادم، اجعل الإرسال إلى /solve-image ثم اعرض النتيجة.
  if(fromCamera) imgInput.setAttribute("capture","environment");
  else imgInput.removeAttribute("capture");

  imgInput.onchange = ()=>{
    if(!imgInput.files?.[0]) return;
    setStatus(false, "خاصية قراءة الصور (OCR) ستُفعَّل من الخادم. النسخة الحالية تقبل الإدخال النصّي.");
    imgInput.value = "";
  };
  imgInput.click();
}
pickImgBtn.addEventListener("click", ()=>pickImage(false));
takeImgBtn.addEventListener("click", ()=>pickImage(true));
