const modeCards = document.querySelectorAll(".mode-card");
const progressSteps = document.querySelectorAll(".progress-step");
const sideLinks = document.querySelectorAll(".side-link");
const fileInput = document.getElementById("fileInput");
const preview = document.getElementById("preview");
const analyzeButton = document.getElementById("analyzeBtn");
const resetButton = document.getElementById("resetBtn");
const statusText = document.getElementById("status");
const resultPreview = document.getElementById("resultPreview");
const resultTitle = document.getElementById("resultTitle");
const summary = document.getElementById("summary");
const scores = document.getElementById("scores");
const diagnosis = document.getElementById("diagnosis");
const storyOutput = document.getElementById("storyOutput");
const backgroundNotes = document.getElementById("backgroundNotes");
const imageTypeControls = document.querySelectorAll('input[name="imageType"]');

const modeCopy = {
  story: {
    status: "图像故事模式：适合整理人物、地点、情绪和可发布文案。",
    summary: "这张图会被整理成一段更有人情味的视觉故事，重点关注画面信息、情绪氛围和表达场景。",
    tags: ["故事线索", "情绪共鸣", "可发布文案", "人物正向表达"],
  },
  aesthetic: {
    status: "审美评测模式：适合优化构图、色彩、主体和视觉层次。",
    summary: "这张图会被拆解为审美评分和修改建议，重点关注画面是否清晰、协调、有传播力。",
    tags: ["构图", "色彩", "主体", "视觉层次"],
  },
  identity: {
    status: "人物地点识别：适合结合你提供的信息整理照片背后的故事。",
    summary: "这张图会先提取可观察线索，再结合背景信息整理人物、地点和事件，不做武断身份判断。",
    tags: ["人物线索", "地点线索", "隐私提醒", "正向评价"],
  },
};

let activeMode = "story";

function setActiveMode(mode) {
  activeMode = mode;
  modeCards.forEach((card) => {
    const isActive = card.dataset.mode === mode;
    card.classList.toggle("active", isActive);
    card.setAttribute("aria-pressed", String(isActive));
  });
  statusText.textContent = modeCopy[mode].status;
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

function renderScores() {
  const items = [
    ["构图", "8.2"],
    ["色彩", "8.6"],
    ["主体", "8.0"],
    ["清晰度", "8.4"],
    ["故事感", "9.0"],
  ];
  const nodes = items.map(([name, score]) => {
    const item = document.createElement("p");
    const label = document.createElement("span");
    const value = document.createElement("strong");
    label.textContent = name;
    value.textContent = `${score}/10`;
    item.append(label, value);
    return item;
  });
  scores.replaceChildren(...nodes);
}

function renderTags(tags) {
  const nodes = tags.map((tag) => {
    const item = document.createElement("span");
    item.textContent = tag;
    return item;
  });
  storyOutput.replaceChildren(...nodes);
}

function renderDiagnosis(hasNotes) {
  const messages = [
    "人物照片优先评价氛围、姿态和表达感，不评价长相好坏。",
    hasNotes ? "已结合背景信息生成更贴近真实语境的故事方向。" : "建议补充人物、地点、时间或用途，减少 AI 纯猜测。",
    "发布前注意隐私、肖像授权和具体地点暴露。",
  ];
  const nodes = messages.map((message) => {
    const item = document.createElement("article");
    item.textContent = message;
    return item;
  });
  diagnosis.replaceChildren(...nodes);
}

function animateProgress() {
  progressSteps.forEach((step) => {
    step.classList.remove("is-active");
  });
  progressSteps.forEach((step, index) => {
    window.setTimeout(() => {
      progressSteps.forEach((item) => item.classList.remove("is-active"));
      step.classList.add("is-active");
    }, index * 260);
  });
}

function renderDemoResult() {
  const hasNotes = backgroundNotes.value.trim().length > 0;
  const copy = modeCopy[activeMode];
  summary.textContent = copy.summary;
  renderTags(copy.tags);
  renderScores();
  renderDiagnosis(hasNotes);
  resultPreview.hidden = false;
  resultTitle.focus();
  resultPreview.scrollIntoView({ behavior: "smooth", block: "start" });
}

modeCards.forEach((card) => {
  card.addEventListener("click", () => {
    setActiveMode(card.dataset.mode);
  });
});

sideLinks.forEach((link) => {
  link.addEventListener("click", () => {
    sideLinks.forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  clearPreview();
  if (!file) {
    statusText.textContent = modeCopy[activeMode].status;
    return;
  }
  const url = URL.createObjectURL(file);
  preview.dataset.url = url;
  preview.src = url;
  preview.hidden = false;
  statusText.textContent = "图片已载入。当前仍是静态原型，只展示交互和结果样式。";
});

analyzeButton.addEventListener("click", () => {
  animateProgress();
  window.setTimeout(renderDemoResult, 980);
});

resetButton.addEventListener("click", () => {
  clearPreview();
  fileInput.value = "";
  backgroundNotes.value = "";
  resultPreview.hidden = true;
  statusText.textContent = modeCopy[activeMode].status;
  imageTypeControls.forEach((control) => {
    control.checked = false;
  });
  fileInput.focus();
});

setActiveMode(activeMode);
