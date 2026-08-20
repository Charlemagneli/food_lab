document.addEventListener('DOMContentLoaded', async () => {
  try {
    const data = await FoodLab.api('/api/users/me/recipes');
    const counts = () => {
      document.querySelector('#published-count').textContent = data.items.filter(r => r.status === 'published').length;
      document.querySelector('#draft-count').textContent = data.items.filter(r => r.status === 'draft').length;
    };
    const render = status => {
      counts();
      document.querySelector('#list-hint').textContent = status === 'draft' ? '只有你可见，发布后进入公开列表' : '公开展示中的菜谱';
      const items = data.items.filter(r => status === 'draft' ? r.status === 'draft' : r.status === 'published');
      document.querySelector('#my-recipes').innerHTML = items.length ? items.map(r => `<div class="recipe-manage-row"><a class="recipe-row-thumb" href="/recipe.html?id=${r.id}">${r.cover_image ? `<img src="${FoodLab.escape(r.cover_image)}" alt="">` : '🍲'}</a><div class="recipe-manage-info"><div class="recipe-manage-title"><strong>${FoodLab.escape(r.title)}</strong>${r.is_featured ? '<span class="editor-pick-mini"><span aria-hidden="true">✦</span> 编辑精选</span>' : ''}</div><small>${FoodLab.escape(r.description || '暂无简介')} · ${FoodLab.escape(r.cuisine || '未分类')} · 难度：${FoodLab.escape(r.difficulty || '简单')}</small></div><div class="recipe-manage-actions"><span class="status-pill">${status === 'draft' ? '未完成' : '已公开'}</span><a class="btn secondary" href="/publish.html?edit=${r.id}">编辑</a><button class="btn ghost" data-delete="${r.id}">删除</button>${status === 'draft' ? `<button class="btn" data-publish="${r.id}">发布</button>` : ''}</div></div>`).join('') : `<div class="empty"><strong>${status === 'draft' ? '草稿箱是空的' : '还没有已发布菜谱'}</strong><p>${status === 'draft' ? '开始创作后，未完成的内容会保存在这里。' : '分享你的第一道菜，让更多人发现它。'}</p><a class="btn" href="/publish.html">创作新菜谱</a></div>`;
      document.querySelectorAll('[data-delete]').forEach(button => button.onclick = async () => { if (!confirm('确认删除这道菜谱吗？')) return; await FoodLab.api('/api/recipes/' + button.dataset.delete, { method: 'DELETE' }); const item = data.items.find(x => String(x.id) === String(button.dataset.delete)); if (item) item.status = 'deleted'; render(status); FoodLab.toast('菜谱已删除'); });
      document.querySelectorAll('[data-publish]').forEach(button => button.onclick = async () => { await FoodLab.api('/api/recipes/' + button.dataset.publish, { method: 'PUT', body: { status: 'published' } }); const item = data.items.find(x => String(x.id) === String(button.dataset.publish)); if (item) item.status = 'published'; render('draft'); FoodLab.toast('菜谱已发布'); });
    };
    document.querySelectorAll('[data-tab]').forEach(tab => tab.onclick = () => { document.querySelectorAll('[data-tab]').forEach(item => item.classList.remove('active')); tab.classList.add('active'); render(tab.dataset.tab); });
    render('published');
  } catch (e) {
    FoodLab.toast(e.message);
    setTimeout(() => location.href = '/login.html', 700);
  }
});
