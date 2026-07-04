const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

const fileInput = document.getElementById("fileInput");
const button = document.getElementById("analyzeBtn");
const resetButton = document.getElementById("resetBtn");
const statusText = document.getElementById("status");
const preview = document.getElementById("preview");
const result = document.getElementById("result");
const resultTitle = document.getElementById("resultTitle");
const summary = document.getElementById("summary");
const diagnosis = document.getElementById("diagnosis");
const scores = document.getElementById("scores");
const imageTypeControls = document.querySelectorAll('input[name="imageType"]');

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

function clearPreview() {
  releasePreview();
  preview.removeAttribute("src");
  preview.hidden = true;
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  try {
    validateFile(file);
  } catch (error) {
    fileInput.value = "";
    clearPreview();
    statusText.textContent = error.message;
    return;
  }
  clearPreview();
  try {
    const url = URL.createObjectURL(file);
    preview.dataset.url = url;
    preview.src = url;
    preview.hidden = false;
    statusText.textContent = "";
  } catch {
    fileInput.value = "";
    clearPreview();
    statusText.textContent = "无法预览图片，请重新选择。";
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

async function parseJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function isValidPayload(payload) {
  return payload !== null
    && typeof payload === "object"
    && typeof payload.summary === "string"
    && Array.isArray(payload.issues)
    && payload.issues.every((issue) => typeof issue === "string")
    && Array.isArray(payload.suggestions)
    && payload.suggestions.length === payload.issues.length
    && payload.suggestions.every((suggestion) => typeof suggestion === "string")
    && payload.scores !== null
    && typeof payload.scores === "object"
    && !Array.isArray(payload.scores)
    && Object.values(payload.scores).every((score) => typeof score === "number");
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
  fileInput.disabled = true;
  imageTypeControls.forEach((control) => {
    control.disabled = true;
  });
  button.textContent = "评测中…";
  statusText.textContent = "正在评测，请稍候。";

  try {
    let body;
    try {
      body = await file.arrayBuffer();
    } catch {
      statusText.textContent = "无法读取图片，请重新选择后重试。";
      return;
    }

    let response;
    try {
      response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": file.type,
          "X-Filename": encodeURIComponent(file.name),
          "X-Image-Type": imageType.value,
        },
        body,
      });
    } catch {
      statusText.textContent = "网络连接失败，请检查后重试。";
      return;
    }

    const payload = await parseJsonResponse(response);
    if (payload === null) {
      statusText.textContent = "服务器返回的数据异常，请稍后重试。";
      return;
    }
    if (!response.ok) {
      const message = payload?.error?.message;
      statusText.textContent = typeof message === "string" && message.trim()
        ? message
        : "评测失败，请稍后重试。";
      return;
    }
    if (!isValidPayload(payload)) {
      statusText.textContent = "服务器返回的数据异常，请稍后重试。";
      return;
    }
    renderResult(payload);
    statusText.textContent = "评测完成。";
    resultTitle.focus();
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  } finally {
    button.disabled = false;
    fileInput.disabled = false;
    imageTypeControls.forEach((control) => {
      control.disabled = false;
    });
    button.textContent = "开始评测";
  }
});

resetButton.addEventListener("click", () => {
  clearPreview();
  fileInput.value = "";
  result.hidden = true;
  summary.textContent = "";
  diagnosis.replaceChildren();
  scores.replaceChildren();
  statusText.textContent = "";
  imageTypeControls.forEach((control) => {
    control.checked = false;
  });
  fileInput.focus();
});
