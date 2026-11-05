    // Toast notification
    function showToast(message, type = "info") {
      const container = document.getElementById("toastContainer");
      const toast = document.createElement("div");
      toast.className = "toast-animate px-4 py-3 rounded-2xl shadow-xl flex items-center gap-3 text-sm font-bold text-white pointer-events-auto transition " +
        (type === "error" ? "bg-rose-600" : type === "success" ? "bg-emerald-600" : "bg-cozy-slate");

      const icon = type === "error" ? "fa-circle-exclamation" : type === "success" ? "fa-circle-check" : "fa-bell";
      toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
      container.appendChild(toast);

      setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
      }, 3500);
    }

    // Load initial data
    window.addEventListener("DOMContentLoaded", () => {
      fetchVideos();
      // Auto-refresh every 2.5s for live status updates
      setInterval(fetchVideos, 2500);
      const body = document.getElementById('videoTableBody');
      if (body) {
      body.addEventListener('click',event => {
        if (event.target.closest('a,button,input,select,textarea,label') || window.getSelection()?.toString()) return;
        const row = event.target.closest('[data-video-detail]');
        if (row) location.assign(row.dataset.videoDetail);
      });
      body.addEventListener('keydown',event => {
        if (event.key === 'Enter' && event.target.matches('[data-video-detail]')) {
          event.preventDefault(); location.assign(event.target.dataset.videoDetail);
        }
      });
      }
    });

    function mediaThumbnail(video,kind,ratio,style,character) {
      const filename = kind === 'original' ? video.video_filename : video.output_filename;
      if (!filename) return `<span class="library-media-empty">${kind === 'original' ? 'Chưa có' : 'Chưa dựng'}</span>`;
      const label = kind === 'original' ? 'Xem video gốc' : 'Xem thành phẩm';
      const action = kind === 'original' ? 'playOriginal(this.dataset.filename,this.dataset.title)' : 'playOutput(this.dataset.filename,this.dataset.title,this.dataset.ratio,this.dataset.style,this.dataset.character)';
      return `<button type="button" class="library-media-thumb" data-media-kind="${kind}" aria-label="${label}"
        data-filename="${escapeHtml(filename)}" data-title="${escapeHtml(video.caption || video.title || '')}"
        data-ratio="${ratio}" data-style="${style}" data-character="${character}" onclick="${action}">
        <img src="/api/social/videos/${encodeURIComponent(video.id)}/thumbnail/${kind}" alt="${label}" loading="lazy" width="64" height="80" onerror="this.hidden=true">
        <span class="library-media-play" aria-hidden="true">▶</span></button>`;
    }

    async function fetchVideos() {
      try {
        const res = await fetch("/api/videos");
        const data = await res.json();
        if (data.status === "success") {
          renderTable(data.videos, data.is_batch_rendering);
          updateStats(data.videos);
          renderCreationActivity(data.videos);
          window.dispatchEvent(new CustomEvent('library:updated',{detail:data.videos}));
        }
      } catch (err) {
        console.error("Fetch videos failed:", err);
      }
    }

    function updateStats(videos) {
      document.getElementById("statTotal").innerText = videos.length;
      document.getElementById("statNew").innerText = videos.filter(v => v.status === "new").length;
      document.getElementById("statProcessing").innerText = videos.filter(v => v.status === "processing").length;
      document.getElementById("statCompleted").innerText = videos.filter(v => v.status === "completed").length;
    }

    function renderCreationActivity(videos) {
      const container = document.getElementById('creationActivity');
      if (!container) return;
      const fragment = document.createDocumentFragment();
      const active = videos.filter(video => video.status === 'processing' || video.status === 'error').slice(-8);
      for (const video of active) {
        const row = document.createElement('div'); row.className = 'creation-task';
        const title = document.createElement('a'); title.href = `/videos/${encodeURIComponent(video.id)}`;
        title.textContent = video.caption || video.title || 'Video'; title.className = 'library-title-link';
        const state = document.createElement('span'); state.className = 'badge';
        state.textContent = video.status === 'processing' ? 'Đang xử lý' : 'Có lỗi';
        const log = document.createElement('p'); log.className = 'hint'; log.textContent = video.log || '';
        row.append(title,state,log); fragment.append(row);
      }
      if (!active.length) {
        const empty = document.createElement('p'); empty.className = 'hint'; empty.textContent = 'Không có video đang xử lý.'; fragment.append(empty);
      }
      container.replaceChildren(fragment);
    }

    function publicationHtml(video) {
      const platforms = {facebook:'Facebook',instagram:'Instagram',threads:'Threads',tiktok:'TikTok',youtube:'YouTube'};
      const labels = {published:'Đã đăng',queued:'Chờ đăng',running:'Đang tải',submitting:'Đang xuất bản',failed:'Lỗi',needs_login:'Cần đăng nhập',needs_review:'Cần kiểm tra',cancelled:'Đã hủy'};
      const entries = Object.entries(video.publication || {});
      if (!entries.length) return '<span class="text-xs text-cozy-slate/60">Chưa có lịch đăng</span>';
      return '<div class="publication-chips">' + entries.filter(([platform]) => Object.hasOwn(platforms,platform)).map(([platform,info]) => {
        const state = Object.hasOwn(labels,info.state) ? info.state : 'queued';
        const text = `${platforms[platform]} · ${labels[state]}`;
        let valid = false;
        try {
          const url = new URL(info.url);
          const allowed = {facebook:['facebook.com','www.facebook.com','m.facebook.com'],instagram:['instagram.com','www.instagram.com'],threads:['threads.com','www.threads.com','threads.net','www.threads.net'],tiktok:['tiktok.com','www.tiktok.com'],youtube:['youtube.com','www.youtube.com','youtu.be']};
          valid = url.protocol === 'https:' && !url.username && !url.password && allowed[platform].includes(url.hostname);
        } catch {}
        return state === 'published' && valid ? `<a data-state="${state}" href="${escapeHtml(info.url)}" target="_blank" rel="noopener noreferrer">${text} ↗</a>` : `<span data-state="${state}">${text}</span>`;
      }).join('') + '</div>';
    }

    function renderTable(videos, isBatchRunning) {
      const tbody = document.getElementById("videoTableBody");
      const btnBatch = document.getElementById("btnBatchRender");

      if (btnBatch) {
      if (isBatchRunning) {
        btnBatch.disabled = true;
        btnBatch.classList.add("opacity-50", "cursor-not-allowed");
        btnBatch.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>Đang Dựng Toàn Bộ...</span>`;
      } else {
        btnBatch.disabled = false;
        btnBatch.classList.remove("opacity-50", "cursor-not-allowed");
        btnBatch.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-cozy-amber"></i><span>Dựng Toàn Bộ</span>`;
      }

      }
      if (!tbody) return;

      if (!videos || videos.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="12" class="py-16 text-center text-cozy-slate/60">
              <div class="text-4xl mb-3">🌿</div>
              <div class="font-bold text-base text-cozy-dark">Chưa có video nào trong danh sách</div>
              <div class="text-xs text-cozy-slate/70 mt-1"><a href="/create">Mở Tạo video</a> để tải và dựng video đầu tiên.</div>
            </td>
          </tr>
        `;
        return;
      }

      const STYLE_MAP = {
        cozy: { label: "☕ Cozy 2D" },
        midnight: { label: "🌌 Midnight Deep" },
        scrapbook: { label: "📝 Scrapbook" },
        pixel: { label: "🎮 Pixel 16-Bit" },
        brutalism: { label: "📊 Neo-Brutalism" },
        whiteboard: { label: "✍️ Whiteboard" }
      };

      const CHARACTER_MAP = {
        stickman: { label: "🧍 Người Que" },
        cat: { label: "🐱 Mèo Béo" },
        hoodie: { label: "🎧 Cậu Bé Hoodie" },
        bear: { label: "🐻 Gấu Teddy" },
        bot: { label: "🤖 Robot AI" },
        ghost: { label: "👻 Bé Ma" }
      };

      tbody.innerHTML = videos.map(v => {
        // Thumbnail
        const currentRatio = ["9:16", "16:9", "1:1", "4:3", "4:5", "16:10", "10:16"].includes(v.aspect_ratio) ? v.aspect_ratio : "9:16";
        const currentStyle = Object.hasOwn(STYLE_MAP, v.style) ? v.style : "cozy";
        const currentCharacter = Object.hasOwn(CHARACTER_MAP, v.character) ? v.character : "stickman";

        // Aspect Ratio Column: Selectable anytime!
        const ratioHtml = `
          <select
            onchange="changeVideoRatio('${v.id}', this.value)"
            ${v.status === 'processing' ? 'disabled' : ''}
            class="px-3 py-1.5 rounded-xl border-2 border-cozy-sand/80 bg-cozy-softCream hover:bg-white hover:border-cozy-terracotta text-xs font-bold text-cozy-dark focus:outline-none focus:border-cozy-terracotta cursor-pointer shadow-sm disabled:opacity-50 transition"
          >
            <option value="9:16" ${currentRatio === '9:16' ? 'selected' : ''}>📱 9:16 (Dọc)</option>
            <option value="16:9" ${currentRatio === '16:9' ? 'selected' : ''}>🖥️ 16:9 (Ngang)</option>
            <option value="1:1" ${currentRatio === '1:1' ? 'selected' : ''}>⏹️ 1:1 (Vuông)</option>
            <option value="4:3" ${currentRatio === '4:3' ? 'selected' : ''}>📺 4:3</option>
            <option value="4:5" ${currentRatio === '4:5' ? 'selected' : ''}>📸 4:5</option>
            <option value="16:10" ${currentRatio === '16:10' ? 'selected' : ''}>💻 16:10</option>
            <option value="10:16" ${currentRatio === '10:16' ? 'selected' : ''}>📱 10:16</option>
          </select>
        `;

        // Style Column: Selectable anytime!
        const styleHtml = `
          <select
            onchange="changeVideoStyle('${v.id}', this.value)"
            ${v.status === 'processing' ? 'disabled' : ''}
            class="px-3 py-1.5 rounded-xl border-2 border-cozy-sand/80 bg-cozy-softCream hover:bg-white hover:border-cozy-terracotta text-xs font-bold text-cozy-dark focus:outline-none focus:border-cozy-terracotta cursor-pointer shadow-sm disabled:opacity-50 transition"
          >
            <option value="cozy" ${currentStyle === 'cozy' ? 'selected' : ''}>☕ Cozy 2D</option>
            <option value="midnight" ${currentStyle === 'midnight' ? 'selected' : ''}>🌌 Midnight</option>
            <option value="scrapbook" ${currentStyle === 'scrapbook' ? 'selected' : ''}>📝 Scrapbook</option>
            <option value="pixel" ${currentStyle === 'pixel' ? 'selected' : ''}>🎮 Pixel Retro</option>
            <option value="brutalism" ${currentStyle === 'brutalism' ? 'selected' : ''}>📊 Brutalism</option>
            <option value="whiteboard" ${currentStyle === 'whiteboard' ? 'selected' : ''}>✍️ Whiteboard</option>
          </select>
        `;

        // Character Column: Selectable anytime!
        const charHtml = `
          <select
            onchange="changeVideoCharacter('${v.id}', this.value)"
            ${v.status === 'processing' ? 'disabled' : ''}
            class="px-3 py-1.5 rounded-xl border-2 border-cozy-sand/80 bg-cozy-softCream hover:bg-white hover:border-cozy-terracotta text-xs font-bold text-cozy-dark focus:outline-none focus:border-cozy-terracotta cursor-pointer shadow-sm disabled:opacity-50 transition"
          >
            <option value="stickman" ${currentCharacter === 'stickman' ? 'selected' : ''}>🧍 Người Que</option>
            <option value="cat" ${currentCharacter === 'cat' ? 'selected' : ''}>🐱 Mèo Béo</option>
            <option value="hoodie" ${currentCharacter === 'hoodie' ? 'selected' : ''}>🎧 Cậu Bé</option>
            <option value="bear" ${currentCharacter === 'bear' ? 'selected' : ''}>🐻 Gấu Teddy</option>
            <option value="bot" ${currentCharacter === 'bot' ? 'selected' : ''}>🤖 Robot AI</option>
            <option value="ghost" ${currentCharacter === 'ghost' ? 'selected' : ''}>👻 Bé Ma</option>
          </select>
        `;

        // Status badge & progress
        let statusHtml = "";
        const styleLabel = (STYLE_MAP[currentStyle] || STYLE_MAP.cozy).label;
        const charLabel = (CHARACTER_MAP[currentCharacter] || CHARACTER_MAP.stickman).label;
        if (v.status === "new") {
          statusHtml = `
            <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 whitespace-nowrap shadow-sm">
              <span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
              <span>Chờ dựng</span>
            </div>
            <div class="text-[11px] text-cozy-slate/60 mt-1 whitespace-nowrap">Sẵn sàng tạo hoạt hình</div>
          `;
        } else if (v.status === "processing") {
          statusHtml = `
            <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-300 whitespace-nowrap shadow-sm">
              <i class="fa-solid fa-spinner fa-spin text-blue-600"></i>
              <span>Đang tiến hành</span>
            </div>
            <div class="text-[11px] font-semibold text-blue-700 mt-1.5 px-2 py-1 rounded-lg bg-blue-50/90 border border-blue-200 shadow-sm animate-pulse line-clamp-2 max-w-[190px] mx-auto" title="${escapeHtml(v.log || '')}">
              <i class="fa-solid fa-gear fa-spin mr-1 text-[10px]"></i>${escapeHtml(v.log || 'Đang xử lý')}
            </div>
          `;
        } else if (v.status === "completed") {
          statusHtml = `
            <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 whitespace-nowrap shadow-sm">
              <i class="fa-solid fa-circle-check text-emerald-600"></i>
              <span>Đã hoàn thành</span>
            </div>
            <div class="text-[11px] text-emerald-700 font-bold mt-1 whitespace-nowrap">${styleLabel} • ${charLabel}</div>
            <div class="text-[10px] text-cozy-slate/60 font-semibold">Tỉ lệ ${currentRatio}</div>
          `;
        } else {
          statusHtml = `
            <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300 whitespace-nowrap shadow-sm">
              <i class="fa-solid fa-triangle-exclamation text-rose-600"></i>
              <span>Lỗi</span>
            </div>
            <div class="text-[11px] text-rose-600 mt-1 line-clamp-1 max-w-[190px] mx-auto" title="${escapeHtml(v.log || '')}">
              ${escapeHtml(v.log || 'Có lỗi xảy ra')}
            </div>
          `;
        }

        // Actions
        let actionsHtml = `
          <div class="flex items-center justify-center gap-1.5 whitespace-nowrap">
            <button type="button" data-caption-rewrite="${escapeHtml(v.id)}" class="px-3 py-2 rounded-xl bg-cozy-softCream text-cozy-dark text-xs font-bold">Viết lại caption</button>
        `;

        if (v.status === "completed" && v.output_filename) {
          actionsHtml += `
            <button type="button" data-schedule-video="${escapeHtml(v.id)}" class="px-3 py-2 rounded-xl bg-cozy-sage/20 text-cozy-dark text-xs font-bold">Lên lịch đăng</button>

            <!-- Nút dựng lại video bất cứ lúc nào -->
            <button
              onclick="renderSingleVideo('${v.id}', '${currentRatio}', '${currentStyle}', '${currentCharacter}')"
              class="px-2.5 py-1.5 rounded-xl bg-white hover:bg-cozy-bg text-cozy-slate border border-cozy-sand text-xs font-bold flex items-center gap-1 transition"
              title="Dựng lại video với ${styleLabel} • ${charLabel} (${currentRatio})"
            >
              <i class="fa-solid fa-arrows-rotate text-cozy-terracotta"></i>
              <span>Dựng Lại</span>
            </button>
          `;
        } else if (v.status === "processing") {
          actionsHtml += `
            <button disabled class="px-3 py-1.5 rounded-xl bg-blue-50 text-blue-500 text-xs font-bold border border-blue-200 cursor-not-allowed flex items-center gap-1.5 animate-pulse">
              <i class="fa-solid fa-spinner fa-spin"></i>
              <span>Đang Dựng...</span>
            </button>
          `;
        } else {
          actionsHtml += `
            <!-- Nút bắt đầu dựng hoạt hình -->
            <button
              onclick="renderSingleVideo('${v.id}', '${currentRatio}', '${currentStyle}', '${currentCharacter}')"
              class="px-3 py-1.5 rounded-xl bg-cozy-slate hover:bg-[#202235] text-white text-xs font-bold shadow-md shadow-cozy-slate/20 flex items-center gap-1.5 transition"
              title="Dựng video hoạt hình (${currentRatio} - ${styleLabel} - ${charLabel})"
            >
              <i class="fa-solid fa-play text-cozy-amber"></i>
              <span>Dựng Video</span>
            </button>
          `;
        }

        // Nút xóa
        actionsHtml += `
            <button
              onclick="deleteVideoItem('${v.id}', ${v.stt})"
              class="p-1.5 rounded-xl hover:bg-rose-100 text-cozy-slate hover:text-rose-600 transition"
              title="Xóa video"
            >
              <i class="fa-regular fa-trash-can text-sm"></i>
            </button>
          </div>
        `;

        return `
          <tr class="hover:bg-white/60 transition group library-record" data-video-detail="/videos/${encodeURIComponent(v.id)}" tabindex="0" aria-label="Xem chi tiết video ${escapeHtml(String(v.stt ?? v.id))}">
            <td class="py-4 px-3 text-center"><input type="checkbox" data-caption-video="${escapeHtml(v.id)}" aria-label="Chọn video ${escapeHtml(String(v.stt ?? v.id))} để viết caption"></td>
            <!-- STT -->
            <td class="py-4 px-3 text-center font-extrabold text-cozy-slate">
              #${v.stt}
            </td>

            <!-- Title & Info -->
            <td class="py-4 px-4 library-title-cell">
              <div class="font-bold text-sm text-cozy-dark leading-snug break-words" title="${escapeHtml(v.caption || v.title)}">
                <a class="library-title-link" href="/videos/${encodeURIComponent(v.id)}" title="${escapeHtml(v.caption || v.title)}">${escapeHtml(v.caption || v.title)}</a>
              </div>
              ${v.caption_ai_saved_at || v.caption ? `<span class="badge caption-rewrite-mark" title="Caption đã lưu">Đã viết lại</span>` : ''}
              <div class="text-xs text-cozy-slate/60 mt-1 flex flex-wrap items-center gap-3">
                <a href="${v.tiktok_url}" target="_blank" class="hover:text-cozy-terracotta hover:underline flex items-center gap-1">
                  <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                  <span>Xem trên TikTok</span>
                </a>
                <span>•</span>
                <span>Ngày tạo: ${v.created_at || 'Mới'}</span>
              </div>
            </td>

            <td class="py-4 px-3 text-center">${mediaThumbnail(v,'original',currentRatio,currentStyle,currentCharacter)}</td>
            <td class="py-4 px-3 text-center">${mediaThumbnail(v,'output',currentRatio,currentStyle,currentCharacter)}</td>
            <!-- Chuẩn Màn Hình -->
            <td class="py-4 px-3 text-center">
              ${ratioHtml}
            </td>

            <!-- Phong Cách -->
            <td class="py-4 px-3 text-center">
              ${styleHtml}
            </td>

            <!-- Nhân Vật -->
            <td class="py-4 px-3 text-center">
              ${charHtml}
            </td>

            <!-- Duration -->
            <td class="py-4 px-3 text-center">
              <span class="inline-block px-2.5 py-1 rounded-lg bg-cozy-bg border border-cozy-sand text-xs font-bold text-cozy-slate">
                ${v.duration_sec ? v.duration_sec + 's' : '--'}
              </span>
            </td>

            <!-- Status -->
            <td class="py-4 px-4 text-center">
              ${statusHtml}
            </td>

            <!-- Actions -->
            <td class="py-4 px-3">${publicationHtml(v)}</td>
            <td class="py-4 px-4 text-center">
              ${actionsHtml}
            </td>
          </tr>
        `;
      }).join("");
    }

    async function changeVideoRatio(videoId, newRatio) {
      try {
        await fetch(`/api/video/${videoId}/aspect-ratio`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ aspect_ratio: newRatio })
        });
        showToast(`Đã đổi tỉ lệ sang ${newRatio}`);
        fetchVideos();
      } catch (err) {
        console.error("Change ratio failed:", err);
      }
    }

    async function changeVideoStyle(videoId, newStyle) {
      try {
        await fetch(`/api/video/${videoId}/style`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ style: newStyle })
        });
        showToast(`Đã đổi phong cách sang ${newStyle}`);
        fetchVideos();
      } catch (err) {
        console.error("Change style failed:", err);
      }
    }

    async function changeVideoCharacter(videoId, newCharacter) {
      try {
        await fetch(`/api/video/${videoId}/character`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ character: newCharacter })
        });
        showToast(`Đã đổi nhân vật sang ${newCharacter}`);
        fetchVideos();
      } catch (err) {
        console.error("Change character failed:", err);
      }
    }

    async function handleDownloadAndRender() {
      const urlInput = document.getElementById("inputUrl");
      const limitInput = document.getElementById("inputLimit");
      const ratioInput = document.getElementById("globalAspectRatio");
      const styleInput = document.getElementById("globalStyle");
      const charInput = document.getElementById("globalCharacter");
      const url = urlInput.value.trim();
      const limit = limitInput.value === "all" ? "all" : (parseInt(limitInput.value) || 5);
      const aspect_ratio = ratioInput.value || "9:16";
      const style = styleInput ? styleInput.value : "cozy";
      const character = charInput ? charInput.value : "stickman";

      if (!url) {
        alert("Vui lòng nhập đường link TikTok vào ô trước!");
        urlInput.focus();
        return;
      }

      if (!url.includes('/video/') && !url.includes('vt.tiktok.com') && !url.includes('vm.tiktok.com')) {
        const proceed = confirm(
          "⚠️ LƯU Ý VỀ TIKTOK:\n\n" +
          "TikTok hiện đang bật hệ thống chống bot (Slardar WAF) chặn cào tự động trang cá nhân kênh.\n\n" +
          "👉 Để tải & dựng 100% thành công, bạn nên dán LINK VIDEO CỤ THỂ (dạng https://www.tiktok.com/@.../video/... hoặc link rút gọn vt.tiktok.com).\n\n" +
          "Bạn có muốn tiếp tục thử tải với đường dẫn này không?"
        );
        if (!proceed) {
          urlInput.focus();
          return;
        }
      }

      showToast(`⚡ Đang kết nối tải và dựng (${aspect_ratio} - ${style} - ${character})...`);
      const btn = document.getElementById("btnDownloadAndRender");
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>Đang xử lý...</span>`;

      try {
        const res = await fetch("/api/download-and-render", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, limit, aspect_ratio, style, character })
        });
        const data = await res.json();
        if (data.status === "success") {
          urlInput.value = "";
          showToast("Đã đưa vào hàng chờ dựng video!", "success");
          fetchVideos();
        } else {
          alert("Lỗi: " + data.message);
        }
      } catch (err) {
        alert("Lỗi: " + err);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-bolt text-yellow-300"></i><span>Tải & Dựng Ngay</span>`;
      }
    }

    async function handleDownload() {
      const urlInput = document.getElementById("inputUrl");
      const limitInput = document.getElementById("inputLimit");
      const ratioInput = document.getElementById("globalAspectRatio");
      const styleInput = document.getElementById("globalStyle");
      const charInput = document.getElementById("globalCharacter");
      const url = urlInput.value.trim();
      const limit = limitInput.value === "all" ? "all" : (parseInt(limitInput.value) || 5);
      const aspect_ratio = ratioInput.value || "9:16";
      const style = styleInput ? styleInput.value : "cozy";
      const character = charInput ? charInput.value : "stickman";

      if (!url) {
        alert("Vui lòng nhập đường link TikTok!");
        urlInput.focus();
        return;
      }

      if (!url.includes('/video/') && !url.includes('vt.tiktok.com') && !url.includes('vm.tiktok.com')) {
        const proceed = confirm(
          "⚠️ LƯU Ý VỀ TIKTOK:\n\n" +
          "TikTok hiện đang bật hệ thống chống bot chặn quét trang cá nhân kênh.\n\n" +
          "👉 Bạn nên dán LINK VIDEO CỤ THỂ (dạng https://www.tiktok.com/@.../video/... hoặc vt.tiktok.com) để tải ngay.\n\n" +
          "Bạn có muốn tiếp tục thử tải không?"
        );
        if (!proceed) {
          urlInput.focus();
          return;
        }
      }

      const btn = document.getElementById("btnDownload");
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>Đang tải...</span>`;
      showToast("Đang kết nối tải video TikTok...");

      try {
        const res = await fetch("/api/download", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, limit, aspect_ratio, style, character })
        });
        const data = await res.json();
        if (data.status === "success") {
          urlInput.value = "";
          showToast("Đã tải video về danh sách thành công!", "success");
          fetchVideos();
        } else {
          alert("Lỗi: " + data.message);
        }
      } catch (err) {
        alert("Lỗi khi kết nối tải video: " + err);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i><span>Tải Video</span>`;
      }
    }

      async function renderSingleVideo(videoId, ratio, style, character) {
        const currentStyle = style || "cozy";
        const currentChar = character || "stickman";
        showToast(`🎬 Đang khởi động dựng hoạt hình (${ratio} - ${currentStyle} - ${currentChar})...`);
        try {
          const res = await fetch(`/api/render/${videoId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ aspect_ratio: ratio, style: currentStyle, character: currentChar })
          });
          const data = await res.json();
          if (data.status === "success") {
            fetchVideos();
          } else {
            alert("Lỗi: " + data.message);
          }
        } catch (err) {
          alert("Không thể bắt đầu dựng video: " + err);
        }
      }

      async function handleRenderAll(force = false) {
        const ratioInput = document.getElementById("globalAspectRatio");
        const styleInput = document.getElementById("globalStyle");
        const charInput = document.getElementById("globalCharacter");
        const urlInput = document.getElementById("inputUrl");
        const ratio = ratioInput.value || "9:16";
        const style = styleInput ? styleInput.value : "cozy";
        const character = charInput ? charInput.value : "stickman";
        const url = urlInput ? urlInput.value.trim() : "";

        const total = parseInt(document.getElementById("statTotal").innerText) || 0;

        if (total === 0 && url) {
          if (confirm(`Bạn đang có đường link TikTok trong ô nhập. Bạn có muốn tải về và dựng hoạt hình (${ratio}) ngay không?`)) {
            handleDownloadAndRender();
            return;
          }
        } else if (total === 0) {
          alert("Chưa có video nào trong danh sách! Vui lòng dán link TikTok ở trên và bấm 'Tải & Dựng Ngay' hoặc 'Tải Video' trước nhé.");
          urlInput.focus();
          return;
        }

        try {
          const res = await fetch("/api/render-all", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ aspect_ratio: ratio, style: style, character: character, force_all: force })
          });
          const data = await res.json();
          if (data.status === "ask_re_render") {
            if (confirm(data.message)) {
              handleRenderAll(true);
            }
          } else if (data.status === "success") {
            showToast("⚡ Đã bắt đầu tiến trình dựng hàng loạt!", "success");
            fetchVideos();
          } else {
            alert(data.message);
          }
        } catch (err) {
          alert("Không thể bắt đầu dựng hàng loạt: " + err);
        }
      }

      async function deleteVideoItem(videoId, stt) {
        if (!confirm(`Bạn có chắc chắn muốn xóa Video #${stt} không?`)) {
          return;
        }

        try {
          const res = await fetch(`/api/video/${videoId}`, { method: "DELETE" });
          const data = await res.json();
          if (data.status === "success") {
            showToast(`Đã xóa Video #${stt}`);
            fetchVideos();
          }
        } catch (err) {
          alert("Lỗi khi xóa video: " + err);
        }
      }

      // Modal player
      function playOriginal(filename, title) {
        const modal = document.getElementById("videoModal");
        const player = document.getElementById("modalVideoPlayer");
        const titleElem = document.getElementById("modalTitle");
        const badgeElem = document.getElementById("modalBadge");
        const iconElem = document.getElementById("modalIcon");
        const dlBtn = document.getElementById("modalDownloadBtn");
        const dialog = document.getElementById("modalDialog");

        const videoUrl = `/video/download/${filename}`;
        player.src = videoUrl;
        titleElem.innerText = title;
        titleElem.title = title;
        badgeElem.innerText = "Video TikTok Gốc";
        badgeElem.className = "text-xs px-2.5 py-0.5 rounded-full font-bold bg-slate-200 text-slate-800";
        iconElem.innerHTML = `<i class="fa-brands fa-tiktok"></i>`;
        dlBtn.href = videoUrl;
        dialog.dataset.format = 'original';

        modal.classList.remove("hidden");
        player.play().catch(() => { });
      }

        function playOutput(filename, title, ratio, style, character) {
          const modal = document.getElementById("videoModal");
          const player = document.getElementById("modalVideoPlayer");
          const titleElem = document.getElementById("modalTitle");
          const badgeElem = document.getElementById("modalBadge");
          const iconElem = document.getElementById("modalIcon");
          const dlBtn = document.getElementById("modalDownloadBtn");
          const dialog = document.getElementById("modalDialog");

          const styleLabels = {
            cozy: "☕ Cozy 2D",
            midnight: "🌌 Midnight Deep",
            scrapbook: "📝 Scrapbook",
            pixel: "🎮 Pixel Retro",
            brutalism: "📊 Neo-Brutalism",
            whiteboard: "✍️ Whiteboard"
          };
          const charLabels = {
            stickman: "🧍 Người Que",
            cat: "🐱 Mèo Béo",
            hoodie: "🎧 Cậu Bé Hoodie",
            bear: "🐻 Gấu Teddy",
            bot: "🤖 Robot AI",
            ghost: "👻 Bé Ma"
          };
          const label = styleLabels[style] || "Cozy 2D";
          const charLabel = charLabels[character] || "Người Que";

          const videoUrl = `/video/output/${filename}`;
          player.src = videoUrl;
          titleElem.innerText = title;
          titleElem.title = title;
          badgeElem.innerText = `🌟 ${label} • ${charLabel} (${ratio || '9:16'})`;
          badgeElem.className = "text-xs px-2.5 py-0.5 rounded-full font-bold bg-cozy-terracotta/20 text-cozy-terracotta border border-cozy-terracotta/40";
          iconElem.innerHTML = `✨`;
          dlBtn.href = videoUrl;

          // Adjust dialog width based on ratio
          if (ratio === "16:9" || ratio === "16:10" || ratio === "4:3") {
            dialog.dataset.format = 'landscape';
          } else {
            dialog.dataset.format = 'portrait';
          }

          modal.classList.remove("hidden");
          player.play().catch(() => { });
        }

        function closeModal() {
          const modal = document.getElementById("videoModal");
          const player = document.getElementById("modalVideoPlayer");
          player.pause();
          player.src = "";
          modal.classList.add("hidden");
        }

        function escapeHtml(text) {
          if (!text) return "";
          return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
        }
