async function postJSON(url, data){
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(data)
  });
  return r.json();
}

const el = id => document.getElementById(id);

/* ========== إعدادات عامة ========== */
let angleMode = "rad"; // rad/deg

// تحويل Deg → راديان
function wrapTrigDegrees(expr){
  const fn = ["sin","cos","tan"];
  fn.forEach(f=>{
    const re = new RegExp(`${f}\\s*\\(([^()]+|\\((?:[^()]+|\\([^()]*\\))*\\))\\)`, "gi");
    expr = expr.replace(re, (m,arg)=> `${f}((${arg})*pi/180)`);
  });
  return expr;
}
function maybeConvertIfDeg(q){ return (angleMode==="deg") ? wrapTrigDegrees(q) : q; }

/* ========== تشغيل الحل ========== */
el("go").onclick = async () => {
  let q = el("q").value.trim();
  const mode = el("mode").value;
  if(!q){ alert("اكتب مسألة أولاً"); return; }
  q = maybeConvertIfDeg(q);

  el("resultBox").classList.remove("hidden");
  el("result").textContent = "… جاري الحل";
  el("steps").innerHTML = "";
  el("steps").classList.add("collapsed");

  const res = await postJSON("/solve", { q, mode });
  if(!res.ok){
    el("result").textContent = "حدث خطأ: " + res.error;
    return;
  }
  if(res.result_latex){ el("result").innerHTML = "$$" + res.result_latex + "$$"; }
  else { el("result").textContent = res.result; }

  const box = el("steps");
  res.steps.forEach(s=>{
    const div = document.createElement("div");
    div.className="step";
    div.innerHTML = `<h4>${s.title}</h4><div class="body">${s.content}</div>`;
    box.appendChild(div);
  });

  if(typeof MathJax !== "undefined") MathJax.typeset();
};

el("moreBtn").onclick = ()=>{
  el("steps").classList.toggle("collapsed");
  el("moreBtn").textContent = el("steps").classList.contains("collapsed") ? "عرض المزيد" : "عرض أقل";
};

/* ========== أمثلة جاهزة قابلة للنقر ========== */
document.querySelectorAll("#examples li").forEach(li=>{
  li.style.cursor = "pointer";
  li.addEventListener("click", ()=>{
    el("q").value = li.getAttribute("data-e");
    el("q").focus();
  });
});

/* ========== لوحة المفاتيح العلمية ========== */
const KBD_LAYOUT = [
  {t:"⌫", k:"backspace", cls:"warn"}, {t:"CLR", k:"clear", cls:"warn"},
  {t:"Rad", k:"toggleAngle"},
  {t:"√", k:"sqrt"}, {t:"(", k:"("}, {t:")", k:")"}, {t:"[", k:"["}, {t:"]", k:"]"},

  {t:"sin", k:"func:sin"}, {t:"cos", k:"func:cos"}, {t:"tan", k:"func:tan"},
  {t:"7", k:"7"}, {t:"8", k:"8"}, {t:"9", k:"9"}, {t:"×", k:"*"}, {t:"÷", k:"/"},

  {t:"ln", k:"func:ln"}, {t:"log", k:"func:log"}, {t:"1/x", k:"inv"},
  {t:"4", k:"4"}, {t:"5", k:"5"}, {t:"6", k:"6"}, {t:"−", k:"-"}, {t:"+", k:"+"},

  {t:"eˣ", k:"func:exp"}, {t:"x²", k:"pow2"}, {t:"xʸ", k:"pow"},
  {t:"1", k:"1"}, {t:"2", k:"2"}, {t:"3", k:"3"}, {t:",", k:","}, {t:";", k:";"},

  {t:"|x|", k:"abs"}, {t:"π", k:"pi"}, {t:"e", k:"e"},
  {t:"x", k:"x"}, {t:"y", k:"y"}, {t:"z", k:"z"}, {t:"a", k:"a"}, {t:"b", k:"b"},

  {t:"∫", k:"template:int", cls:"op"}, {t:"d/dx", k:"template:diff", cls:"op"},
  {t:"Mat", k:"template:mat", cls:"op"}, {t:"=", k:"solve", cls:"eq wide"},
];

function buildKeyboard(){
  const box = el("kbd"); box.innerHTML="";
  KBD_LAYOUT.forEach(b=>{
    const btn=document.createElement("button");
    btn.type="button"; btn.textContent=b.t;
    btn.className=(b.cls||"");
    btn.addEventListener("click", ()=>handleKey(b.k, btn));
    box.appendChild(btn);
  });
}
buildKeyboard();

el("toggleKbd").onclick = ()=>{
  el("kbd").classList.toggle("hidden");
  el("kbd").setAttribute("aria-hidden", el("kbd").classList.contains("hidden")?"true":"false");
};

el("toggleHelp").onclick = ()=>{
  const d = el("help");
  d.open = !d.open;
  d.scrollIntoView({behavior:"smooth", block:"start"});
};

/* ========== إدخال مباشر في خانة السؤال ========== */
function insertAtCursor(text, caretShift=0){
  const inp=el("q");
  const start=inp.selectionStart ?? inp.value.length;
  const end=inp.selectionEnd ?? start;
  inp.value = inp.value.slice(0,start) + text + inp.value.slice(end);
  const pos=start + text.length + caretShift;
  requestAnimationFrame(()=>{ inp.focus(); inp.setSelectionRange(pos,pos); });
}

function wrapSelection(prefix,suffix,placeCursor=-1){
  const inp=el("q"); const s=inp.selectionStart??0; const e=inp.selectionEnd??0;
  const sel=inp.value.slice(s,e); const inside=sel||"";
  const text=prefix+inside+suffix; const newPos=s+prefix.length+(placeCursor>=0?placeCursor:inside.length);
  inp.value = inp.value.slice(0,s) + text + inp.value.slice(e);
  requestAnimationFrame(()=>{ inp.focus(); inp.setSelectionRange(newPos,newPos); });
}

/* ========== التحكم في الأزرار ========== */
function handleKey(k, btn){
  const inp=el("q");
  switch(k){
    case "backspace": {
      const s=inp.selectionStart, e=inp.selectionEnd;
      if(s!==e){ inp.value = inp.value.slice(0,s) + inp.value.slice(e); inp.setSelectionRange(s,s); }
      else if(s>0){ inp.value = inp.value.slice(0,s-1)+inp.value.slice(e); inp.setSelectionRange(s-1,s-1); }
      inp.focus();
      return;
    }
    case "clear":
      inp.value = ""; inp.focus(); return;

    case "toggleAngle":
      angleMode = (angleMode==="rad"?"deg":"rad");
      btn.textContent = angleMode==="rad" ? "Rad" : "Deg";
      return;

    // دوال وقوالب
    case "sqrt": wrapSelection("sqrt(",")"); return;
    case "func:sin": wrapSelection("sin(",")"); return;
    case "func:cos": wrapSelection("cos(",")"); return;
    case "func:tan": wrapSelection("tan(",")"); return;
    case "func:ln":  wrapSelection("ln(",")");  return;
    case "func:log": wrapSelection("log(",")"); return;
    case "func:exp": wrapSelection("exp(",")"); return;
    case "pow2": insertAtCursor("**2"); return;
    case "pow": insertAtCursor("**"); return;
    case "inv": wrapSelection("1/(",")"); return;
    case "abs": wrapSelection("Abs(",")"); return;
    case "pi": insertAtCursor("pi"); return;
    case "e": insertAtCursor("E"); return;

    case "template:int": insertAtCursor("تكامل "); return;
    case "template:diff": insertAtCursor("مشتق "); return;
    case "template:mat": insertAtCursor("[[ , ],[ , ]]"); return;
    case "solve": el("go").click(); return;

    default:
      insertAtCursor(k);
  }
}

/* ========== MathJax لتنسيق المعادلات ========== */
(function(){
  const s = document.createElement("script");
  s.src = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js";
  s.async = true;
  document.head.appendChild(s);
})();

/* ========== دعم الضغط المطوّل للحذف المتتابع ========== */
let backspaceInterval;
document.addEventListener("mousedown", e=>{
  if(e.target.textContent==="⌫"){
    backspaceInterval = setInterval(()=>handleKey("backspace"), 100);
  }
});
document.addEventListener("mouseup", ()=>clearInterval(backspaceInterval));
document.addEventListener("mouseleave", ()=>clearInterval(backspaceInterval));
