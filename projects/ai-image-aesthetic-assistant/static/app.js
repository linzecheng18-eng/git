const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

const fileInput = document.getElementById("fileInput");
const button = document.getElementById("analyzeBtn");
const resetButton = document.getElementById("resetBtn");
const statusText = document.getElementById("status");
const preview = document.getElementById("preview");
const result = document.getElementById("result");
const summary = document.getElementById("summary");
const diagnosis = document.getElementById("diagnosis");
const scores = document.getElementById("scores");

function validateFile(file) {
  if (!file) throw new Error("请先选择图片。");
  if (!ALLOWED_TYPES.has(file.type)) throw new Error("仅支持 JPG、PNG 和 WebP 图片。");
  if (file.size > MAX_BYTES) throw new Error("图片不能超过 10 MiB。");
}

function releasePreview() {
  if (preview.dataset.url) {
    URL.revokeObjectURL(preview.dataset.url);
    delete preview.dataset.url;
  }
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  try {
    validateFile(file);
    releasePreview();
    const url = URL.createObjectURL(file);
    preview.dataset.url = url;
    preview.src = url;
    preview.hidden = false;
    statusText.textContent = "";
  } catch (error) {
    fileInput.value = "";
    statusText.textContent = error.message;
  }
});

function renderResult(payload) {
  summary.textContent = payload.summary;

  const issueCards = payload.issues.map((issue, index) => {
    const card = document.createElement("article");
    const title = document.createElement("h4");
    const advice = document.createElement("p");
    title.textContent = issue;
    advice.textContent = payload.suggestions[index];
    card.append(title, advice);
    return card;
  });
  diagnosis.replaceChildren(...issueCards);

  const scoreItems = Object.entries(payload.scores).map(([name, score]) => {
    const item = document.createElement("p");
    const label = document.createElement("span");
    const value = document.createElement("strong");
    label.textContent = name;
    value.textContent = `${score}/10`;
    item.append(label, value);
    return item;
  });
  scores.replaceChildren(...scoreItems);
  result.hidden = false;
}

button.addEventListener("click", async () => {
  if (button.disabled) return;

  const file = fileInput.files[0];
  const imageType = document.querySelector('input[name="imageType"]:checked');
  try {
    validateFile(file);
    if (!imageType) throw new Error("请选择图片类型。");
  } catch (error) {
    statusText.textContent = error.message;
    return;
  }

  button.disabled = true;
  button.textContent = "评测中…";
  statusText.textContent = "正在评测，请稍候。";

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {
        "Content-Type": file.type,
        "X-Filename": file.name,
        "X-Image-Type": imageType.value,
      },
      body: await file.arrayBuffer(),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error.message);
    }
    renderResult(payload);
    statusText.textContent = "评测完成。";
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    statusText.textContent = error instanceof TypeError
      ? "网络连接失败，请检查后重试。"
      : error.message;
  } finally {
    button.disabled = false;
    button.textContent = "开始评测";
  }
});

resetButton.addEventListener("click", () => {
  releasePreview();
  fileInput.value = "";
  preview.removeAttribute("src");
  preview.hidden = true;
  result.hidden = true;
  summary.textContent = "";
  diagnosis.replaceChildren();
  scores.replaceChildren();
  statusText.textContent = "";
  document.querySelectorAll('input[name="imageType"]').forEach((control) => {
    control.checked = false;
  });
  document.getElementById("imageTypeGroup").scrollIntoView({ behavior: "smooth" });
});
