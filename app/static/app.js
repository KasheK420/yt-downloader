"use strict";

const translations = {
  cs: {
    skip: "Přejít ke stažení",
    headline: "Tvoje videa.\nTeď i offline.",
    intro:
      "Vlož odkaz z YouTube. Vyber video nebo jen zvuk. Zbytek nech na nás.",
    newDownload: "Nové stažení",
    linkLabel: "Odkaz na YouTube",
    paste: "Vložit",
    linkHelp: "Fungují i odkazy youtu.be a Shorts.",
    formatLabel: "Co chceš stáhnout?",
    videoLabel: "Video MP4",
    videoHint: "Obraz i zvuk",
    audioLabel: "Audio MP3",
    audioHint: "Jen zvuková stopa",
    qualityLabel: "Kvalita",
    qualityHelp: "Podle dostupnosti původního videa.",
    submit: "Připravit ke stažení",
    submitting: "Přidávám do fronty…",
    downloads: "Tvoje soubory",
    sessionNote: "Viditelné jen v tomto prohlížeči.",
    emptyTitle: "Tady budou tvoje soubory",
    emptyText:
      "Začni odkazem. Hotové video nebo MP3 si pak stáhneš jedním kliknutím.",
    usage: "Stahuj obsah, který vlastníš nebo k jehož stažení máš svolení.",
    footer: "Jeden odkaz. Tvůj soubor.",
    queued: "Ve frontě",
    downloading: "Stahování",
    processing: "Zpracování",
    complete: "Připraveno",
    failed: "Nepodařilo se",
    cancelled: "Zrušeno",
    cancel: "Zrušit",
    download: "Stáhnout",
    untitled: "Načítám název videa…",
    connectionError: "Spojení se přerušilo. Zkoušíme to znovu…",
    runtimeUnavailable: "Server ještě není připravený ke stahování.",
    limits: (minutes, size) =>
      `Jedno video do ${minutes} minut / soubor do ${size} MB`,
    retention: (minutes) =>
      `Soubory se automaticky smažou ${minutes} minut po dokončení.`,
    expires: (minutes) => `Zbývá ${minutes} min`,
    expired: "Platnost souboru vypršela.",
    clipboard: "Odkaz vlož do pole pomocí Ctrl+V nebo nabídky Vložit.",
    errors: {
      invalid_request:
        "Zkontroluj odkaz na jedno video z YouTube a vybranou kvalitu.",
      session_limit:
        "Nejdřív dokonči nebo zruš některé ze svých rozpracovaných stahování.",
      rate_limit:
        "Příliš mnoho požadavků. Počkej několik minut a zkus to znovu.",
      queue_full: "Fronta je právě plná. Zkus to za chvíli.",
      provider_error:
        "YouTube toto video teď neposkytl. Zkus jiný veřejný odkaz nebo to zopakuj později.",
      processing_error: "Soubor se nepodařilo zpracovat. Zkus to znovu.",
      duration_limit: "Video je příliš dlouhé nebo není dostupná jeho délka.",
      live_unsupported:
        "Probíhající ani plánované živé přenosy zatím nepodporujeme.",
      size_limit:
        "Soubor překročil limit velikosti. Zvol nižší kvalitu nebo kratší video.",
      timeout:
        "Stahování trvalo příliš dlouho. Zkus kratší video nebo nižší kvalitu.",
      interrupted: "Stahování přerušil restart serveru. Spusť ho znovu.",
      storage_full: "Na serveru právě není dost místa. Zkus to později.",
      runtime_unavailable:
        "Serveru chybí nástroj pro zpracování. Zkus to později.",
      invalid_origin: "Požadavek se nepodařilo ověřit. Obnov stránku.",
      session_required: "Platnost relace vypršela. Obnov stránku.",
      file_expired: "Soubor už není dostupný. Připrav ho znovu.",
      job_not_found: "Úloha už není dostupná. Obnov seznam.",
      network: "Nepodařilo se spojit se serverem. Zkus to znovu.",
    },
  },
  en: {
    skip: "Skip to download",
    headline: "Your videos.\nNow offline.",
    intro:
      "Paste a YouTube link. Choose video or just audio. We’ll take it from there.",
    newDownload: "New download",
    linkLabel: "YouTube link",
    paste: "Paste",
    linkHelp: "youtu.be and Shorts links work too.",
    formatLabel: "What would you like to save?",
    videoLabel: "Video MP4",
    videoHint: "Picture and sound",
    audioLabel: "Audio MP3",
    audioHint: "Just the audio track",
    qualityLabel: "Quality",
    qualityHelp: "Subject to the original video’s availability.",
    submit: "Prepare download",
    submitting: "Adding to queue…",
    downloads: "Your files",
    sessionNote: "Visible only in this browser.",
    emptyTitle: "Your files will appear here",
    emptyText:
      "Start with a link. Download your finished video or MP3 with one click.",
    usage: "Download content you own or have permission to download.",
    footer: "One link. Your file.",
    queued: "Queued",
    downloading: "Downloading",
    processing: "Processing",
    complete: "Ready",
    failed: "Failed",
    cancelled: "Cancelled",
    cancel: "Cancel",
    download: "Download",
    untitled: "Loading video details…",
    connectionError: "Connection lost. Trying again…",
    runtimeUnavailable: "The server is not ready to process downloads yet.",
    limits: (minutes, size) =>
      `One video up to ${minutes} minutes / file up to ${size} MB`,
    retention: (minutes) =>
      `Files are automatically deleted ${minutes} minutes after completion.`,
    expires: (minutes) => `${minutes} min left`,
    expired: "This file has expired.",
    clipboard: "Paste the link into the field with Ctrl+V or the Paste menu.",
    errors: {
      invalid_request:
        "Check the link to a single YouTube video and the selected quality.",
      session_limit: "Finish or cancel one of your active downloads first.",
      rate_limit: "Too many requests. Wait a few minutes and try again.",
      queue_full: "The queue is full right now. Try again shortly.",
      provider_error:
        "YouTube did not provide this video. Try another public link or try again later.",
      processing_error: "We couldn’t process this file. Please try again.",
      duration_limit: "The video is too long, or its duration is unavailable.",
      live_unsupported:
        "Ongoing and upcoming live streams are not supported yet.",
      size_limit:
        "The file exceeded the size limit. Try a lower quality or a shorter video.",
      timeout:
        "The download took too long. Try a shorter video or lower quality.",
      interrupted:
        "A server restart interrupted this download. Please start it again.",
      storage_full: "The server is out of available storage. Try again later.",
      runtime_unavailable:
        "A processing tool is unavailable on the server. Try again later.",
      invalid_origin: "The request could not be verified. Refresh this page.",
      session_required: "Your session expired. Refresh this page.",
      file_expired: "This file is no longer available. Prepare it again.",
      job_not_found: "This job is no longer available. Refresh the list.",
      network: "Couldn’t connect to the server. Please try again.",
    },
  },
};

const $ = (id) => document.getElementById(id);
let language = "cs";
try {
  language = localStorage.getItem("ytd-language") === "en" ? "en" : "cs";
} catch {
  /* Storage is optional. */
}
let config = null;
let jobs = [];
let submitting = false;
let lastAnnouncement = "";
let lastError = null;
const active = new Set(["queued", "downloading", "processing"]);
const t = () => translations[language];

function errorMessage(code) {
  return t().errors[code] || t().errors.network;
}
function showError(code) {
  lastError = code;
  $("form-error").textContent =
    code === "clipboard" ? t().clipboard : errorMessage(code);
  $("form-error").hidden = false;
}
function setLanguage() {
  document.documentElement.lang = language;
  $("language").value = language;
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t()[element.dataset.i18n];
  });

  if (config) {
    $("limits").textContent = t().limits(
      Math.round(config.max_duration_seconds / 60),
      Math.round(config.max_file_bytes / 1024 ** 2),
    );
    $("retention").textContent = t().retention(
      Math.round(config.retention_seconds / 60),
    );
  }
  if (lastError && !$("form-error").hidden) showError(lastError);
  setSubmit();
  renderJobs();
}
function setSubmit() {
  $("submit").disabled = submitting || !config?.ready;
  $("submit").querySelector("span").textContent = submitting
    ? t().submitting
    : t().submit;
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "yt-downloader",
      ...options.headers,
    },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === "string" ? data.detail : "network");
  }
  return response.json();
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function renderJobs() {
  const focused = document.activeElement?.closest(".job");
  const focusedId = focused?.dataset.id;
  const fragment = document.createDocumentFragment();
  for (const job of jobs) {
    const card = element("article", "job");
    card.dataset.id = job.id;
    card.dataset.state = job.state;
    const top = element("div", "job-top");
    top.append(element("span", "job-type", job.kind.toUpperCase()));
    const info = element("div", "job-info");
    info.append(element("h3", "job-title", job.title || t().untitled));
    const metadata = [
      job.kind === "mp3" ? `${job.quality} kbps` : `${job.quality}p`,
    ];
    if (job.file_bytes)
      metadata.push(`${(job.file_bytes / 1024 ** 2).toFixed(1)} MB`);
    if (job.state === "complete")
      metadata.push(
        t().expires(
          Math.max(0, Math.ceil((job.expires_at - Date.now() / 1000) / 60)),
        ),
      );
    info.append(element("p", "job-meta", metadata.join(" / ")));
    top.append(info);
    card.append(top);
    if (active.has(job.state)) {
      const progress = element("progress");
      progress.max = 100;
      if (job.state === "downloading") progress.value = job.progress || 0;
      progress.setAttribute("aria-label", t()[job.state]);
      card.append(progress);
    }
    if (job.error)
      card.append(element("p", "job-error", errorMessage(job.error)));
    const bottom = element("div", "job-bottom");
    bottom.append(
      element(
        "span",
        "job-status",
        `${t()[job.state] || job.state}${job.state === "downloading" ? ` ${Math.floor(job.progress)} %` : ""}`,
      ),
    );
    if (job.state === "complete") {
      const link = element(
        "a",
        "job-action",
        `${t().download} ${job.kind.toUpperCase()}`,
      );
      link.href = `/api/jobs/${encodeURIComponent(job.id)}/file`;
      link.addEventListener("click", async (event) => {
        event.preventDefault();
        try {
          if (Date.now() / 1000 >= job.expires_at)
            throw new Error("file_expired");
          // Check availability before starting a native browser download; do not buffer large files.
          await api(`/api/jobs/${encodeURIComponent(job.id)}`);
          const probe = await fetch(link.href, {
            method: "HEAD",
            credentials: "same-origin",
          });
          if (!probe.ok && probe.status !== 405)
            throw new Error("file_expired");
          window.location.assign(link.href);
        } catch (error) {
          showError(error.message);
        }
      });
      bottom.append(link);
    } else if (active.has(job.state)) {
      const cancel = element("button", "job-action cancel", t().cancel);
      cancel.type = "button";
      cancel.addEventListener("click", async () => {
        cancel.disabled = true;
        try {
          await api(`/api/jobs/${encodeURIComponent(job.id)}`, {
            method: "DELETE",
          });
          await refresh();
        } catch (error) {
          showError(error.message);
          cancel.disabled = false;
        }
      });
      bottom.append(cancel);
    }
    card.append(bottom);
    fragment.append(card);
  }
  $("jobs").replaceChildren(fragment);
  $("empty-state").hidden = jobs.length > 0;
  $("job-count").textContent = String(jobs.length);
  if (focusedId)
    Array.from($("jobs").children)
      .find((item) => item.dataset.id === focusedId)
      ?.querySelector(".job-action")
      ?.focus();
  const announcement = jobs
    .map((job) => `${job.title || job.kind}: ${t()[job.state]}`)
    .join(". ");
  if (announcement !== lastAnnouncement) {
    $("queue-announcement").textContent = announcement;
    lastAnnouncement = announcement;
  }
}
async function refresh() {
  jobs = await api("/api/jobs");
  $("connection-notice").hidden = true;
  renderJobs();
}
async function poll() {
  try {
    if (!config || !config.ready) {
      config = await api("/api/session");
      setLanguage();
    }
    await refresh();
  } catch {
    $("connection-notice").hidden = false;
  }
  $("runtime-notice").hidden = !config || config.ready;
  setTimeout(poll, jobs.some((job) => active.has(job.state)) ? 1500 : 6000);
}
$("language").addEventListener("change", () => {
  language = $("language").value;
  try {
    localStorage.setItem("ytd-language", language);
  } catch {
    /* Storage is optional. */
  }
  setLanguage();
});
document.querySelectorAll('[name="kind"]').forEach((input) =>
  input.addEventListener("change", () => {
    const isAudio = input.value === "mp3";
    $("quality").replaceChildren(
      ...(isAudio ? [128, 192, 320] : [360, 720, 1080]).map((value) => {
        const option = element(
          "option",
          "",
          `${value}${isAudio ? " kbps" : "p"}`,
        );
        option.value = value;
        option.selected = value === (isAudio ? 192 : 720);
        return option;
      }),
    );
  }),
);
$("paste").addEventListener("click", async () => {
  try {
    $("url").value = (await navigator.clipboard.readText()).trim();
    $("url").focus();
  } catch {
    showError("clipboard");
    $("url").focus();
  }
});
$("download-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (submitting) return;
  submitting = true;
  $("form-error").hidden = true;
  setSubmit();
  try {
    const payload = {
      url: $("url").value.trim(),
      kind: document.querySelector('[name="kind"]:checked').value,
      quality: Number($("quality").value),
    };
    const job = await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    jobs = [job, ...jobs.filter((item) => item.id !== job.id)];
    renderJobs();
    await refresh();
  } catch (error) {
    showError(error.message);
  } finally {
    submitting = false;
    setSubmit();
  }
});
setLanguage();
poll();
