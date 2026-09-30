"use strict";

const translations = {
  cs: {
    skip: "Přejít ke stažení",
    headline: "Tvoje videa.\nTeď i offline.",
    intro:
      "YouTube, Facebook nebo Instagram. Tvoje oblíbená videa i zvuk na jednom místě.",
    newDownload: "Nové stažení",
    linkLabel: "Odkaz na video",
    paste: "Vložit",
    linkHelp: "Vlož odkaz na jedno veřejné video, Short nebo Reel.",
    sourceDetected: (name) => `Zdroj: ${name}`,
    supportedLinks: "Jaké odkazy fungují?",
    youtubeLinks: "Videa, Shorts, youtu.be a ukončené živé přenosy.",
    facebookLinks: "Videa, Reels, fb.watch a sdílené odkazy na video.",
    instagramLinks:
      "Reels a příspěvky s jedním videem, včetně sdílených odkazů.",
    publicOnly:
      "Video musí být dostupné bez přihlášení. Profily, Stories a alba s více položkami nepodporujeme.",
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
        "Vlož odkaz na jedno video z YouTube, Facebooku nebo Instagramu a zkontroluj kvalitu.",
      session_limit:
        "Nejdřív dokonči nebo zruš některé ze svých rozpracovaných stahování.",
      rate_limit:
        "Příliš mnoho požadavků. Počkej několik minut a zkus to znovu.",
      queue_full: "Fronta je právě plná. Zkus to za chvíli.",
      provider_error:
        "Platforma video teď neposkytla. Ověř, že jde přehrát bez přihlášení, nebo to zkus později.",
      playlist_unsupported:
        "Odkaz obsahuje více položek. Vlož odkaz přímo na jedno video nebo Reel.",
      link_unresolved:
        "Sdílený odkaz se nepodařilo otevřít. Otevři video v prohlížeči a zkopíruj jeho přímý odkaz.",
      processing_error: "Soubor se nepodařilo zpracovat. Zkus to znovu.",
      audio_unavailable:
        "Toto video nemá dostupnou zvukovou stopu. Vyber Video MP4.",
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
      "YouTube, Facebook or Instagram. Your favorite videos and audio, all in one place.",
    newDownload: "New download",
    linkLabel: "Video link",
    paste: "Paste",
    linkHelp: "Paste a link to one public video, Short or Reel.",
    sourceDetected: (name) => `Source: ${name}`,
    supportedLinks: "Which links work?",
    youtubeLinks: "Videos, Shorts, youtu.be and completed live streams.",
    facebookLinks: "Videos, Reels, fb.watch and shared video links.",
    instagramLinks: "Reels and single-video posts, including share links.",
    publicOnly:
      "The video must be available without signing in. Profiles, Stories and multi-item albums are not supported.",
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
        "Use a link to one YouTube, Facebook or Instagram video and check the selected quality.",
      session_limit: "Finish or cancel one of your active downloads first.",
      rate_limit: "Too many requests. Wait a few minutes and try again.",
      queue_full: "The queue is full right now. Try again shortly.",
      provider_error:
        "The platform did not provide this video. Check that it plays without signing in, or try again later.",
      playlist_unsupported:
        "This link contains multiple items. Use a direct link to one video or Reel.",
      link_unresolved:
        "We couldn’t open this share link. Open the video in your browser and copy its direct link.",
      processing_error: "We couldn’t process this file. Please try again.",
      audio_unavailable:
        "This video has no available audio track. Choose Video MP4.",
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

Object.assign(translations.cs, {
  accountLimits: "Účet a limity",
  guest: "Bez účtu",
  free: "Bezplatný účet",
  personal: "Osobní instance",
  accountLibrary:
    "Tvoje soubory jsou dostupné po přihlášení i z jiného zařízení.",
  accountWelcome: (name) => `Přihlášen jako ${name}.`,
  accountGuest:
    "Stahuj bez účtu. Dobrovolné přihlášení zpřístupní tvoje úlohy i na dalších zařízeních.",
  quotaHelp:
    "Počítá se každý přijatý pokus, i neúspěšný nebo zrušený. Opakování je nový pokus. Smazání úlohy limit nevrací.",
  remaining: (n, total) => `${n} z ${total} zbývá`,
  quotaWindow: (minutes) => `Za posledních ${minutes} minut.`,
  resetAt: (time) => `Další místo v limitu: ${time}.`,
  signIn: (name) => `Pokračovat přes ${name}`,
  loginNote:
    "První přihlášení vytvoří účet. Google je i pro Gmail a YouTube. Přihlašujeme tě jen do této aplikace, bez přístupu k poště nebo soukromým videím.",
  loginDisabled:
    "Přihlášení tu zatím není dostupné. Stahování funguje bez účtu.",
  separateAccounts:
    "Google a Facebook vytvářejí samostatné účty. Pro svou historii používej stejnou službu.",
  logout: "Odhlásit",
  logoutAll: "Odhlásit všechna zařízení",
  deleteAccount: "Smazat účet",
  deleteAccountCopy:
    "Odhlásíme všechna zařízení a smažeme účet, úlohy i soubory na serveru. Krátkodobé záznamy pro limity doběhnou do své expirace. Toto nelze vrátit.",
  remove: "Smazat",
  keep: "Ponechat",
  removeTitle: "Smazat tuto úlohu?",
  removeCopy:
    "Smažeme úlohu a její soubor na serveru. Kopie už stažená do tvého zařízení zůstane.",
  retry: "Zkusit znovu",
  preview: "Přehrát",
  closePreview: "Zavřít náhled",
  close: "Zavřít",
  previewUnsupported:
    "Prohlížeč toto médium nepřehraje. Soubor si můžeš stáhnout a otevřít v přehrávači.",
  allFilter: "Vše",
  activeFilter: "Probíhá",
  completeFilter: "Hotové",
  filterLabel: "Filtr souborů",
  filterEmpty: "V tomto pohledu nejsou žádné soubory.",
  reconnect: "Obnovit spojení",
  privacy: "Soukromí a data",
  signedIn: "Přihlášení proběhlo úspěšně.",
  expiresIn: (time) => `Smazání za ${time}`,
  wait: (seconds) => `Zkus to za ${seconds} s.`,
  planLine: (n, hours, active) =>
    `${n} pokusů / ${hours} h · ${active} rozpracované`,
});
Object.assign(translations.en, {
  accountLimits: "Account & limits",
  guest: "Guest",
  free: "Free account",
  personal: "Personal instance",
  accountLibrary: "Sign in on another device to access your files.",
  accountWelcome: (name) => `Signed in as ${name}.`,
  accountGuest:
    "Download as a guest. Optional sign-in gives you access to your jobs on other devices.",
  quotaHelp:
    "Every accepted attempt counts, including failures and cancellations. Retrying is a new attempt. Deleting a job does not refund quota.",
  remaining: (n, total) => `${n} of ${total} left`,
  quotaWindow: (minutes) => `Over the last ${minutes} minutes.`,
  resetAt: (time) => `Next quota slot: ${time}.`,
  signIn: (name) => `Continue with ${name}`,
  loginNote:
    "Your first sign-in creates an account. Google also covers Gmail and YouTube. Sign-in is for this app only, without access to email or private videos.",
  loginDisabled:
    "Sign-in is not available here yet. You can download as a guest.",
  separateAccounts:
    "Google and Facebook create separate accounts. Use the same provider for your history.",
  logout: "Sign out",
  logoutAll: "Sign out all devices",
  deleteAccount: "Delete account",
  deleteAccountCopy:
    "Sign out all devices and delete your account, jobs and server files. Short-lived quota records remain until they expire. This cannot be undone.",
  remove: "Delete",
  keep: "Keep",
  removeTitle: "Delete this job?",
  removeCopy:
    "Delete the job and its server file. A copy already downloaded to your device will stay there.",
  retry: "Retry",
  preview: "Play",
  closePreview: "Close preview",
  close: "Close",
  previewUnsupported:
    "This browser cannot play this media. Download it and open it in a media player.",
  allFilter: "All",
  activeFilter: "Active",
  completeFilter: "Ready",
  filterLabel: "File filter",
  filterEmpty: "There are no files in this view.",
  reconnect: "Reconnect",
  privacy: "Privacy & data",
  signedIn: "You are now signed in.",
  expiresIn: (time) => `Deletes in ${time}`,
  wait: (seconds) => `Try again in ${seconds} s.`,
  planLine: (n, hours, active) =>
    `${n} attempts / ${hours} h · ${active} active`,
});
Object.assign(translations.cs.errors, {
  already_signed_in: "Už jsi přihlášený. Obnov stránku pro aktuální stav účtu.",
  account_required: "Tato akce vyžaduje přihlášený účet.",
  file_not_ready: "Soubor se ještě připravuje. Počkej na dokončení.",
  queue_timeout:
    "Úloha čekala příliš dlouho ve frontě. Zkus ji spustit později.",
  quota_exhausted:
    "Limit stahování je vyčerpaný. Čas dalšího pokusu najdeš u svého limitu.",
  ip_daily_limit: "Tato síť dosáhla denního limitu. Zkus to později.",
  quality_limit:
    "Tato kvalita přesahuje limit tvého účtu. Vyber nižší kvalitu.",
  login_required: "Tato instance vyžaduje přihlášení před stahováním.",
  login_unavailable: "Přihlášení teď není dostupné. Zkus to později.",
  login_failed: "Přihlášení se nepodařilo ověřit. Spusť ho znovu.",
  login_expired:
    "Přihlašovací odkaz vypršel nebo už byl použitý. Spusť přihlášení znovu.",
  login_cancelled: "Přihlášení bylo zrušeno. Můžeš pokračovat jako host.",
  login_origin_mismatch: "Přihlášení otevři na hlavní adrese této aplikace.",
  auth_rate_limit: "Příliš mnoho pokusů o přihlášení. Chvíli počkej.",
  retry_unavailable: "Zopakovat lze jen neúspěšné nebo zrušené úlohy.",
  request_expired: "Původní úloha už vypršela. Odešli nový požadavek.",
  idempotency_conflict:
    "Požadavek se změnil. Zkontroluj odkaz a odešli ho znovu.",
});
Object.assign(translations.en.errors, {
  already_signed_in:
    "You are already signed in. Refresh the page for the current account state.",
  account_required: "This action requires a signed-in account.",
  file_not_ready: "This file is still being prepared. Wait for completion.",
  queue_timeout: "This job waited too long in the queue. Please retry later.",
  quota_exhausted:
    "Your download allowance is used up. Check your budget for the next available slot.",
  ip_daily_limit: "This network has reached its daily limit. Please try later.",
  quality_limit:
    "This quality exceeds your account limit. Choose a lower quality.",
  login_required: "This instance requires sign-in before downloading.",
  login_unavailable: "Sign-in is unavailable right now. Please try later.",
  login_failed: "Sign-in could not be verified. Please start again.",
  login_expired:
    "This sign-in link expired or was already used. Please start sign-in again.",
  login_cancelled: "Sign-in was cancelled. You can continue as a guest.",
  login_origin_mismatch: "Open sign-in on this app’s configured main address.",
  auth_rate_limit: "Too many sign-in attempts. Please wait a while.",
  retry_unavailable: "Only failed or cancelled jobs can be retried.",
  request_expired: "The original job expired. Submit a new request.",
  idempotency_conflict: "The request changed. Check the link and submit again.",
});
