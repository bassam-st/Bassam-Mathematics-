import os
from flask import Flask, render_template, request, jsonify
from sympy import sympify, simplify, latex
from sympy.parsing.sympy_parser import (
    standard_transformations, implicit_multiplication_application
)

app = Flask(__name__, static_url_path="/static", template_folder="templates")

# ---------- مساعدات ----------
def to_caret(expr) -> str:
    return str(expr).replace('**', '^').replace('*', '·')

def arabic_steps_for(expr, original_text):
    steps = []
    steps.append("<h3 class='section-title'>الوضع: حساب — شرح مُوسّع</h3>")

    safe_orig = (original_text or "").replace('<', '&lt;').replace('>', '&gt;')
    steps.append("<h4>الخطوة 1:</h4>")
    steps.append(f"<p>المسألة كما أُدخِلت/استُخرِجت: <code>{safe_orig}</code></p>")

    simp = simplify(expr)
    if str(simp) != str(expr):
        steps.append("<h4>الخطوة 2:</h4>")
        steps.append("<p>تبسيط جبري دون تغيير المعنى:</p>")
        steps.append(f"<div class='result-line'>قبل: <code>{to_caret(expr)}</code></div>")
        steps.append(f"<div class='result-line'>بعد: <code>{to_caret(simp)}</code></div>")
    else:
        steps.append("<h4>الخطوة 2:</h4>")
        steps.append("<p>لا يحتاج التعبير لتبسيط إضافي.</p>")

    if len(simp.free_symbols) == 0:
        val = simp.evalf(15)
        steps.append("<h4>الخطوة 3:</h4>")
        steps.append("<p>التعبير عددي بالكامل، نحسب قيمته بدقة مناسبة:</p>")
        steps.append(f"<div class='result-line'><b>القيمة النهائية</b> ≈ {val}</div>")

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
            numeric_value = str(simplified.evalf(15))

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
