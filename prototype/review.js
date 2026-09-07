let currentPack = null;
let completedPack = null;

const $ = (id) => document.getElementById(id);

$("packFile").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const text = await file.text();
    const pack = JSON.parse(text);
    validatePack(pack);
    currentPack = structuredClone(pack);
    completedPack = null;
    renderPack(currentPack);
    $("loadStatus").textContent = `Loaded ${pack.audience} review pack for ${pack.problem_id}.`;
    $("reviewApp").classList.remove("hidden");
    $("copyResponse").disabled = true;
    $("saveResponse").disabled = true;
    $("responsePreviewPanel").classList.add("hidden");
  } catch (error) {
    currentPack = null;
    $("reviewApp").classList.add("hidden");
    $("loadStatus").textContent = `Could not load pack: ${error.message}`;
  }
});

$("reviewForm").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!currentPack) return;
  try {
    completedPack = collectResponse(currentPack);
    $("responsePreview").textContent = JSON.stringify(completedPack, null, 2);
    $("responsePreviewPanel").classList.remove("hidden");
    $("copyResponse").disabled = false;
    $("saveResponse").disabled = false;
    $("formStatus").textContent = "Response is complete. Return the resulting JSON to the curator; this page does not submit it automatically.";
  } catch (error) {
    completedPack = null;
    $("formStatus").textContent = error.message;
    $("copyResponse").disabled = true;
    $("saveResponse").disabled = true;
  }
});

$("copyResponse").addEventListener("click", async () => {
  if (!completedPack) return;
  try {
    await navigator.clipboard.writeText(JSON.stringify(completedPack, null, 2));
    $("formStatus").textContent = "Completed review JSON copied.";
  } catch {
    $("formStatus").textContent = "Clipboard access was unavailable; use Save response JSON instead.";
  }
});

$("saveResponse").addEventListener("click", () => {
  if (!completedPack) return;
  const blob = new Blob([JSON.stringify(completedPack, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${sanitize(currentPack.problem_id)}-${currentPack.audience}-review.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  $("formStatus").textContent = "Completed review JSON prepared.";
});

function validatePack(pack) {
  if (!pack || pack.schema !== "problem-review-pack/v0.1") throw new Error("Unsupported review-pack schema.");
  if (!["owner", "reviewer", "solver"].includes(pack.audience)) throw new Error("Invalid review audience.");
  if (!pack.problem_id || !pack.problem || pack.problem.id !== pack.problem_id) throw new Error("Problem identity mismatch.");
  if (!pack.rubric || !Array.isArray(pack.rubric.items) || pack.rubric.items.length === 0) throw new Error("Review pack has no rubric items.");
  if (!pack.response || !Array.isArray(pack.response.item_scores)) throw new Error("Review pack has no response template.");
}

function renderPack(pack) {
  const problem = pack.problem;
  $("audienceLabel").textContent = `${pack.audience.toUpperCase()} REVIEW · ${pack.problem_id}`;
  $("problemTitle").textContent = problem.title || "Untitled problem";
  $("problemStatus").textContent = problem.status || "unknown";
  $("privacyNote").textContent = pack.privacy_note || "";
  $("observedCondition").textContent = problem.observed_condition || "Not specified.";
  $("unresolvedCore").textContent = problem.unresolved_core || "Not specified.";
  $("authorityBoundary").textContent = problem.authority_boundary || "Not specified.";
  renderList($("uncertaintyList"), problem.disputes_uncertainty || [], "No explicit uncertainty items provided.");
  renderList($("instructions"), pack.instructions || [], "No instructions provided.");

  $("rubricName").textContent = humanize(pack.rubric.name || "review rubric");
  $("rubricScoring").textContent = pack.rubric.scoring || "";
  const rubricRoot = $("rubricItems");
  rubricRoot.innerHTML = "";
  pack.rubric.items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "rubric-item";
    row.innerHTML = `<strong>${index + 1}. ${escapeHtml(item)}</strong><div class="score-row"><label><input type="radio" name="score-${index}" value="1" /> Yes / supported</label><label><input type="radio" name="score-${index}" value="0" /> No / not supported</label></div>`;
    rubricRoot.appendChild(row);
  });

  const stages = $("stageSummary");
  stages.innerHTML = "";
  const profiles = pack.stage_profiles || [];
  if (!profiles.length) {
    stages.innerHTML = '<article class="review-card"><p>No stage profiles are exposed for this pack.</p></article>';
  } else {
    profiles.forEach((profile) => {
      const card = document.createElement("article");
      card.className = "review-card";
      card.innerHTML = `<p class="eyebrow">${escapeHtml(profile.stage || "stage")}</p><h3>${escapeHtml(profile.question || profile.subproblem_id || "Contribution")}</h3><p>${escapeHtml(profile.work_mode || "")}</p><small>${escapeHtml((profile.expected_outputs || []).join(" · "))}</small>`;
      stages.appendChild(card);
    });
  }

  $("ownerReviewerFields").classList.toggle("hidden", pack.audience === "solver");
  $("solverFields").classList.toggle("hidden", pack.audience !== "solver");
  const select = $("selectedSubproblem");
  select.innerHTML = '<option value="">No path selected</option>';
  (problem.subproblems || []).forEach((subproblem) => {
    const option = document.createElement("option");
    option.value = subproblem.id;
    option.textContent = `${subproblem.title} (${subproblem.kind})`;
    select.appendChild(option);
  });

  $("disagreements").value = "";
  $("materialErrors").value = "";
  $("coachingReceived").checked = false;
  $("reframeRequired").checked = false;
  $("publishRecommendation").value = "undecided";
  $("reviewNotes").value = "";
  $("minutesToEdge").value = "";
  $("usefulness").value = "";
  $("seriousAttempt").checked = false;
  $("abandoned").checked = false;
  $("abandonmentReason").value = "";
  $("observerNotes").value = "";
  $("formStatus").textContent = "";
}

function collectResponse(pack) {
  const copy = structuredClone(pack);
  const scores = pack.rubric.items.map((_, index) => {
    const selected = document.querySelector(`input[name="score-${index}"]:checked`);
    if (!selected) throw new Error(`Complete rubric item ${index + 1} before preparing the response.`);
    return Number(selected.value);
  });

  copy.response.item_scores = scores;
  copy.response.disagreement_notes = lines($("disagreements").value);
  copy.response.material_errors = lines($("materialErrors").value);
  copy.response.coaching_received = $("coachingReceived").checked;

  if (pack.audience === "solver") {
    const minutes = optionalNumber($("minutesToEdge").value, 0, Infinity, "Minutes to useful edge");
    const usefulness = optionalNumber($("usefulness").value, 0, 1, "Usefulness rating");
    const selected = $("selectedSubproblem").value || null;
    if ($("seriousAttempt").checked && !selected) throw new Error("A serious attempt must identify the selected contribution path.");
    copy.response.selected_subproblem_id = selected;
    copy.response.minutes_to_useful_edge = minutes;
    copy.response.usefulness_rating = usefulness;
    copy.response.serious_attempt = $("seriousAttempt").checked;
    copy.response.abandoned = $("abandoned").checked;
    copy.response.abandonment_reason = $("abandonmentReason").value.trim();
    copy.response.observer_notes = $("observerNotes").value.trim();
    copy.response.arm = copy.response.arm || "problem_packet";
  } else {
    copy.response.reframe_required = $("reframeRequired").checked;
    copy.response.publish_recommendation = $("publishRecommendation").value;
    copy.response.review_notes = $("reviewNotes").value.trim();
  }
  return copy;
}

function optionalNumber(raw, min, max, label) {
  if (raw === "") return null;
  const value = Number(raw);
  if (!Number.isFinite(value) || value < min || value > max) throw new Error(`${label} must be between ${min} and ${max === Infinity ? "a valid positive value" : max}.`);
  return value;
}

function lines(value) {
  return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function renderList(root, values, fallback) {
  root.innerHTML = "";
  if (!values.length) {
    const li = document.createElement("li");
    li.textContent = fallback;
    root.appendChild(li);
    return;
  }
  values.forEach((value) => {
    const li = document.createElement("li");
    li.textContent = value;
    root.appendChild(li);
  });
}

function humanize(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function sanitize(value) {
  return value.replace(/[^a-z0-9._-]+/gi, "-").replace(/^-+|-+$/g, "");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}
