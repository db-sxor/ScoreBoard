const teamList = document.getElementById("team-list");
const eventList = document.getElementById("event-list");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[c]));
}
function formatTime(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleTimeString("ko-KR", {hour:"2-digit", minute:"2-digit"});
}
function renderTeams(teams) {
  const sorted = [...teams].sort((a,b) => b.score - a.score || a.id - b.id);
  const ranks = new Map(sorted.map((t,i) => [t.id, i + 1]));
  teamList.innerHTML = teams.map(team => {
    const rank = ranks.get(team.id);
    const rankClass = rank === 1 ? "rank-first" : "";
    return `<article class="team-card ${rankClass}">
      <div class="team-card-top"><span class="team-name">${escapeHtml(team.name)}</span>
      <span class="rank-badge">${rank}위</span></div>
      <div class="team-score">${Number(team.score).toLocaleString("ko-KR")}<small>점</small></div>
      <div class="score-track"><span style="width:${Math.max(4, Math.min(100, team.score > 0 ? team.score / Math.max(1, ...teams.map(t=>t.score)) * 100 : 4))}%"></span></div>
    </article>`;
  }).join("");
}
function renderEvents(events) {
  if (!events.length) {
    eventList.innerHTML = '<div class="empty-state">아직 점수 기록이 없습니다.</div>';
    return;
  }
  eventList.innerHTML = events.map(event => {
    const positive = event.points > 0;
    return `<div class="event-row">
      <div class="event-main"><strong>${escapeHtml(event.team_name)}</strong></div>
      <div class="event-right"><strong class="${positive ? "positive" : "negative"}">${positive ? "+" : ""}${event.points}점</strong><time>${formatTime(event.created_at)}</time></div>
    </div>`;
  }).join("");
}
async function refresh() {
  try {
    const response = await fetch("/api/scoreboard", {cache:"no-store"});
    if (!response.ok) throw new Error("점수판을 불러오지 못했습니다.");
    const data = await response.json();
    renderTeams(data.teams);
    renderEvents(data.events);
  } catch (error) {
    teamList.innerHTML = `<div class="loading-card">${escapeHtml(error.message)} · 연결을 확인해 주세요.</div>`;
  }
}
refresh();
setInterval(refresh, 2000);
