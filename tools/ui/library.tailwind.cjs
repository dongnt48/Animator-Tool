// Optional rebuild: npx --yes --package tailwindcss@3.4.17 tailwindcss -c tools/ui/library.tailwind.cjs -i tools/ui/library.css -o static/admin/css/library-utilities.css --minify
module.exports = {
  content: ['./templates/admin/pages/library.html', './templates/admin/pages/create.html', './templates/admin/partials/video-*.html', './static/admin/js/library.js'],
  corePlugins: { preflight: false },
  theme: {
    extend: {
      fontFamily: { sans: ['"Segoe UI"', 'system-ui', 'sans-serif'], serif: ['Georgia', 'serif'] },
      colors: {
        cozy: { bg:'#FAF6EE', card:'#FFFFFF', dark:'#2B2D42', slate:'#3D405B',
          terracotta:'#E07A5F', amber:'#F4A261', sage:'#81B29A', sand:'#E5DCC5', softCream:'#FFFDF9' }
      }
    }
  }
};
