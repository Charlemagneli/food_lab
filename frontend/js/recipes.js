document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(location.search);
  const search = document.querySelector('#recipe-search');
  const state = { sort: params.get('sort') || 'latest', category: params.get('category') || '' };
  const hiddenCategories = new Set(['drinks', 'staple', 'breakfast', 'snack']);
  search.q.value = params.get('q') || '';
  const sortOptions = [
    ['latest', '最新发布'], ['popular', '浏览最多'], ['likes', '点赞最多'], ['favorites', '收藏最多'], ['views', '浏览最多']
  ];
  const makeControl = (key, label, options) => `<label class="filter-field"><span>${label}</span><div class="filter-control" data-filter="${key}"><button class="filter-trigger" type="button" aria-expanded="false"><span></span><b aria-hidden="true">⌄</b></button><div class="filter-menu">${options.map(([value, text]) => `<button type="button" class="filter-option" data-value="${FoodLab.escape(value)}">${FoodLab.escape(text)}</button>`).join('')}</div></div></label>`;
  try {
    const cats = await FoodLab.api('/api/categories');
    const categoryOptions = [['', '全部分类'], ...cats.items.filter(category => !hiddenCategories.has(category.slug)).map(category => [category.slug, category.name])];
    document.querySelector('#filters').innerHTML = `<div class="filter-fields">${makeControl('sort', '排序方式', sortOptions)}${makeControl('category', '菜系分类', categoryOptions)}</div>`;
    const updateControls = () => document.querySelectorAll('[data-filter]').forEach(control => { const value = state[control.dataset.filter]; const option = [...control.querySelectorAll('.filter-option')].find(item => item.dataset.value === value) || control.querySelector('.filter-option'); control.querySelector('.filter-trigger span').textContent = option.textContent; control.querySelectorAll('.filter-option').forEach(item => item.classList.toggle('selected', item === option)); });
    const closeControls = () => document.querySelectorAll('.filter-control.open').forEach(control => { control.classList.remove('open'); control.querySelector('.filter-trigger').setAttribute('aria-expanded', 'false'); });
    updateControls();
    document.querySelectorAll('.filter-trigger').forEach(trigger => trigger.onclick = event => { event.stopPropagation(); const control = trigger.closest('.filter-control'); const wasOpen = control.classList.contains('open'); closeControls(); if (!wasOpen) { control.classList.add('open'); trigger.setAttribute('aria-expanded', 'true'); } });
    document.querySelectorAll('.filter-option').forEach(option => option.onclick = () => { const control = option.closest('.filter-control'); state[control.dataset.filter] = option.dataset.value; closeControls(); updateControls(); const query = new URLSearchParams(location.search); query.delete('page'); Object.entries(state).forEach(([key, value]) => value ? query.set(key, value) : query.delete(key)); history.pushState({}, '', location.pathname + (query.toString() ? '?' + query : '')); load(); });
    document.addEventListener('click', closeControls);
    async function load() {
      const query = new URLSearchParams(location.search);
      Object.entries(state).forEach(([key, value]) => value ? query.set(key, value) : query.delete(key));
      const data = await FoodLab.api('/api/recipes?' + query);
      document.querySelector('#recipe-grid').innerHTML = data.items.length ? data.items.map(FoodLab.renderCard).join('') : '<div class="empty">还没有找到匹配菜谱，换个关键词试试。</div>';
      document.querySelector('#pagination').innerHTML = Array.from({ length: data.pagination.pages }, (_, index) => `<button class="btn ${index + 1 === data.pagination.page ? '' : 'secondary'}" data-page="${index + 1}">${index + 1}</button>`).join('');
      document.querySelectorAll('[data-page]').forEach(button => button.onclick = () => { query.set('page', button.dataset.page); history.pushState({}, '', location.pathname + '?' + query); load(); });
    }
    search.onsubmit = event => { event.preventDefault(); const query = new URLSearchParams(location.search); query.set('q', search.q.value); query.delete('page'); history.pushState({}, '', location.pathname + '?' + query); load(); };
    load();
  } catch (error) {
    FoodLab.toast(error.message);
  }
});
