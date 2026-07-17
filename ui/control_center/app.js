let state = null;

const $ = (id) => document.getElementById(id);

const api = async (path, options = {}) => {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Jarvis-Control-Token": window.JARVIS_CONTROL_TOKEN,
      ...(options.headers || {}),
    },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
};

const setStatus = (text, error = false) => {
  const target = $("saveState");
  target.textContent = text;
  target.classList.toggle("error", error);
};

const numberValue = (id) => Number($(id).value);
const boolValue = (id) => $(id).checked;

const bindRange = (inputId, outputId) => {
  const input = $(inputId);
  const output = $(outputId);
  const update = () => {
    output.textContent = input.value;
  };
  input.oninput = update;
  update();
};

const showTab = (name) => {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === name);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === name);
  });
};

const loadState = async () => {
  setStatus("Loading");
  state = await api("/api/state");
  render();
  setStatus("Ready");
};

const render = () => {
  const device = state.device || {};
  const voice = device.voice || {};
  const tts = device.tts || {};
  const local = tts.local || {};
  const eleven = tts.elevenlabs || {};

  $("deviceName").textContent = device.device_name || "Jarvis";
  $("wakeWord").value = voice.wake_word || "hey jarvis";
  $("wakeThreshold").value = voice.wake_threshold ?? 0.8;
  $("silenceSeconds").value = voice.silence_seconds ?? 3;
  $("startTimeout").value = voice.start_timeout_seconds ?? 8;
  $("commandSeconds").value = voice.command_seconds ?? 45;
  $("preRoll").value = voice.pre_roll_seconds ?? 0.7;
  $("minSpeechRms").value = voice.min_speech_rms_threshold ?? 120;
  $("audibleCues").checked = Boolean(voice.audible_cues ?? true);

  $("ttsEnabled").checked = Boolean(tts.enabled ?? true);
  $("ttsProvider").value = tts.provider || "windows";
  $("ttsFallback").value = tts.fallback_provider || "local";
  $("localRate").value = local.rate ?? 185;
  $("elevenVoiceId").value = eleven.voice_id || "";
  $("elevenModel").value = eleven.model_id || "eleven_multilingual_v2";
  $("elevenStability").value = eleven.stability ?? 0.45;
  $("elevenSimilarity").value = eleven.similarity_boost ?? 0.75;

  renderMap("appsList", device.apps || {});
  renderMap("sitesList", device.websites || {});
  renderFolders(device.allowed_folders || []);
  renderVoiceProfiles(eleven.profiles || {}, eleven.active_voice || "");
  renderModes(device.assistant_modes || {});
  renderDashboard(state.dashboard || {});
  renderLive(device, state.dashboard || {}, state.activity || []);
  renderActions();
  bindRange("wakeThreshold", "wakeThresholdValue");
  bindRange("elevenStability", "elevenStabilityValue");
  bindRange("elevenSimilarity", "elevenSimilarityValue");
};

const renderLive = (device, dashboard, activity) => {
  const modes = device.assistant_modes || {};
  const modeOptions = state.mode_options || {};
  const activeMode = modes.active || "command";
  const modeInfo = modeOptions[activeMode] || {};
  const tts = device.tts || {};
  const counts = dashboard.counts || {};
  const tasks = dashboard.tasks || {};
  const reminders = dashboard.reminders || {};

  $("liveModeTitle").textContent = `${modeInfo.label || "Command"} Mode`;
  $("liveModeMetric").textContent = modeInfo.label || activeMode;
  $("liveVoiceMetric").textContent = tts.enabled === false ? "Muted" : providerLabel(tts.provider || "windows");
  $("liveTaskMetric").textContent = counts.open_tasks ?? 0;
  $("liveDueMetric").textContent = counts.due_today ?? 0;
  $("liveFocusText").textContent = dashboard.recommended_focus || "Pick one concrete task";
  $("liveStateLabel").textContent = activeMode === "assist" ? "Low-cost standby" : "Online";

  renderLiveActivity(activity);
  renderList("liveTodayList", [
    ...(tasks.overdue || []).slice(0, 3).map((item) => listItem(item.title, `overdue ${item.due || ""}`.trim())),
    ...(tasks.due_today || []).slice(0, 3).map((item) => listItem(item.title, item.due || "due today")),
    ...(reminders.due_today || []).slice(0, 2).map((item) => listItem(item.title, item.due || "reminder")),
  ]);
};

const providerLabel = (provider) => ({
  elevenlabs: "ElevenLabs",
  windows: "Windows",
  local: "Local",
  none: "Muted",
}[provider] || provider);

const renderLiveActivity = (activity) => {
  const container = $("liveActivityList");
  container.replaceChildren();
  const useful = activity
    .filter((event) => event.status !== "started")
    .slice(-8)
    .reverse();

  if (!useful.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No recent activity.";
    container.append(empty);
    return;
  }

  useful.forEach((event) => {
    const rowElement = document.createElement("div");
    rowElement.className = "timeline-row";
    const dot = document.createElement("span");
    dot.className = `timeline-dot ${event.status || "unknown"}`;
    const body = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = event.command || event.action || "Activity";
    const meta = document.createElement("span");
    meta.textContent = [event.action, event.status].filter(Boolean).join(" | ");
    body.append(title, meta);
    rowElement.append(dot, body);
    container.append(rowElement);
  });
};

const defaultModeSettings = {
  enabled: true,
  use_llm_router: true,
  speak_responses: true,
  continuous_session: false,
  wake_word_required: true,
  session_idle_timeout_seconds: 18,
  session_max_turns: 1,
};

const renderModes = (assistantModes) => {
  const modeOptions = state.mode_options || {};
  const modes = assistantModes.modes || {};
  const realtime = assistantModes.realtime || {};
  const active = $("activeMode");
  active.replaceChildren();

  Object.entries(modeOptions).forEach(([name, info]) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = info.label || name;
    active.append(option);
  });

  active.value = assistantModes.active || "command";
  active.onchange = updateActiveModeCopy;

  const container = $("modeList");
  container.replaceChildren();
  Object.entries(modeOptions).forEach(([name, info]) => {
    container.append(modeCard(name, info, { ...defaultModeSettings, ...(modes[name] || {}) }));
  });

  $("realtimeEnabled").checked = Boolean(realtime.enabled ?? false);
  $("realtimeProvider").value = realtime.provider || "openai";
  $("realtimeModel").value = realtime.model || "gpt-4o-realtime-preview";
  $("realtimeSessionTimeout").value = realtime.session_timeout_seconds ?? 600;
  $("realtimeIdleTimeout").value = realtime.idle_timeout_seconds ?? 45;
  $("realtimeProxyRequired").checked = Boolean(realtime.requires_backend_proxy ?? true);
  updateActiveModeCopy();
};

const updateActiveModeCopy = () => {
  const modeOptions = state?.mode_options || {};
  const info = modeOptions[$("activeMode").value] || {};
  $("activeModeTitle").textContent = info.label || $("activeMode").value;
  $("activeModeDescription").textContent = info.description || "";
};

const modeCard = (name, info, settings) => {
  const card = document.createElement("section");
  card.className = "mode-card";
  card.dataset.mode = name;

  const heading = document.createElement("div");
  heading.className = "mode-card-head";
  const title = document.createElement("div");
  title.innerHTML = `<h3>${escapeHtml(info.label || name)}</h3><p>${escapeHtml(info.description || "")}</p>`;
  heading.append(title);
  heading.append(checkField("enabled", "Enabled", settings.enabled));
  card.append(heading);

  const grid = document.createElement("div");
  grid.className = "settings-grid compact";
  grid.append(
    checkField("use_llm_router", "LLM Router", settings.use_llm_router),
    checkField("speak_responses", "Speak Responses", settings.speak_responses),
    checkField("continuous_session", "Continuous Session", settings.continuous_session),
    checkField("wake_word_required", "Wake Word Required", settings.wake_word_required),
    numberField("session_idle_timeout_seconds", "Idle Timeout", settings.session_idle_timeout_seconds, 1, 600, 1),
    numberField("session_max_turns", "Max Turns", settings.session_max_turns, 1, 100, 1),
  );
  card.append(grid);
  return card;
};

const checkField = (name, labelText, checked) => {
  const label = document.createElement("label");
  label.className = "check-row";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = name;
  input.checked = Boolean(checked);
  label.append(input, document.createTextNode(labelText));
  return label;
};

const numberField = (name, labelText, value, min, max, step) => {
  const label = document.createElement("label");
  label.textContent = labelText;
  const input = document.createElement("input");
  input.type = "number";
  input.name = name;
  input.value = value;
  input.min = min;
  input.max = max;
  input.step = step;
  label.append(input);
  return label;
};

const renderDashboard = (dashboard) => {
  const counts = dashboard.counts || {};
  $("metricTasks").textContent = counts.open_tasks ?? 0;
  $("metricDueToday").textContent = counts.due_today ?? 0;
  $("metricProjects").textContent = counts.active_projects ?? 0;
  $("metricReminders").textContent = counts.open_reminders ?? 0;
  $("metricGmail").textContent = counts.gmail_messages ?? 0;
  $("recommendedFocus").textContent = dashboard.recommended_focus || "Pick one concrete task";
  $("briefText").textContent = dashboard.brief || "No brief available.";

  const tasks = dashboard.tasks || {};
  const reminders = dashboard.reminders || {};
  const projects = dashboard.projects || {};
  const school = dashboard.school || {};
  const gmail = dashboard.gmail || {};

  renderList("dueTodayList", [
    ...(tasks.due_today || []).map((item) => listItem(item.title, item.due || "task")),
    ...(reminders.due_today || []).map((item) => listItem(item.title, item.due || "reminder")),
  ]);
  renderList("upcomingList", [
    ...(tasks.upcoming || []).map((item) => listItem(item.title, item.due || "task")),
    ...(reminders.upcoming || []).map((item) => listItem(item.title, item.due || "reminder")),
  ]);
  renderList("projectList", (projects.active || []).map((item) => (
    listItem(item.name, [item.status || "active", item.due ? `due ${item.due}` : "", item.next_action ? `next: ${item.next_action}` : ""].filter(Boolean).join(" | "))
  )));
  renderList("schoolList", [
    ...(school.sources || []).map((source) => listItem(source, "source")),
    ...(school.courses || []).map((course) => listItem(course, "course")),
  ]);
  renderList("reminderList", (reminders.open || []).map((item) => (
    listItem(item.title, item.due ? `due ${item.due}` : "open")
  )));
  const gmailItems = (gmail.messages || []).map((item) => (
    listItem(item.subject || "No subject", [item.from || "unknown sender", item.date || ""].filter(Boolean).join(" | "))
  ));
  renderList("gmailList", gmailItems.length ? gmailItems : [
    listItem(gmail.configured ? "No matching email found" : "Gmail not connected", gmail.message || gmail.status || "Run python main.py --gmail-connect"),
  ]);
};

const listItem = (title, meta) => ({ title, meta });

const renderList = (containerId, items) => {
  const container = $(containerId);
  container.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "Nothing here yet.";
    container.append(empty);
    return;
  }

  items.forEach((item) => {
    const entry = document.createElement("div");
    entry.className = "list-item";
    const title = document.createElement("strong");
    title.textContent = item.title || "Untitled";
    const meta = document.createElement("span");
    meta.textContent = item.meta || "";
    entry.append(title, meta);
    container.append(entry);
  });
};

const renderMap = (containerId, values) => {
  const container = $(containerId);
  container.replaceChildren();
  Object.entries(values).forEach(([name, target]) => {
    container.append(row([
      { value: name, placeholder: "Name" },
      { value: target, placeholder: "Path or URL" },
    ]));
  });
};

const renderVoiceProfiles = (profiles, activeVoice) => {
  const container = $("voiceProfilesList");
  const active = $("elevenActiveVoice");
  container.replaceChildren();
  active.replaceChildren();

  const none = document.createElement("option");
  none.value = "";
  none.textContent = "Manual Voice ID";
  active.append(none);

  Object.entries(profiles).forEach(([name, profile]) => {
    container.append(voiceProfileRow(name, profile.voice_id || "", profile.description || ""));
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    active.append(option);
  });

  active.value = activeVoice || "";
  active.onchange = () => {
    const selected = profiles[active.value];
    if (selected?.voice_id) {
      $("elevenVoiceId").value = selected.voice_id;
    }
  };
};

const renderFolders = (folders) => {
  const container = $("foldersList");
  container.replaceChildren();
  folders.forEach((folder) => {
    container.append(row([{ value: folder, placeholder: "Folder path" }]));
  });
};

const row = (fields) => {
  const wrapper = document.createElement("div");
  wrapper.className = "row";

  fields.forEach((field) => {
    const input = document.createElement("input");
    input.value = field.value;
    input.autocomplete = "off";
    input.placeholder = field.placeholder;
    if (field.ariaLabel) {
      input.setAttribute("aria-label", field.ariaLabel);
    }
    wrapper.append(input);
  });

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "remove";
  remove.textContent = "X";
  remove.title = "Remove";
  remove.addEventListener("click", () => wrapper.remove());
  wrapper.append(remove);
  return wrapper;
};

const voiceProfileRow = (name = "", voiceId = "", description = "") => {
  const wrapper = row([
    { value: name, placeholder: "Profile name", ariaLabel: "Voice profile name" },
    { value: voiceId, placeholder: "ElevenLabs voice ID", ariaLabel: "ElevenLabs voice ID" },
    { value: description, placeholder: "Description", ariaLabel: "Voice profile description" },
  ]);
  wrapper.classList.add("voice-profile-row");
  return wrapper;
};

const readMap = (containerId) => {
  const result = {};
  $(containerId).querySelectorAll(".row").forEach((entry) => {
    const inputs = entry.querySelectorAll("input");
    const key = inputs[0].value.trim().toLowerCase();
    const value = inputs[1].value.trim();
    if (key && value) {
      result[key] = value;
    }
  });
  return result;
};

const readFolders = () => {
  const result = [];
  $("foldersList").querySelectorAll(".row").forEach((entry) => {
    const value = entry.querySelector("input").value.trim();
    if (value) {
      result.push(value);
    }
  });
  return result;
};

const readVoiceProfiles = () => {
  const result = {};
  $("voiceProfilesList").querySelectorAll(".row").forEach((entry) => {
    const inputs = entry.querySelectorAll("input");
    const name = inputs[0].value.trim();
    const voiceId = inputs[1].value.trim();
    const description = inputs[2].value.trim();
    if (name && voiceId) {
      result[name] = { voice_id: voiceId };
      if (description) {
        result[name].description = description;
      }
    }
  });
  return result;
};

const readModes = () => {
  const modes = {};
  $("modeList").querySelectorAll(".mode-card").forEach((card) => {
    const mode = card.dataset.mode;
    modes[mode] = {
      enabled: card.querySelector("input[name='enabled']").checked,
      use_llm_router: card.querySelector("input[name='use_llm_router']").checked,
      speak_responses: card.querySelector("input[name='speak_responses']").checked,
      continuous_session: card.querySelector("input[name='continuous_session']").checked,
      wake_word_required: card.querySelector("input[name='wake_word_required']").checked,
      session_idle_timeout_seconds: Number(card.querySelector("input[name='session_idle_timeout_seconds']").value),
      session_max_turns: Number.parseInt(card.querySelector("input[name='session_max_turns']").value, 10),
    };
  });
  return {
    active: $("activeMode").value,
    modes,
    realtime: {
      enabled: boolValue("realtimeEnabled"),
      provider: $("realtimeProvider").value,
      model: $("realtimeModel").value,
      session_timeout_seconds: Number.parseInt($("realtimeSessionTimeout").value, 10),
      idle_timeout_seconds: Number.parseInt($("realtimeIdleTimeout").value, 10),
      requires_backend_proxy: boolValue("realtimeProxyRequired"),
    },
  };
};

const renderActions = () => {
  const container = $("actionsList");
  container.replaceChildren();
  const permissions = state.permissions || {};
  const bucketByAction = {};
  ["auto_allow", "require_confirmation", "blocked"].forEach((bucket) => {
    (permissions[bucket] || []).forEach((action) => {
      bucketByAction[action] = bucket;
    });
  });

  Object.entries(state.actions || {}).forEach(([name, definition]) => {
    const wrapper = document.createElement("div");
    wrapper.className = "policy-row";
    wrapper.dataset.action = name;

    const title = document.createElement("div");
    title.innerHTML = `<div class="policy-name">${escapeHtml(name)}</div><div class="policy-risk">${escapeHtml(definition.risk)}</div>`;

    const description = document.createElement("div");
    description.className = "policy-description";
    description.textContent = definition.description;

    const select = document.createElement("select");
    select.innerHTML = `
      <option value="auto_allow">Auto Allow</option>
      <option value="require_confirmation">Confirm</option>
      <option value="blocked">Blocked</option>
    `;
    select.value = bucketByAction[name] || definition.default_policy;

    wrapper.append(title, description, select);
    container.append(wrapper);
  });
};

const readPermissions = () => {
  const result = {
    auto_allow: [],
    require_confirmation: [],
    blocked: [],
  };
  $("actionsList").querySelectorAll(".policy-row").forEach((rowElement) => {
    const action = rowElement.dataset.action;
    const bucket = rowElement.querySelector("select").value;
    result[bucket].push(action);
  });
  return result;
};

const saveDevice = async (payload) => {
  setStatus("Saving");
  const result = await api("/api/device", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.device = result.device;
  render();
  setStatus("Saved");
};

const setActiveMode = async (mode) => {
  const current = state.device?.assistant_modes || {};
  await saveDevice({
    assistant_modes: {
      ...current,
      active: mode,
    },
  });
};

const savePermissions = async () => {
  setStatus("Saving");
  const result = await api("/api/permissions", {
    method: "POST",
    body: JSON.stringify(readPermissions()),
  });
  state.permissions = result.permissions;
  renderActions();
  setStatus("Saved");
};

const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (char) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[char]));

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => showTab(tab.dataset.tab));
  });

  $("refreshButton").addEventListener("click", () => loadState().catch((error) => setStatus(error.message, true)));
  $("refreshDashboard").addEventListener("click", () => loadState().catch((error) => setStatus(error.message, true)));
  $("liveRefresh").addEventListener("click", () => loadState().catch((error) => setStatus(error.message, true)));
  $("liveConversation").addEventListener("click", () => setActiveMode("conversation").catch((error) => setStatus(error.message, true)));
  $("liveCommand").addEventListener("click", () => setActiveMode("command").catch((error) => setStatus(error.message, true)));
  $("liveAssist").addEventListener("click", () => setActiveMode("assist").catch((error) => setStatus(error.message, true)));

  $("saveModes").addEventListener("click", () => {
    saveDevice({
      assistant_modes: readModes(),
    }).catch((error) => setStatus(error.message, true));
  });

  $("saveVoice").addEventListener("click", () => {
    saveDevice({
      voice: {
        wake_word: $("wakeWord").value,
        wake_threshold: numberValue("wakeThreshold"),
        silence_seconds: numberValue("silenceSeconds"),
        start_timeout_seconds: numberValue("startTimeout"),
        command_seconds: numberValue("commandSeconds"),
        pre_roll_seconds: numberValue("preRoll"),
        min_speech_rms_threshold: Number.parseInt($("minSpeechRms").value, 10),
        audible_cues: boolValue("audibleCues"),
      },
    }).catch((error) => setStatus(error.message, true));
  });

  $("saveTts").addEventListener("click", () => {
    saveDevice({
      tts: {
        enabled: boolValue("ttsEnabled"),
        provider: $("ttsProvider").value,
        fallback_provider: $("ttsFallback").value,
        local: {
          rate: Number.parseInt($("localRate").value, 10),
        },
        elevenlabs: {
          active_voice: $("elevenActiveVoice").value,
          voice_id: $("elevenVoiceId").value,
          profiles: readVoiceProfiles(),
          model_id: $("elevenModel").value,
          stability: numberValue("elevenStability"),
          similarity_boost: numberValue("elevenSimilarity"),
        },
      },
    }).catch((error) => setStatus(error.message, true));
  });

  $("saveTargets").addEventListener("click", () => {
    saveDevice({
      apps: readMap("appsList"),
      websites: readMap("sitesList"),
      allowed_folders: readFolders(),
    }).catch((error) => setStatus(error.message, true));
  });

  $("saveVoices").addEventListener("click", () => {
    saveDevice({
      tts: {
        provider: $("ttsProvider").value,
        enabled: boolValue("ttsEnabled"),
        elevenlabs: {
          active_voice: $("elevenActiveVoice").value,
          voice_id: $("elevenVoiceId").value,
          profiles: readVoiceProfiles(),
          model_id: $("elevenModel").value,
          stability: numberValue("elevenStability"),
          similarity_boost: numberValue("elevenSimilarity"),
        },
      },
    }).catch((error) => setStatus(error.message, true));
  });

  $("saveSafety").addEventListener("click", () => {
    savePermissions().catch((error) => setStatus(error.message, true));
  });

  $("addApp").addEventListener("click", () => $("appsList").append(row([
    { value: "", placeholder: "Name" },
    { value: "", placeholder: "Path or URL" },
  ])));
  $("addSite").addEventListener("click", () => $("sitesList").append(row([
    { value: "", placeholder: "Name" },
    { value: "", placeholder: "URL" },
  ])));
  $("addFolder").addEventListener("click", () => $("foldersList").append(row([
    { value: "", placeholder: "Folder path" },
  ])));
  $("addVoiceProfile").addEventListener("click", () => $("voiceProfilesList").append(voiceProfileRow()));

  loadState().catch((error) => setStatus(error.message, true));
});
