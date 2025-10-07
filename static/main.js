// static/main.js — Bassam Math Pro v2.6 (UI + Strong OCR + Arabic NLU)

(function () {
  const qInput   = document.getElementById("q");
  const modeSel  = document.getElementById("mode");
  const form     = document.getElementById("solveForm");
  const output   = document.getElementById("output");
  const kbd      = document.getElementById("keyboard");
  const cameraBtn= document.getElementById("cameraBtn");
  const galleryBtn=document.getElementById("galleryBtn");
  const fileInput= document.getElementById("fileInput");

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

  // ----------------- تطبيع نص المستخدم/الـ OCR -----------------
  function replaceArabicMathWords(t) {
    const pairs = [
      ["القيمة المطلقة", "Abs"],
      ["قيمة مطلقة", "Abs"],
      ["جذر تربيعي", "sqrt"],
      ["جذر مربع", "sqrt"],
      ["جذر", "sqrt"],
      ["يساوي", "="], ["تساوي", "="],
      ["زائد", "+"], ["جمع", "+"],
      ["ناقص", "-"], ["طرح", "-"],
      ["في", "*"], ["ضرب", "*"],
      ["على", "/"], ["قسمة", "/"],
      ["باي", "pi"],
    ];
    // استبدال بطول-أطول لتفادي تداخل العبارات
    pairs.sort((a, b) => b[0].length - a[0].length);
    let s = " " + t + " ";
    pairs.forEach(([w, v]) => {
      const re = new RegExp(`(?<!\\w)${w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?!\\w)`, "g");
      s = s.replace(re, ` ${v} `);
    });
    return s.trim();
  }

  function normalizePlain(t) {
    t = t || "";
    // إزالة محارف الاتجاه/التحكم
    t = t.replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, "");

    // أرقام عربية -> إنجليزية
    t = arabicToEnDigits(t);

    // توحيد الرموز
    t = t
      .replace(/[×]/g, "*")
      .replace(/÷/g, "/")
      .replace(/–|—/g, "-")
      .replace(/√/g, "sqrt")
      .replace(/π/g, "pi")
      .replace(/،/g, ",")
      .replace(/\^/g, "**")
      .replace(/\s*=\s*/g, " = ");

    // |x| -> Abs(x)
    try { t = t.replace(/\|([^|]+)\|/g, "Abs($1)"); } catch {}

    // sin 60 درجة -> sin(60)
    t = t.replace(/\b(sin|cos|tan)\s+([+\-]?\d+(?:\.\d+)?)\s*(?:درجة|°)/g, "$1($2)");
    // sin x -> sin(x)
    t = t.replace(/\b(sin|cos|tan)\s+([A-Za-z0-9_.+-]+)/g, "$1($2)");

    // كلمات عربية رياضية
    t = replaceArabicMathWords(t);

    // إزالة أي محارف ليست من المجموعة الآمنة (نستثني أسماء الدوال والمتغيرات)
    t = t.replace(/[^0-9A-Za-z+\-*/=^().,;_| \t\r\n\[\]π]/g, " ");

    // تنظيف المسافات
    t = t.replace(/\s+\)/g, ")").replace(/\(\s+/g, "(").replace(/[^\S\r\n]+/g, " ").trim();

    return t;
  }

  function normalizeOCR(t) {
    // نفس normalizePlain لكن مع تشديد أكبر
    return normalizePlain(t);
  }

  function setLoading(msg = "⏳ جاري الحل…") {
    output.innerHTML = `<div class="step">${msg}</div>`;
  }

  function showError(err) {
    output.innerHTML = `<div class="step" style="color:#ff6b6b">❌ ${err}</div>`;
  }

  function renderSolution(data) {
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

  // قبل الإرسال: طبيع/نظّف
  function preprocessInput(raw) {
    return normalizePlain(raw);
  }

  // ----------------- حل الآن -----------------
  async function solveNow() {
    let raw = (qInput.value || "").trim();
    if (!raw) return;

    // طبيع مسبق قبل الإرسال
    const cleaned = preprocessInput(raw);
    qInput.value = cleaned;

    setLoading();

    try {
      const payload = { q: cleaned, mode: (modeSel.value || "auto") };
      const data = await postJSON("/solve", payload);
      if (!data.ok) return showError(data.error || "فشل الحل");
      renderSolution(data);
    } catch (e) {
      showError(e?.message || e);
    }
  }

  // أحداث
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    solveNow();
  });

  qInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      solveNow();
    }
  });

  // لوحة المفاتيح
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
          modeSel.value = "derivative"; qInput.focus(); return;
        case "∫":
          modeSel.value = "integral"; qInput.focus(); return;
        case "|x|":
          insertAtCursor("Abs(x)"); return;
        case "√":
          insertAtCursor("sqrt()"); {
            const pos = (qInput.selectionStart ?? qInput.value.length) - 1;
            qInput.setSelectionRange(pos, pos);
          }
          return;
        case "π":
          insertAtCursor("pi"); return;
        case "×": insertAtCursor("*"); return;
        case "÷": insertAtCursor("/"); return;
        case "^": insertAtCursor("**"); return;
        case ")sin": insertAtCursor("sin()"); {
          const pos = (qInput.selectionStart ?? qInput.value.length) - 1;
          qInput.setSelectionRange(pos, pos);
        } return;
        case ")cos": insertAtCursor("cos()"); {
          const pos = (qInput.selectionStart ?? qInput.value.length) - 1;
          qInput.setSelectionRange(pos, pos);
        } return;
        case ")tan": insertAtCursor("tan()"); {
          const pos = (qInput.selectionStart ?? qInput.value.length) - 1;
          qInput.setSelectionRange(pos, pos);
        } return;
        case ")Abs": insertAtCursor("Abs()"); {
          const pos = (qInput.selectionStart ?? qInput.value.length) - 1;
          qInput.setSelectionRange(pos, pos);
        } return;
        default:
          insertAtCursor(val);
      }
    });
  }

  // --------- الكاميرا / الأستوديو + OCR ---------
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
      fileInput.removeAttribute("capture");
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
        },
        // الحد من الحروف لزيادة دقة OCR مع خط اليد
        tessedit_char_whitelist:
          "0123456789+-*/=^().,;[]| xXyYzZaAbBcCsSiInNoOtTlLgGpPrReEqQuUhHkKmMdDfF" +
          "π√"
      });
      let text = (data.text || "").trim();
      text = normalizeOCR(text);
      qInput.value = text;
      setLoading("✅ تم استخراج النص. جاري الحل…");
      setTimeout(solveNow, 120);
    } catch (err) {
      showError("فشل التعرف على النص بالـ OCR");
      console.error(err);
    } finally {
      fileInput.value = "";
    }
  });

  if (!qInput.value) {
    qInput.placeholder = "اكتب مسألة أو حتى بالعربي: اشتق 3x^3-5x^2+4x-7 | sin(60)+cos(30) | x+y=7;2x-y=3";
  }
})();
