import os
from flask import Flask, render_template, request, jsonify
from sympy import sympify, simplify, latex, Number
from sympy.parsing.sympy_parser import (
    standard_transformations, implicit_multiplication_application
)

# إنشاء التطبيق
app = Flask(__name__, static_url_path="/static", template_folder="templates")

# ---------- أدوات مساعدة ----------

def to_caret(expr) -> str:
    """
    يحوّل تمثيل SymPy إلى شكل x^3 و x^2 (باستخدام ^ بدلاً من **)،
    ويضيف نقطة وسطية للضرب لجعل التعبير أسهل للقراءة.
    """
    s = str(expr)
    s = s.replace('**', '^')
    s = s.replace('*', '·')
    return s


def arabic_steps_for(expr, original_text):
    """
    يبني شرحًا عربيًا خطوة بخطوة لعملية الحل أو التبسيط.
    """
    steps = []
    steps.append("<h3 class='section-title'>الوضع: حساب — شرح مُوسع</h3>")

    # الخطوة 1: عرض ما أدخله المستخدم
    safe_orig = (original_text or "").replace('<', '&lt;').replace('>', '&gt;')
    steps.append("<h4>الخطوة 1:</h4>")
    steps.append(f"<p>المعادلة كما أُدخِلت: <code>{safe_orig}</code></p>")

    # الخطوة 2: تبسيط التعبير جبرياً
    simp = simplify(expr)
    if str(simp) != str(expr):
        steps.append("<h4>الخطوة 2:</h4>")
        steps.append("<p>نُبسّط التعبير جبريًّا دون تغيير معناه:</p>")
        steps.append(f"<div class='result-line'>قبل: <code>{to_caret(expr)}</code></div>")
        steps.append(f"<div class='result-line'>بعد: <code>{to_caret(simp)}</code></div>")
    else:
        steps.append("<h4>الخطوة 2:</h4>")
        steps.append("<p>لا يحتاج التعبير لتبسيط إضافي.</p>")

    # الخطوة 3: إذا كان التعبير عددي بالكامل، نحسب قيمته
    if len(simp.free_symbols) == 0:
        try:
            val = simp.evalf(15)
            steps.append("<h4>الخطوة 3:</h4>")
            steps.append("<p>التعبير عددي بالكامل، ونقيّمه بدقة مناسبة:</p>")
            steps.append(f"<div class='result-line'><b>القيمة النهائية</b> ≈ {val}</div>")
        except Exception:
            pass

    return "\n".join(steps), simp


# ---------- الواجهات ----------

@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/solve")
def api_solve():
    """
    نقطة API لحل أو تبسيط المسائل الرياضية وإرجاعها بصيغتين:
    - عرض نصّي إنجليزي (x^3 - 5x^2 ...)
    - عرض رياضي منسق (LaTeX)
    مع شرح تفصيلي بالعربية.
    """
    data = request.get_json(force=True, silent=True) or {}
    user_text = (data.get("q") or "").strip()

    if not user_text:
        return jsonify({"ok": False, "error": "أدخل مسألة لحلّها."}), 400

    try:
        # دعم الضرب الضمني (مثل 2x أو 3(x+1))
        expr = sympify(
            user_text,
            transformations=(standard_transformations + (implicit_multiplication_application,))
        )

        # إعداد الشرح والتبسيط
        steps_html, simplified = arabic_steps_for(expr, user_text)

        # صيغ العرض
        caret_text = to_caret(simplified)   # x^3 - 5x^2 + ...
        ar_latex   = latex(simplified)      # LaTeX

        # لو التعبير عددي (بدون متغيرات)
        numeric_value = None
        if len(simplified.free_symbols) == 0:
            try:
                v = simplified.evalf(15)
                numeric_value = str(v)
            except Exception:
                pass

        # النتيجة النهائية
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


# ---------- تشغيل التطبيق ----------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
