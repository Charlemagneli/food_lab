document.addEventListener('DOMContentLoaded', async () => {
  const user = await FoodLab.loadUser();
  if (!user) {
    location.replace('/login.html?next=' + encodeURIComponent('/messages.html'));
    return;
  }

  const list = document.querySelector('#system-message-list');
  const count = document.querySelector('#system-message-count');
  try {
    const inbox = await FoodLab.api('/api/messages');
    count.textContent = `${inbox.items.length} 条消息`;
    list.innerHTML = inbox.items.length
      ? inbox.items.map(item => `<article class="platform-row ${item.is_read ? '' : 'is-unread'}"><div class="message-meta"><strong><span class="system-message-mark" aria-hidden="true">✦</span> 食研所系统${item.is_read ? '' : '<i class="message-unread"></i>'}</strong><time>${new Date(item.created_at).toLocaleString()}</time></div><p>${FoodLab.escape(item.content)}</p></article>`).join('')
      : '<div class="empty message-empty">暂时没有系统消息。</div>';
    if (inbox.unread) await FoodLab.api('/api/messages/read', {method: 'PATCH'});
  } catch (error) {
    FoodLab.toast(error.message);
  }
});
