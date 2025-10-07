import os
from flask import Flask, render_template, request, jsonify
from sympy import sympify, simplify, latex, Number
from sympy.parsing.sympy_parser import (
    standard_transformations, implicit_multiplication_application
)

app = Flask(__name__, static_url_path="/static", template_folder="templates")

# ---------- أدوات مساعدة ----------
def to_caret(expr) -> str:
    """تحويل x**3 إلى x^3 وإضافة نقطة للضرب."""
    s = str(expr)
    s = s.replace('**', '^')
    s = s.replace('*', '·')
    return s


def arabic_steps_for(expr, original_text):
    """شرح خطوات الحل بالعربية."""
    steps = []
    steps.append("<h3 class='section-title'>الوضع: حساب — شرح مُوسع</h3>")

    safe_orig = (original_text or "").replace('<', '&lt;').replace('>', '&gt;')
    steps.append("<h4>الخطوة 1:</h4>")
    steps.append(f"<p>المعادلة كما أُدخِلت: <code>{safe_orig}</code></p>")

    simp = simplify(expr)
    if str(simp) != str(expr):
        steps.append("<h4>الخطوة 2:</h4>")
        steps.append("<p>نُبسّط التعبير جبريًّا دون تغيير معناه:</p>")
        steps.append(f"<div class='result-line'>قبل: <code>{to_caret(expr)}</code></div>")
        steps.append(f"<div class='result-line'>بعد: <code>{to_caret(simp)}</code></div>")
    else:
        steps.append("<h4>الخطوة 2:</h4>")
        steps.append("<p>لا يحتاج التعبير لتبسيط إضافي.</p>")

    if len(simp.free_symbols) == 0:
        try:
            val = simp.evalf(15)
            steps.append("<h4>الخطوة 3:</h4>")
            steps.append("<p>التعبير عددي بالكامل، ونقيّمه بدقة مناسبة:</p>")
            steps.append(f"<div class='result-line'><b>القيمة النهائية</b> ≈ {val}</div>")
        except Exception:
            pass

    return "\n".join(steps), simp


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
        expr = sympify(
            user_text,
            transformations=(standard_transformations + (implicit_multiplication_application,))
        )

        steps_html, simplified = arabic_steps_for(expr, user_text)
        caret_text = to_caret(simplified)
        ar_latex = latex(simplified)

        numeric_value = None
        if len(simplified.free_symbols) == 0:
            try:
                numeric_value = str(simplified.evalf(15))
            except Exception:
                pass

        return jsonify({
            "ok": True,
            "steps_html": steps_html,
            "pretty": {"en_text": caret_text, "ar_latex": ar_latex},
            "numeric_value": numeric_value
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"خطأ في قراءة المسألة: {e}"}), 400


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
