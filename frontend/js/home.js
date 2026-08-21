document.addEventListener('DOMContentLoaded', async () => {
  try {
    const [popular, latest, cats, featured] = await Promise.all([
      FoodLab.api('/api/recipes?sort=popular&per_page=3'),
      FoodLab.api('/api/recipes?sort=latest&per_page=3'),
      FoodLab.api('/api/categories'),
      FoodLab.api('/api/homepage-featured'),
    ]);
    document.querySelector('#popular-grid').innerHTML = popular.items.map(FoodLab.renderCard).join('');
    document.querySelector('#latest-grid').innerHTML = latest.items.map(FoodLab.renderCard).join('');
    document.querySelector('#category-grid').innerHTML = cats.items.slice(0, 8).map(c => `<a class="category-card" href="/recipes.html?category=${encodeURIComponent(c.slug)}">${FoodLab.escape(c.name)}</a>`).join('');
    if (featured.data) {
      const hero = document.querySelector('#homepage-featured');
      const copy = document.querySelector('#homepage-featured-copy');
      hero.href = `/recipe.html?id=${featured.data.id}`;
      hero.classList.add('has-cover');
      hero.style.backgroundImage = `linear-gradient(to top,rgba(28,18,13,.66),rgba(28,18,13,.05) 58%),url("${String(featured.data.cover_image).replace(/["\\]/g, '\\$&')}")`;
      copy.hidden = false;
      copy.innerHTML = `<span>编辑精选 · ${FoodLab.escape(featured.data.cuisine || '食研所')}</span><strong>${FoodLab.escape(featured.data.title)}</strong>`;
    }
  } catch (error) {
    FoodLab.toast(error.message);
  }
  document.querySelector('#home-search').onsubmit = event => {
    event.preventDefault();
    location.href = '/recipes.html?q=' + encodeURIComponent(new FormData(event.target).get('q'));
  };
});
