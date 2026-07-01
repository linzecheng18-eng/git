const fileInput = document.getElementById("fileInput");
const button = document.getElementById("analyzeBtn");
const statusText = document.getElementById("status");
const result = document.getElementById("result");

button.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) {
    statusText.textContent = "请先选择图片";
    return;
  }
  const imageType = document.querySelector('input[name="imageType"]:checked');
  if (!imageType) {
    statusText.textContent = "请选择图片类型";
    return;
  }

  statusText.textContent = "分析中...";
  result.innerHTML = "";

  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: {
      "X-Filename": file.name,
      "X-Image-Type": imageType.value,
      "Content-Type": file.type || "application/octet-stream",
    },
    body: await file.arrayBuffer(),
  });

  const payload = await response.json();
  statusText.textContent = "分析完成";
  result.innerHTML = `
    <pre>${JSON.stringify(payload.scores, null, 2)}</pre>
    <p>${payload.summary}</p>
    <ul>${payload.issues.map((item) => `<li>${item}</li>`).join("")}</ul>
  `;
});

