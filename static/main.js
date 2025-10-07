async function postJSON(url, data) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  });
  return r.json();
}

const q = document.getElementById("q");
const btn = document.getElementById("solveBtn");
const modeSel = document.getElementById("mode");
const stepsDiv = document.getElementById("steps");
const resultDiv = document.getElementById("result");

btn.onclick = async () => {
  const query = q.value.trim();
  if (!query) return;
  stepsDiv.innerHTML = "<p>⏳ جاري الحل...</p>";
  resultDiv.textContent = "";
  const data = await postJSON("/solve", { q: query, mode: modeSel.value });
  if (!data.ok) {
    stepsDiv.innerHTML = `<p style='color:red'>❌ ${data.error}</p>`;
    return;
  }
  let html = "";
  for (const s of data.steps || []) {
    html += `<div class='step'><b>${s.title}:</b><br/>${s.content}</div>`;
  }
  stepsDiv.innerHTML = html;
  resultDiv.innerHTML = `<h3>النتيجة:</h3><p>${data.result}</p>`;
};
