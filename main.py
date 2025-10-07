import os
from flask import Flask, render_template, request, jsonify
import sympy as sp
from sympy.parsing.sympy_parser import (
    standard_transformations, implicit_multiplication_application
)

app = Flask(__name__, static_url_path="/static", template_folder="templates")

# رموز شائعة
x, y, z, t = sp.symbols("x y z t")
pi = sp.pi

TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

def _parse(expr_text: str):
    local = {
        "x": x, "y": y, "z": z, "t": t,
        "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
        "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt,
        "Abs": sp.Abs, "pi": sp.pi, "e": sp.E, "E": sp.E,
    }
    return sp.sympify(expr_text, locals=local, transformations=TRANSFORMS)

def _to_caret(expr) -> str:
    return str(expr).replace("**", "^").replace("*", "·")

def _latex(expr) -> str:
    try:
        return sp.latex(expr)
    except Exception:
        return sp.latex(sp.sympify(expr))

# --------- بناء شرح مبسط للأطفال ---------
def explain_evaluate(expr):
    steps = []
    steps.append("<h3 class='section-title'>الوضع: حساب عددي</h3>")
    steps.append("<h4>١) نرتّب التعبير:</h4>")
    simp = sp.simplify(expr)
    if str(simp) != str(expr):
        steps.append(f"<p>قبل: <code>{_to_caret(expr)}</code></p>")
        steps.append(f"<p>بعد: <code>{_to_caret(simp)}</code></p>")
    else:
        steps.append("<p>التعبير واضح ولا يحتاج تبسيط.</p>")
    out = simp
    if len(out.free_symbols) == 0:
        val = sp.N(out, 15)
        steps.append("<h4>٢) نحسب القيمة:</h4>")
        steps.append(f"<p>النتيجة العددية ≈ <b>{val}</b></p>")
    else:
        steps.append("<h4>٢) نتيجة رمزية:</h4>")
        steps.append("<p>فيه متغيّرات، فنكتب النتيجة بشكل جبري مبسّط.</p>")
    return steps, out

def explain_derivative(expr):
    steps = []
    steps.append("<h3 class='section-title'>الوضع: تفاضل (مشتقّة)</h3>")
    steps.append("<h4>١) قاعدة الجمع:</h4><p>نشتق كل حد لوحده ثم نجمع.</p>")
    steps.append("<h4>٢) قاعدة القوة:</h4><p>مشتق x^n هو n·x^(n-1).</p>")
    d = sp.diff(expr, x)
    steps.append(f"<h4>٣) الاشتقاق:</h4><p>d/dx(<code>{_to_caret(expr)}</code>) = <code>{_to_caret(d)}</code></p>")
    s = sp.simplify(d)
    if str(s) != str(d):
        steps.append(f"<h4>٤) تبسيط:</h4><p><code>{_to_caret(d)}</code> ⟶ <code>{_to_caret(s)}</code></p>")
    return steps, s

def explain_integral(expr):
    steps = []
    steps.append("<h3 class='section-title'>الوضع: تكامل</h3>")
    steps.append("<h4>١) خطية التكامل:</h4><p>نفكّك المجموع ونكامل كل حد.</p>")
    I = sp.integrate(expr, x)
    steps.append(f"<h4>٢) نحسب التكامل:</h4><p>∫(<code>{_to_caret(expr)}</code>) dx = <code>{_to_caret(I)}</code> + C</p>")
    s = sp.simplify(I)
    if str(s) != str(I):
        steps.append(f"<h4>٣) تبسيط:</h4><p><code>{_to_caret(I)}</code> ⟶ <code>{_to_caret(s)}</code></p>")
    steps.append("<p><b>ملاحظة:</b> نضيف ثابت التكامل (+C).</p>")
    return steps, s

def explain_solve(eqs_text):
    steps = []
    steps.append("<h3 class='section-title'>الوضع: حلّ معادلة/نظام</h3>")
    parts = [p.strip() for p in eqs_text.split(";") if p.strip()]
    eqs = []
    try:
        if len(parts) == 1:
            if "=" in parts[0]:
                L, R = parts[0].split("=", 1)
                eqs.append(sp.Eq(_parse(L), _parse(R)))
            else:
                eqs.append(sp.Eq(_parse(parts[0]), 0))
        else:
            for p in parts:
                if "=" in p:
                    L, R = p.split("=", 1)
                    eqs.append(sp.Eq(_parse(L), _parse(R)))
                else:
                    eqs.append(sp.Eq(_parse(p), 0))
    except Exception as e:
        return [f"<p>تعذّر فهم المعادلات: {e}</p>"], None

    for i, eq in enumerate(eqs, 1):
        steps.append(f"<p>المعادلة {i}: <code>{_to_caret(eq.lhs)}</code> = <code>{_to_caret(eq.rhs)}</code></p>")

    steps.append("<h4>١) نستخدم طرق جبرية (إحلال/حذف) لحلّ المتغيّرات.</h4>")
    vars_set = set()
    for eq in eqs:
        vars_set |= set(eq.free_symbols)
    vars_list = sorted(list(vars_set), key=lambda s: s.name) or [x]
    sol = sp.solve(eqs, *vars_list, dict=True)

    if not sol:
        steps.append("<p>لا توجد حلول (قد يكون النظام متناقضًا).</p>")
        return steps, None

    if len(sol) == 1:
        s = sol[0]
        for k, v in s.items():
            steps.append(f"<p><b>{k}</b> = <code>{_to_caret(sp.simplify(v))}</code></p>")
        return steps, s
    else:
        for i, s in enumerate(sol, 1):
            pretty = ", ".join(f"{k}={_to_caret(sp.simplify(v))}" for k, v in s.items())
            steps.append(f"<p>حل {i}: {pretty}</p>")
        return steps, sol

def detect_mode(q: str):
    low = q.lower()
    if any(w in low for w in ["تفاضل", "مشتق", "d/dx", "deriv"]):
        return "derivative"
    if any(w in low for w in ["تكامل", "integr", "∫"]):
        return "integral"
    if "=" in q or ";" in q:
        return "solve"
    return "evaluate"

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/solve")
def api_solve():
    data = request.get_json(force=True, silent=True) or {}
    raw = (data.get("q") or "").strip()
    if not raw:
        return jsonify({"ok": False, "error": "أدخل مسألة."}), 400

    try:
        mode = detect_mode(raw)
        if mode == "solve":
            steps, out = explain_solve(raw)
            if out is None:
                return jsonify({"ok": False, "error": "تعذّر حلّ المعادلة/النظام."}), 400
            # صيغة العرض
            if isinstance(out, dict):
                pretty_text = "; ".join(f"{k}={_to_caret(sp.simplify(v))}" for k, v in out.items())
                latex_text  = _latex(sp.Matrix([[sp.simplify(v) for v in out.values()]]))
            else:
                pretty_text = " ; ".join(", ".join(f"{k}={_to_caret(sp.simplify(v))}" for k, v in s.items()) for s in out)
                latex_text  = _latex(sp.Matrix([[sp.simplify(v) for v in out[0].values()]]))
            return jsonify({"ok": True, "steps_html": "\n".join(steps), "pretty": {"en_text": pretty_text, "ar_latex": latex_text}})

        # للباقي نحلّل كتعابير
        expr = _parse(raw)
        if mode == "derivative":
            steps, result = explain_derivative(expr)
        elif mode == "integral":
            steps, result = explain_integral(expr)
        else:
            steps, result = explain_evaluate(expr)

        caret_text = _to_caret(result if result is not None else expr)
        latex_text = _latex(result if result is not None else expr)

        numeric_value = None
        if hasattr(result, "free_symbols") and len(result.free_symbols) == 0:
            try:
                numeric_value = str(sp.N(result, 15))
            except Exception:
                pass

        return jsonify({
            "ok": True,
            "steps_html": "\n".join(steps),
            "pretty": {"en_text": caret_text, "ar_latex": latex_text},
            "numeric_value": numeric_value
        })
    except Exception as e:
        return jsonify({"ok": False, "error": f"خطأ في القراءة/الحل: {e}"}), 400

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
