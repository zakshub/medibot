"use strict";

const byId = (id) => document.getElementById(id);
const activityLog = byId("activity-log");

function operatorHeaders() {
  const key = byId("operator-key").value.trim();
  return key ? {"X-Operator-Key": key} : {};
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...operatorHeaders(),
    ...(options.headers || {})
  };
  const response = await fetch(path, {...options, headers});
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Request failed";
    throw new Error(detail);
  }
  return payload;
}

function log(message, kind = "info") {
  const item = document.createElement("li");
  const stamp = document.createElement("time");
  const text = document.createElement("span");
  stamp.dateTime = new Date().toISOString();
  stamp.textContent = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });
  text.textContent = kind.toUpperCase() + " / " + message;
  item.append(stamp, text);
  activityLog.prepend(item);
  while (activityLog.children.length > 10) {
    activityLog.lastElementChild.remove();
  }
}

function setBusy(button, busy) {
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
}

function commaValues(id) {
  return byId(id).value
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

async function loadStatus() {
  try {
    const data = await api("/v1/video/status", {method: "GET"});
    byId("service-state").textContent = data.status.replaceAll("_", " ").toUpperCase();
    byId("implementation-percent").textContent = String(data.implementation_percent) + "%";
    byId("video-count").textContent = String(data.counts.videos);
    byId("insight-count").textContent = String(data.counts.insights);
    byId("decision-count").textContent = String(data.counts.decisions);
    byId("production-state").textContent = data.production_ready ? "READY" : "LOCKED";
    log(
      "Status refreshed. " + data.counts.videos + " videos, " +
      data.counts.insights + " insights."
    );
  } catch (error) {
    byId("service-state").textContent = "OFFLINE";
    log(error.message, "error");
  }
}

function makeCell(value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  return cell;
}

async function approve(candidateId) {
  const reviewId = window.prompt("Medical review ID");
  const reviewer = window.prompt("Reviewer name");
  if (!reviewId || !reviewer) {
    log("Approval cancelled.", "warn");
    return;
  }
  await api(
    "/v1/video/videos/" + encodeURIComponent(candidateId) + "/approve",
    {
      method: "POST",
      body: JSON.stringify({
        medical_review_id: reviewId,
        approved_by: reviewer
      })
    }
  );
  log(candidateId + " approved for scheduling.");
  await loadInventory();
  await loadStatus();
}

async function loadInventory() {
  try {
    const data = await api("/v1/video/videos", {method: "GET"});
    const body = byId("inventory-body");
    const rows = [];
    for (const video of data.videos) {
      const row = document.createElement("tr");
      const idCell = makeCell("");
      const code = document.createElement("code");
      code.textContent = video.candidate_id;
      idCell.append(code);

      const statusCell = makeCell("");
      const pill = document.createElement("span");
      pill.className = "status-pill";
      pill.textContent = video.status;
      statusCell.append(pill);

      const action = makeCell("");
      if (video.status === "rendered") {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "APPROVE";
        button.addEventListener("click", () => {
          approve(video.candidate_id).catch((error) => log(error.message, "error"));
        });
        action.append(button);
      } else {
        action.textContent = "-";
      }

      row.append(
        idCell,
        makeCell(video.topic),
        makeCell((video.style_tags || []).join(", ") || "default"),
        statusCell,
        action
      );
      rows.push(row);
    }

    if (!rows.length) {
      const row = document.createElement("tr");
      const cell = makeCell("No videos yet. Import a dataset or generate a preview.");
      cell.colSpan = 5;
      row.append(cell);
      rows.push(row);
    }
    body.replaceChildren(...rows);
  } catch (error) {
    log(error.message, "error");
  }
}

byId("domain-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  setBusy(button, true);
  try {
    const result = await api("/v1/video/domain", {
      method: "PUT",
      body: JSON.stringify({
        name: byId("domain-name").value,
        allowed_topics: commaValues("allowed-topics"),
        allowed_keywords: commaValues("allowed-keywords"),
        blocked_keywords: commaValues("blocked-keywords")
      })
    });
    log("Domain profile " + result.profile + " saved.");
    await loadStatus();
  } catch (error) {
    log(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

byId("dataset-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  setBusy(button, true);
  try {
    const manifest = JSON.parse(byId("dataset-json").value);
    const result = await api("/v1/video/dataset", {
      method: "POST",
      body: JSON.stringify(manifest)
    });
    log(String(result.imported) + " dataset video(s) imported.");
    await Promise.all([loadInventory(), loadStatus()]);
  } catch (error) {
    log(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

byId("preview-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  setBusy(button, true);
  log("Rendering local vertical MP4. This can take a few seconds.");
  try {
    const result = await api("/v1/video/previews", {
      method: "POST",
      body: JSON.stringify({
        profile_name: byId("preview-profile").value,
        content_id: byId("content-id").value,
        topic: byId("preview-topic").value,
        title: byId("preview-title").value,
        hook: byId("preview-hook").value,
        facts: [{
          text: byId("fact-text").value,
          source_url: byId("fact-source").value,
          approval_id: byId("fact-approval").value
        }],
        call_to_action: byId("preview-cta").value,
        target_duration_seconds: Number(byId("preview-duration").value),
        style: byId("preview-style").value,
        medical_review_approved: byId("medical-approved").checked
      })
    });
    byId("preview-output").hidden = false;
    byId("preview-video").src = result.video_url;
    byId("storyboard-link").href = result.storyboard_url;
    byId("preview-meta").textContent =
      String(Math.round(result.size_bytes / 1024)) + " KB / AUDIO: " +
      (result.has_audio ? "YES" : "NO");
    byId("preview-badge").textContent =
      result.publishable ? "PUBLISHABLE" : "PREVIEW ONLY";
    log(
      result.content_id + " MP4 generated. " +
      result.blocking_reasons.join(", ") + "."
    );
    await Promise.all([loadInventory(), loadStatus()]);
  } catch (error) {
    log(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

byId("schedule-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  setBusy(button, true);
  try {
    const result = await api("/v1/video/schedule/recommend", {
      method: "POST",
      body: JSON.stringify({
        profile_name: byId("schedule-profile").value,
        current_posts_per_day: Number(byId("daily-target").value),
        recent_performance: []
      })
    });
    const lines = [
      "RESULT: " + result.reason,
      "DAILY TARGET: " + result.frequency.posts_per_day,
      "FREQUENCY LOGIC: " + result.frequency.reason
    ];
    if (result.strategy) {
      lines.push(
        "STRATEGY: " + result.strategy.topic + " / " +
        result.strategy.posting_hour + ":00 / " + result.strategy.style
      );
      lines.push(
        "MODE: " + result.strategy.mode + " / CONFIDENCE: " +
        Math.round(result.strategy.confidence * 100) + "%"
      );
    }
    if (result.schedule) {
      lines.push(
        "RESERVED: " + result.schedule.candidate_id +
        " @ " + result.schedule.publish_at
      );
    }
    byId("schedule-result").textContent = lines.join("\n");
    log("Schedule decision: " + result.reason + ".");
    await Promise.all([loadInventory(), loadStatus()]);
  } catch (error) {
    log(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

byId("refresh-button").addEventListener("click", () => {
  Promise.all([loadStatus(), loadInventory()]);
});

Promise.all([loadStatus(), loadInventory()]);
