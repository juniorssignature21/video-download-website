(() => {
  const urlInput = document.getElementById("url-input");
  const form = document.getElementById("fetch-form");
  const pasteBtn = document.getElementById("paste-btn");
  const statusBox = document.getElementById("status");
  const resultCard = document.getElementById("result-card");
  const resultThumb = document.getElementById("result-thumb");
  const resultTitle = document.getElementById("result-title");
  const resultMeta = document.getElementById("result-meta");
  const qualityList = document.getElementById("quality-list");

  const toast = document.getElementById("clipboard-toast");
  const toastText = document.getElementById("clipboard-toast-text");
  const toastUse = document.getElementById("clipboard-toast-use");
  const toastDismiss = document.getElementById("clipboard-toast-dismiss");

  const CSRF_TOKEN = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");

  const installBtn = document.getElementById("install-btn");
  let deferredInstallPrompt = null;

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    installBtn.hidden = false;
  });

  installBtn.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    installBtn.hidden = true;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
  });

  window.addEventListener("appinstalled", () => {
    installBtn.hidden = true;
    deferredInstallPrompt = null;
  });

  const VIDEO_LINK_RE =
    /https?:\/\/(www\.)?(facebook\.com|fb\.watch|instagram\.com|tiktok\.com|twitter\.com|x\.com|youtube\.com|youtu\.be|vimeo\.com|reddit\.com|dailymotion\.com|twitch\.tv)\/\S+/i;

  const QUALITY_LABELS = {
    best: "Best quality (MP4)",
    audio: "Audio only (MP3)",
    "1080p": "1080p",
    "720p": "720p",
    "480p": "480p",
    "360p": "360p",
    "240p": "240p",
  };

  let lastSeenClipboardText = "";
  let lastToastedLink = "";

  function isVideoLink(text) {
    return !!text && VIDEO_LINK_RE.test(text.trim());
  }

  function showToastForLink(link) {
    if (link === lastToastedLink || document.activeElement === urlInput) return;
    lastToastedLink = link;
    toastText.textContent = "We found a video link in your clipboard.";
    toast.hidden = false;
    toastUse.onclick = () => {
      urlInput.value = link;
      toast.hidden = true;
      form.requestSubmit();
    };
    toastDismiss.onclick = () => {
      toast.hidden = true;
    };
  }

  // Browsers only allow silent clipboard reads when the page already has
  // clipboard-read permission (or the Permissions API isn't required by the
  // browser); otherwise this quietly fails and the visible Paste button /
  // paste-event fallback below still work without needing that permission.
  async function checkClipboardSilently() {
    if (!navigator.clipboard || !navigator.clipboard.readText) return;
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const status = await navigator.permissions
          .query({ name: "clipboard-read" })
          .catch(() => null);
        if (status && status.state === "denied") return;
      }
      const text = await navigator.clipboard.readText();
      if (text && text !== lastSeenClipboardText) {
        lastSeenClipboardText = text;
        if (isVideoLink(text)) showToastForLink(text.trim());
      }
    } catch (err) {
      // Permission not granted yet — user can still use the Paste button.
    }
  }

  window.addEventListener("load", checkClipboardSilently);
  window.addEventListener("focus", checkClipboardSilently);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) checkClipboardSilently();
  });

  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        urlInput.focus();
      }
    } catch (err) {
      statusBox.hidden = false;
      statusBox.className = "status error";
      statusBox.textContent =
        "Couldn't read the clipboard automatically — please paste the link manually (Ctrl/Cmd+V).";
      urlInput.focus();
    }
  });

  urlInput.addEventListener("paste", () => {
    setTimeout(() => {
      if (isVideoLink(urlInput.value)) {
        statusBox.hidden = true;
      }
    }, 0);
  });

  function setStatus(message, isError) {
    if (!message) {
      statusBox.hidden = true;
      return;
    }
    statusBox.hidden = false;
    statusBox.className = isError ? "status error" : "status";
    statusBox.textContent = message;
  }

  function renderResult(info, sourceUrl) {
    resultCard.hidden = false;
    resultThumb.src = info.thumbnail || "";
    resultThumb.alt = info.title || "Video thumbnail";
    resultTitle.textContent = info.title;

    const bits = [];
    if (info.site) bits.push(info.site);
    if (info.uploader) bits.push(info.uploader);
    if (info.duration) {
      const mins = Math.floor(info.duration / 60);
      const secs = String(info.duration % 60).padStart(2, "0");
      bits.push(`${mins}:${secs}`);
    }
    resultMeta.textContent = bits.join(" • ");

    qualityList.innerHTML = "";
    (info.qualities || ["best"]).forEach((quality) => {
      const link = document.createElement("a");
      link.href = `/api/download/?url=${encodeURIComponent(sourceUrl)}&quality=${encodeURIComponent(
        quality
      )}`;
      link.textContent = QUALITY_LABELS[quality] || quality;
      qualityList.appendChild(link);
    });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;

    resultCard.hidden = true;
    setStatus("Fetching video info…", false);

    try {
      const response = await fetch("/api/fetch/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": CSRF_TOKEN,
        },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();

      if (!response.ok) {
        setStatus(data.error || "Something went wrong. Please try another link.", true);
        return;
      }

      setStatus("", false);
      renderResult(data, url);
    } catch (err) {
      setStatus("Network error — please try again.", true);
    }
  });
})();
