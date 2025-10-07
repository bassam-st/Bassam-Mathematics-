import os
from flask import Flask, render_template, request, jsonify
from sympy import sympify, simplify, latex, Number
from sympy.parsing.sympy_parser import (
    standard_transformations, implicit_multiplication_application
)

app = Flask(__name__, static_url_path="/static", template_folder="templates")

# ---------- أدوات مساعدة ----------

def to_caret(expr) -> str:
    """
    يحوّل تمثيل SymPy النصّي إلى شكل x^3 و x^2 باستخدام ^،
    ويضع نقطة وسطية للضرب لتوضيح الشكل للمستخدم.
    """
    s = str(expr)
    s = s.replace('**', '^')  # قوّة
    s = s.replace('*', '·')   # ضرب
    return s

def arabic_steps_for(expr, original_text):
    """
    يبني شرحًا عربيًا مختصرًا خطوة بخطوة.
    يمكن توسعته لاحقًا ليشمل مزيد من الحالات.
    """
    steps = []
    steps.append("<h3 class='section-title'>الوضع: حساب — شرح مُوسع</h3>")

    # الخطوة 1: عرض المسألة كما كُتبت
    safe_orig = (original_text or "").replace('<', '&lt;').replace('>', '&gt;')
    steps.append("<h4>الخطوة 1:</h4>")
    steps.append(f"<p>المعادلة كما أُدخِلت: <code>{safe_orig}</code></p>")

    # الخطوة 2: تبسيط رمزي عام
    simp = simplify(expr)
    if str(simp) != str(expr):
        steps.append("<h4>الخطوة 2:</h4>")
        steps.append("<p>نُبسّط التعبير جبريًّا دون تغيير معناه.</p>")
        steps.append(f"<div class='result-line'>قبل: <code>{to_caret(expr)}</code></div>")
        steps.append(f"<div class='result-line'>بعد: <code>{to_caret(simp)}</code></div>")
    else:
        steps.append("<h4>الخطوة 2:</h4>")
        steps.append("<p>لا يحتاج التعبير لتبسيط إضافي.</p>")

    # الخطوة 3: إن أمكن، تقييم ثوابت مستقلة عن المتغيرات
    if len(simp.free_symbols) == 0:
        try:
            val = simp.evalf(15)
            steps.append("<h4>الخطوة 3:</h4>")
            steps.append(f"<p>التعبير عددي بالكامل، ونقيّمه بدقة مناسبة:</p>")
            steps.append(f"<div class='result-line'><b>القيمة</b> ≈ {val}</div>")
        except Exception:
            pass

    return "\n".join(steps), simp

# ---------- الواجهات ----------

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/solve")
def api_solve():
    data = request.get_json(force=True, silent=True) or {}
    user_text = (data.get("q") or "").strip()

    if not user_text:
        return jsonify({"ok": False, "error": "أدخل مسألة لحلّها."}), 400

    try:
        # دعم الضرب الضمني: 2x ، 3(x+1) ، إلخ
        expr = sympify(
            user_text,
            transformations=(standard_transformations + (implicit_multiplication_application,))
        )

        # شرح بالعربية + تبسيط
        steps_html, simplified = arabic_steps_for(expr, user_text)

        # صيغتا العرض
        caret_text = to_caret(simplified)  # x^3 - 5x^2 ... بنص إنجليزي
        ar_latex   = latex(simplified)     # LaTeX للعرض العربي المنسّق

        # لو كانت قيمة عددية خالصة، أعدّ قيمة رقمية أيضًا
        numeric_value = None
        if len(simplified.free_symbols) == 0:
            try:
                v = simplified.evalf(15)
                if isinstance(v, Number) or isinstance(v, float) or True:
                    numeric_value = str(v)
            except Exception:
                pass

        return jsonify({
            "ok": True,
            "steps_html": steps_html,
            "pretty": {
                "en_text": caret_text,
                "ar_latex": ar_latex
            },
            "numeric_value": numeric_value
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"خطأ في قراءة المسألة: {e}"}), 400


if __name__ == "__main__":
    # PORT لبيئات الاستضافة (اختياري)
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)    verbose_triggers = ("شرح", "بالتفصيل", "#شرح", "شرح موسع", "شرح مُوسّع")
    verbose = explain in ("extended", "verbose") or any(t in raw_q for t in verbose_triggers)

    inferred_mode, inferred_expr = parse_intent_ar(raw_q)
    mode = ui_mode if ui_mode != "auto" else inferred_mode
    expr_raw = raw_q if ui_mode != "auto" else inferred_expr
    expr = normalize_text(expr_raw)

    if mode == "derivative":   query = f"تفاضل {expr}"
    elif mode == "integral":   query = f"تكامل {expr}"
    elif mode == "solve":      query = expr
    else:                      query = expr

    out = smart_solve(query, verbose=verbose)
    if "error" in out:
        return JSONResponse({"ok": False, "error": out["error"]})

    return JSONResponse({
        "ok": True,
        "mode": out.get("type", mode),
        "result": out.get("result", ""),
        "steps": out.get("steps", []),
        "raw": query,
        "verbose": verbose,
    })
