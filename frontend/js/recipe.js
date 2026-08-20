document.addEventListener('DOMContentLoaded', async () => {
  const id = new URLSearchParams(location.search).get('id');
  const root = document.querySelector('#recipe-detail');
  try {
    const d = (await FoodLab.api('/api/recipes/' + id)).data;
    let servings = d.servings;
    const scaled = amount => {
      const n = Number.parseFloat(amount);
      if (!Number.isFinite(n) || !String(amount).match(/[0-9]/)) return amount;
      const value = n * servings / d.servings;
      return Number.isInteger(value) ? String(value) : value.toFixed(1);
    };
    const render = () => {
      root.innerHTML = `<section class="detail-hero"><div class="detail-cover">${d.cover_image ? `<img src="${FoodLab.escape(d.cover_image)}" alt="${FoodLab.escape(d.title)}">` : '🍅🍳'}</div><div>${d.is_featured ? '<span class="detail-editor-pick"><span aria-hidden="true">✦</span> 编辑精选</span>' : ''}<span class="eyebrow">${FoodLab.escape(d.cuisine)} · ${FoodLab.escape(d.meal_type)}</span><h1>${FoodLab.escape(d.title)}</h1><p class="muted">${FoodLab.escape(d.description)}</p><div class="stats"><span>难度：${FoodLab.escape(d.difficulty)}</span><span>浏览 ${d.views_count}</span></div><div class="actions"><button class="btn" id="like">${d.is_liked ? '♥' : '♡'} 点赞 ${d.likes_count}</button><button class="btn secondary" id="favorite">${d.is_favorited ? '★ 已收藏' : '☆ 收藏'} ${d.favorites_count}</button><button class="btn ghost" id="share">复制链接</button><button class="btn ghost" id="cook">开始烹饪</button></div></div></section><section class="detail-grid"><div class="panel"><div class="section-head"><h2>食材</h2><div class="actions" style="margin:0"><button class="btn secondary" id="minus">−</button><b id="servings">${servings} 人份</b><button class="btn secondary" id="plus">＋</button></div></div><ul class="ingredient-list">${d.ingredients.map(x => `<li><span>${FoodLab.escape(x.name)}</span><span>${FoodLab.escape(scaled(x.amount))} ${FoodLab.escape(x.unit)}</span></li>`).join('')}</ul></div><div class="panel"><h2>步骤</h2><div id="steps">${d.steps.map(x => `<div class="step"><span class="step-num">${x.position}</span><div>${FoodLab.escape(x.instruction)}</div></div>`).join('')}</div></div></section><section class="panel" style="margin-top:24px"><h2>评论</h2><form id="comment-form" class="search-bar" style="margin:18px 0"><input name="content" placeholder="写下你的评论……"><button class="btn">发布</button></form><div id="comments">${d.comments.map(c => `<div class="comment"><div class="comment-head"><b>${FoodLab.escape(c.username)}</b><span>${new Date(c.created_at).toLocaleDateString()}</span></div><div>${FoodLab.escape(c.content)}</div></div>`).join('') || '<p class="muted">还没有评论，来说说你的感受吧。</p>'}</div></section>`;
      document.querySelector('#like').onclick = async () => { try { const r = await FoodLab.api('/api/recipes/' + id + '/like', { method: 'POST' }); d.is_liked = r.active; d.likes_count = r.count; render(); } catch (e) { FoodLab.toast(e.message); } };
      document.querySelector('#favorite').onclick = async () => { try { const r = await FoodLab.api('/api/recipes/' + id + '/favorite', { method: 'POST' }); d.is_favorited = r.active; d.favorites_count = r.count; render(); } catch (e) { FoodLab.toast(e.message); } };
      document.querySelector('#share').onclick = () => navigator.clipboard?.writeText(location.href).then(() => FoodLab.toast('链接已复制'));
      document.querySelector('#plus').onclick = () => { servings++; render(); };
      document.querySelector('#minus').onclick = () => { if (servings > 1) servings--; render(); };
      document.querySelector('#cook').onclick = () => document.querySelector('#steps').scrollIntoView({ behavior: 'smooth' });
      document.querySelector('#comment-form').onsubmit = async e => { e.preventDefault(); try { await FoodLab.api('/api/recipes/' + id + '/comments', { method: 'POST', body: Object.fromEntries(new FormData(e.target)) }); FoodLab.toast('评论已发布'); location.reload(); } catch (err) { FoodLab.toast(err.message); } };
    };
    render();
  } catch (e) {
    root.innerHTML = '<div class="empty">菜谱不存在或尚未公开。</div>';
  }
});
