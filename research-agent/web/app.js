const state = { projects: [], activeProjectId: null };

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

function renderProjects() {
  const list = document.getElementById('project-list');
  if (!state.projects.length) {
    list.innerHTML = '<div class="empty-state">No projects yet.</div>';
    return;
  }

  list.innerHTML = '';
  state.projects.forEach((project) => {
    const pill = document.createElement('div');
    pill.className = `project-pill ${project.id === state.activeProjectId ? 'active' : ''}`;
    pill.innerHTML = `<strong>${project.title}</strong><span>${project.research_area}</span>`;
    pill.addEventListener('click', () => selectProject(project.id));
    list.appendChild(pill);
  });
}

function renderOverview(project) {
  const overview = document.getElementById('project-overview');
  if (!project) {
    overview.innerHTML = '<div class="empty-state">Select or create a project to begin.</div>';
    return;
  }

  overview.innerHTML = `
    <h4>${project.title}</h4>
    <p>${project.research_area}</p>
    <p><strong>Papers:</strong> ${project.papers?.length || 0}</p>
    <p><strong>Status:</strong> ${project.status || 'created'}</p>
  `;
}

function renderWorkspace(project) {
  const workspace = document.getElementById('project-workspace');
  if (!project) {
    workspace.style.display = 'none';
    return;
  }

  workspace.style.display = 'block';
  document.getElementById('paper-list').innerHTML = '';
  document.getElementById('suggestion-list').innerHTML = '';

  if (project.papers?.length) {
    const heading = document.createElement('h3');
    heading.textContent = 'Papers';
    document.getElementById('paper-list').appendChild(heading);
    project.papers.forEach((paper) => {
      const card = document.createElement('div');
      card.className = 'paper-card';
      card.innerHTML = `
        <h4>${paper.title}</h4>
        <p>${paper.summary}</p>
        <p><small>${paper.authors?.join(', ') || 'Unknown authors'} • ${paper.published || 'Unknown'}</small></p>
      `;
      document.getElementById('paper-list').appendChild(card);
    });
  }

  if (project.suggestions?.length) {
    const heading = document.createElement('h3');
    heading.textContent = 'Suggested papers';
    document.getElementById('suggestion-list').appendChild(heading);
    project.suggestions.forEach((suggestion) => {
      const card = document.createElement('div');
      card.className = 'paper-card';
      card.innerHTML = `
        <h4>${suggestion.title}</h4>
        <p>${suggestion.reason}</p>
        <button class="secondary suggestion-btn" data-id="${suggestion.id}">Add paper</button>
      `;
      card.querySelector('button').addEventListener('click', () => addSuggestedPaper(project.id, suggestion.id));
      document.getElementById('suggestion-list').appendChild(card);
    });
  }
}

async function loadProjects() {
  const projects = await api('/api/projects');
  state.projects = projects;
  if (!state.activeProjectId && projects.length) {
    state.activeProjectId = projects[0].id;
  }
  renderProjects();
  const active = projects.find((p) => p.id === state.activeProjectId) || null;
  renderOverview(active);
  renderWorkspace(active);
}

async function selectProject(projectId) {
  state.activeProjectId = projectId;
  renderProjects();
  const project = state.projects.find((p) => p.id === projectId) || null;
  renderOverview(project);
  renderWorkspace(project);
}

async function createProject(event) {
  event.preventDefault();
  const payload = {
    title: document.getElementById('project-title').value,
    research_area: document.getElementById('research-area').value,
    arxiv_input: document.getElementById('arxiv-input').value,
    user_id: document.getElementById('user-id').value,
  };
  const response = await api('/api/projects', { method: 'POST', body: JSON.stringify(payload) });
  state.projects.unshift(response.project);
  state.activeProjectId = response.project.id;
  renderProjects();
  renderOverview(response.project);
  renderWorkspace(response.project);
}

async function addPapers(event) {
  event.preventDefault();
  if (!state.activeProjectId) return;
  const payload = {
    arxiv_input: document.getElementById('extra-arxiv-input').value,
    user_id: document.getElementById('user-id').value,
  };
  const response = await api(`/api/projects/${state.activeProjectId}/add-papers`, { method: 'POST', body: JSON.stringify(payload) });
  const updatedProject = response.project;
  const index = state.projects.findIndex((p) => p.id === updatedProject.id);
  if (index >= 0) state.projects[index] = updatedProject;
  renderProjects();
  renderOverview(updatedProject);
  renderWorkspace(updatedProject);
}

async function addSuggestedPaper(projectId, paperId) {
  const response = await api(`/api/projects/${projectId}/suggestions/${paperId}`, { method: 'POST' });
  const updatedProject = response.project;
  const index = state.projects.findIndex((p) => p.id === updatedProject.id);
  if (index >= 0) state.projects[index] = updatedProject;
  renderProjects();
  renderOverview(updatedProject);
  renderWorkspace(updatedProject);
}

async function sendChat(event) {
  event.preventDefault();
  if (!state.activeProjectId) return;
  const chatInput = document.getElementById('chat-input');
  const message = chatInput.value.trim();
  if (!message) return;

  const log = document.getElementById('chat-log');
  const userBubble = document.createElement('div');
  userBubble.className = 'message user';
  userBubble.textContent = message;
  log.appendChild(userBubble);
  chatInput.value = '';

  const response = await api(`/api/projects/${state.activeProjectId}/chat`, { method: 'POST', body: JSON.stringify({ user_query: message, user_id: document.getElementById('user-id').value }) });
  const assistantBubble = document.createElement('div');
  assistantBubble.className = 'message assistant';
  assistantBubble.textContent = response.reply;
  log.appendChild(assistantBubble);
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('create-project-form').addEventListener('submit', createProject);
  document.getElementById('add-papers-form').addEventListener('submit', addPapers);
  document.getElementById('chat-form').addEventListener('submit', sendChat);
  loadProjects().catch((error) => {
    document.getElementById('project-overview').innerHTML = `<div class="empty-state">${error.message}</div>`;
  });
});
