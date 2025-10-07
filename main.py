# main.py — Bassam Mathematics Pro (Arabic Teaching + Degrees + OCR-ready)
from typing import Any, Dict, List, Tuple
import re

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sympy import (
    symbols, Symbol, Eq, S, Matrix, eye, Poly, simplify, expand, factor,
    together, apart, diff, integrate, nroots, discriminant, Rational,
    sin, cos, tan, exp, log, sqrt, solveset, fraction, pi, Abs
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
    convert_xor   # ⬅️ يحوّل ^ إلى ** تلقائياً
)
from sympy.printing.str import sstr

app = FastAPI(title="Bassam Mathematics Pro — Arabic / Degrees")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ⬅️ التحويلات: ضرب ضمني + تحويل ^ إلى **.
TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

def T(x) -> str:
    try: return sstr(x)
    except Exception: return str(x)

def step(title: str, content: str) -> Dict[str, str]:
    return {"title": title, "content": content}

# ⬅️ تنظيف الإدخال: أرقام عربية، ÷×√، π، |x| → Abs(x)، ^ → **.
def normalize_text(q: str) -> str:
    q = (q or "").strip()
    q = q.replace("÷", "/").replace("×", "*").replace("√", "sqrt")
    q = q.replace("–", "-").replace("—", "-")
    ar = "٠١٢٣٤٥٦٧٨٩"; en = "0123456789"
    q = q.translate(str.maketrans(ar, en))
    q = q.replace("^", "**")           # أسس
    q = q.replace("π", "pi").replace("،", ",")
    try:
        q = re.sub(r"\|([^|]+)\|", r"Abs(\1)", q)  # مطلق
    except Exception:
        pass
    return q

def parse(q: str):
    return parse_expr(q, transformations=TRANSFORMS, evaluate=False)

def choose_symbol(expr):
    syms = sorted(expr.free_symbols, key=lambda s: s.name)
    return syms[0] if syms else symbols("x")

# --------- درجات بدلاً من الراديان للدوال المثلثية ----------
from sympy import pi
def trig_degrees(expr):
    if expr.func in (sin, cos, tan):
        a = trig_degrees(expr.args[0])
        if not a.free_symbols and not a.has(pi):
            return expr.func(a * pi / 180)
        return expr.func(a)
    if hasattr(expr, "args") and expr.args:
        return expr.func(*[trig_degrees(a) for a in expr.args])
    return expr

# --------- تقييم/تبسيط مع شرح عربي ----------
def trace_eval(expr) -> Tuple[Any, List[Dict[str, str]]]:
    steps: List[Dict[str, str]] = []
    original = expr
    steps.append(step("قراءة التعبير", f"نقرأ التعبير كما هو: <code>{T(original)}</code>"))

    deg_expr = trig_degrees(expr)
    if deg_expr != expr:
        steps.append(step("الدرجات بدل الراديان",
            f"نحوِّل الدوال المثلثية إلى درجات: <code>{T(expr)}</code> → <code>{T(deg_expr)}</code>"))
    expr = deg_expr

    s1 = simplify(expr)
    if s1 != expr:
        steps.append(step("تبسيط جبري", f"<code>{T(expr)}</code> → <code>{T(s1)}</code>"))
    expr = s1

    tog = together(expr)
    if tog != expr:
        steps.append(step("توحيد المقامات", f"<code>{T(expr)}</code> → <code>{T(tog)}</code>"))
        expr = tog

    ap = apart(expr) if expr.is_rational_function() else expr
    if ap != expr:
        steps.append(step("تجزئة جزئية", f"<code>{T(expr)}</code> → <code>{T(ap)}</code>"))
        expr = ap

    val = expr.evalf()
    steps.append(step("قيمة عددية تقريبية", f"<code>{T(expr)}</code> ≈ <b>{val}</b>"))
    return expr, steps

def do_evaluate(text: str) -> Dict[str, Any]:
    expr = parse(text)
    res, steps = trace_eval(expr)
    return {"mode": "evaluate", "ok": True, "result": T(res.evalf()), "steps": steps}

# --------- تفاضل ----------
def rule_name(term, x: Symbol) -> str:
    if term.is_Pow and term.base == x: return "قاعدة القوة: d(x^n)/dx = n·x^(n-1)"
    if term.is_Mul and any(t.has(x) for t in term.args): return "قاعدة الضرب: (uv)' = u'v + uv'"
    if term.is_Add: return "قاعدة الجمع: (u+v)' = u' + v'"
    if term.func in (sin, cos, tan, exp, log, sqrt, Abs): return f"مشتقة الدالة {term.func.__name__}"
    return "قواعد التفاضل العامة + تبسيط"

def do_derivative(text: str) -> Dict[str, Any]:
    expr = parse(text)
    expr = trig_degrees(expr)
    x = choose_symbol(expr)
    steps: List[Dict[str, str]] = [step("الدالة", f"لدينا: <code>f({T(x)}) = {T(expr)}</code>")]
    parts = list(expr.as_ordered_terms()) if expr.is_Add else [expr]
    for t in parts:
        d_t = simplify(diff(t, x))
        steps.append(step("اشتقاق حد", f"<code>{T(t)}</code> ← {rule_name(t, x)} → <code>{T(d_t)}</code>"))
    d = simplify(diff(expr, x))
    steps.append(step("جمع وتبسيط", f"بجمع المشتقات وتبسيطها: <code>f'({T(x)}) = {T(d)}</code>"))
    return {"mode": "derivative", "ok": True, "result": T(d), "steps": steps}

# --------- تكامل ----------
def do_integral(text: str) -> Dict[str, Any]:
    expr = parse(text)
    expr = trig_degrees(expr)
    x = choose_symbol(expr)
    steps: List[Dict[str, str]] = [step("الدالة", f"لدينا: <code>f({T(x)}) = {T(expr)}</code>")]
    t = together(expr)
    if t != expr:
        steps.append(step("توحيد المقامات", f"<code>{T(expr)}</code> → <code>{T(t)}</code>"))
        expr = t
    if expr.is_rational_function(x):
        ap = apart(expr, x)
        if ap != expr:
            steps.append(step("تجزئة جزئية", f"<code>{T(expr)}</code> → <code>{T(ap)}</code>"))
            expr = ap
    if expr.is_Add:
        for term in expr.as_ordered_terms():
            steps.append(step("تكامل حد", f"نحسب <code>∫ {T(term)} dx</code>"))
    else:
        steps.append(step("التكامل", f"نحسب <code>∫ {T(expr)} dx</code>"))
    F = simplify(integrate(expr, x))
    steps.append(step("النتيجة", f"<code>∫ {T(expr)} dx = {T(F)} + C</code>"))
    return {"mode": "integral", "ok": True, "result": T(F) + " + C", "steps": steps}

# --------- أنظمة/معادلات (Gauss–Jordan بالعربي) ----------
def parse_equations(text: str):
    parts = [p.strip() for p in text.split(";") if p.strip()]
    eqs = []
    for p in parts or [text]:
        if "=" in p:
            l, r = p.split("=", 1)
            eqs.append((parse(l), parse(r)))
        else:
            eqs.append((parse(p), S.Zero))
    return eqs

def symbols_of(eqs):
    syms = set()
    for LHS, RHS in eqs:
        syms |= (LHS - RHS).free_symbols
    return sorted(syms, key=lambda s: s.name)

def rref_with_steps(M: Matrix):
    steps = []
    M = Matrix(M)
    steps.append(step("بداية", f"نشكّل المصفوفة: <code>{T(M)}</code>"))
    r = c = 0
    rows, cols = M.rows, M.cols
    while r < rows and c < cols:
        pivot = None
        for i in range(r, rows):
            if M[i, c] != 0:
                pivot = i; break
        if pivot is None:
            c += 1; continue
        if pivot != r:
            M.row_swap(r, pivot)
            steps.append(step("تبديل صفوف", f"R{r+1} ↔ R{pivot+1}: <code>{T(M)}</code>"))
        piv = M[r, c]
        if piv != 1:
            M.row_op(r, lambda v, _: v / piv)
            steps.append(step("تطبيع محور", f"R{r+1} ← R{r+1}/{T(piv)}: <code>{T(M)}</code>"))
        for i in range(rows):
            if i == r: continue
            f = M[i, c]
            if f != 0:
                M.row_op(i, lambda v, j: v - f * M[r, j])
                steps.append(step("تصفير عمود", f"R{i+1} ← R{i+1} − ({T(f)})·R{r+1}: <code>{T(M)}</code>"))
        r += 1; c += 1
        M = Matrix(M.applyfunc(lambda x: x.simplify()))
    return M, steps

def inverse_with_steps(A: Matrix):
    A = Matrix(A)
    if A.rows != A.cols:
        return None, [step("تحقق", "لا يوجد معكوس لمصفوفة غير مربعة")]
    Aug = A.row_join(eye(A.rows))
    steps = [step("تهيئة", f"نكوّن [A|I]: <code>{T(Aug)}</code>")]
    RREF, s2 = rref_with_steps(Aug)
    steps += s2
    left = RREF[:, :A.rows]; right = RREF[:, A.rows:]
    if left != eye(A.rows):
        steps.append(step("نتيجة", "لم نصل إلى I على اليسار ⇒ لا يوجد معكوس"))
        return None, steps
    steps.append(step("استخراج", f"المعكوس هو الجزء الأيمن: <code>{T(right)}</code>"))
    return right, steps

def do_solve(text: str) -> Dict[str, Any]:
    steps: List[Dict[str, str]] = []
    eqs = parse_equations(text)
    if len(eqs) > 1:
        syms = symbols_of(eqs)
        rows = []; rhs = []
        for LHS, RHS in eqs:
            expr = simplify(LHS - RHS)
            row = [expr.expand().coeff(s) for s in syms]
            const = -expr.subs({s: 0 for s in syms})
            rows.append(row); rhs.append([const])
        A = Matrix(rows); b = Matrix(rhs)
        steps.append(step("صياغة مصفوفية", f"نكتب النظام على صورة <code>A·X=b</code> حيث <code>X=[{', '.join(map(T, syms))}]^T</code>"))
        steps.append(step("A و b", f"<code>A={T(A)}</code> ، <code>b={T(b)}</code>"))
        Aug = A.row_join(b)
        steps.append(step("المصفوفة المُعزَّزة", f"<code>[A|b]={T(Aug)}</code>"))
        R, s2 = rref_with_steps(Aug); steps += s2
        from sympy import linsolve
        sol = linsolve((A, b))
        steps.append(step("استخراج الحل", f"نقرأ الحل من الشكل المختزل: <code>{T(sol)}</code>"))
        return {"mode": "solve", "ok": True, "result": T(sol), "steps": steps}

    LHS, RHS = eqs[0]
    steps.append(step("المعادلة", f"<code>{T(LHS)} = {T(RHS)}</code>"))
    expr = simplify(LHS - RHS)
    steps.append(step("نقل الحدود", f"ننقل كل الحدود لطرف واحد: <code>{T(expr)}</code> = 0"))
    x = choose_symbol(expr)
    try:
        P = Poly(expr, x); deg = P.degree()
        steps.append(step("درجة كثير الحدود", f"الدرجة = {deg}"))
        if deg == 1:
            sol = P.solve(x); steps.append(step("حل خطي", f"نرتّب ونقسم على معامل <code>{T(x)}</code>"))
        elif deg == 2:
            D = discriminant(P); steps.append(step("المميز", f"Δ = <code>{T(D)}</code>"))
            steps.append(step("الصيغة التربيعية", "x = (-b ± √Δ) / (2a)"))
            sol = P.solve(x)
        elif deg in (3, 4):
            steps.append(step("حل تحليلي", "نستخدم صيغ التكعيبي/الرباعي أو التحليل إن أمكن"))
            sol = P.solve(x)
        else:
            roots = [c for c in nroots(P)]
            steps.append(step("حل عددي", "للدرجات ≥5 نستخدم nroots"))
            return {"mode": "solve", "ok": True, "result": T(roots), "steps": steps}
        return {"mode": "solve", "ok": True, "result": T(sol), "steps": steps}
    except Exception:
        sol = solveset(expr, x)
        return {"mode": "solve", "ok": True, "result": T(sol), "steps": steps}

# --------- مصفوفات ----------
def parse_matrix_like(s: str) -> Matrix:
    s = normalize_text(s)
    if s.startswith("Matrix("): return parse(s)
    if s.startswith("[[") and s.endswith("]]"): return parse(f"Matrix({s})")
    rows = [r.strip() for r in re.split(r";|\n", s) if r.strip()]
    data = []
    for r in rows:
        data.append([parse(c) for c in re.split(r"[,\s]+", r) if c])
    return Matrix(data)

def do_matrix(text: str) -> Dict[str, Any]:
    s = normalize_text(text); steps: List[Dict[str, str]] = []
    low = s.lower()
    if low.startswith("rref("):
        A = parse_matrix_like(re.sub(r"rref\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"<code>A={T(A)}</code>"))
        R, s2 = rref_with_steps(A); steps += s2
        return {"mode": "matrix", "ok": True, "result": T(R), "steps": steps}
    if low.startswith("det("):
        A = parse_matrix_like(s[4:-1]); steps.append(step("المصفوفة", f"<code>A={T(A)}</code>"))
        d = A.det(); steps.append(step("المحدد", f"det(A) = <code>{T(d)}</code>"))
        return {"mode": "matrix", "ok": True, "result": T(d), "steps": steps}
    if low.startswith("inv("):
        A = parse_matrix_like(s[4:-1]); steps.append(step("المصفوفة", f"<code>A={T(A)}</code>"))
        Ainv, s2 = inverse_with_steps(A); steps += s2
        if Ainv is None: return {"mode": "matrix", "ok": True, "result": "non-invertible", "steps": steps}
        return {"mode": "matrix", "ok": True, "result": T(Ainv), "steps": steps}
    if "eigenvals" in low:
        A = parse_matrix_like(re.sub(r"eigenvals\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"<code>A={T(A)}</code>")); steps.append(step("المعادلة المميزة", "det(A-λI)=0"))
        ev = A.eigenvals(); return {"mode": "matrix", "ok": True, "result": T(ev), "steps": steps}
    if "eigenvects" in low:
        A = parse_matrix_like(re.sub(r"eigenvects?\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"<code>A={T(A)}</code>")); steps.append(step("حل (A-λI)v=0", "نستخرج الفضاءات الذاتية"))
        ev = A.eigenvects(); return {"mode": "matrix", "ok": True, "result": T(ev), "steps": steps}
    if low.startswith(("diag(", "diagonalize(")):
        A = parse_matrix_like(re.sub(r"diag(?:onalize)?\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"<code>A={T(A)}</code>"))
        try:
            P, D = A.diagonalize()
            steps.append(step("تشابه", "A = P·D·P^{-1}")); steps.append(step("P", f"<code>{T(P)}</code>")); steps.append(step("D", f"<code>{T(D)}</code>"))
            return {"mode": "matrix", "ok": True, "result": f"P={T(P)}, D={T(D)}", "steps": steps}
        except Exception:
            steps.append(step("غير قطري", "A غير قابلة للتقطيع قطريًا"))
            return {"mode": "matrix", "ok": True, "result": "not diagonalizable", "steps": steps}
    if low.startswith("jordan("):
        A = parse_matrix_like(re.sub(r"jordan\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"<code>A={T(A)}</code>"))
        J, P = A.jordan_normal_form()
        steps.append(step("شكل جوردان", f"<code>{T(J)}</code>"))
        return {"mode": "matrix", "ok": True, "result": T(J), "steps": steps}
    A = parse_matrix_like(s)
    steps.append(step("المصفوفة", f"<code>A={T(A)}</code>"))
    R, s2 = rref_with_steps(A); steps += s2
    return {"mode": "matrix", "ok": True, "result": T(R), "steps": steps}

def detect_mode(text: str) -> str:
    t = (text or "").lower().strip()
    if t.startswith("deriv") or t.startswith("مشتق"): return "derivative"
    if t.startswith("integ") or t.startswith("تكامل"): return "integral"
    if any(k in t for k in ["eigen","det(","inv(","rank","[[","matrix(","jordan(","diag(","rref("]): return "matrix"
    if ";" in t or "=" in t: return "solve"
    return "evaluate"

@app.post("/solve")
async def solve_api(request: Request):
    data = await request.json()
    q: str = normalize_text(data.get("q", ""))
    mode: str = data.get("mode", "auto")
    if q.startswith("مشتق "):   return do_derivative(q.replace("مشتق ", "", 1))
    if q.startswith("تكامل "):  return do_integral(q.replace("تكامل ", "", 1))
    if not q: return JSONResponse({"ok": False, "error": "لا يوجد نص مسألة"})
    try:
        m = detect_mode(q) if mode == "auto" else mode
        if   m == "derivative": out = do_derivative(q)
        elif m == "integral":   out = do_integral(q)
        elif m == "matrix":     out = do_matrix(q)
        elif m == "solve":      out = do_solve(q)
        else:                   out = do_evaluate(q)
        out["ok"] = True
        return JSONResponse(out)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Bassam Math Pro (PWA, OCR, Degrees)"})
