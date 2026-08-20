document.addEventListener('DOMContentLoaded', async () => {
  const ingredientBox = document.querySelector('#ingredients');
  const stepBox = document.querySelector('#steps');
  const editId = new URLSearchParams(location.search).get('edit');
  const picker = document.querySelector('#cuisine-picker');
  const cuisineInput = picker.querySelector('[name=cuisine]');
  const cuisineTrigger = picker.querySelector('.cuisine-trigger');
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
    const row = document.createElement('div'); row.className = 'dynamic-row';
    row.innerHTML = '<textarea placeholder="步骤说明" data-instruction rows="2"></textarea><input type="file" accept="image/*"><button type="button" class="btn secondary">×</button>';
    row.querySelector('[data-instruction]').value = item.instruction || ''; row.querySelector('button').onclick = () => row.remove(); stepBox.append(row);
  };
  document.querySelector('#add-ingredient').onclick = () => addIngredient(); document.querySelector('#add-step').onclick = () => addStep();
  if (editId) {
    try {
      const d = (await FoodLab.api('/api/recipes/' + editId)).data;
      document.querySelector('[name=title]').value = d.title; document.querySelector('[name=description]').value = d.description;
      setCuisine(d.cuisine); document.querySelector('[name=servings]').value = d.servings;
      ingredientBox.innerHTML = ''; stepBox.innerHTML = ''; d.ingredients.forEach(addIngredient); d.steps.forEach(addStep);
      document.querySelector('.form-wrap h1').textContent = '编辑菜谱';
    } catch (error) { FoodLab.toast(error.message); }
  } else { addIngredient(); addStep(); }
  document.querySelector('#recipe-form').onsubmit = async event => {
    event.preventDefault();
    if (!cuisineInput.value) { FoodLab.toast('请选择菜系'); cuisineTrigger.focus(); return; }
    const formData = new FormData(event.target); formData.set('status', event.submitter.value);
    formData.set('ingredients', JSON.stringify([...ingredientBox.children].map(row => ({name: row.querySelector('[data-name]').value, amount: row.querySelector('[data-amount]').value, unit: row.querySelector('[data-unit]').value}))));
    formData.set('steps', JSON.stringify([...stepBox.children].map(row => ({instruction: row.querySelector('[data-instruction]').value}))));
    try {
      await FoodLab.api(editId ? '/api/recipes/' + editId : '/api/recipes', {method: editId ? 'PUT' : 'POST', body: formData});
      FoodLab.toast(editId ? '菜谱已更新并进入审核' : '菜谱已提交'); setTimeout(() => location.href = '/profile.html', 700);
    } catch (error) { FoodLab.toast(error.message); }
  };
});
