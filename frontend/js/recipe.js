document.addEventListener('DOMContentLoaded', async () => {
  const id = new URLSearchParams(location.search).get('id');
  const root = document.querySelector('#recipe-detail');
  try {
    const viewer = await FoodLab.loadUser();
    const d = (await FoodLab.api('/api/recipes/' + id)).data;
    let servings = 1;
    const scaled = amount => {
      const n = Number.parseFloat(amount);
      if (!Number.isFinite(n) || !String(amount).match(/[0-9]/)) return amount;
      const value = n * servings;
      return Number.isInteger(value) ? String(value) : value.toFixed(1);
    };
    const render = () => {
      root.innerHTML = `<section class="detail-hero"><div class="detail-cover">${d.cover_image ? `<img src="${FoodLab.escape(d.cover_image)}" alt="${FoodLab.escape(d.title)}">` : '🍅🍳'}</div><div>${d.is_featured ? '<span class="detail-editor-pick"><span aria-hidden="true">✦</span> 编辑精选</span>' : ''}<span class="eyebrow">${FoodLab.escape(d.cuisine)}</span><h1>${FoodLab.escape(d.title)}</h1><p class="muted">${FoodLab.escape(d.description)}</p><div class="stats"><span>浏览 ${d.views_count}</span></div><div class="actions"><button class="btn" id="like">${d.is_liked ? '♥' : '♡'} 点赞 ${d.likes_count}</button><button class="btn secondary" id="favorite">${d.is_favorited ? '★ 已收藏' : '☆ 收藏'} ${d.favorites_count}</button><button class="btn ghost" id="share">复制链接</button><button class="btn ghost" id="cook">开始烹饪</button></div></div></section><section class="detail-grid"><div class="panel"><div class="section-head"><h2>食材</h2><div class="actions" style="margin:0"><button class="btn secondary" id="minus">−</button><b id="servings">${servings} 人份</b><button class="btn secondary" id="plus">＋</button></div></div><ul class="ingredient-list">${d.ingredients.map(x => `<li><span>${FoodLab.escape(x.name)}</span><span>${FoodLab.escape(scaled(x.amount))} ${FoodLab.escape(x.unit)}</span></li>`).join('')}</ul></div><div class="panel"><h2>步骤</h2><div id="steps">${d.steps.map(x => `<div class="step"><span class="step-num">${x.position}</span><div><div>${FoodLab.escape(x.instruction)}</div>${x.image_url ? `<img class="step-media" src="${FoodLab.escape(x.image_url)}" alt="步骤 ${x.position}">` : ''}</div></div>`).join('')}</div></div></section><section class="panel" style="margin-top:24px"><h2>评论</h2><form id="comment-form" class="search-bar" style="margin:18px 0 7px"><input name="content" maxlength="500" placeholder="写下你的评论……"><button class="btn">发布</button></form><p class="comment-policy">请勿发布违法有害、诈骗、赌博、色情或侵害他人权益的信息。</p><div id="comments">${d.comments.map(c => `<div class="comment"><div class="comment-head"><b>${FoodLab.escape(c.username)}</b><span>${new Date(c.created_at).toLocaleDateString()}</span></div><div>${FoodLab.escape(c.content)}</div></div>`).join('') || '<p class="muted">还没有评论，来说说你的感受吧。</p>'}</div></section>`;
      const description = root.querySelector('.detail-hero > div:last-child > .muted');
      if (description && d.tags?.length) description.insertAdjacentHTML('afterend', `<div class="tags detail-tags">${d.tags.map(tag => `<span class="tag">${FoodLab.escape(tag)}</span>`).join('')}</div>`);
      const commentsRoot = document.querySelector('#comments');
      commentsRoot.innerHTML = d.comments.length ? d.comments.map(comment => `<article class="comment-card"><div class="comment-avatar">${comment.avatar_url ? `<img src="${FoodLab.escape(comment.avatar_url)}" alt="${FoodLab.escape(comment.username)}">` : `<span>${FoodLab.escape(comment.username.slice(0, 1))}</span>`}</div><div class="comment-main"><div class="comment-head"><b>${FoodLab.escape(comment.username)}</b><time>${new Date(comment.created_at).toLocaleDateString()}</time></div><p>${FoodLab.escape(comment.content)}</p><div class="comment-actions"><button type="button" class="comment-like ${comment.is_liked ? 'active' : ''}" data-comment-like="${comment.id}">${comment.is_liked ? '♥' : '♡'} <span>${comment.likes_count || 0}</span></button>${viewer && (viewer.id === comment.user_id || viewer.role === 'admin') ? `<button type="button" class="comment-delete" data-comment-delete="${comment.id}">删除</button>` : ''}</div></div></article>`).join('') : '<p class="muted comment-empty">还没有评论，来说说你的感受吧。</p>';
      commentsRoot.querySelectorAll('[data-comment-like]').forEach(button => button.onclick = async () => { try { const comment = d.comments.find(item => String(item.id) === button.dataset.commentLike); const result = await FoodLab.api('/api/comments/' + button.dataset.commentLike + '/like', {method: 'POST'}); comment.is_liked = result.active; comment.likes_count = result.count; render(); } catch (error) { FoodLab.toast(error.message); } });
      commentsRoot.querySelectorAll('[data-comment-delete]').forEach(button => button.onclick = async () => { if (!confirm('确认删除这条评论吗？')) return; try { await FoodLab.api('/api/comments/' + button.dataset.commentDelete, {method: 'DELETE'}); d.comments = d.comments.filter(item => String(item.id) !== button.dataset.commentDelete); render(); FoodLab.toast('评论已删除'); } catch (error) { FoodLab.toast(error.message); } });
      document.querySelector('#like').onclick = async () => { try { const r = await FoodLab.api('/api/recipes/' + id + '/like', { method: 'POST' }); d.is_liked = r.active; d.likes_count = r.count; render(); } catch (e) { FoodLab.toast(e.message); } };
      document.querySelector('#favorite').onclick = async () => { try { const r = await FoodLab.api('/api/recipes/' + id + '/favorite', { method: 'POST' }); d.is_favorited = r.active; d.favorites_count = r.count; render(); } catch (e) { FoodLab.toast(e.message); } };
      document.querySelector('#share').onclick = () => navigator.clipboard?.writeText(location.href).then(() => FoodLab.toast('链接已复制'));
      document.querySelector('#plus').onclick = () => { servings++; render(); };
      document.querySelector('#minus').onclick = () => { if (servings > 1) servings--; render(); };
      document.querySelector('#cook').onclick = () => document.querySelector('#steps').scrollIntoView({ behavior: 'smooth' });
      const commentForm = document.querySelector('#comment-form');
      if (!viewer) commentForm.innerHTML = `<span class="comment-login-hint">登录后可以参与讨论</span><a class="btn" href="/login.html?next=${encodeURIComponent(location.pathname + location.search)}">去登录</a>`;
      else commentForm.onsubmit = async e => { e.preventDefault(); try { await FoodLab.api('/api/recipes/' + id + '/comments', { method: 'POST', body: Object.fromEntries(new FormData(e.target)) }); FoodLab.toast('评论已发布'); location.reload(); } catch (err) { FoodLab.toast(err.message); } };
    };
    render();
  } catch (e) {
    root.innerHTML = '<div class="empty">菜谱不存在或尚未公开。</div>';
  }
});
