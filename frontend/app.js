// ─────────────────────────────────────────────────────────────
//  app.js  —  Blog Frontend JavaScript
//  Connects to Django REST API at API_BASE
// ─────────────────────────────────────────────────────────────

const API_BASE = 'http://127.0.0.1:8000/api';  // Change this to your deployed URL

// ── STATE ─────────────────────────────────────────────────────
// We keep a simple "state" object so all functions can share data
const state = {
  user: null,           // logged-in user object (null if not logged in)
  accessToken: null,    // JWT access token
  refreshToken: null,   // JWT refresh token
  posts: [],            // all fetched posts
  filteredPosts: [],    // posts after search/tag filter
  currentPost: null,    // post being viewed
  editingPostId: null,  // post being edited (null = creating new)
  currentPage: 1,
  postsPerPage: 9,
  activeTag: null,      // currently selected tag filter
  categories: [],
  tags: [],
};

// ─────────────────────────────────────────────────────────────
//  HELPER: API CALL
//  Wraps fetch() so we don't repeat headers + token logic
// ─────────────────────────────────────────────────────────────
async function apiCall(endpoint, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json' };

  // Attach JWT token if we have one
  if (state.accessToken) {
    headers['Authorization'] = `Bearer ${state.accessToken}`;
  }

  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);

  const response = await fetch(`${API_BASE}${endpoint}`, options);

  let data = null;

  if (response.status !== 204) {
    data = await response.json();
  }

  // If access token expired, try to refresh it automatically
  if (response.status === 401 && state.refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry the original request with new token
      headers['Authorization'] = `Bearer ${state.accessToken}`;
      const retry = await fetch(`${API_BASE}${endpoint}`, { method, headers, body: body ? JSON.stringify(body) : null });
      return await retry.json();
    }
  }

  return { data, status: response.status, ok: response.ok };
}

// Try to get a new access token using the refresh token
async function refreshAccessToken() {
  const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: state.refreshToken }),
  });
  if (response.ok) {
    const data = await response.json();
    state.accessToken = data.access;
    localStorage.setItem('accessToken', data.access);
    return true;
  }
  // Refresh token also expired — log user out
  logout();
  return false;
}

// ─────────────────────────────────────────────────────────────
//  PAGE NAVIGATION
//  Shows one page div, hides all others
// ─────────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(`page-${name}`).classList.add('active');

  // Load page-specific data
  if (name === 'home') loadPosts();
  if (name === 'dashboard') loadMyPosts();
  if (name === 'write' && !state.editingPostId) clearWriteForm();

  window.scrollTo(0, 0);
}

// ─────────────────────────────────────────────────────────────
//  AUTH: LOGIN, REGISTER, LOGOUT
// ─────────────────────────────────────────────────────────────
async function login() {
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  const errorEl = document.getElementById('loginError');
  errorEl.style.display = 'none';

  const res = await apiCall('/auth/login/', 'POST', { email, password });

  if (res.ok) {
    // Save tokens and user info
    state.accessToken = res.data.access;
    state.refreshToken = res.data.refresh;
    state.user = res.data.user;

    // Save to localStorage so login persists on page refresh
    localStorage.setItem('accessToken', res.data.access);
    localStorage.setItem('refreshToken', res.data.refresh);
    localStorage.setItem('user', JSON.stringify(res.data.user));

    updateNavbar();
    showPage('home');
  } else {
    const msg = res.data.detail || 'Invalid email or password.';
    errorEl.textContent = msg;
    errorEl.style.display = 'block';
  }
}

async function register() {
  const username = document.getElementById('regUsername').value;
  const email = document.getElementById('regEmail').value;
  const password = document.getElementById('regPassword').value;
  const password2 = document.getElementById('regPassword2').value;
  const errorEl = document.getElementById('registerError');
  errorEl.style.display = 'none';

  const res = await apiCall('/auth/register/', 'POST', { username, email, password, password2 });

  if (res.ok) {
    // Auto-login after registration
    state.accessToken = res.data.tokens.access;
    state.refreshToken = res.data.tokens.refresh;
    state.user = res.data.user;

    localStorage.setItem('accessToken', res.data.tokens.access);
    localStorage.setItem('refreshToken', res.data.tokens.refresh);
    localStorage.setItem('user', JSON.stringify(res.data.user));

    updateNavbar();
    showPage('home');
  } else {
    // Collect all error messages from DRF
    const errors = Object.values(res.data).flat().join(' ');
    errorEl.textContent = errors;
    errorEl.style.display = 'block';
  }
}

async function logout() {
  // Tell the API to blacklist the refresh token
  if (state.refreshToken) {
    await apiCall('/auth/logout/', 'POST', { refresh: state.refreshToken });
  }

  // Clear everything from memory and localStorage
  state.user = null;
  state.accessToken = null;
  state.refreshToken = null;
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');

  updateNavbar();
  showPage('home');
}

// Show/hide nav items based on login state
function updateNavbar() {
  const loggedIn = !!state.user;

  document.getElementById('navLogin').style.display = loggedIn ? 'none' : 'inline';
  document.getElementById('navRegister').style.display = loggedIn ? 'none' : 'inline';
  document.getElementById('navWrite').style.display = loggedIn ? 'inline' : 'none';
  document.getElementById('navDashboard').style.display = loggedIn ? 'inline' : 'none';
  document.getElementById('navLogout').style.display = loggedIn ? 'inline' : 'none';
  document.getElementById('navUser').style.display = loggedIn ? 'inline' : 'none';

  if (loggedIn) {
    document.getElementById('navUser').textContent = `Hi, ${state.user.username}`;
  }
}

// ─────────────────────────────────────────────────────────────
//  POSTS: LIST & SEARCH
// ─────────────────────────────────────────────────────────────
async function loadPosts() {
  const res = await apiCall('/posts/?ordering=-published_at');

  if (res.ok) {
    state.posts = res.data.results || res.data;
    state.filteredPosts = [...state.posts];
    state.currentPage = 1;
    renderTagFilter();
    renderPosts();
  }
}

async function loadCategories() {
  const res = await apiCall('/categories/');

  if (res.ok) {
    state.categories = res.data.results || res.data;

    const select = document.getElementById('postCategory');

    select.innerHTML = `
      <option value="">-- No category --</option>
    `;

    state.categories.forEach(category => {
      select.innerHTML += `
        <option value="${category.id}">
          ${category.name}
        </option>
      `;
    });
  }
}

// Filter posts by search input
function searchPosts() {
  const query = document.getElementById('searchInput').value.toLowerCase();
  state.filteredPosts = state.posts.filter(post =>
    post.title.toLowerCase().includes(query) ||
    (post.excerpt || '').toLowerCase().includes(query) ||
    post.author.username.toLowerCase().includes(query)
  );
  state.currentPage = 1;
  state.activeTag = null;
  document.querySelectorAll('.tag-pill').forEach(p => p.classList.remove('active'));
  renderPosts();
}

// Filter posts by tag
function filterByTag(tagName) {
  if (state.activeTag === tagName) {
    // Clicking the active tag again clears the filter
    state.activeTag = null;
    state.filteredPosts = [...state.posts];
  } else {
    state.activeTag = tagName;
    state.filteredPosts = state.posts.filter(post =>
      post.tags && post.tags.some(t => t.name === tagName)
    );
  }
  state.currentPage = 1;
  renderTagFilter();
  renderPosts();
}

// Build the tag pills row from all unique tags in fetched posts
function renderTagFilter() {
  const allTags = new Set();
  state.posts.forEach(post => {
    (post.tags || []).forEach(t => allTags.add(t.name));
  });

  const container = document.getElementById('tagFilter');
  container.innerHTML = '';

  allTags.forEach(tag => {
    const pill = document.createElement('span');
    pill.className = 'tag-pill' + (state.activeTag === tag ? ' active' : '');
    pill.textContent = '#' + tag;
    pill.onclick = () => filterByTag(tag);
    container.appendChild(pill);
  });
}

// Render post cards with simple pagination
function renderPosts() {
  const start = (state.currentPage - 1) * state.postsPerPage;
  const end = start + state.postsPerPage;
  const pagePosts = state.filteredPosts.slice(start, end);
  const grid = document.getElementById('postsGrid');

  if (pagePosts.length === 0) {
    grid.innerHTML = '<div class="empty-state"><p>No posts found.</p></div>';
    document.getElementById('pagination').innerHTML = '';
    return;
  }

  grid.innerHTML = pagePosts.map(post => `
    <div class="post-card" onclick="openPost('${post.slug}')">
      ${post.category ? `<div class="category-badge">${post.category.name}</div>` : ''}
      <h3>${post.title}</h3>
      <p class="excerpt">${post.excerpt || post.content.substring(0, 120) + '...'}</p>
      <div class="tags">
        ${(post.tags || []).map(t => `<span class="tag">#${t.name}</span>`).join('')}
      </div>
      <div class="card-footer">
        <span>by ${post.author.username}</span>
        <span>❤ ${post.likes_count || 0} &nbsp; 💬 ${post.comments_count || 0}</span>
      </div>
    </div>
  `).join('');

  renderPagination();
}

function renderPagination() {
  const totalPages = Math.ceil(state.filteredPosts.length / state.postsPerPage);
  const container = document.getElementById('pagination');

  if (totalPages <= 1) { container.innerHTML = ''; return; }

  let html = '';
  for (let i = 1; i <= totalPages; i++) {
    html += `<button class="page-btn ${i === state.currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
  }
  container.innerHTML = html;
}

function goToPage(page) {
  state.currentPage = page;
  renderPosts();
  window.scrollTo(0, 0);
}

// ─────────────────────────────────────────────────────────────
//  POST DETAIL
// ─────────────────────────────────────────────────────────────
async function openPost(slug) {
  const res = await apiCall(`/posts/${slug}/`);

  if (res.ok) {
    state.currentPost = res.data;
    renderPostDetail(res.data);
    showPage('post');
  }
}

function renderPostDetail(post) {
  const isLiked = post.is_liked;
  const isBookmarked = post.is_bookmarked;

  document.getElementById('postDetail').innerHTML = `
    <div class="post-detail-header">
      <div class="meta-row" style="margin-bottom:8px">
        ${post.category ? `<span style="color:#2563eb; font-size:13px; font-weight:500">${post.category.name}</span>` : ''}
      </div>
      <h1>${post.title}</h1>
      <div class="post-meta">
        <span>By ${post.author.username}</span>
        <span>${formatDate(post.published_at || post.created_at)}</span>
        <span>${post.views_count} views</span>
      </div>
      <div class="tags" style="margin-bottom:0">
        ${(post.tags || []).map(t => `<span class="tag">#${t.name}</span>`).join('')}
      </div>
    </div>

    <div class="post-body">${post.content}</div>

    <div class="post-actions">
      <button class="action-btn ${isLiked ? 'liked' : ''}" id="likeBtn" onclick="toggleLike('${post.slug}')">
        ❤ <span id="likesCount">${post.likes_count || 0}</span> Likes
      </button>
      <button class="action-btn ${isBookmarked ? 'bookmarked' : ''}" id="bookmarkBtn" onclick="toggleBookmark('${post.slug}')">
        🔖 ${isBookmarked ? 'Bookmarked' : 'Bookmark'}
      </button>
    </div>
  `;

  // Render comments
  renderComments(post.top_level_comments || []);
  document.getElementById('commentCount').textContent = post.comments_count || 0;

  // Show/hide comment form
  if (state.user) {
    document.getElementById('commentForm').style.display = 'block';
    document.getElementById('commentLoginMsg').style.display = 'none';
  } else {
    document.getElementById('commentForm').style.display = 'none';
    document.getElementById('commentLoginMsg').style.display = 'block';
  }
}

function renderComments(comments) {
  const list = document.getElementById('commentsList');
  if (comments.length === 0) {
    list.innerHTML = '<p style="color:#888; font-size:14px; margin-top:16px">No comments yet. Be the first!</p>';
    return;
  }
  list.innerHTML = comments.map(c => renderComment(c)).join('');
}

// Builds HTML for a comment + its nested replies
function renderComment(comment) {
  const replies = (comment.replies || []).map(r => renderComment(r)).join('');
  const isDeleted = comment.is_deleted;
  const canReply = state.user && !isDeleted;

  return `
    <div class="comment-item">
      <div class="comment-author">${isDeleted ? '[deleted]' : (comment.author?.username || 'Unknown')}</div>
      <div class="comment-date">${formatDate(comment.created_at)}</div>
      <div class="comment-text">${comment.content}</div>
      ${canReply ? `
        <button class="reply-toggle" onclick="toggleReplyForm(${comment.id})">Reply</button>
        <div class="reply-form" id="reply-${comment.id}" style="display:none">
          <textarea id="replyInput-${comment.id}" placeholder="Write a reply..." rows="2"></textarea>
          <br/>
          <button class="btn-primary" style="margin-top:6px; font-size:13px; padding:6px 14px" onclick="addReply(${comment.id})">Post Reply</button>
        </div>
      ` : ''}
      ${replies ? `<div class="comment-replies">${replies}</div>` : ''}
    </div>
  `;
}

function toggleReplyForm(commentId) {
  const form = document.getElementById(`reply-${commentId}`);
  form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

// ─────────────────────────────────────────────────────────────
//  COMMENTS: ADD COMMENT & REPLY
// ─────────────────────────────────────────────────────────────
async function addComment() {
  const content = document.getElementById('commentInput').value.trim();
  if (!content) return;

  const res = await apiCall(`/posts/${state.currentPost.slug}/comments/`, 'POST', { content });

  if (res.ok) {
    document.getElementById('commentInput').value = '';
    // Reload the post to get updated comments
    openPost(state.currentPost.slug);
  }
}

async function addReply(parentId) {
  const content = document.getElementById(`replyInput-${parentId}`).value.trim();
  if (!content) return;

  const res = await apiCall(`/posts/${state.currentPost.slug}/comments/`, 'POST', {
    content,
    parent: parentId,
  });

  if (res.ok) {
    openPost(state.currentPost.slug);
  }
}

// ─────────────────────────────────────────────────────────────
//  LIKES & BOOKMARKS
// ─────────────────────────────────────────────────────────────
async function toggleLike(slug) {
  if (!state.user) { showPage('login'); return; }

  const res = await apiCall(`/posts/${slug}/like/`, 'POST');
  if (res.ok) {
    const btn = document.getElementById('likeBtn');
    btn.classList.toggle('liked', res.data.liked);
    document.getElementById('likesCount').textContent = res.data.likes_count;
  }
}

async function toggleBookmark(slug) {
  if (!state.user) { showPage('login'); return; }

  const res = await apiCall(`/posts/${slug}/bookmark/`, 'POST');
  if (res.ok) {
    const btn = document.getElementById('bookmarkBtn');
    btn.classList.toggle('bookmarked', res.data.bookmarked);
    btn.innerHTML = `🔖 ${res.data.bookmarked ? 'Bookmarked' : 'Bookmark'}`;
  }
}

// ─────────────────────────────────────────────────────────────
//  WRITE / EDIT POST
// ─────────────────────────────────────────────────────────────
function newPost() {
  state.editingPostId = null;
  clearWriteForm();
  document.getElementById('writeTitle').textContent = 'Write a new post';
  showPage('write');
}

function clearWriteForm() {
  document.getElementById('postTitle').value = '';
  document.getElementById('postExcerpt').value = '';
  document.getElementById('postContent').value = '';
  document.getElementById('postTags').value = '';
  document.getElementById('postStatus').value = 'draft';
  document.getElementById('writeError').style.display = 'none';
}

function editPost(postId) {
  // Find the post from myPosts list and pre-fill the form
  const post = state.myPosts.find(p => p.id === postId);
  if (!post) return;

  state.editingPostId = postId;
  document.getElementById('writeTitle').textContent = 'Edit post';
  document.getElementById('postTitle').value = post.title;
  document.getElementById('postExcerpt').value = post.excerpt || '';
  document.getElementById('postContent').value = post.content;
  document.getElementById('postTags').value = (post.tags || []).map(t => t.name).join(', ');
  document.getElementById('postStatus').value = post.status;
  showPage('write');
}

async function savePost() {
  const title = document.getElementById('postTitle').value.trim();
  const excerpt = document.getElementById('postExcerpt').value.trim();
  const content = document.getElementById('postContent').value.trim();
  const tagsRaw = document.getElementById('postTags').value;
  const status = document.getElementById('postStatus').value;
  const category = document.getElementById('postCategory').value;
  const errorEl = document.getElementById('writeError');
  errorEl.style.display = 'none';

  if (!title || !content) {
    errorEl.textContent = 'Title and content are required.';
    errorEl.style.display = 'block';
    return;
  }

  // Tags: we'll send names and let the backend handle IDs
  // For simplicity, if you want tags you need to create them first via the API
  // Here we skip tags for the basic flow
  const tags = tagsRaw
  .split(',')
  .map(t => t.trim())
  .filter(Boolean);

  const body = { title, excerpt, content, status, tag_names: tags, category_id: category || null };

  let res;
  if (state.editingPostId) {
    // PATCH = update existing post
    res = await apiCall(`/posts/${state.editingPostSlug}/`, 'PATCH', body);
  } else {
    // POST = create new post
    res = await apiCall('/posts/', 'POST', body);
  }

  if (res.ok) {
    state.editingPostId = null;
    showPage('dashboard');
  } else {
    const errors = Object.values(res.data).flat().join(' ');
    errorEl.textContent = errors;
    errorEl.style.display = 'block';
  }
}

// ─────────────────────────────────────────────────────────────
//  DASHBOARD — MY POSTS
// ─────────────────────────────────────────────────────────────
async function loadMyPosts() {
  const res = await apiCall('/posts/mine/');

  if (res.ok) {
    state.myPosts = res.data.results || res.data;
    renderMyPosts();
  }
}

function renderMyPosts() {
  const container = document.getElementById('myPostsList');

  if (state.myPosts.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>You haven\'t written any posts yet.</p></div>';
    return;
  }

  container.innerHTML = state.myPosts.map(post => `
    <div class="my-post-item">
      <div>
        <h4>${post.title}</h4>
        <div class="meta">${formatDate(post.created_at)} &nbsp;·&nbsp; ${post.views_count} views &nbsp;·&nbsp; ❤ ${post.likes_count || 0}</div>
      </div>
      <div style="display:flex; align-items:center; gap:12px">
        <span class="status-badge status-${post.status}">${post.status}</span>
        <div class="my-post-actions">
          <button class="btn-secondary" onclick="editPostBySlug('${post.slug}', '${post.id}')">Edit</button>
          <button class="btn-secondary" style="color:#b91c1c" onclick="deletePost('${post.slug}')">Delete</button>
        </div>
      </div>
    </div>
  `).join('');
}

function editPostBySlug(slug, id) {
  const post = state.myPosts.find(p => p.id === id);
  if (!post) return;
  state.editingPostId = id;
  state.editingPostSlug = slug;
  document.getElementById('writeTitle').textContent = 'Edit post';
  document.getElementById('postTitle').value = post.title;
  document.getElementById('postExcerpt').value = post.excerpt || '';
  document.getElementById('postContent').value = post.content || '';
  document.getElementById('postCategory').value = post.category?.id || '';
  document.getElementById('postTags').value = (post.tags || []).map(t => t.name).join(', ');
  document.getElementById('postStatus').value = post.status;
  showPage('write');
}

async function deletePost(slug) {
  if (!confirm('Delete this post? This cannot be undone.')) return;

  const res = await apiCall(`/posts/${slug}/`, 'DELETE');

  if (res.ok || res.status === 204) {

    state.myPosts = state.myPosts.filter(p => p.slug !== slug);

    renderMyPosts();

    loadPosts();
  }
}

// ─────────────────────────────────────────────────────────────
//  UTILITY
// ─────────────────────────────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

// ─────────────────────────────────────────────────────────────
//  INIT — runs when the page first loads
// ─────────────────────────────────────────────────────────────
function init() {
  // Restore login state from localStorage (so refresh doesn't log you out)
  const savedAccess = localStorage.getItem('accessToken');
  const savedRefresh = localStorage.getItem('refreshToken');
  const savedUser = localStorage.getItem('user');

  if (savedAccess && savedUser) {
    state.accessToken = savedAccess;
    state.refreshToken = savedRefresh;
    state.user = JSON.parse(savedUser);
  }

  updateNavbar();
  loadPosts();
  loadCategories();
}

// Run init when the DOM is ready
document.addEventListener('DOMContentLoaded', init);
