document.addEventListener('DOMContentLoaded', async () => {
  const grid = document.querySelector('#hero-picker-grid');
  try {
    const user = await FoodLab.loadUser();
    if (!user || user.role !== 'admin') {
      location.replace(user ? '/' : '/login.html?next=' + encodeURIComponent('/admin-homepage.html'));
      return;
    }
    const result = await FoodLab.api('/api/admin/homepage-featured');
    if (!result.items.length) {
      grid.innerHTML = '<div class="empty hero-picker-empty"><strong>暂无可选择的菜谱</strong><p>请先为已发布且有封面的菜谱设置“编辑精选”。</p><a class="btn" href="/admin.html">前往菜谱审核</a></div>';
      return;
    }
    grid.innerHTML = result.items.map(item => `<article class="hero-choice-card ${String(item.id) === String(result.selected_id) ? 'selected' : ''}">
      <div class="hero-choice-image"><img src="${FoodLab.escape(item.cover_image)}" alt="${FoodLab.escape(item.title)}">${String(item.id) === String(result.selected_id) ? '<span class="current-badge">当前主视觉</span>' : ''}</div>
      <div class="hero-choice-body"><div class="hero-choice-meta"><span>${FoodLab.escape(item.cuisine || '食研所')}</span><span>${FoodLab.escape(item.author || '')}</span></div><h2>${FoodLab.escape(item.title)}</h2><p>${FoodLab.escape(item.description || '暂无简介')}</p>
      <div class="hero-choice-stats"><span><b>${item.views_count || 0}</b><small>浏览</small></span><span><b>${item.likes_count || 0}</b><small>点赞</small></span><span><b>${item.comments_count || 0}</b><small>评论</small></span></div>
      <button class="btn ${String(item.id) === String(result.selected_id) ? 'secondary' : ''}" data-select-hero="${item.id}" ${String(item.id) === String(result.selected_id) ? 'disabled' : ''}>${String(item.id) === String(result.selected_id) ? '正在使用' : '设为首页主视觉'}</button></div>
    </article>`).join('');
    grid.querySelectorAll('[data-select-hero]').forEach(button => button.onclick = async () => {
      button.disabled = true;
      try {
        await FoodLab.api('/api/admin/homepage-featured', {method: 'PATCH', body: {recipe_id: Number(button.dataset.selectHero)}});
        FoodLab.toast('首页主视觉已更新');
        setTimeout(() => location.href = '/admin.html', 650);
      } catch (error) {
        FoodLab.toast(error.message); button.disabled = false;
      }
    });
  } catch (error) {
    grid.innerHTML = `<div class="empty">${FoodLab.escape(error.message)}</div>`;
  }
});
