# Bassam Math Pro v8 — Smart Auto Mode
# إعداد: بسّام الذكي 💜
# واجهة واحدة لحل جميع أنواع المسائل (جبر، تفاضل، تكامل، كسرية، حقيقية...)

from flask import Flask, render_template, request, jsonify
from sympy import *
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
import re, os

app = Flask(__name__, static_folder="static", template_folder="templates")

# إعداد التحويلات لقراءة x^2 كـ x**2 و 3x كـ 3*x
TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
x, y, z = symbols("x y z")
SYMS = {"x": x, "y": y, "z": z, "pi": pi}

def normalize_input(expr_text: str) -> str:
    """تنظيف النص وإرجاعه بصيغة قابلة للفهم"""
    t = expr_text.strip()
    ar_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, d in enumerate(ar_digits):
        t = t.replace(d, str(i))
    t = t.replace("^", "**").replace("×", "*").replace("÷", "/")
    t = t.replace("−", "-").replace("–", "-")
    t = t.replace("π", "pi").replace("√", "sqrt")
    return t

def detect_type(text: str) -> str:
    """تحليل نوع المسألة"""
    low = text.lower()
    if any(k in low for k in ["تفاضل", "اشتق", "مشتقة", "d/dx"]):
        return "diff"
    if any(k in low for k in ["تكامل", "integral", "∫"]):
        return "int"
    if "=" in low:
        return "eq"
    if "/" in low:
        return "frac"
    return "calc"

def explain_fraction(expr_text):
    steps = []
    steps.append("🔹 هذه دالة كسرية لأنها تحتوي على مقام فيه متغير x.")
    steps.append("⚠️ لا يمكن للدالة أن تكون معرفة عندما يكون المقام = 0.")
    steps.append("سنقوم بتبسيط التعبير إن أمكن.")
    expr = parse_expr(expr_text, transformations=TRANSFORMS, local_dict=SYMS)
    simplified = simplify(expr)
    steps.append(f"التعبير بعد التبسيط:\n{simplified}")
    return steps, simplified

def explain_diff(expr_text):
    expr = parse_expr(expr_text, transformations=TRANSFORMS, local_dict=SYMS)
    steps = []
    steps.append("🧮 نريد إيجاد المشتقة بالنسبة إلى x.")
    d = diff(expr, x)
    steps.append(f"مشتقة التعبير:\n d/dx({expr}) = {d}")
    return steps, d

def explain_int(expr_text):
    expr = parse_expr(expr_text, transformations=TRANSFORMS, local_dict=SYMS)
    steps = []
    steps.append("🧮 نريد حساب التكامل بالنسبة إلى x.")
    I = integrate(expr, x)
    steps.append(f"∫({expr}) dx = {I} + C (ثابت التكامل)")
    return steps, I

def explain_eq(expr_text):
    parts = expr_text.split("=")
    if len(parts) != 2:
        raise ValueError("المعادلة غير صحيحة. يرجى كتابة '='.")
    left = parse_expr(parts[0], transformations=TRANSFORMS, local_dict=SYMS)
    right = parse_expr(parts[1], transformations=TRANSFORMS, local_dict=SYMS)
    eq = Eq(left, right)
    steps = []
    steps.append("📘 نريد حل المعادلة:")
    steps.append(str(eq))
    sol = solve(eq, x)
    steps.append(f"✅ الحلول: {sol}")
    return steps, sol

def explain_calc(expr_text):
    expr = parse_expr(expr_text, transformations=TRANSFORMS, local_dict=SYMS)
    steps = []
    steps.append("🧮 هذه دالة حقيقية لأنها لا تحتوي على مقام متغير.")
    simp = simplify(expr)
    steps.append(f"نبسّط التعبير:\n{expr} = {simp}")
    val = simp.evalf()
    steps.append(f"القيمة التقريبية = {val}")
    return steps, simp

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/solve")
def solve_expr():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify(error="يرجى كتابة مسألة."), 400

    expr_text = normalize_input(text)
    typ = detect_type(expr_text)

    try:
        if typ == "diff":
            steps, result = explain_diff(expr_text)
        elif typ == "int":
            steps, result = explain_int(expr_text)
        elif typ == "eq":
            steps, result = explain_eq(expr_text)
        elif typ == "frac":
            steps, result = explain_fraction(expr_text)
        else:
            steps, result = explain_calc(expr_text)

        return jsonify(ok=True, steps=steps, result=str(result))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
