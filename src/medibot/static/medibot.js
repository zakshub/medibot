"use strict";

const elements = {
  characterCount: document.querySelector("#character-count"),
  countryCode: document.querySelector("#country-code"),
  form: document.querySelector("#message-form"),
  healthStatus: document.querySelector("#health-status"),
  lastRequestId: document.querySelector("#last-request-id"),
  lastRoute: document.querySelector("#last-route"),
  locale: document.querySelector("#locale"),
  messageFeed: document.querySelector("#message-feed"),
  messageInput: document.querySelector("#message-input"),
  policyStatus: document.querySelector("#policy-status"),
  readinessReasons: document.querySelector("#readiness-reasons"),
  readyStatus: document.querySelector("#ready-status"),
  refreshStatus: document.querySelector("#refresh-status"),
  requestCard: document.querySelector("#request-card"),
  sendButton: document.querySelector("#send-button"),
  sendLabel: document.querySelector("#send-label"),
  serviceLabel: document.querySelector("#service-label"),
  servicePill: document.querySelector("#service-pill"),
  versionStatus: document.querySelector("#version-status"),
};

function setText(element, value) {
  element.textContent = value;
}

function setStatus(element, value, className) {
  setText(element, value);
  element.classList.remove("status-good", "status-blocked", "status-bad");
  element.classList.add(className);
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function formatReason(reason) {
  return reason.replaceAll("_", " ");
}

async function refreshServiceStatus() {
  elements.refreshStatus.disabled = true;
  try {
    const [healthResponse, readyResponse] = await Promise.all([
      fetch("/v1/health", { headers: { Accept: "application/json" } }),
      fetch("/v1/ready", { headers: { Accept: "application/json" } }),
    ]);
    const health = await readJson(healthResponse);
    const readiness = await readJson(readyResponse);

    if (healthResponse.ok && health) {
      setStatus(elements.healthStatus, "Online", "status-good");
      setText(elements.versionStatus, health.version || "Unknown");
      elements.servicePill.className = "service-pill is-online";
      setText(elements.serviceLabel, "API online");
    } else {
      throw new Error("Health check failed");
    }

    if (readyResponse.ok && readiness) {
      setStatus(elements.readyStatus, "Ready", "status-good");
      setStatus(elements.policyStatus, readiness.policy_version || "Unknown", "status-good");
      elements.readinessReasons.hidden = true;
    } else if (readyResponse.status === 503 && readiness) {
      setStatus(elements.readyStatus, "Locked", "status-blocked");
      setStatus(
        elements.policyStatus,
        readiness.policy_version || "Unapproved",
        "status-blocked",
      );
      const reasons = Array.isArray(readiness.reasons) ? readiness.reasons : [];
      elements.readinessReasons.replaceChildren(
        ...reasons.map((reason) => {
          const item = document.createElement("span");
          item.textContent = `Blocked: ${formatReason(reason)}`;
          return item;
        }),
      );
      elements.readinessReasons.hidden = reasons.length === 0;
    } else {
      setStatus(elements.readyStatus, "Unavailable", "status-bad");
      setStatus(elements.policyStatus, "Unknown", "status-bad");
      elements.readinessReasons.hidden = true;
    }
  } catch {
    setStatus(elements.healthStatus, "Offline", "status-bad");
    setStatus(elements.readyStatus, "Unknown", "status-bad");
    setStatus(elements.policyStatus, "Unknown", "status-bad");
    setText(elements.versionStatus, "Unknown");
    elements.servicePill.className = "service-pill is-offline";
    setText(elements.serviceLabel, "API offline");
    elements.readinessReasons.hidden = true;
  } finally {
    elements.refreshStatus.disabled = false;
  }
}

function createMeta(label, route) {
  const meta = document.createElement("div");
  meta.className = "message-meta";

  const author = document.createElement("span");
  author.textContent = label;
  meta.append(author);

  if (route) {
    const routeTag = document.createElement("span");
    const routeClass = route === "emergency" ? "route-emergency" : `route-${route}`;
    routeTag.className = `route-tag ${routeClass}`;
    routeTag.textContent = formatReason(route);
    meta.append(routeTag);
  }

  return meta;
}

function appendUserMessage(message) {
  const article = document.createElement("article");
  article.className = "message message-user";
  article.append(createMeta("You"));

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const paragraph = document.createElement("p");
  paragraph.textContent = message;
  bubble.append(paragraph);
  article.append(bubble);

  elements.messageFeed.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function appendSources(container, sources) {
  if (!Array.isArray(sources) || sources.length === 0) {
    return;
  }

  const list = document.createElement("ul");
  list.className = "source-list";
  for (const source of sources) {
    if (!source || typeof source.title !== "string") {
      continue;
    }

    const item = document.createElement("li");
    let parsedUrl = null;
    try {
      parsedUrl = new URL(source.url);
    } catch {
      parsedUrl = null;
    }

    if (parsedUrl && ["http:", "https:"].includes(parsedUrl.protocol)) {
      const link = document.createElement("a");
      link.href = parsedUrl.href;
      link.rel = "noreferrer noopener";
      link.target = "_blank";
      link.textContent = source.title;
      item.append(link);
    } else {
      item.textContent = source.title;
    }
    list.append(item);
  }

  if (list.childElementCount > 0) {
    container.append(list);
  }
}

function appendAssistantMessage(payload) {
  const article = document.createElement("article");
  article.className = "message message-assistant";
  article.append(createMeta("Medibot", payload.route || "service_unavailable"));

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const paragraph = document.createElement("p");
  paragraph.textContent = payload.message || "The request could not be completed.";
  bubble.append(paragraph);

  const details = document.createElement("dl");
  details.className = "response-details";
  const rows = [
    ["Current limit", payload.limitations],
    ["Safe next step", payload.next_step],
  ];
  for (const [label, value] of rows) {
    if (!value) {
      continue;
    }
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value;
    row.append(term, detail);
    details.append(row);
  }
  if (details.childElementCount > 0) {
    bubble.append(details);
  }

  appendSources(bubble, payload.sources);
  article.append(bubble);
  elements.messageFeed.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "nearest" });

  if (payload.request_id || payload.route) {
    elements.requestCard.hidden = false;
    setText(elements.lastRoute, formatReason(payload.route || "unknown"));
    setText(elements.lastRequestId, payload.request_id || "Not returned");
  }
}

function normalizeError(payload) {
  const detail = payload && payload.error;
  return {
    limitations: "No medical guidance was produced.",
    message: detail && detail.message ? detail.message : "The service could not process this request.",
    next_step: "Check the message and service status, then try again.",
    request_id: payload && payload.request_id,
    route: "service_unavailable",
    sources: [],
  };
}

async function submitMessage(event) {
  event.preventDefault();
  const message = elements.messageInput.value.trim();
  if (!message) {
    elements.messageInput.focus();
    return;
  }

  appendUserMessage(message);
  elements.messageInput.value = "";
  setText(elements.characterCount, "0 / 4000");
  elements.sendButton.disabled = true;
  setText(elements.sendLabel, "Sending...");

  const payload = {
    locale: elements.locale.value,
    message,
  };
  if (elements.countryCode.value) {
    payload.country_code = elements.countryCode.value;
  }

  try {
    const response = await fetch("/v1/messages", {
      body: JSON.stringify(payload),
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      method: "POST",
    });
    const body = await readJson(response);
    if (body && typeof body.message === "string") {
      appendAssistantMessage(body);
    } else {
      appendAssistantMessage(normalizeError(body));
    }
  } catch {
    appendAssistantMessage({
      limitations: "No medical guidance was produced.",
      message: "The Medibot API is not reachable.",
      next_step: "Check the live system status before retrying.",
      route: "service_unavailable",
      sources: [],
    });
  } finally {
    elements.sendButton.disabled = false;
    setText(elements.sendLabel, "Send message");
    elements.messageInput.focus();
    refreshServiceStatus();
  }
}

elements.messageInput.addEventListener("input", () => {
  setText(elements.characterCount, `${elements.messageInput.value.length} / 4000`);
});
elements.form.addEventListener("submit", submitMessage);
elements.refreshStatus.addEventListener("click", refreshServiceStatus);

refreshServiceStatus();
