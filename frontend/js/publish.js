document.addEventListener('DOMContentLoaded', async () => {
  const user = await FoodLab.loadUser();
  if (!user) {
    location.replace('/register.html?next=' + encodeURIComponent(location.pathname + location.search));
    return;
  }
  const ingredientBox = document.querySelector('#ingredients');
  const stepBox = document.querySelector('#steps');
  const editId = new URLSearchParams(location.search).get('edit');
  const picker = document.querySelector('#cuisine-picker');
  const cuisineInput = picker.querySelector('[name=cuisine]');
  const cuisineTrigger = picker.querySelector('.cuisine-trigger');
  const coverInput = document.querySelector('[name=cover_image]');
  const coverPreview = document.querySelector('#cover-preview');
  const tagsInput = document.querySelector('[name=tags]');
  const tagKeyword = document.querySelector('#tag-keyword');
  const tagItems = document.querySelector('#tag-editor-items');
  let tags = [];
  let hasExistingCover = false;
  const renderTags = () => {
    tagsInput.value = JSON.stringify(tags);
    tagItems.innerHTML = tags.map((tag, index) => `<button class="tag-editor-chip" type="button" data-tag-index="${index}"><span>${FoodLab.escape(tag)}</span><b aria-label="删除 ${FoodLab.escape(tag)}">×</b></button>`).join('');
    tagItems.querySelectorAll('[data-tag-index]').forEach(button => button.onclick = () => { tags.splice(Number(button.dataset.tagIndex), 1); renderTags(); tagKeyword.focus(); });
  };
  const addTag = () => {
    const tag = tagKeyword.value.trim().replace(/^#+/, '');
    if (!tag) return;
    if (tags.includes(tag)) { FoodLab.toast('这个标签已经添加过了'); tagKeyword.select(); return; }
    if (tags.length >= 12) { FoodLab.toast('最多添加 12 个标签'); return; }
    tags.push(tag); tagKeyword.value = ''; renderTags();
  };
  tagKeyword.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); addTag(); }
    if (event.key === 'Backspace' && !tagKeyword.value && tags.length) { tags.pop(); renderTags(); }
  });
  document.querySelector('#tag-editor').onclick = () => tagKeyword.focus();
  const showPreview = (element, url, alt) => { element.innerHTML = url ? `<img src="${FoodLab.escape(url)}" alt="${FoodLab.escape(alt)}">` : '<span>选择图片后可在这里预览</span>'; };
  coverInput.onchange = () => { const file = coverInput.files[0]; if (file) showPreview(coverPreview, URL.createObjectURL(file), '封面预览'); };
  const setCuisine = value => {
    const option = [...picker.querySelectorAll('[data-value]')].find(item => item.dataset.value === value);
    cuisineInput.value = option ? value : '';
    cuisineTrigger.querySelector('span').textContent = option ? value : '请选择菜系';
    picker.querySelectorAll('[data-value]').forEach(item => item.classList.toggle('selected', item === option));
  };
  const closeCuisine = () => { picker.classList.remove('open'); cuisineTrigger.setAttribute('aria-expanded', 'false'); };
  cuisineTrigger.onclick = event => { event.stopPropagation(); const open = !picker.classList.contains('open'); closeCuisine(); if (open) { picker.classList.add('open'); cuisineTrigger.setAttribute('aria-expanded', 'true'); } };
  picker.querySelectorAll('[data-value]').forEach(option => option.onclick = () => { setCuisine(option.dataset.value); closeCuisine(); });
  document.addEventListener('click', closeCuisine);

  const addIngredient = (item = {}) => {
    const row = document.createElement('div'); row.className = 'dynamic-row';
    row.innerHTML = '<input placeholder="食材名称" data-name><input placeholder="数量" data-amount><input placeholder="单位" data-unit><button type="button" class="btn secondary">×</button>';
    row.querySelector('[data-name]').value = item.name || ''; row.querySelector('[data-amount]').value = item.amount || ''; row.querySelector('[data-unit]').value = item.unit || '';
    row.querySelector('button').onclick = () => row.remove(); ingredientBox.append(row);
  };
  const addStep = (item = {}) => {
    const row = document.createElement('div'); row.className = 'step-editor-row';
    row.dataset.imageUrl = item.image_url || '';
    row.innerHTML = `<div class="step-image-preview">${item.image_url ? `<img src="${FoodLab.escape(item.image_url)}" alt="步骤图片">` : '<span>步骤图片</span>'}</div><div class="step-editor-fields"><textarea placeholder="步骤说明" data-instruction rows="3"></textarea><label class="step-image-button">添加图片<input data-step-image type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif"></label></div><button type="button" class="btn secondary step-remove" aria-label="删除步骤">×</button>`;
    row.querySelector('[data-instruction]').value = item.instruction || '';
    const imageInput = row.querySelector('[data-step-image]');
    imageInput.onchange = () => { const file = imageInput.files[0]; if (file) row.querySelector('.step-image-preview').innerHTML = `<img src="${URL.createObjectURL(file)}" alt="步骤图片预览">`; };
    row.querySelector('.step-remove').onclick = () => row.remove(); stepBox.append(row);
  };
  document.querySelector('#add-ingredient').onclick = () => addIngredient(); document.querySelector('#add-step').onclick = () => addStep();
  if (editId) {
    try {
      const d = (await FoodLab.api('/api/recipes/' + editId)).data;
      document.querySelector('[name=title]').value = d.title; document.querySelector('[name=description]').value = d.description;
      setCuisine(d.cuisine);
      tags = [...(d.tags || [])]; renderTags();
      showPreview(coverPreview, d.cover_image, '当前封面');
      hasExistingCover = Boolean(d.cover_image);
      ingredientBox.innerHTML = ''; stepBox.innerHTML = ''; d.ingredients.forEach(addIngredient); d.steps.forEach(addStep);
      document.querySelector('.form-wrap h1').textContent = '编辑菜谱';
    } catch (error) { FoodLab.toast(error.message); }
  } else { addIngredient(); addStep(); }
  document.querySelector('#recipe-form').onsubmit = async event => {
    event.preventDefault();
    if (!cuisineInput.value) { FoodLab.toast('请选择菜系'); cuisineTrigger.focus(); return; }
    if (tagKeyword.value.trim()) addTag();
    const formData = new FormData(event.target); formData.set('status', event.submitter.value);
    formData.set('ingredients', JSON.stringify([...ingredientBox.children].map(row => ({name: row.querySelector('[data-name]').value, amount: row.querySelector('[data-amount]').value, unit: row.querySelector('[data-unit]').value}))));
    const stepRows = [...stepBox.children];
    if (event.submitter.value === 'pending') {
      const ingredients = [...ingredientBox.children].map(row => ({name: row.querySelector('[data-name]').value.trim(), amount: row.querySelector('[data-amount]').value.trim()})).filter(item => item.name && item.amount);
      const steps = stepRows.map(row => row.querySelector('[data-instruction]').value.trim()).filter(Boolean);
      if (!document.querySelector('[name=title]').value.trim()) { FoodLab.toast('请填写菜谱名称'); return; }
      if (!hasExistingCover && !coverInput.files[0]) { FoodLab.toast('提交审核前必须上传封面图片'); return; }
      if (!ingredients.length) { FoodLab.toast('提交审核前至少添加一项包含名称和数量的食材'); return; }
      if (!steps.length) { FoodLab.toast('提交审核前至少添加一个制作步骤'); return; }
    }
    formData.set('steps', JSON.stringify(stepRows.map(row => ({instruction: row.querySelector('[data-instruction]').value, image_url: row.dataset.imageUrl || ''}))));
    stepRows.forEach((row, index) => { const file = row.querySelector('[data-step-image]').files[0]; if (file) formData.append(`step_image_${index}`, file); });
    try {
      await FoodLab.api(editId ? '/api/recipes/' + editId : '/api/recipes', {method: editId ? 'PUT' : 'POST', body: formData});
      if (event.submitter.value === 'pending') {
        document.querySelector('.recipe-editor-panel').innerHTML = '<div class="submission-success"><div class="submission-mark" aria-hidden="true">✓</div><span class="eyebrow">Submission received</span><h1>已提交</h1><p>请等待审核，审核通过后菜谱会在公开列表中展示。</p><small id="submission-countdown">3 秒后返回发布菜谱页面</small></div>';
        let seconds = 3;
        const countdown = document.querySelector('#submission-countdown');
        const timer = setInterval(() => { seconds -= 1; if (seconds <= 0) { clearInterval(timer); location.href = '/publish.html'; } else countdown.textContent = `${seconds} 秒后返回发布菜谱页面`; }, 1000);
      } else {
        FoodLab.toast('草稿已保存'); setTimeout(() => location.href = '/my-recipes.html', 700);
      }
    } catch (error) { FoodLab.toast(error.message); }
  };
});
