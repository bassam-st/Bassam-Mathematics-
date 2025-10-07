# main.py — Bassam Mathematics Pro (Teaching Edition, Final)
# FastAPI + SymPy مع خطوات تعليمية مفصّلة لكل العمليات

from typing import Any, Dict, List, Tuple
import re

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# === SymPy ===
from sympy import (
    symbols, Symbol, Eq, S, Matrix, eye, Poly, simplify, expand, factor,
    together, apart, diff, integrate, latex, nroots, discriminant, Rational,
    sin, cos, tan, exp, log, sqrt, solveset, fraction
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application
)

# -----------------------------------------------------------------------------
# إعداد التطبيق
# -----------------------------------------------------------------------------
app = FastAPI(title="Bassam Mathematics Pro — Teaching Edition")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

# -----------------------------------------------------------------------------
# أدوات مساعدة مشتركة
# -----------------------------------------------------------------------------
def L(obj) -> str:
    """تحويل آمن إلى LaTeX (يتفادى الأعطال)."""
    try:
        return latex(obj)
    except Exception:
        return str(obj)

def step(title: str, content: str) -> Dict[str, str]:
    return {"title": title, "content": content}

def normalize_text(q: str) -> str:
    """تطبيع الإدخال: رموز عربية، ضرب/قسمة، جذر… إلخ."""
    q = (q or "").strip()
    q = q.replace("÷", "/").replace("×", "*").replace("√", "sqrt")
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    q = q.translate(trans)
    return q

def parse(q: str):
    return parse_expr(q, transformations=TRANSFORMS)

def choose_symbol(expr):
    syms = sorted(expr.free_symbols, key=lambda s: s.name)
    return syms[0] if syms else symbols("x")

# -----------------------------------------------------------------------------
# 1) التقييم مع تتبّع تعليمي (PEMDAS)
# -----------------------------------------------------------------------------
def trace_eval(expr) -> Tuple[Any, List[Dict[str, str]]]:
    steps: List[Dict[str, str]] = []

    def _trace(e):
        if e.is_Number or (e.is_Symbol and not e.is_Function):
            return e
        if e.is_Add:
            parts = list(e.as_ordered_terms())
            computed = [_trace(p) for p in parts]
            before = e
            after = sum(computed)
            steps.append(step("جمع/طرح", f"${L(before)} \\Rightarrow {L(after)}$"))
            return after
        if e.is_Mul:
            parts = list(e.as_ordered_factors())
            computed = [_trace(p) for p in parts]
            before = e
            prod = S.One
            for p in computed:
                prod *= p
            steps.append(step("ضرب/قسمة", f"${L(before)} \\Rightarrow {L(prod)}$"))
            return prod
        if e.is_Pow:
            base = _trace(e.base)
            expn = _trace(e.exp)
            before = e
            after = base ** expn
            steps.append(step("قوة", f"${L(before)} \\Rightarrow {L(after)}$"))
            return after
        if e.is_Function:
            args2 = [_trace(a) for a in e.args]
            before = e
            after = e.func(*args2)
            steps.append(step("دالة", f"${L(before)} \\Rightarrow {L(after)}$"))
            return after
        return e

    t = together(expr)
    if t != expr:
        steps.append(step("توحيد المقامات", f"${L(expr)} \\Rightarrow {L(t)}$"))

    e2 = _trace(t)
    simp = simplify(e2)
    if simp != e2:
        steps.append(step("تبسيط", f"${L(e2)} \\Rightarrow {L(simp)}$"))

    val = simp.evalf()
    p, q = fraction(simp)
    nice = simp if q == 1 else Rational(p, q)
    steps.append(step("قيمة عددية", f"${L(simp)} = {L(val)}$"))
    return nice, steps

def do_evaluate(text: str) -> Dict[str, Any]:
    expr = parse(text)
    res, steps = trace_eval(expr)
    return {"mode": "evaluate", "ok": True, "result": str(res), "result_latex": L(res), "steps": steps}

# -----------------------------------------------------------------------------
# 2) التفاضل — مع ذكر القواعد
# -----------------------------------------------------------------------------
def rule_name(term, x: Symbol) -> str:
    if term.is_Pow and term.base == x:
        return "قاعدة القوة: d(x^n)/dx = n x^{n-1}"
    if term.is_Mul and any(t.has(x) for t in term.args):
        return "قاعدة الضرب: (uv)' = u'v + uv'"
    if term.is_Add:
        return "قاعدة الجمع: (u+v)' = u' + v'"
    if term.func in (sin, cos, tan, exp, log, sqrt):
        return f"قاعدة مشتقة {term.func.__name__}"
    return "قواعد عامة + تبسيط"

def do_derivative(text: str) -> Dict[str, Any]:
    expr = parse(text)
    x = choose_symbol(expr)
    steps: List[Dict[str, str]] = [step("الدالة", f"$f({L(x)})={L(expr)}$")]

    parts = list(expr.as_ordered_terms()) if expr.is_Add else [expr]
    for t in parts:
        d_t = diff(t, x)
        steps.append(step("اشتقاق حد", f"${L(t)} \\Rightarrow {L(d_t)}$ — {rule_name(t, x)}"))

    d = simplify(diff(expr, x))
    steps.append(step("جمع وتبسيط", f"$f'({L(x)})={L(d)}$"))
    return {"mode": "derivative", "ok": True, "result": str(d), "result_latex": L(d), "steps": steps}

# -----------------------------------------------------------------------------
# 3) التكامل — توحيد مقامات + تجزئة جزئية عند اللزوم
# -----------------------------------------------------------------------------
def do_integral(text: str) -> Dict[str, Any]:
    expr = parse(text)
    x = choose_symbol(expr)
    steps: List[Dict[str, str]] = [step("الدالة", f"$f({L(x)})={L(expr)}$")]

    t = together(expr)
    if t != expr:
        steps.append(step("توحيد المقامات", f"${L(expr)} \\Rightarrow {L(t)}$"))
        expr = t

    if expr.is_rational_function(x):
        ap = apart(expr, x)
        if ap != expr:
            steps.append(step("تجزئة جزئية", f"${L(expr)} \\Rightarrow {L(ap)}$"))
            expr = ap

    if expr.is_Add:
        for term in expr.as_ordered_terms():
            steps.append(step("تكامل حد", f"$\\int {L(term)}\\,dx$"))
    else:
        steps.append(step("التكامل", f"$\\int {L(expr)}\\,dx$"))

    F = simplify(integrate(expr, x))
    steps.append(step("النتيجة", f"$\\int {L(expr)}\\,dx = {L(F)} + C$"))
    return {"mode": "integral", "ok": True, "result": str(F), "result_latex": L(F) + " + C", "steps": steps}

# -----------------------------------------------------------------------------
# 4) المعادلات والأنظمة — مع تتبّع صفّي مفصل
# -----------------------------------------------------------------------------
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

# تتبّع Gauss-Jordan خطوة بخطوة (RREF/معكوس)
def _latexM(M):
    return L(Matrix(M))

def rref_with_steps(M: Matrix):
    M = Matrix(M)
    steps = [step("بداية", f"${_latexM(M)}$")]
    r = c = 0
    rows, cols = M.rows, M.cols
    while r < rows and c < cols:
        pivot = None
        for i in range(r, rows):
            if M[i, c] != 0:
                pivot = i
                break
        if pivot is None:
            c += 1
            continue
        if pivot != r:
            M.row_swap(r, pivot)
            steps.append(step("تبديل صفوف", f"R{r+1} ↔ R{pivot+1}<br/>${_latexM(M)}$"))

        piv = M[r, c]
        if piv != 1:
            M.row_op(r, lambda v, _: v / piv)
            steps.append(step("تطبيع محور", f"R{r+1} ← R{r+1}/{L(piv)}<br/>${_latexM(M)}$"))

        for i in range(rows):
            if i == r: 
                continue
            f = M[i, c]
            if f != 0:
                M.row_op(i, lambda v, j: v - f * M[r, j])
                steps.append(step("تصفير عمود", f"R{i+1} ← R{i+1} − ({L(f)})·R{r+1}<br/>${_latexM(M)}$"))

        r += 1; c += 1
        M = Matrix(M.applyfunc(lambda x: x.simplify()))
    return M, steps

def inverse_with_steps(A: Matrix):
    A = Matrix(A)
    if A.rows != A.cols:
        return None, [step("تحقق", "لا يوجد معكوس لمصفوفة غير مربعة")]
    Aug = A.row_join(eye(A.rows))
    steps = [step("تهيئة", f"$[A|I]={_latexM(Aug)}$")]
    RREF, s2 = rref_with_steps(Aug)
    steps += s2
    left = RREF[:, :A.rows]
    right = RREF[:, A.rows:]
    if left != eye(A.rows):
        steps.append(step("نتيجة", "لم نصل إلى I على اليسار ⇒ لا يوجد معكوس"))
        return None, steps
    steps.append(step("استخراج", f"$A^{{-1}}={_latexM(right)}$"))
    return right, steps

def do_solve(text: str) -> Dict[str, Any]:
    steps: List[Dict[str, str]] = []
    eqs = parse_equations(text)

    # نظام خطي
    if len(eqs) > 1:
        syms = symbols_of(eqs)
        rows = []; rhs = []
        for LHS, RHS in eqs:
            expr = simplify(LHS - RHS)
            row = [expr.expand().coeff(s) for s in syms]
            const = -expr.subs({s: 0 for s in syms})
            rows.append(row); rhs.append([const])
        A = Matrix(rows); b = Matrix(rhs)
        steps.append(step("صياغة مصفوفية", f"نكتب النظام $A X = b$ حيث $X=[{', '.join(map(str, syms))}]^T$"))
        steps.append(step("A و b", f"$A={L(A)},\\quad b={L(b)}$"))
        Aug = A.row_join(b)
        steps.append(step("المصفوفة المُعزَّزة", f"$[A|b]={L(Aug)}$"))
        R, s2 = rref_with_steps(Aug)
        steps += s2
        steps.append(step("RREF", f"${L(R)}$"))
        from sympy import linsolve
        sol = linsolve((A, b))
        steps.append(step("استخراج الحل", f"${L(sol)}$"))
        return {"mode": "solve", "ok": True, "result": str(sol), "result_latex": L(sol), "steps": steps}

    # معادلة واحدة
    LHS, RHS = eqs[0]
    steps.append(step("المعادلة", f"${L(LHS)}={L(RHS)}$"))
    expr = simplify(LHS - RHS)
    steps.append(step("نقل الحدود", f"${L(LHS)}-{L(RHS)}=0 \\Rightarrow {L(expr)}=0$"))
    x = choose_symbol(expr)

    try:
        P = Poly(expr, x)
        deg = P.degree()
        steps.append(step("درجة كثير الحدود", f"${deg}$"))
        if deg == 1:
            sol = P.solve(x)
            steps.append(step("حل خطي", f"ترتيب ثم قسمة على معامل {L(x)} ⇒ {L(sol)}"))
        elif deg == 2:
            D = discriminant(P)
            steps.append(step("المميز", f"$\\Delta = {L(D)}$"))
            steps.append(step("الصيغة التربيعية", "$x=\\frac{-b\\pm\\sqrt{\\Delta}}{2a}$"))
            sol = P.solve(x)
        elif deg in (3, 4):
            steps.append(step("حل تحليلي", "استخدام صيغ التكعيبي/الرباعي"))
            sol = P.solve(x)
        else:
            roots = [c for c in nroots(P)]
            steps.append(step("حل عددي", "للدرجات ≥5 نستخدم nroots"))
            return {"mode": "solve", "ok": True, "result": str(roots), "result_latex": L(roots), "steps": steps}
        return {"mode": "solve", "ok": True, "result": str(sol), "result_latex": L(sol), "steps": steps}
    except Exception:
        sol = solveset(expr, x)
        return {"mode": "solve", "ok": True, "result": str(sol), "result_latex": L(sol), "steps": steps}

# -----------------------------------------------------------------------------
# 5) المصفوفات — det/inv/rref/eigen/diag/jordan (مع خطوات)
# -----------------------------------------------------------------------------
def parse_matrix_like(s: str) -> Matrix:
    s = normalize_text(s)
    if s.startswith("Matrix("):
        return parse(s)
    if s.startswith("[[") and s.endswith("]]"):
        return parse(f"Matrix({s})")
    rows = [r.strip() for r in re.split(r";|\n", s) if r.strip()]
    data = []
    for r in rows:
        data.append([parse(c) for c in re.split(r"[,\s]+", r) if c])
    return Matrix(data)

def do_matrix(text: str) -> Dict[str, Any]:
    s = normalize_text(text)
    steps: List[Dict[str, str]] = []
    low = s.lower()

    if low.startswith("rref("):
        A = parse_matrix_like(re.sub(r"rref\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        R, s2 = rref_with_steps(A)
        steps += s2
        steps.append(step("RREF", f"${L(R)}$"))
        return {"mode": "matrix", "ok": True, "result": str(R), "result_latex": L(R), "steps": steps}

    if low.startswith("det("):
        A = parse_matrix_like(s[4:-1])
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        d = A.det()
        steps.append(step("المحدد", f"$\\det(A)={L(d)}$"))
        return {"mode": "matrix", "ok": True, "result": str(d), "result_latex": L(d), "steps": steps}

    if low.startswith("inv("):
        A = parse_matrix_like(s[4:-1])
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        Ainv, s2 = inverse_with_steps(A)
        steps += s2
        if Ainv is None:
            return {"mode": "matrix", "ok": True, "result": "non-invertible", "result_latex": "", "steps": steps}
        return {"mode": "matrix", "ok": True, "result": str(Ainv), "result_latex": L(Ainv), "steps": steps}

    if "eigenvals" in low:
        A = parse_matrix_like(re.sub(r"eigenvals\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        steps.append(step("المعادلة المميِّزة", "$\\det(A-\\lambda I)=0$"))
        ev = A.eigenvals()
        return {"mode": "matrix", "ok": True, "result": str(ev), "result_latex": L(ev), "steps": steps}

    if "eigenvects" in low:
        A = parse_matrix_like(re.sub(r"eigenvects?\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        steps.append(step("حل (A-λI)v=0", "نستخرج الفضاءات الذاتية"))
        ev = A.eigenvects()
        return {"mode": "matrix", "ok": True, "result": str(ev), "result_latex": L(ev), "steps": steps}

    if low.startswith(("diag(", "diagonalize(")):
        A = parse_matrix_like(re.sub(r"diag(?:onalize)?\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        try:
            P, D = A.diagonalize()
            steps.append(step("تشابه", "$A=PDP^{-1}$"))
            steps.append(step("P", f"$P={L(P)}$"))
            steps.append(step("D", f"$D={L(D)}$"))
            return {"mode": "matrix", "ok": True, "result": "diagonalized", "result_latex": f"P={L(P)},\\ D={L(D)}", "steps": steps}
        except Exception:
            steps.append(step("غير قطري", "A غير قابلة للتقطيع قطريًا"))
            return {"mode": "matrix", "ok": True, "result": "not diagonalizable", "result_latex": "", "steps": steps}

    if low.startswith("jordan("):
        A = parse_matrix_like(re.sub(r"jordan\s*\(|\)$", "", s, flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        J, P = A.jordan_normal_form()
        steps.append(step("شكل جوردان", f"$J={L(J)}$"))
        return {"mode": "matrix", "ok": True, "result": "jordan", "result_latex": L(J), "steps": steps}

    # إدخال مصفوفة خام: أعرض معلومات + RREF مختصر
    A = parse_matrix_like(s)
    steps.append(step("المصفوفة", f"$A={L(A)}$"))
    R, s2 = rref_with_steps(A)
    steps += s2
    steps.append(step("RREF", f"${L(R)}$"))
    return {"mode": "matrix", "ok": True, "result": f"Matrix {A.shape}", "result_latex": L(R), "steps": steps}

# -----------------------------------------------------------------------------
# كشف الوضع تلقائيًا
# -----------------------------------------------------------------------------
def detect_mode(text: str) -> str:
    t = (text or "").lower().strip()
    if t.startswith("deriv") or t.startswith("مشتق"): return "derivative"
    if t.startswith("integ") or t.startswith("تكامل"): return "integral"
    if any(k in t for k in ["eigen", "det(", "inv(", "rank", "[[", "matrix(", "jordan(", "diag(", "rref("]): return "matrix"
    if ";" in t or "=" in t: return "solve"
    return "evaluate"

# -----------------------------------------------------------------------------
# API
# -----------------------------------------------------------------------------
@app.post("/solve")
async def solve_api(request: Request):
    data = await request.json()
    q: str = normalize_text(data.get("q", ""))
    mode: str = data.get("mode", "auto")

    # اختصارات عربية مباشرة
    if q.startswith("مشتق "):   return do_derivative(q.replace("مشتق ", "", 1))
    if q.startswith("تكامل "):  return do_integral(q.replace("تكامل ", "", 1))
    if not q:
        return JSONResponse({"ok": False, "error": "empty_query"})

    try:
        m = detect_mode(q) if mode == "auto" else mode
        if m == "derivative": out = do_derivative(q)
        elif m == "integral": out = do_integral(q)
        elif m == "matrix":   out = do_matrix(q)
        elif m == "solve":    out = do_solve(q)
        else:                 out = do_evaluate(q)
        out["ok"] = True
        return JSONResponse(out)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Bassam Math Pro"})
