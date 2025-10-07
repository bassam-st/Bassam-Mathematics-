// static/main.js — Bassam Math Pro v2.5 (UI + OCR + Arabic steps)
// يعمل مع templates/index.html و main.py (Auto + Degrees)

(function () {
  // --------- عناصر الواجهة ---------
  const qInput   = document.getElementById("q");
  const modeSel  = document.getElementById("mode");
  const form     = document.getElementById("solveForm");
  const output   = document.getElementById("output");

  const kbd      = document.getElementById("keyboard");
  const cameraBtn= document.getElementById("cameraBtn");
  const galleryBtn=document.getElementById("galleryBtn");
  const fileInput= document.getElementById("fileInput");

  // --------- أدوات مساعدة ---------
  const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";
  const EN_DIGITS = "0123456789";

  function insertAtCursor(text) {
    const el = qInput;
    const st = el.selectionStart ?? el.value.length;
    const en = el.selectionEnd ?? el.value.length;
    el.value = el.value.slice(0, st) + text + el.value.slice(en);
    const pos = st + text.length;
    el.focus();
    el.setSelectionRange(pos, pos);
  }

  function arabicToEnDigits(s) {
    return s.split("").map(ch => {
      const i = AR_DIGITS.indexOf(ch);
      return i >= 0 ? EN_DIGITS[i] : ch;
    }).join("");
  }

  // تنظيف نص الـ OCR (وبشكل عام قبل الإرسال)
  function normalizeOCR(t) {
    t = t || "";
    t = arabicToEnDigits(t);
    t = t
      .replace(/[×xX]\s*(?=(\d|\w|\())/g, "*")
      .replace(/÷/g, "/")
      .replace(/–|—/g, "-")
      .replace(/√/g, "sqrt")
      .replace(/π/g, "pi")
      .replace(/،/g, ",")
      .replace(/\s*=\s*/g, " = ")
      .replace(/\s*\n+\s*/g, "; ")
      .replace(/\s+\)/g, ")")
      .replace(/\(\s+/g, "(")
      .replace(/[^\S\r\n]+/g, " ")
      .trim();

    // |x| -> Abs(x)
    try {
      t = t.replace(/\|([^|]+)\|/g, "Abs($1)");
    } catch {}
    // ^ -> ** للأسس
    t = t.replace(/\^/g, "**");
    return t;
  }

  function setLoading(msg = "⏳ جاري الحل…") {
    output.innerHTML = `<div class="step">${msg}</div>`;
  }

  function showError(err) {
    output.innerHTML = `<div class="step" style="color:#ff6b6b">❌ ${err}</div>`;
  }

  function renderSolution(data) {
    // data = { ok, mode, result, steps[] }
    let html = "";
    const modeLabel = {
      "evaluate": "حساب",
      "derivative": "تفاضل",
      "integral": "تكامل",
      "solve": "حلّ معادلة/نظام",
      "matrix": "مصفوفات",
      "auto": "تلقائي"
    }[data.mode] || data.mode || "تلقائي";

    html += `<h3>الوضع: ${modeLabel}</h3>`;

    if (Array.isArray(data.steps) && data.steps.length) {
      html += `<div class="steps">`;
      data.steps.forEach((s, i) => {
        // في solver v2.5 الخطوات عبارة عن نصوص، وليس title/content
        if (typeof s === "string") {
          html += `<div class="step"><b>الخطوة ${i + 1}:</b><br>${s}</div>`;
        } else if (s && s.title) {
          html += `<div class="step"><b>${s.title}:</b><br>${s.content || ""}</div>`;
        }
      });
      html += `</div>`;
    }

    html += `<div class="result"><h3>النتيجة:</h3><p>${(data.result ?? "").toString()}</p></div>`;
    output.innerHTML = html;
  }

  async function postJSON(url, payload) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return r.json();
  }

  // --------- إرسال للحل ---------
  async function solveNow() {
    const raw = (qInput.value || "").trim();
    if (!raw) return;
    setLoading();

    try {
      const payload = { q: raw, mode: modeSel.value || "auto" };
      const data = await postJSON("/solve", payload);
      if (!data.ok) return showError(data.error || "فشل الحل");
      renderSolution(data);
    } catch (e) {
      showError(e?.message || e);
    }
  }

  // --------- أحداث الواجهة ---------
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    solveNow();
  });

  // إدخال سريع عبر Enter (بدون Shift)
  qInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      solveNow();
    }
  });

  // لوحة المفاتيح الرياضية
  if (kbd) {
    kbd.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      const val = btn.textContent.trim();

      switch (val) {
        case "CLR":
          qInput.value = "";
          qInput.focus();
          return;
        case "d/dx":
          modeSel.value = "derivative";
          qInput.focus();
          return;
        case "∫":
          modeSel.value = "integral";
          qInput.focus();
          return;
        case "|x|":
          insertAtCursor("Abs(x)");
          return;
        case "sin(":
        case "cos(":
        case "tan(":
        case "Abs(":
        case "√":
          if (val === "√") {
            insertAtCursor("sqrt()");
          } else {
            insertAtCursor(val + ")");
          }
          // ضع المؤشر قبل القوس الأخير
          const pos = (qInput.selectionStart ?? qInput.value.length) - 1;
          qInput.setSelectionRange(pos, pos);
          qInput.focus();
          return;
        case "×":
          insertAtCursor("*"); return;
        case "÷":
          insertAtCursor("/"); return;
        case "π":
          insertAtCursor("pi"); return;
        case "^":
          insertAtCursor("**"); return;
        default:
          insertAtCursor(val);
      }
    });
  }

  // --------- الكاميرا / الأستوديو + OCR ---------
  // نحمّل Tesseract عند الحاجة فقط (Lazy load)
  let tesseractReady = false;
  function ensureTesseract() {
    return new Promise((resolve, reject) => {
      if (tesseractReady && window.Tesseract) return resolve();
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
      s.onload = () => { tesseractReady = true; resolve(); };
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  cameraBtn?.addEventListener("click", async () => {
    try {
      // بعض المتصفحات تحتاج capture لتشغيل الكاميرا مباشرة
      fileInput.removeAttribute("hidden");
      fileInput.setAttribute("accept", "image/*");
      fileInput.setAttribute("capture", "environment");
      fileInput.click();
    } catch {}
  });

  galleryBtn?.addEventListener("click", () => {
    try {
      fileInput.removeAttribute("hidden");
      fileInput.setAttribute("accept", "image/*");
      fileInput.removeAttribute("capture"); // يفتح الأستوديو
      fileInput.click();
    } catch {}
  });

  fileInput?.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading("🔎 قراءة النص من الصورة…");
    try {
      await ensureTesseract();
      const { data } = await window.Tesseract.recognize(file, "eng+ara", {
        logger: (m) => {
          if (m.status === "recognizing text") {
            setLoading(`🔎 التعرف: ${Math.round(m.progress * 100)}%`);
          }
        }
      });
      let text = (data.text || "").trim();
      text = normalizeOCR(text);
      qInput.value = text;
      setLoading("✅ تم استخراج النص. جاري الحل…");
      setTimeout(solveNow, 150);
    } catch (err) {
      showError("فشل التعرف على النص بالـ OCR");
      console.error(err);
    } finally {
      // تنظيف الاختيار حتى نقدر نختار نفس الملف لاحقًا
      fileInput.value = "";
    }
  });

  // --------- أمثلة سريعة (اختيارية) ---------
  if (!qInput.value) {
    qInput.placeholder = "مثال: تفاضل 3*x^3 - 5*x^2 + 4*x - 7  |  sin(60)+25  |  x+y=1; 2*x-y=3";
  }
})();
