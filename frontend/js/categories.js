document.addEventListener('DOMContentLoaded', async () => {
  const cats = await FoodLab.api('/api/categories');
  const grid = document.querySelector('#category-grid');
  const q = new URLSearchParams(location.search);
  const hidden = new Set(['drinks', 'staple', 'breakfast', 'snack']);
  grid.innerHTML = cats.items.filter(c => !hidden.has(c.slug)).map(c => `<a class="category-card${q.get('category') === c.slug ? ' active' : ''}" href="?category=${encodeURIComponent(c.slug)}">${FoodLab.escape(c.name)}</a>`).join('');
  const data = await FoodLab.api('/api/recipes?' + q);
  document.querySelector('#recipe-grid').innerHTML = data.items.length ? data.items.map(FoodLab.renderCard).join('') : '<div class="empty">这个分类暂时还没有菜谱。</div>';
});
