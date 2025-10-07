// static/main.js — Bassam Math Pro v2.7 (UI + Strong OCR + Verbose toggle)

(function () {
  const qInput   = document.getElementById("q");
  const modeSel  = document.getElementById("mode");
  const form     = document.getElementById("solveForm");
  const output   = document.getElementById("output");
  const kbd      = document.getElementById("keyboard");
  const cameraBtn= document.getElementById("cameraBtn");
  const galleryBtn=document.getElementById("galleryBtn");
  const fileInput= document.getElementById("fileInput");

  // --------- أضف زر "شرح مُوسّع" ديناميكيًا بدون تعديل HTML ---------
  let verboseChk;
  (function injectVerboseToggle(){
    const btns = document.querySelector(".btns");
    if(!btns) return;
    const label = document.createElement("label");
    label.style.display = "flex";
    label.style.alignItems = "center";
    label.style.gap = "6px";
    label.style.background = "#141a2a";
    label.style.border = "1px solid #2a3250";
    label.style.borderRadius = "10px";
    label.style.padding = "10px 12px";
    label.style.color = "#eaeef8";
    label.style.fontWeight = "700";
    label.style.cursor = "pointer";
    verboseChk = document.createElement("input");
    verboseChk.type = "checkbox";
    verboseChk.id = "verboseExplain";
    label.appendChild(verboseChk);
    label.appendChild(document.createTextNode("شرح مُوسّع"));
    btns.appendChild(label);
  })();

  const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";
  const EN_DIGITS = "0123456789";

  function insertAtCursor(text) {
    const el = qInput;
    const st = el.selectionStart ?? el.value.length;
    const en = el.selectionEnd ?? el.value.length;
    el.value = el.value.slice(0, st) + text + el.value.slice(en);
    const pos = st + text.length;
    el.focus(); el.setSelectionRange(pos, pos);
  }

  function arabicToEnDigits(s) {
    return s.split("").map(ch => {
      const i = AR_DIGITS.indexOf(ch);
      return i >= 0 ? EN_DIGITS[i] : ch;
    }).join("");
  }

  function replaceArabicMathWords(t) {
    const pairs = [
      ["القيمة المطلقة","Abs"],["قيمة مطلقة","Abs"],
      ["جذر تربيعي","sqrt"],["جذر مربع","sqrt"],["جذر","sqrt"],
      ["يساوي","="],["تساوي","="],["زائد","+"],["جمع","+"],
      ["ناقص","-"],["طرح","-"],["في","*"],["ضرب","*"],
      ["على","/"],["قسمة","/"],["باي","pi"],
    ];
    pairs.sort((a,b)=>b[0].length-a[0].length);
    let s=" "+t+" ";
    pairs.forEach(([w,v])=>{
      const re = new RegExp(`(?<!\\w)${w.replace(/[.*+?^${}()|[\\]\\\\]/g,"\\$&")}(?!\\w)`,"g");
      s=s.replace(re,` ${v} `);
    });
    return s.trim();
  }

  function normalizePlain(t) {
    t = t || "";
    t = t.replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, ""); // رموز خفية
    t = arabicToEnDigits(t);
    t = t
      .replace(/[×]/g, "*").replace(/÷/g, "/")
      .replace(/–|—/g, "-").replace(/√/g, "sqrt")
      .replace(/π/g, "pi").replace(/،/g, ",")
      .replace(/\^/g, "**").replace(/\s*=\s*/g, " = ");
    try { t = t.replace(/\|([^|]+)\|/g, "Abs($1)"); } catch {}
    t = t.replace(/\b(sin|cos|tan)\s+([+\-]?\d+(?:\.\d+)?)\s*(?:درجة|°)/g, "$1($2)");
    t = t.replace(/\b(sin|cos|tan)\s+([A-Za-z0-9_.+-]+)/g, "$1($2)");
    t = replaceArabicMathWords(t);
    t = t.replace(/[^0-9A-Za-z+\-*/=^().,;_| \t\r\n\[\]π]/g, " ");
    t = t.replace(/\s+\)/g, ")").replace(/\(\s+/g, "(").replace(/[^\S\r\n]+/g, " ").trim();
    return t;
  }
  const normalizeOCR = normalizePlain;

  function setLoading(msg="⏳ جاري الحل…"){ output.innerHTML=`<div class="step">${msg}</div>`; }
  function showError(err){ output.innerHTML=`<div class="step" style="color:#ff6b6b">❌ ${err}</div>`; }

  function renderSolution(data){
    let html="";
    const modeLabel = {
      "evaluate":"حساب","derivative":"تفاضل","integral":"تكامل",
      "solve":"حلّ معادلة/نظام","matrix":"مصفوفات","auto":"تلقائي"
    }[data.mode] || data.mode || "تلقائي";
    html+=`<h3>الوضع: ${modeLabel}${data.verbose?" — شرح مُوسّع":""}</h3>`;
    if(Array.isArray(data.steps)&&data.steps.length){
      html+=`<div class="steps">`;
      data.steps.forEach((s,i)=>{
        if(typeof s==="string"){
          html+=`<div class="step"><b>الخطوة ${i+1}:</b><br>${s}</div>`;
        } else if(s && s.title){
          html+=`<div class="step"><b>${s.title}:</b><br>${s.content||""}</div>`;
        }
      });
      html+=`</div>`;
    }
    html+=`<div class="result"><h3>النتيجة:</h3><p>${(data.result??"").toString()}</p></div>`;
    output.innerHTML=html;
  }

  async function postJSON(url,payload){
    const r = await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    return r.json();
  }

  function preprocessInput(raw){ return normalizePlain(raw); }

  // يلتقط إشارات النص لشرح موسّع
  function detectVerboseFromText(txt){
    const triggers = ["#شرح","شرح موسع","شرح مُوسّع","بالتفصيل","اشرح"];
    return triggers.some(t => txt.includes(t));
  }

  async function solveNow(){
    let raw = (qInput.value||"").trim();
    if(!raw) return;

    const cleaned = preprocessInput(raw);
    qInput.value = cleaned;

    // إن كتب المستخدم كلمة دلالية في النص، فعّل الخيار تلقائيًا
    if(verboseChk && detectVerboseFromText(raw)){ verboseChk.checked = true; }

    setLoading();
    try{
      const payload = {
        q: cleaned,
        mode: (modeSel.value||"auto"),
        explain: (verboseChk && verboseChk.checked) ? "extended" : "normal"
      };
      const data = await postJSON("/solve", payload);
      if(!data.ok) return showError(data.error||"فشل الحل");
      renderSolution(data);
    }catch(e){
      showError(e?.message||e);
    }
  }

  form.addEventListener("submit",(e)=>{ e.preventDefault(); solveNow(); });
  qInput.addEventListener("keydown",(e)=>{ if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); solveNow(); }});

  if(kbd){
    kbd.addEventListener("click",(e)=>{
      const btn = e.target.closest("button"); if(!btn) return;
      const val = btn.textContent.trim();
      switch(val){
        case "CLR": qInput.value=""; qInput.focus(); return;
        case "d/dx": modeSel.value="derivative"; qInput.focus(); return;
        case "∫": modeSel.value="integral"; qInput.focus(); return;
        case "|x|": insertAtCursor("Abs(x)"); return;
        case "√": insertAtCursor("sqrt()"); {const p=(qInput.selectionStart??qInput.value.length)-1; qInput.setSelectionRange(p,p);} return;
        case "π": insertAtCursor("pi"); return;
        case "×": insertAtCursor("*"); return;
        case "÷": insertAtCursor("/"); return;
        case "^": insertAtCursor("**"); return;
        default: insertAtCursor(val); return;
      }
    });
  }

  // --------- الكاميرا / الأستوديو + OCR ---------
  let tesseractReady=false;
  function ensureTesseract(){
    return new Promise((resolve,reject)=>{
      if(tesseractReady && window.Tesseract) return resolve();
      const s=document.createElement("script");
      s.src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
      s.onload=()=>{ tesseractReady=true; resolve(); };
      s.onerror=reject;
      document.head.appendChild(s);
    });
  }

  cameraBtn?.addEventListener("click",()=>{
    try{
      fileInput.removeAttribute("hidden");
      fileInput.setAttribute("accept","image/*");
      fileInput.setAttribute("capture","environment");
      fileInput.click();
    }catch{}
  });
  galleryBtn?.addEventListener("click",()=>{
    try{
      fileInput.removeAttribute("hidden");
      fileInput.setAttribute("accept","image/*");
      fileInput.removeAttribute("capture");
      fileInput.click();
    }catch{}
  });

  fileInput?.addEventListener("change", async (e)=>{
    const file = e.target.files?.[0]; if(!file) return;
    output.innerHTML = `<div class="step">🔎 قراءة النص من الصورة…</div>`;
    try{
      await ensureTesseract();
      const { data } = await window.Tesseract.recognize(file,"eng+ara",{
        logger:(m)=>{ if(m.status==="recognizing text"){ output.innerHTML=`<div class="step">🔎 التعرف: ${Math.round(m.progress*100)}%</div>`; } },
        tessedit_char_whitelist:
          "0123456789+-*/=^().,;[]| xXyYzZaAbBcCsSiInNoOtTlLgGpPrReEqQuUhHkKmMdDfFπ√"
      });
      let text=(data.text||"").trim();
      text = normalizeOCR(text);
      qInput.value = text;
      output.innerHTML = `<div class="step">✅ تم استخراج النص. جاري الحل…</div>`;
      setTimeout(solveNow, 120);
    }catch(err){
      output.innerHTML = `<div class="step" style="color:#ff6b6b">❌ فشل التعرف على النص</div>`;
      console.error(err);
    }finally{ fileInput.value=""; }
  });

  if(!qInput.value){
    qInput.placeholder="اكتب مسألة… ويمكنك تفعيل الشرح المُوسّع من الزر بجانب (حلّ)";
  }
})();
