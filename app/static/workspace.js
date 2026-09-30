"use strict";

const $ = (id) => document.getElementById(id);
const t = () => translations[language];
const active = new Set(["queued", "downloading", "processing"]);
const providerNames = {
  youtube: "YouTube",
  facebook: "Facebook",
  instagram: "Instagram",
};
const cards = new Map();
const pending = new Set();
let authPending = false;
let language = "cs",
  config = null,
  jobs = [],
  submitting = false,
  lastError = null;
let filter = "all",
  lastAnnouncement = "",
  clockOffset = 0,
  cooldown = 0;
let sessionPromise = null,
  sessionUpdated = 0,
  pollPromise = null,
  pollTimer,
  failures = 0;
let revision = 0,
  refreshSequence = 0,
  submission = null;
let preferences = { kind: "mp4", mp4: 720, mp3: 192 };
try {
  language = localStorage.getItem("ytd-language") === "en" ? "en" : "cs";
  const saved = JSON.parse(localStorage.getItem("ytd-preferences"));
  if (saved) {
    if (["mp3", "mp4"].includes(saved.kind)) preferences.kind = saved.kind;
    for (const kind of ["mp3", "mp4"])
      if (
        (kind === "mp3" ? [128, 192, 320] : [360, 720, 1080]).includes(
          saved[kind],
        )
      )
        preferences[kind] = saved[kind];
  }
} catch {
  /* Preferences are optional; never store source URLs or history. */
}

function now() {
  return Date.now() / 1000 + clockOffset;
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function button(text, action, className = "job-action") {
  const node = element("button", className, text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function errorMessage(code) {
  return t().errors[code] || t().errors.network;
}
function showError(code) {
  lastError = code;
  $("form-error").textContent =
    code === "clipboard" ? t().clipboard : errorMessage(code);
  if (cooldown > now())
    $("form-error").textContent += ` ${t().wait(Math.ceil(cooldown - now()))}`;
  $("form-error").hidden = false;
}
function clearError() {
  lastError = null;
  $("form-error").hidden = true;
}
function updateSource() {
  let provider = null;
  try {
    const host = new URL($("url").value.trim()).hostname;
    if (
      [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
      ].includes(host)
    )
      provider = "youtube";
    if (
      [
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "mbasic.facebook.com",
        "fb.watch",
      ].includes(host)
    )
      provider = "facebook";
    if (["instagram.com", "www.instagram.com"].includes(host))
      provider = "instagram";
  } catch {
    /* An incomplete input keeps the neutral hint. */
  }
  $("source-status").textContent = provider
    ? t().sourceDetected(providerNames[provider])
    : "";
  document
    .querySelectorAll("[data-provider]")
    .forEach((badge) =>
      badge.classList.toggle("detected", badge.dataset.provider === provider),
    );
}
function savePreferences() {
  try {
    localStorage.setItem("ytd-preferences", JSON.stringify(preferences));
  } catch {
    /* Optional. */
  }
}
function qualityOptions() {
  const audio = preferences.kind === "mp3";
  const values = audio
    ? [128, 192, 320]
    : [360, 720, 1080].filter(
        (value) => value <= (config?.max_quality || 1080),
      );
  if (!values.includes(preferences[preferences.kind]))
    preferences[preferences.kind] = values.at(-1);
  document.querySelector(`[name="kind"][value="${preferences.kind}"]`).checked =
    true;
  $("quality").replaceChildren(
    ...values.map((value) => {
      const option = element("option", "", `${value}${audio ? " kbps" : "p"}`);
      option.value = value;
      option.selected = value === preferences[preferences.kind];
      return option;
    }),
  );
}
function setSubmit() {
  const quotaBlocked =
    config?.quota?.remaining === 0 && config.quota.resets_at > now();
  $("submit").disabled =
    submitting ||
    !config?.ready ||
    quotaBlocked ||
    cooldown > now() ||
    (config?.login_required && !config.account);
  $("submit").querySelector("span").textContent = submitting
    ? t().submitting
    : t().submit;
}
async function api(path, options = {}, recover = true) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 25000);
  let response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      cache: "no-store",
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "yt-downloader",
        ...options.headers,
      },
    });
    if (response.status === 401 && recover && path !== "/api/session") {
      const wasAccount = Boolean(config?.account);
      await loadSession();
      if (
        wasAccount &&
        !config.account &&
        options.method &&
        options.method !== "HEAD"
      )
        throw new Error("session_required");
      return api(path, options, false);
    }
    if (!response.ok) {
      if (options.method === "HEAD" && [404, 410].includes(response.status))
        throw new Error("file_expired");
      const data = await response.json().catch(() => ({}));
      const retry = Number(response.headers.get("Retry-After"));
      if (response.status === 429 && Number.isFinite(retry) && retry > 0)
        cooldown = now() + retry;
      throw new Error(
        typeof data.detail === "string" ? data.detail : "network",
      );
    }
    return response.status === 204 || options.method === "HEAD"
      ? null
      : await response.json();
  } catch (error) {
    if (error.name === "AbortError" || error instanceof TypeError)
      throw new Error("network");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
async function loadSession() {
  if (sessionPromise) return sessionPromise;
  sessionPromise = (async () => {
    const next = await api("/api/session");
    if (config?.account && !next.account) {
      jobs = [];
      revision++;
    }
    config = next;
    if (Number.isFinite(next.server_time))
      clockOffset = next.server_time - Date.now() / 1000;
    sessionUpdated = Date.now();
    qualityOptions();
    setLanguage();
  })();
  try {
    await sessionPromise;
  } finally {
    sessionPromise = null;
  }
}
function setLanguage() {
  document.documentElement.lang = language;
  $("language").value = language;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t()[node.dataset.i18n];
  });
  document
    .querySelectorAll(".dialog-close")
    .forEach((node) => node.setAttribute("aria-label", t().close));
  $("job-filters").setAttribute("aria-label", t().filterLabel);
  $("budget-progress").setAttribute("aria-label", t().accountLimits);
  if (config) {
    $("limits").textContent = t().limits(
      Math.round(config.max_duration_seconds / 60),
      Math.round(config.max_file_bytes / 1024 ** 2),
    );
    $("retention").textContent = t().retention(
      Math.round(config.retention_seconds / 60),
    );
    $("session-note").textContent = config.account
      ? t().accountLibrary
      : t().sessionNote;
    $("runtime-notice").hidden = config.ready;
  }
  if (lastError) showError(lastError);
  renderAccount();
  renderBudget();
  updateSource();
  setSubmit();
  renderJobs();
}
function renderBudget() {
  const quota = config?.quota;
  $("budget").hidden = !quota;
  if (!quota) return;
  $("budget-title").textContent = t()[config.tier] || t().guest;
  $("budget-remaining").textContent = t().remaining(
    quota.remaining,
    quota.limit,
  );
  $("budget-progress").max = quota.limit;
  $("budget-progress").value = quota.remaining;
  $("budget-reset").textContent =
    quota.resets_at && quota.resets_at > now()
      ? t().resetAt(
          new Date(quota.resets_at * 1000).toLocaleTimeString(language, {
            hour: "2-digit",
            minute: "2-digit",
          }),
        )
      : t().quotaWindow(Math.round(quota.window_seconds / 60));
}
function renderAccount() {
  if (authPending) return;
  const account = config?.account;
  $("account-open").textContent = account ? account.name : t().accountLimits;
  $("account-summary").textContent = account
    ? t().accountWelcome(account.name)
    : t().accountGuest;
  $("account-actions").hidden = !account;
  $("login-options").replaceChildren();
  for (const provider of account ? [] : config?.login_providers || []) {
    const name = provider === "google" ? "Google" : "Facebook";
    const login = button(
      t().signIn(name),
      async () => {
        if (authPending) return;
        authPending = true;
        $("login-options")
          .querySelectorAll("button")
          .forEach((node) => {
            node.disabled = true;
          });
        $("account-error").hidden = true;
        try {
          const result = await api(`/api/auth/${provider}`, { method: "POST" });
          window.location.assign(result.url);
        } catch (error) {
          $("account-error").textContent = errorMessage(error.message);
          $("account-error").hidden = false;
        } finally {
          authPending = false;
          $("login-options")
            .querySelectorAll("button")
            .forEach((node) => {
              node.disabled = false;
            });
        }
      },
      "login-button",
    );
    $("login-options").append(login);
  }
  $("login-note").textContent = account
    ? t().separateAccounts
    : config?.login_providers?.length
      ? t().loginNote
      : t().loginDisabled;
  $("plan-comparison").replaceChildren();
  for (const plan of config?.plans ||
    (config?.quota
      ? [
          {
            ...config,
            downloads: config.quota.limit,
            window_seconds: config.quota.window_seconds,
          },
        ]
      : [])) {
    const block = element("div", "plan");
    block.append(
      element("strong", "", t()[plan.tier]),
      element(
        "p",
        "",
        t().planLine(
          plan.downloads,
          Math.round((plan.window_seconds / 3600) * 10) / 10,
          plan.max_active,
        ),
      ),
      element(
        "small",
        "",
        `${plan.max_quality}p · ${Math.round(plan.max_duration_seconds / 60)} min · ${Math.round(plan.max_file_bytes / 1024 ** 2)} MB`,
      ),
    );
    $("plan-comparison").append(block);
  }
}
function closePreview(card) {
  const media = card.preview.querySelector("video,audio");
  if (media) {
    media.pause();
    media.removeAttribute("src");
    media.load();
  }
  card.preview.replaceChildren();
  card.preview.hidden = true;
  card.previewButton?.setAttribute("aria-expanded", "false");
  if (card.previewButton) card.previewButton.textContent = t().preview;
}
async function preview(card) {
  if (!card.preview.hidden) {
    closePreview(card);
    return;
  }
  const job = card.job;
  try {
    await api(`/api/jobs/${job.id}/preview`, { method: "HEAD" });
    if (!card.node.isConnected || card.node.hidden) return;
    const media = element(job.kind === "mp3" ? "audio" : "video");
    media.controls = true;
    media.preload = "metadata";
    media.setAttribute("aria-label", job.title || job.kind.toUpperCase());
    if (job.kind === "mp4") media.playsInline = true;
    media.src = `/api/jobs/${job.id}/preview`;
    media.addEventListener("error", () => {
      if (
        card.preview.contains(media) &&
        !card.preview.querySelector(".preview-error")
      )
        card.preview.append(
          element("p", "preview-error field-help", t().previewUnsupported),
        );
    });
    card.preview.append(media);
    card.preview.hidden = false;
    card.previewButton.textContent = t().closePreview;
    card.previewButton.setAttribute("aria-expanded", "true");
  } catch (error) {
    showError(error.message);
  }
}
async function mutateJob(card, action) {
  const job = card.job;
  if (pending.has(job.id)) return;
  pending.add(job.id);
  revision++;
  renderJobs();
  clearError();
  try {
    const result = await api(
      `/api/jobs/${job.id}${action === "retry" ? "/retry" : ""}`,
      {
        method: action === "retry" ? "POST" : "DELETE",
        headers:
          action === "retry"
            ? {
                "Idempotency-Key":
                  card.retryKey || (card.retryKey = crypto.randomUUID()),
              }
            : {},
      },
    );
    if (action === "retry") {
      jobs = [result, ...jobs.filter((item) => item.id !== result.id)];
      card.retryKey = null;
      filter = "all";
    } else
      jobs = jobs
        .map((item) => (item.id === job.id ? result : item))
        .filter(Boolean);
    revision++;
    renderJobs();
    await loadSession().catch(() => {
      $("connection-notice").hidden = false;
    });
    if (action === "retry") cards.get(result.id)?.node.focus();
  } catch (error) {
    if (error.message === "request_expired") card.retryKey = null;
    throw error;
  } finally {
    pending.delete(job.id);
    renderJobs();
  }
}
function makeCard(job) {
  const node = element("article", "job");
  node.dataset.id = job.id;
  node.tabIndex = -1;
  const top = element("div", "job-top"),
    info = element("div", "job-info");
  const type = element("span", "job-type"),
    title = element("h3", "job-title");
  const meta = element("p", "job-meta"),
    expiry = element("span", "job-expiry");
  info.append(title, meta);
  top.append(type, info);
  const progress = element("progress");
  progress.max = 100;
  const error = element("p", "job-error"),
    bottom = element("div", "job-bottom");
  const status = element("span", "job-status"),
    actions = element("div", "job-actions");
  const previewBox = element("div", "media-preview");
  previewBox.hidden = true;
  bottom.append(status, expiry);
  node.append(top, progress, error, bottom, actions, previewBox);
  return {
    node,
    type,
    title,
    meta,
    expiry,
    progress,
    error,
    status,
    actions,
    preview: previewBox,
    job,
    actionKey: "",
  };
}
function renderJobs() {
  const current = new Set(jobs.map((job) => job.id));
  for (const [id, card] of cards)
    if (!current.has(id)) {
      const focused = card.node.contains(document.activeElement);
      closePreview(card);
      card.node.remove();
      cards.delete(id);
      if (focused) $("url").focus();
    }
  let visible = 0;
  jobs.forEach((job, index) => {
    let card = cards.get(job.id);
    if (!card) {
      card = makeCard(job);
      cards.set(job.id, card);
    }
    card.job = job;
    if ($("jobs").children[index] !== card.node)
      $("jobs").insertBefore(card.node, $("jobs").children[index] || null);
    card.node.dataset.state = job.state;
    card.node.hidden =
      filter === "active"
        ? !active.has(job.state)
        : filter === "complete"
          ? job.state !== "complete"
          : false;
    if (card.node.hidden) closePreview(card);
    else visible++;
    card.title.textContent = job.title || t().untitled;
    card.type.textContent = job.kind.toUpperCase();
    card.meta.textContent = [
      providerNames[job.provider],
      `${job.quality}${job.kind === "mp3" ? " kbps" : "p"}`,
      job.file_bytes ? `${(job.file_bytes / 1024 ** 2).toFixed(1)} MB` : null,
    ]
      .filter(Boolean)
      .join(" / ");
    card.progress.hidden = !active.has(job.state);
    if (job.state === "downloading") card.progress.value = job.progress || 0;
    else card.progress.removeAttribute("value");
    card.progress.setAttribute("aria-label", t()[job.state]);
    card.error.hidden = !job.error;
    card.error.textContent = job.error ? errorMessage(job.error) : "";
    card.status.textContent = `${t()[job.state] || job.state}${job.state === "downloading" ? ` ${Math.floor(job.progress || 0)} %` : ""}`;
    const actionKey = `${job.state}:${language}`;
    if (card.actionKey !== actionKey) {
      const focusedAction =
        document.activeElement?.closest(".job-actions") === card.actions;
      card.actions.replaceChildren();
      if (job.state === "complete") {
        const link = element(
          "a",
          "job-action",
          `${t().download} ${job.kind.toUpperCase()}`,
        );
        link.href = `/api/jobs/${job.id}/file`;
        link.addEventListener("click", async (event) => {
          event.preventDefault();
          try {
            if (now() >= job.expires_at) throw new Error("file_expired");
            await api(link.getAttribute("href"), { method: "HEAD" });
            window.location.assign(link.href);
          } catch (error) {
            showError(error.message);
          }
        });
        card.previewButton = button(t().preview, () => preview(card));
        card.previewButton.setAttribute(
          "aria-expanded",
          String(!card.preview.hidden),
        );
        if (!card.preview.hidden)
          card.previewButton.textContent = t().closePreview;
        card.actions.append(link, card.previewButton);
      } else {
        closePreview(card);
        const action = active.has(job.state) ? "cancel" : "retry";
        card.actions.append(
          button(t()[action], () =>
            mutateJob(card, action).catch((error) => showError(error.message)),
          ),
        );
      }
      if (!active.has(job.state))
        card.actions.append(
          button(
            t().remove,
            () =>
              confirmAction(t().removeTitle, t().removeCopy, () =>
                mutateJob(card, "remove"),
              ),
            "job-action cancel",
          ),
        );
      card.actionKey = actionKey;
      if (focusedAction) card.actions.querySelector("button,a")?.focus();
    }
    card.actions.querySelectorAll("button").forEach((node) => {
      node.disabled = pending.has(job.id);
    });
  });
  $("empty-state").hidden = jobs.length > 0;
  $("filter-empty").hidden = jobs.length === 0 || visible > 0;
  $("job-count").textContent = String(jobs.length);
  for (const node of $("job-filters").children) {
    const mode = node.dataset.filter;
    const count = jobs.filter(
      (job) =>
        mode === "all" ||
        (mode === "active" ? active.has(job.state) : job.state === "complete"),
    ).length;
    node.textContent = `${t()[`${mode}Filter`]} ${count}`;
    node.setAttribute("aria-pressed", String(mode === filter));
  }
  const announcement = jobs
    .map((job) => `${job.title || job.kind}: ${t()[job.state]}`)
    .join(". ");
  if (announcement !== lastAnnouncement) {
    $("queue-announcement").textContent = announcement;
    lastAnnouncement = announcement;
  }
  tick();
}
function tick() {
  for (const card of cards.values()) {
    const job = card.job;
    card.expiry.hidden = !job.expires_at;
    if (job.expires_at) {
      const left = Math.max(0, Math.ceil(job.expires_at - now()));
      card.expiry.textContent = left
        ? t().expiresIn(
            `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`,
          )
        : t().expired;
    }
  }
  setSubmit();
  if (lastError && cooldown > now()) showError(lastError);
}
async function refresh() {
  const sequence = ++refreshSequence,
    startRevision = revision;
  const next = await api("/api/jobs");
  if (sequence === refreshSequence && startRevision === revision) {
    jobs = next;
    renderJobs();
  }
  $("connection-notice").hidden = true;
}
async function poll() {
  clearTimeout(pollTimer);
  if (pollPromise) return pollPromise;
  pollPromise = (async () => {
    try {
      if (
        !config ||
        !config.ready ||
        Date.now() - sessionUpdated > 30000 ||
        (Number.isFinite(config.quota?.resets_at) &&
          config.quota.resets_at < now())
      )
        await loadSession();
      await refresh();
      failures = 0;
    } catch {
      failures++;
      $("connection-notice").hidden = false;
    }
  })();
  try {
    await pollPromise;
  } finally {
    pollPromise = null;
    const delay = failures
      ? Math.min(30000, 2000 * 2 ** Math.min(failures - 1, 4))
      : jobs.some((job) => active.has(job.state))
        ? 1500
        : 6000;
    pollTimer = setTimeout(
      poll,
      document.hidden ? Math.max(delay, 15000) : delay,
    );
  }
}
let confirmation = null;
function confirmAction(title, copy, action) {
  confirmation = action;
  $("confirm-title").textContent = title;
  $("confirm-copy").textContent = copy;
  $("confirm-error").hidden = true;
  $("confirm-dialog").showModal();
  $("confirm-cancel").focus();
}
$("confirm-cancel").addEventListener("click", () =>
  $("confirm-dialog").close(),
);
$("confirm-accept").addEventListener("click", async () => {
  $("confirm-accept").disabled = true;
  $("confirm-cancel").disabled = true;
  try {
    await confirmation();
    $("confirm-dialog").close();
  } catch (error) {
    $("confirm-error").textContent = errorMessage(error.message);
    $("confirm-error").hidden = false;
  } finally {
    $("confirm-accept").disabled = false;
    $("confirm-cancel").disabled = false;
  }
});
$("confirm-dialog").addEventListener("cancel", (event) => {
  if ($("confirm-accept").disabled) event.preventDefault();
});
$("confirm-dialog").addEventListener("close", () => {
  if (document.activeElement === document.body)
    ($("account-dialog").open ? $("account-open") : $("url")).focus();
});
$("account-open").addEventListener("click", () => {
  $("account-error").hidden = true;
  $("account-dialog").showModal();
});
document
  .querySelectorAll("[data-close]")
  .forEach((node) =>
    node.addEventListener("click", () => $(node.dataset.close).close()),
  );
async function leaveAccount(path, method) {
  await api(path, { method });
  jobs = [];
  config = null;
  revision++;
  submission = null;
  clearError();
  renderJobs();
  $("account-dialog").close();
  try {
    await loadSession();
    await refresh();
  } catch {
    $("connection-notice").hidden = false;
    poll();
  }
}
for (const id of ["logout", "logout-all"])
  $(id).addEventListener("click", async () => {
    $(id).disabled = true;
    try {
      await leaveAccount(
        `/api/logout${id === "logout-all" ? "?all_devices=true" : ""}`,
        "POST",
      );
    } catch (error) {
      $("account-error").textContent = errorMessage(error.message);
      $("account-error").hidden = false;
    } finally {
      $(id).disabled = false;
    }
  });
$("delete-account").addEventListener("click", () =>
  confirmAction(t().deleteAccount, t().deleteAccountCopy, () =>
    leaveAccount("/api/account", "DELETE"),
  ),
);
$("language").addEventListener("change", () => {
  language = $("language").value;
  try {
    localStorage.setItem("ytd-language", language);
  } catch {
    /* Optional. */
  }
  setLanguage();
});
document.querySelectorAll('[name="kind"]').forEach((input) =>
  input.addEventListener("change", () => {
    preferences.kind = input.value;
    qualityOptions();
    savePreferences();
  }),
);
$("quality").addEventListener("change", () => {
  preferences[preferences.kind] = Number($("quality").value);
  savePreferences();
});
$("paste").addEventListener("click", async () => {
  try {
    $("url").value = (await navigator.clipboard.readText()).trim();
    updateSource();
  } catch {
    showError("clipboard");
  }
  $("url").focus();
});
$("url").addEventListener("input", updateSource);
$("reconnect").addEventListener("click", () => {
  sessionUpdated = 0;
  poll();
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) poll();
});
window.addEventListener("online", () => poll());
$("job-filters").addEventListener("click", (event) => {
  if (event.target.dataset.filter) {
    filter = event.target.dataset.filter;
    renderJobs();
  }
});
$("download-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if ($("submit").disabled) return;
  submitting = true;
  clearError();
  setSubmit();
  revision++;
  const payload = {
    url: $("url").value.trim(),
    kind: preferences.kind,
    quality: Number($("quality").value),
  };
  const body = JSON.stringify(payload);
  if (!submission || submission.body !== body)
    submission = { body, key: crypto.randomUUID() };
  try {
    const job = await api("/api/jobs", {
      method: "POST",
      body,
      headers: { "Idempotency-Key": submission.key },
    });
    submission = null;
    revision++;
    filter = "all";
    jobs = [job, ...jobs.filter((item) => item.id !== job.id)];
    renderJobs();
    // Accepted job stays visible even when the following refresh loses connectivity.
    await loadSession().catch(() => {
      $("connection-notice").hidden = false;
    });
  } catch (error) {
    if (["request_expired", "idempotency_conflict"].includes(error.message))
      submission = null;
    showError(error.message);
  } finally {
    submitting = false;
    setSubmit();
  }
});
const authResult = new URLSearchParams(location.search).get("auth");
if (authResult) {
  const clean = new URL(location.href);
  clean.searchParams.delete("auth");
  history.replaceState(null, "", clean);
  if (authResult === "success")
    $("queue-announcement").textContent = translations[language].signedIn;
  else showError(authResult);
}
qualityOptions();
setLanguage();
poll();
setInterval(tick, 1000);
