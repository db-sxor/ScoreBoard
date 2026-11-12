let csrfToken = "";
let selectedTeam = null;
let selectedPoints = 0;
let teamsCache = [];

const $ = id => document.getElementById(id);
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({
    "&": "&", "<": "<", ">": ">", '"': '"', "'": "'"
  }[c]));
}
function formatTime(value) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("ko-KR", {month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit"});
}
async function api(url, body = {}) {
  const response = await fetch(url, {
    method:"POST",
    headers:{"Content-Type":"application/json", "X-CSRF-Token":csrfToken},
    body:JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "요청에 실패했습니다.");
  return data;
}
function updateSummary() {
  const team = teamsCache.find(t => t.id === selectedTeam);
  const pv = $("points-value");
  pv.textContent = `${selectedPoints > 0 ? "+" : ""}${selectedPoints}`;
  pv.classList.toggle("zero", selectedPoints === 0);
  pv.classList.toggle("plus", selectedPoints > 0);
  pv.classList.toggle("minus", selectedPoints < 0);
  
  if (!team || selectedPoints === 0) {
    $("submit-score").disabled = true;
    return;
  }
  $("submit-score").disabled = false;
}
function renderTeamButtons(teams) {
  teamsCache = teams;
  $("admin-teams").innerHTML = teams.map(t =>
    `<button type="button" class="team-choice ${selectedTeam === t.id ? "active" : ""}" data-team="${t.id}">${escapeHtml(t.name)}</button>`
  ).join("");
  $("admin-teams").querySelectorAll("[data-team]").forEach(button => {
    button.addEventListener("click", () => {
      selectedTeam = Number(button.dataset.team);
      renderTeamButtons(teamsCache);
      updateSummary();
    });
  });
  teams.forEach(t => { $(`team-name-${t.id}`).value = t.name; });
  updateSummary();
}
function renderHistory(events) {
  const target = $("admin-event-list");
  if (!events.length) {
    target.innerHTML = '<div class="empty-state">아직 점수 기록이 없습니다.</div>';
    return;
  }
  target.innerHTML = events.map(e => `
    <div class="event-row ${e.undone ? "undone" : ""}">
      <div class="event-main"><strong>${escapeHtml(e.team_name)}</strong>${e.undone ? "<span>취소됨</span>" : ""}</div>
      <div class="event-right"><strong class="${e.points > 0 ? "positive" : "negative"}">${e.points > 0 ? "+" : ""}${e.points}점</strong><time>${formatTime(e.created_at)}</time></div>
    </div>`).join("");
}
async function refreshAdmin() {
  const response = await fetch("/api/admin/state", {cache:"no-store"});
  if (response.status === 401) { location.href = "/admin/login"; return; }
  const data = await response.json();
  csrfToken = data.csrf_token;
  renderTeamButtons(data.teams);
  renderHistory(data.events);
  $("undo-score").disabled = !data.can_undo;
}
function changePoints(delta) {
  selectedPoints = Math.max(-1000, Math.min(1000, selectedPoints + delta));
  updateSummary();
}
$("points-up").addEventListener("click", () => changePoints(1));
$("points-down").addEventListener("click", () => changePoints(-1));
$("submit-score").addEventListener("click", async () => {
  const team = teamsCache.find(t => t.id === selectedTeam);
  if (!team || selectedPoints === 0) return;
  const label = `${team.name} ${selectedPoints > 0 ? "+" : ""}${selectedPoints}점을 등록하시겠습니까?`;
  if (!confirm(label)) return;
  try {
    await api("/api/admin/score", {team_id:selectedTeam, points:selectedPoints});
    selectedTeam = null;
    selectedPoints = 0;
    await refreshAdmin();
    alert("점수가 등록되었습니다.");
  } catch (e) { alert(e.message); }
});
$("save-team-names").addEventListener("click", async () => {
  const names = [1,2,3].map(i => $(`team-name-${i}`).value.trim());
  if (names.some(n => !n)) return alert("팀 이름을 모두 입력해 주세요.");
  if (!confirm("팀 이름을 변경하시겠습니까?")) return;
  try { await api("/api/admin/teams", {names}); await refreshAdmin(); alert("팀 이름을 저장했습니다."); }
  catch (e) { alert(e.message); }
});
$("undo-score").addEventListener("click", async () => {
  if (!confirm("가장 최근 점수 입력을 취소하시겠습니까?")) return;
  try { await api("/api/admin/undo"); await refreshAdmin(); alert("마지막 점수를 취소했습니다."); }
  catch (e) { alert(e.message); }
});
$("reset-scores").addEventListener("click", async () => {
  if (!confirm("정말 모든 점수를 초기화하시겠습니까? 이 작업은 점수판에서 모든 점수를 0점으로 만듭니다.")) return;
  if (!confirm("초기화를 한 번 더 확인합니다. 계속하시겠습니까?")) return;
  try { await api("/api/admin/reset"); await refreshAdmin(); alert("모든 점수를 초기화했습니다."); }
  catch (e) { alert(e.message); }
});
refreshAdmin().catch(e => alert("관리자 정보를 불러오지 못했습니다: " + e.message));