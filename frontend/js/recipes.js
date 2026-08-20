document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(location.search);
  const search = document.querySelector('#recipe-search');
  search.q.value = params.get('q') || '';
  try {
    const cats = await FoodLab.api('/api/categories');
    document.querySelector('#filters').innerHTML = `<div class="filter-fields"><label class="filter-field"><span>排序方式</span><select id="sort"><option value="latest">最新发布</option><option value="popular">浏览最多</option><option value="likes">点赞最多</option><option value="favorites">收藏最多</option><option value="views">浏览最多</option></select></label><label class="filter-field"><span>菜系分类</span><select id="category"><option value="">全部分类</option>${cats.items.map(c => `<option value="${FoodLab.escape(c.slug)}">${FoodLab.escape(c.name)}</option>`).join('')}</select></label></div>`;
    document.querySelector('#sort').value = params.get('sort') || 'latest';
    document.querySelector('#category').value = params.get('category') || '';
    async function load() {
      const query = new URLSearchParams(location.search);
      ['sort', 'category'].forEach(key => {
        const value = document.querySelector('#' + key).value;
        if (value) query.set(key, value); else query.delete(key);
      });
      const data = await FoodLab.api('/api/recipes?' + query);
      document.querySelector('#recipe-grid').innerHTML = data.items.length ? data.items.map(FoodLab.renderCard).join('') : '<div class="empty">还没有找到匹配菜谱，换个关键词试试。</div>';
      document.querySelector('#pagination').innerHTML = Array.from({ length: data.pagination.pages }, (_, index) => `<button class="btn ${index + 1 === data.pagination.page ? '' : 'secondary'}" data-page="${index + 1}">${index + 1}</button>`).join('');
      document.querySelectorAll('[data-page]').forEach(button => button.onclick = () => { query.set('page', button.dataset.page); history.pushState({}, '', location.pathname + '?' + query); load(); });
    }
    document.querySelectorAll('#filters select').forEach(select => select.onchange = () => { const query = new URLSearchParams(location.search); query.delete('page'); document.querySelectorAll('#filters select').forEach(field => field.value ? query.set(field.id, field.value) : query.delete(field.id)); history.pushState({}, '', location.pathname + '?' + query); load(); });
    search.onsubmit = event => { event.preventDefault(); const query = new URLSearchParams(location.search); query.set('q', search.q.value); query.delete('page'); history.pushState({}, '', location.pathname + '?' + query); load(); };
    load();
  } catch (error) {
    FoodLab.toast(error.message);
  }
});
