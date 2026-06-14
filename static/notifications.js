// ExplorerFrame Notifications
document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('news-container');
  if (!container) return;
  
  try {
    const resp = await fetch('/api/v1/news');
    if (!resp.ok) throw new Error('No response');
    const html = await resp.text();
    container.innerHTML = html;
    container.classList.remove('news-loading');
  } catch (e) {
    container.innerHTML = '<p style="color:var(--muted);font-size:.9rem;">Sin novedades por ahora.</p>';
    container.classList.remove('news-loading');
  }
});