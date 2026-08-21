document.addEventListener('DOMContentLoaded', async () => {
  const list = document.querySelector('#admin-recipes');
  let currentStatus = 'pending';
  const statusText = { pending: '待审核', published: '已发布', rejected: '已驳回', hidden: '已隐藏', draft: '草稿' };
  const adminDecision = ({title, message, reason = false, confirmText = '确认'}) => new Promise(resolve => {
    const overlay = document.createElement('div'); overlay.className = 'admin-modal-overlay';
    overlay.innerHTML = `<section class="admin-modal" role="dialog" aria-modal="true"><span class="eyebrow">Content action</span><h2>${FoodLab.escape(title)}</h2><p>${FoodLab.escape(message)}</p>${reason ? '<textarea maxlength="300" rows="4" placeholder="请填写具体原因"></textarea><small>最多 300 个字符</small>' : ''}<div class="admin-modal-actions"><button class="btn secondary" data-modal-cancel>取消</button><button class="btn" data-modal-confirm>${FoodLab.escape(confirmText)}</button></div></section>`;
    const close = value => { document.removeEventListener('keydown', escape); overlay.remove(); resolve(value); };
    const escape = event => { if (event.key === 'Escape') close(null); };
    overlay.querySelector('[data-modal-cancel]').onclick = () => close(null);
    overlay.querySelector('[data-modal-confirm]').onclick = () => { const value = reason ? overlay.querySelector('textarea').value.trim() : true; if (reason && !value) { FoodLab.toast('请填写处理原因'); overlay.querySelector('textarea').focus(); return; } close(value); };
    overlay.onclick = event => { if (event.target === overlay) close(null); };
    document.addEventListener('keydown', escape); document.body.append(overlay); (overlay.querySelector('textarea') || overlay.querySelector('[data-modal-confirm]')).focus();
  });
  const loadStats = async () => {
    const result = await FoodLab.api('/api/admin/stats');
    const labels = { users: '用户', recipes: '菜谱', pending: '待审核', featured: '编辑精选' };
    document.querySelector('#admin-stats').innerHTML = Object.entries(labels).map(([key, label]) => `<div class="panel"><span class="muted">${label}</span><strong>${result.data[key] || 0}</strong></div>`).join('');
  };
  const loadHomepageFeatured = async () => {
    const result = await FoodLab.api('/api/admin/homepage-featured');
    const preview = document.querySelector('#homepage-featured-preview');
    const selected = result.items.find(item => String(item.id) === String(result.selected_id));
    preview.innerHTML = selected ? `<img src="${FoodLab.escape(selected.cover_image)}" alt="${FoodLab.escape(selected.title)}"><span><b>${FoodLab.escape(selected.title)}</b><small>当前展示</small></span>` : '<span>尚未设置主视觉图片</span>';
  };
  const loadRecipes = async status => {
    currentStatus = status;
    list.innerHTML = '<div class="admin-loading">正在加载菜谱……</div>';
    const query = status === 'all' ? '' : '?status=' + encodeURIComponent(status);
    const result = await FoodLab.api('/api/admin/recipes' + query);
    if (!result.items.length) {
      list.innerHTML = `<div class="empty admin-empty-state"><strong>${status === 'pending' ? '暂时没有待审核菜谱' : '没有符合条件的菜谱'}</strong><p>${status === 'pending' ? '新的投稿会出现在这里。' : '换一个筛选条件试试。'}</p></div>`;
      return;
    }
    list.innerHTML = result.items.map(recipe => `<article class="admin-review-row"><a class="admin-review-thumb" href="/recipe.html?id=${recipe.id}" target="_blank" rel="noreferrer">${recipe.cover_image ? `<img src="${FoodLab.escape(recipe.cover_image)}" alt="">` : '🍲'}</a><div class="admin-review-info"><div class="admin-review-title"><strong>${FoodLab.escape(recipe.title)}</strong>${recipe.is_featured ? '<span class="editor-pick-mini"><span aria-hidden="true">✦</span> 编辑精选</span>' : ''}</div><p>${FoodLab.escape(recipe.description || '暂无简介')}</p><small>${FoodLab.escape(recipe.author)} · ${FoodLab.escape(recipe.cuisine || '未分类')} · ${statusText[recipe.status] || recipe.status}</small>${recipe.reviewed_at ? `<small class="admin-review-audit">处理人：${FoodLab.escape(recipe.reviewer || '管理员')} · ${new Date(recipe.reviewed_at).toLocaleString()}</small>` : ''}${recipe.rejection_reason ? `<small class="admin-review-reason">原因：${FoodLab.escape(recipe.rejection_reason)}</small>` : ''}</div><div class="admin-review-actions"><span class="status-pill ${recipe.status}">${statusText[recipe.status] || recipe.status}</span>${recipe.status === 'pending' ? `<button class="btn" data-action="status" data-id="${recipe.id}" data-value="published">通过</button><button class="btn secondary" data-action="status" data-id="${recipe.id}" data-value="rejected">驳回</button>` : ''}${recipe.status === 'published' ? `<button class="btn secondary" data-action="status" data-id="${recipe.id}" data-value="hidden">隐藏</button>` : ''}${['rejected','hidden'].includes(recipe.status) ? `<button class="btn secondary" data-action="status" data-id="${recipe.id}" data-value="pending">重新审核</button>` : ''}${recipe.status === 'published' ? `<button class="btn ${recipe.is_featured ? 'featured-on' : 'ghost'}" data-action="featured" data-id="${recipe.id}" data-value="${recipe.is_featured ? 'false' : 'true'}">${recipe.is_featured ? '取消精选' : '设为精选'}</button>` : ''}<button class="btn danger-ghost" data-delete-recipe="${recipe.id}" data-title="${FoodLab.escape(recipe.title)}">删除</button></div></article>`).join('');
    list.querySelectorAll('[data-action]').forEach(button => {
      button.onclick = async () => {
        button.disabled = true;
        try {
          const body = button.dataset.action === 'featured' ? { is_featured: button.dataset.value === 'true' } : { status: button.dataset.value };
          if (['rejected', 'hidden'].includes(body.status)) {
            const reason = await adminDecision({title: body.status === 'hidden' ? '隐藏菜谱' : '驳回投稿', message: body.status === 'hidden' ? '隐藏后菜谱将立即从公开页面撤下。' : '原因会保留在审核记录中，供后续复核。', reason: true, confirmText: body.status === 'hidden' ? '确认隐藏' : '确认驳回'});
            if (!reason) { button.disabled = false; return; }
            body.reason = reason;
          }
          const endpoint = button.dataset.action === 'featured' ? '/api/admin/recipes/' + button.dataset.id + '/featured' : '/api/admin/recipes/' + button.dataset.id;
          await FoodLab.api(endpoint, { method: 'PATCH', body });
          FoodLab.toast(button.dataset.action === 'featured' ? (body.is_featured ? '已设为编辑精选' : '已取消编辑精选') : '审核状态已更新');
          await Promise.all([loadStats(), loadRecipes(currentStatus)]);
        } catch (error) {
          FoodLab.toast(error.message);
          button.disabled = false;
        }
      };
    });
    list.querySelectorAll('[data-delete-recipe]').forEach(button => button.onclick = async () => {
      const confirmed = await adminDecision({title: '永久删除菜谱', message: `即将删除“${button.dataset.title}”及其食材、步骤、评论和互动记录。该操作无法撤销。`, confirmText: '永久删除'});
      if (!confirmed) return;
      button.disabled = true;
      try { await FoodLab.api('/api/admin/recipes/' + button.dataset.deleteRecipe, {method: 'DELETE'}); FoodLab.toast('菜谱已删除'); await Promise.all([loadStats(), loadRecipes(currentStatus)]); }
      catch (error) { FoodLab.toast(error.message); button.disabled = false; }
    });
  };
  const loadManagement = async () => {
    const [users, comments] = await Promise.all([FoodLab.api('/api/admin/users'), FoodLab.api('/api/admin/comments')]);
    document.querySelector('#admin-users').innerHTML = users.items.map(user => `<div class="admin-simple-row"><div><strong>${FoodLab.escape(user.username)}</strong><small>${FoodLab.escape(user.email)} · ${FoodLab.escape(user.role)}</small></div>${user.role !== 'admin' ? `<button class="btn ghost" data-delete-user="${user.id}">删除</button>` : '<span class="status-pill">管理员</span>'}</div>`).join('') || '<div class="empty">暂无用户。</div>';
    document.querySelector('#admin-comments').innerHTML = comments.items.length ? comments.items.map(comment => `<div class="admin-simple-row"><div><strong>${FoodLab.escape(comment.username)} · ${FoodLab.escape(comment.title)}</strong><small>${FoodLab.escape(comment.content)}</small></div><button class="btn ghost" data-delete-comment="${comment.id}">删除</button></div>`).join('') : '<div class="empty">暂无评论。</div>';
    document.querySelectorAll('[data-delete-user]').forEach(button => button.onclick = async () => { if (!confirm('确认删除这个用户吗？')) return; try { await FoodLab.api('/api/admin/users/' + button.dataset.deleteUser, { method: 'DELETE' }); button.closest('.admin-simple-row').remove(); FoodLab.toast('用户已删除'); } catch (error) { FoodLab.toast(error.message); } });
    document.querySelectorAll('[data-delete-comment]').forEach(button => button.onclick = async () => { try { await FoodLab.api('/api/comments/' + button.dataset.deleteComment, { method: 'DELETE' }); button.closest('.admin-simple-row').remove(); FoodLab.toast('评论已删除'); } catch (error) { FoodLab.toast(error.message); } });
  };
  try {
    await FoodLab.loadUser();
    if (!FoodLab.user || FoodLab.user.role !== 'admin') {
      location.href = FoodLab.user ? '/' : '/login.html';
      return;
    }
    await Promise.all([loadStats(), loadRecipes(currentStatus), loadManagement(), loadHomepageFeatured()]);
    document.querySelectorAll('[data-status]').forEach(tab => {
      tab.onclick = async () => {
        document.querySelectorAll('[data-status]').forEach(item => item.classList.remove('active'));
        tab.classList.add('active');
        try { await loadRecipes(tab.dataset.status); } catch (error) { FoodLab.toast(error.message); }
      };
    });
  } catch (error) {
    FoodLab.toast(error.message);
  }
});
