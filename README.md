# 🎬 TikTok Animator Studio (2D Cozy Storytelling 9:16)

Hệ thống quản lý, tải và tự động chuyển thể video TikTok sang phong cách **Cozy 2D Animated Storytelling with Kinetic Typography**. Dựng video bằng Remotion trên máy cá nhân; tải video, nhận diện giọng nói qua Google và đăng mạng xã hội cần Internet. Các luồng Playwright không dùng API key của nền tảng.

## Hoạt hình theo lời thoại bằng Antigravity

Mở tab riêng **Hoạt hình AI** (`/animation`), chọn video đã tải trong thư viện rồi bấm **Dựng bằng Antigravity**. Tab này có cấu hình model, model nhận diện, ảnh thu nhỏ và tiến trình của video đã chọn. Cấu hình được chốt khi bấm dựng; kết quả có thể xem từ liên kết chi tiết hoặc trong thư viện. File AI có tiền tố `antigravity_`, không ghi đè file dựng cũ.

Trạng thái của video hiện rõ ngay dưới tiêu đề: **Đang chạy** có vòng xoay và giai đoạn 1/4–4/4 (âm thanh, nhận diện/phân cảnh, dựng cảnh, xuất video); **Thất bại** màu đỏ kèm lỗi; **Đã hoàn thành** màu xanh. Đây là giai đoạn xử lý, không phải phần trăm render thực tế. Trang cập nhật mỗi 2,5 giây; thông báo đã nhận yêu cầu tự thay bằng kết quả cuối, không giữ thông báo thành công khi tác vụ đã lỗi. Các phong cách cũ `semantic_dark` và `ai_storyboard` được ánh xạ riêng cho AI sang `midnight` và `cozy`, giữ cấu hình tạo video cũ trong thư viện. Cấu hình không hỗ trợ bị từ chối trước khi chạy AI.

**Tạo video** và các nút **Tải & Dựng Ngay**, **Dựng Toàn Bộ**, **Dựng Lại** trong luồng cũ luôn dùng bộ phân tích ban đầu, không đọc cấu hình AI, không gọi Antigravity. Chỉ endpoint riêng `/api/animation/render/<video_id>` mới bật AI. Không có bộ chọn chế độ AI trong màn tạo hoặc thư viện cũ.

Cài thêm một lần trên Windows:

```powershell
powershell -ExecutionPolicy Bypass -File tools/setup-animation.ps1
```

Cài CLI chính thức theo [hướng dẫn Antigravity](https://antigravity.google/docs/getting-started?tab=cli), mở terminal chạy `agy` và đăng nhập tài khoản Google dùng gói/quota mong muốn. Không nhập API key XAH vào phần này. CLI hỗ trợ [chạy tự động và kết quả JSON](https://antigravity.google/docs/cli/headless/). Kiểm tra trạng thái trên giao diện chỉ xác nhận CLI và thư viện nhận diện đã cài, không kiểm tra đăng nhập/quota. Trong **Tùy chỉnh model**, để trống dùng model mặc định tài khoản; `agy models` liệt kê các model khả dụng. Model caption được cấu hình riêng.

Nhận diện tiếng Việt bằng faster-whisper trên CPU/int8, chạy trong `.venv-speech` Python 3.13 để không thay đổi môi trường Python hiện tại của Studio. Mặc định model `small`; lần đầu cần Internet tải model, sau đó nhận diện cục bộ. Có thể đổi model trong giao diện. Mốc từng từ do bộ nhận diện ước lượng theo âm thanh; độ chính xác phụ thuộc giọng nói, nhạc nền và model, không phải bảo đảm khớp tuyệt đối từng âm tiết.

Gửi **toàn bộ lời thoại** cho Antigravity một lần để chọn cảm xúc, tình huống minh họa và điểm bắt đầu hành động. Python giữ nguyên chữ và mốc thời gian, không để AI bịa timestamp. Giới hạn 300 ký tự của viết caption **không áp dụng** cho hoạt hình. Bộ dựng AI có mười cảnh có chuyển động: hai người rời nhau, nâng đỡ nhau, buông gánh nặng, chọn ngã rẽ, tưới cây, bước đi trên đường, trò chuyện, soi gương/suy ngẫm, vượt khó/ăn mừng và bình yên. Tay/chân nhân vật có khớp chuyển động, có nhân vật thứ hai và đạo cụ theo tình huống. Các đoạn phụ đề cùng tình huống tiếp tục dùng cùng cảnh và giữ hành động đã bắt đầu; không reset mỗi câu. Miệng và chữ chỉ nhấn theo mốc nói. Chưa có tạo ảnh/video AI tùy ý hoặc lip-sync theo âm vị; đây là thư viện cảnh minh họa bằng SVG/Remotion.

Cache nhận diện và kịch bản ở `data/animation/` (không đưa lên Git), theo nội dung file, model nhận diện và model Antigravity đã chọn. Dựng lại cùng cấu hình dùng cache, đổi tỉ lệ/phong cách/nhân vật không gọi AI lại. Lỗi đăng nhập, quota hoặc kịch bản thiếu cảnh sẽ dừng rõ ràng, không tự gọi lại/XAH; file thành phẩm cũ giữ nguyên cho đến khi render mới hoàn tất. Antigravity tiêu hao quota theo [gói tài khoản và thiết lập credit](https://antigravity.google/docs/plans); render MP4 chạy trên máy.

Remotion cho AI nằm trong `remotion/`, được theo dõi cùng repo. Luồng dựng cũ tiếp tục dùng `../remotion-project` nếu tồn tại, nếu không sẽ dùng composition tương thích trong repo. Project Remotion bên ngoài được giữ nguyên. Có thể chỉ định đường dẫn CLI qua biến môi trường `ANTIGRAVITY_CLI`, hoặc Python nhận diện qua `ANIMATION_PYTHON` nếu cài ở vị trí khác.

Kịch bản v1 chỉ chọn cử động nhẹ sẽ được phân tích lại một lần khi dựng AI sau bản cập nhật cảnh minh họa. Bộ nhớ lời thoại vẫn dùng lại; các lần sau giữ nguyên kịch bản v2 đã lưu.

Kiểm tra bổ sung (fixture không gọi AI):

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_animation -v
npm.cmd --prefix remotion run check
.\.venv\Scripts\python.exe tools/check-animation-render.py
node tests/check_story_motion.cjs
.\.venv\Scripts\python.exe tools/check-story-scenes.py
```

Video kiểm tra ghi vào `data/animation/check.mp4`; bản minh họa mười cảnh không có giọng nói ở `data/animation/story-scenes.mp4`.

## Lên lịch đăng mạng xã hội bằng Playwright

### Tên kênh trên video

Vào **Tạo video → Tên kênh trên video** (cũng có trong **Hoạt hình AI**), nhập tên (tối đa 80 ký tự, một dòng) rồi **Lưu cấu hình**. Trang Tạo video cũng tự lưu thay đổi khi bấm **Tải & Dựng Ngay** hoặc **Dựng Toàn Bộ**. Tên được in mờ ở chính giữa xuyên suốt video, áp dụng cho các lượt dựng thường, tải và dựng, dựng hàng loạt và AI tiếp theo. Để trống để tắt. Video đã xuất cần dựng lại để có watermark. Khi bật watermark, dựng thường dùng engine Remotion đi kèm để bảo đảm tên kênh được in vào thành phẩm; engine ngoài cũ không có lớp này.

TikTok: khi lịch có ảnh bìa của app, bộ đăng mở **Edit cover → Upload cover**, tải bản ảnh dọc đã chốt rồi **Save**. Chỉ tiếp tục xuất bản sau khi thấy ảnh mới và đã lưu trình chọn bìa. Nếu chưa xác minh được ảnh, lượt TikTok dừng trước khi bấm Đăng; không tự thay bằng khung video hoặc ảnh TikTok chọn. Áp dụng cho các lượt đăng tiếp theo, giữ nguyên các bài đã đăng.

Facebook: hộp **Chọn hình thu nhỏ** được xử lý trước khi chuyển sang Cài đặt. App dùng ô tải ảnh trong đúng vùng ảnh bìa, chờ nút Lưu bật và chờ hộp đóng rồi mới bấm Tiếp. Nếu không lưu hoặc chưa xác minh được ảnh mới, trạng thái ảnh bìa được giữ là tự động/chưa xác minh, không báo đã áp dụng.

### Lấy nội dung để đăng thủ công

Trong **Thư viện**, bấm **tiêu đề** để copy nguyên caption đã lưu, gồm xuống dòng và hashtag (dùng tiêu đề nếu chưa có caption). Bấm phần khác của hàng để mở chi tiết. **Tải video thành phẩm** nằm dưới bản xem trước thành phẩm; **Tải ảnh bìa** lấy bản dọc/ngang theo tỉ lệ video. Chỉ hiện nút tải khi record có file tương ứng. Tải file không đánh dấu record đã đăng.

### Nhận biết video đã đăng trong Thư viện

Trạng thái chỉ nằm trong cột **Đã Đăng Ở Đâu**: nền tảng đã được hệ thống xác nhận có link bài; kết quả chưa rõ hiện **Chưa xác định**. Không có thao tác người dùng nhập link để xác nhận trên giao diện kết quả đăng.

TikTok có thêm xác nhận từ trang **TikTok Studio → Nội dung** của đúng tài khoản. Hệ thống đối chiếu toàn bộ caption, thời điểm trong lượt đăng và ID/link bài trên danh sách Posts, không lấy link gợi ý hay bài có cùng tiêu đề rút gọn. Cơ chế này áp dụng ngay sau đăng và tự kiểm tra lại các lượt TikTok chưa rõ kết quả khi worker rảnh, tối đa một lượt kiểm tra mỗi 10 phút. Không tải lên hay bấm đăng lại khi kiểm tra. Lịch chưa từng chạy, kết quả trùng khớp nhiều bài, link đã thuộc lượt khác hoặc tài khoản đã đổi không được xác nhận. Facebook cũng tự đối chiếu bài Reel trên hồ sơ/Fanpage đã dùng: tác giả Story và chủ sở hữu Video, toàn bộ caption, thời điểm và link phải cùng khớp. Hồ sơ/Fanpage được lưu tại checkpoint trước khi bấm Đăng. Khi Facebook chuyển về bảng tin mà không có thông báo kèm link, app mở hồ sơ đã lưu để đối chiếu ngay; worker cũng kiểm tra lại các lượt chưa rõ khi rảnh. Lượt cũ thiếu hồ sơ chỉ được xử lý nếu xác minh được giá trị và thời điểm của cookie hồ sơ đã lưu; cookie mã hóa hoặc khác giá trị không đủ làm bằng chứng. Các nền tảng khác tiếp tục cần bằng chứng từ giao diện hoàn tất; nếu chưa lấy được bằng chứng, trạng thái vẫn chưa xác định và không tự đăng lại.

### Xóa video và kiểm tra trùng

Nút xóa trong thư viện **xóa mềm record, xóa cứng media**: lưu `deleted_at`, ID nguồn TikTok và SHA256 file gốc, giữ ID/STT/caption/lịch sử; ẩn record khỏi thư viện, dựng video, viết caption và nguồn bài tự động. File gốc, bản render đang dùng, các biến thể render thuộc record và thumbnail/cached thumbnail được xóa trên ổ đĩa. File còn được record đang hoạt động khác dùng chung sẽ được giữ cho record đó. Không xóa video đang tải/dựng; nếu file đang bị khóa, record vẫn được giữ và API trả lỗi dọn file để có thể thử lại thao tác xóa theo ID.

Tải lại kiểm tra cả record đang có và record đã xóa theo ID TikTok/URL bỏ tham số chia sẻ; sau khi tải một file mới còn so SHA256 để nhận ra nguồn qua link khác. Link trực tiếp trùng trả HTTP 409 trước khi chạy nền; quét kênh bỏ qua video đã có hoặc đã xóa. Không so theo tiêu đề/caption. Link rút gọn chưa từng gặp có thể cần tải về trước để nhận diện ID/hash; file tạm trùng được xóa, không tạo lại video trong thư viện. `GET /api/videos/check-duplicate?url=...` trả ID record và cờ đã xóa mà không tải media.

Trong **Thư viện**, tích nhiều record hoặc **Chọn tất cả**, rồi bấm **Xóa đã chọn**. App xác nhận số record và việc xóa media, xử lý lần lượt và báo kết quả từng record; không cần API key AI. Record đang xử lý được giữ lại. Record lỗi vẫn được chọn nếu còn hiển thị; nút **Thử xóa lại … record lỗi** cũng xử lý được record đã ẩn nhưng còn file chưa dọn xong. Các file dùng chung vẫn được bảo vệ như khi xóa từng record.

Record lưu trong `data/videos.json`; truy vấn nội bộ `get_all_videos(include_deleted=True)` hoặc `get_video(id, include_deleted=True)` có thể xem lịch sử đã xóa. Không có thao tác khôi phục media đã xóa cứng. Thay đổi áp dụng cho những lần xóa từ bản này; record từng bị xóa cứng trước đây không tự được phục hồi. Các lượt đăng đã lên lịch trước đó dùng bản sao riêng và lịch sử đăng được giữ nguyên.

Khi nhập link kênh TikTok (`https://www.tiktok.com/@username`), app thử quét danh sách bằng yt-dlp và dịch vụ dự phòng. Nếu chưa lấy được danh sách, app mở Google Chrome với hồ sơ TikTok riêng. Hoàn thành CAPTCHA hoặc đăng nhập thủ công khi TikTok yêu cầu, giữ cửa sổ mở; app chờ tối đa 10 phút, lấy link đúng kênh, cuộn để tìm thêm, rồi tự đóng Chrome và tiếp tục tải/dựng. Đóng Chrome sớm sẽ dừng lượt quét và hiện lỗi rõ ràng. Không tự giải CAPTCHA. Trạng thái chờ xác minh hiển thị trong tiến trình video. Hồ sơ được giữ riêng cho lượt quét để không mở trùng với đăng bài/đăng nhập; phiên và công tắc cho phép đăng được giữ nguyên. Video trùng vẫn được bỏ qua. Quét “tất cả” dừng khi danh sách không xuất hiện link mới qua nhiều lượt chờ; TikTok có thể giới hạn số video tải được trong phiên.

Hỗ trợ luồng giao diện cho **Facebook Reels trên hồ sơ cá nhân, Instagram Reels, Threads, TikTok và YouTube**. Mỗi lịch tạo tác vụ riêng cho những nền tảng đang bật, dùng caption hiện có (`caption`, nếu có; mặc định là `title` kèm hashtag). Không cần nhập lại caption. Các adapter có thể cần điều chỉnh selector khi giao diện nền tảng thay đổi.

Trong **Tài khoản**, công tắc **Cho phép đăng** của từng nền tảng lưu độc lập với phiên đăng nhập. Tắt nền tảng sẽ bỏ nó khỏi lịch mới và hủy tác vụ còn chờ; tác vụ đang chạy được tiếp tục, tác vụ cần kiểm tra vẫn giữ để xác minh. Bật lại không tự khôi phục tác vụ đã hủy. Khi tất cả đều tắt, không thể tạo lịch mới; lịch hằng ngày không lấy bài nếu không có nền tảng đang bật đã lưu phiên. Dữ liệu cũ mặc định bật cả năm để giữ cấu hình trước đây.

Facebook hiện mở trang tạo Reels bằng hồ sơ đang hoạt động trong phiên trình duyệt đã lưu. Chưa có bộ chọn hoặc xác minh đích Fanpage riêng; hãy chuyển về hồ sơ cá nhân khi kết nối và kiểm tra đúng hồ sơ trước khi lưu phiên. Không suy ra đích đăng chỉ từ tài khoản đăng nhập.

### Cài đặt và chạy trên Windows

### Tự lấy bài theo các giờ trong ngày

Tại `/publishing`, thêm các giờ trong mục **Lịch lặp hằng ngày**, chẳng hạn `08:00`, `12:00`, `19:00`. Mặc định dùng giờ Việt Nam/Bangkok (UTC+7) và **lấy ngẫu nhiên trong video chưa dùng**. Chọn đối tượng khán giả YouTube, bật **Bật đăng tự động hằng ngày**, xác nhận rồi bấm **Lưu lịch hằng ngày**. Không cần chọn video riêng cho mỗi giờ.

Đến mỗi giờ, bộ đăng tự lấy một video đã dựng với caption có sẵn và tạo một lượt cho các nền tảng đang bật trong Tài khoản. Các video đã từng có lịch hoặc đã được bộ đăng giữ lại sẽ không được tự chọn lại, kể cả lượt đó lỗi/hủy; xử lý nền tảng lỗi trong lượt gốc để tránh đăng trùng. Khi hết video, khung giờ được ghi nhận là **Hết bài** và bỏ qua; video thêm sau đó được xét từ khung giờ kế tiếp.

Thay đổi cấu hình áp dụng từ khi lưu, không chạy bù các giờ trước đó. Sau khi máy tắt hoặc sleep, chỉ khung giờ gần nhất trễ không quá 15 phút mới được lấy bài; các giờ cũ được bỏ qua để không đăng dồn. Tắt tự động chỉ ngừng lấy bài mới, không hủy các lượt đã tạo. Máy và worker cần hoạt động, có mạng; các nền tảng vẫn được xử lý lần lượt. Có thể mở mục **Đặt lịch riêng cho một video (tùy chọn)** nếu muốn lên lịch thủ công.

### Cài đặt và chạy trên Windows

1. Cài Python tương thích với các gói trong `requirements.txt` (môi trường phát triển đã kiểm tra Python 3.15).
2. Chạy `setup.bat` một lần để tạo `.venv`, cài dependency và Chromium của Playwright.
3. Khởi động lại ứng dụng bằng `run.bat`. Mở `http://localhost:5000/publishing`, hoặc chọn **Lên lịch đăng mạng xã hội** trong thư viện.
4. Với từng nền tảng, chọn **Kết nối**, đăng nhập thủ công trong cửa sổ vừa mở, kiểm tra đúng tài khoản/hồ sơ/kênh rồi quay lại Studio bấm **Lưu phiên**. Thực hiện xác minh/2FA trực tiếp khi nền tảng yêu cầu. Mỗi lần kết nối có tối đa 20 phút.
5. Chọn video đã dựng, kiểm tra video và caption, chọn ngày/giờ và đối tượng trẻ em của YouTube, xác nhận rồi bấm **Lên lịch cho cả 5 nền tảng**. YouTube dùng dòng đầu caption làm tiêu đề (tối đa 100 ký tự) và giữ toàn bộ caption trong mô tả; xuất bản công khai.

Máy phải bật, không sleep và có mạng. Bộ đăng xử lý lần lượt để hạn chế tải bộ nhớ; giờ xuất hiện công khai không được đảm bảo đồng thời. Đóng trang web không hủy các lịch: bộ đăng là tiến trình riêng. Dùng **Hủy phần chưa chạy** để dừng các đích còn chờ; tác vụ đã bắt đầu không bị hủy giữa chừng.

Khi đăng bài, trình duyệt dùng nhịp nghỉ 5 giây cho mỗi thao tác Playwright và vẫn kiểm tra phần tử sẵn sàng trước khi bấm/nhập. Nhịp nghỉ áp dụng cho cả năm nền tảng; không thay đổi tốc độ cửa sổ đăng nhập. Đây không phải cơ chế tránh nhận diện automation. Sau khi cập nhật mã bộ đăng, cần khởi động lại worker để nhận thay đổi.

### Trạng thái, thử lại và tránh đăng trùng

- Mỗi nền tảng có trạng thái và link riêng. Chỉ báo **Đã đăng** khi có thông báo hoàn thành cùng permalink trong giao diện xác nhận của nền tảng.
- Nếu lỗi trước bước xuất bản, có thể thử lại riêng nền tảng đó. Phiên hết hạn sẽ yêu cầu kết nối lại.
- Nếu đã bắt đầu bấm xuất bản nhưng chưa nhận được kết quả, chuyển sang **Cần kiểm tra bài**. Mở tài khoản để kiểm tra: nếu đã đăng, dùng **Bài đã đăng • lưu link**; nếu chắc chắn chưa có, dùng **Đã kiểm tra, thử lại**. Không tự động lặp lại thao tác xuất bản.
- Lịch trễ hơn 15 phút (máy tắt/sleep hoặc hàng đợi chậm) cần xác nhận lại thay vì tự động đăng muộn.
- Lịch giữ một bản sao MP4 và caption riêng. Dựng lại/xóa video gốc không đổi lịch đã tạo. Nếu bản sao bị thay đổi, worker dừng tác vụ.
- Khi xác định được ID tài khoản/kênh, lịch gắn với tài khoản lúc tạo. Đổi tài khoản sẽ yêu cầu kết nối lại tài khoản cũ hoặc tạo lịch mới. Kiểm tra tài khoản khi lưu phiên, đặc biệt nếu dùng nhiều kênh YouTube.

### Dữ liệu cục bộ và bộ đăng

SQLite, hồ sơ trình duyệt, bản sao MP4, log và ảnh chụp lỗi nằm trong `data/social/`, đã được loại khỏi Git. Không chia sẻ thư mục này vì hồ sơ chứa phiên đăng nhập. Ảnh chụp lỗi: `data/social/diagnostics/<task-id>.png`; log tiến trình: `data/social/process.log`. Bản sao video được giữ lại để bảo toàn lịch; chỉ dọn khi không còn lịch cần dùng chúng.

`run.bat` dùng Python trong `.venv` nếu có và tự khởi động bộ đăng. Có thể chạy bộ đăng thủ công:

```powershell
.\.venv\Scripts\python.exe -m services.social.worker
```

Chỉ một worker được hoạt động cho cùng thư mục dữ liệu; khóa hệ điều hành ngăn tiến trình thứ hai xử lý trùng. Để chạy Studio mà không tự mở worker, đặt `SOCIAL_AUTOSTART_WORKER=0` trước khi chạy `app.py`. `SOCIAL_DATA_DIR` cho phép chỉ định thư mục dữ liệu riêng; Studio, login và worker phải dùng chung thư mục này. Web chỉ nghe `127.0.0.1` và nhận các thao tác từ cùng nguồn localhost.

Engine render nằm tại `remotion/` trong repo. Chạy `npm.cmd --prefix remotion ci` hoặc script cài hoạt hình bên trên để cài dependency. Không cần engine để mở trang lịch và quản lý các video đã dựng sẵn.

### Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/admin/js/core.js
```

Kiểm tra dùng SQLite tạm, MP4 thử và Playwright headless trên trang HTML cục bộ; không đăng nhập hoặc đăng bài thật. Môi trường chưa cài Playwright sẽ bỏ qua các kiểm tra trình duyệt. Chạy `setup.bat` để chạy đủ.

### Các trang quản trị

- `/publishing`: Tổng quan.
- `/publishing/schedule`: Lịch tự động hằng ngày.
- `/publishing/accounts`: Kết nối tài khoản.
- `/publishing/results`: Kết quả và thử lại nền tảng lỗi.
- `/publishing/new`: Đặt lịch riêng cho một video.
- `/publishing/captions`: Chọn video và nhờ AI viết lại caption.

### Trạng thái đăng và caption AI

Thư viện video có cột **Đã đăng ở đâu**, chỉ hiển thị những nền tảng đã đăng thành công cùng link bài; chưa có nền tảng thành công thì hiện **Chưa đăng**. Lỗi, chờ và cần kiểm tra xem ở **Kết quả đăng**. Thành công trên bất kỳ một nền tảng nào cũng tính record đã đăng: khóa tạo lượt mới và loại khỏi lựa chọn đặt lịch. Các nền tảng còn lại trong cùng lượt vẫn chạy. Lịch trùng cũ chưa chạy bị chặn khi record đã thành công trong lượt khác. Chỉ tính thành công khi worker có xác nhận hoặc bạn xác nhận thủ công bằng link bài; **Cần kiểm tra** chưa tự được coi là đã đăng.

Trong **Thư viện**, tích chọn ngay trong bảng (hoặc chọn tất cả), rồi bấm **Viết lại caption** trên thanh caption. Nút **Viết lại caption** của từng dòng chạy ngay cho video đó, không thay đổi lựa chọn hoặc chuyển màn; thao tác riêng từng dòng cho phép viết lại cả video đã viết, không phụ thuộc bộ lọc xử lý hàng loạt. Nút hiện **Đang viết…** trong khi xử lý. **AI viết thành công là lưu trực tiếp vào video, cập nhật ngay nội dung trong bảng; không có bản nháp hoặc bước duyệt/lưu thêm.** AI không tự tạo hoặc giữ hashtag cũ trong kết quả mới. Bấm tiêu đề/dòng để xem video gốc/đã dựng, thông tin dựng, caption hiện tại, lời thoại và trạng thái đăng. Vẫn có thể sửa caption thủ công ở màn chi tiết rồi bấm lưu. Nếu caption đã thay đổi trong lúc AI chạy, hệ thống báo lỗi video đó và không ghi đè. Đường dẫn `/publishing/captions` cũ vẫn dùng được để tương thích; kết quả AI ở đó cũng đã lưu trực tiếp.

Nút **Lên lịch đăng** của từng dòng mở hộp chọn giờ ngay trong Thư viện: xem caption và các nền tảng đang bật, chọn thời gian, phân loại nội dung nếu có YouTube và xác nhận. Bấm **Lưu lịch đăng** để tạo lịch mà không chuyển màn. Nếu mất phản hồi, thử lại với dữ liệu không đổi dùng cùng mã yêu cầu để lấy lại lịch cũ, kể cả record đã đăng hoặc công tắc nền tảng đã đổi. Màn Đặt lịch riêng vẫn hoạt động.

Hai màn riêng trong thanh bên: **Tạo video** (`/create`) gồm tải/dựng, cấu hình mặc định, thống kê và tiến trình xử lý; **Thư viện** (`/`) gồm bảng quản lý video, viết caption và trạng thái đăng. Màn tạo không tải phần cấu hình caption; thư viện không có ô nhập link/tải video. Các nút dựng lại từng video vẫn có trong thư viện.

Trong **Tạo video**, mục **Tiến trình xử lý** liệt kê toàn bộ video đang tải/dựng, tiếp theo là các video chờ dựng/chờ đến lượt. Mỗi dòng có thumbnail, tiêu đề rút gọn, trạng thái và log/bước 1/4–4/4. Đây là giai đoạn xử lý, không phải phần trăm render thực tế. Danh sách cập nhật mỗi 2,5 giây; video vừa hoàn tất được giữ trên màn hình 60 giây khi đang theo dõi. Các video hoàn tất từ trước không chiếm danh sách, và các dòng đang chạy không bị giới hạn 8 mục như bản cũ. Có thể cuộn danh sách và bấm tiêu đề/thumbnail để xem record. Khi mất kết nối, phần tổng hợp thông báo chưa cập nhật thay vì giả định trạng thái vẫn mới.

Trong bảng thư viện, tiêu đề chỉ hiện tối đa hai dòng với dấu “…”, rê chuột để đọc đầy đủ. Cột **Video gốc** và **Thành phẩm** có thumbnail lấy từ đúng file video trên máy; bấm ảnh để mở trình phát. Không còn cột Xem trước hoặc nút Chi tiết; bấm vào nội dung dòng (hoặc Enter khi dòng được chọn) để mở record. Các ô chọn, dropdown, nút và liên kết vẫn thao tác riêng. Thumbnail được tạo và lưu đệm trong `data/social/thumbnails`, tự tạo lại khi file nguồn thay đổi.

Khi khởi động bản mới, các bản nháp cũ còn khớp caption gốc được áp dụng trực tiếp; bản cũ đã lệch caption hiện tại được bỏ qua. Trước khi chuyển đổi, hệ thống sao lưu thư viện vào `data/social/videos-before-direct-captions.json`. Bản gốc `title` và caption đã chốt trong các lịch đăng hiện có được giữ nguyên.

Trong **Tùy chỉnh → Hashtag mặc định**, nhập bộ hashtag của bạn rồi bấm **Lưu hashtag**. Có thể nhập có/không có dấu `#`, tách bằng khoảng trắng, dấu phẩy hoặc xuống dòng; hệ thống chuẩn hóa và bỏ trùng. Để trống thì caption mới không có hashtag. Thay đổi chưa lưu được lưu khi bấm viết lại; toàn bộ batch trong một lượt dùng cùng bộ hashtag đó. Cài đặt được nhớ trong SQLite trên máy. Hashtag do AI sinh ra được loại bỏ trước khi ghép đúng hashtag bạn đã nhập. Cài đặt chỉ áp dụng cho lần viết lại tiếp theo, không tự sửa caption đã có hoặc lịch đã tạo. Nếu tự gõ hashtag khi chỉnh caption ở màn chi tiết, thao tác lưu vẫn giữ nguyên.

Thanh caption gọn có hai chế độ trên các video đang chọn: **Chỉ chưa viết lại** (mặc định, bỏ qua caption đã viết lại) hoặc **Viết lại tất cả đã chọn**. Số “sẽ viết” cho biết số video thực sự được xử lý. Bấm **Viết lại caption** để chạy. Backend kiểm tra lại trạng thái trước khi nhận diện/gọi AI, nên video vừa được xử lý ở nơi khác cũng được bỏ qua trong chế độ chưa viết lại. Yêu cầu thêm và hướng dẫn nằm trong **Tùy chỉnh**.

Giao diện chia lần lượt thành các batch tối đa 100 video; mỗi batch gửi chung **một request AI** tới `https://api.xah.io/v1/chat/completions`, dùng model đã cấu hình (mặc định `gemini-3.8-flash`). Kết quả ghép bằng ID video, không dựa vào thứ tự. ID thiếu/trùng hoặc caption lỗi được báo riêng. Không tự thử lại hoặc chuyển sang gọi AI từng video. Kết quả batch trước vẫn giữ nếu batch sau gặp lỗi. Việc sử dụng API có thể tính phí theo tài khoản của bạn.

Vào **Tùy chỉnh → Cấu hình AI**, nhập **Model** và **API key**, rồi bấm **Lưu cấu hình AI**. Model phải được XAH hỗ trợ. Để trống ô API key để giữ khóa hiện tại; ô mật khẩu tự xóa sau khi lưu và khóa đã lưu không được trả lại qua API. Cấu hình được lưu cục bộ trong SQLite thuộc `data/social/` (đã được Git bỏ qua). Khóa nhập trong giao diện được ưu tiên; nếu chưa lưu khóa thì vẫn dùng biến môi trường `XAH_API_KEY` hoặc `.env` ở thư mục gốc (xem `.env.example`). Thay đổi chưa lưu cũng được lưu khi bấm viết lại; backend đọc model/key một lần cho mỗi batch. Việc lưu chỉ xác nhận cấu hình, không gọi nhà cung cấp để kiểm tra khóa/model.

Caption mới lưu trong trường `caption`, tiêu đề gốc vẫn được giữ. Các lịch đã tạo giữ nguyên bản caption đã chốt; lịch mới và bộ lấy bài tự động dùng caption mới.

Mặc định tab AI bật **Dùng lời thoại video**: gửi văn bản lời thoại, caption hiện tại và yêu cầu của bạn cho XAH. Video chưa lưu thoại sẽ nhận diện âm thanh qua Google Speech Recognition khi bấm viết lại; thoại thật được lưu trong thư viện để lần sau dùng lại. Video dựng mới cũng lưu thoại từ bước nhận diện. Không gửi câu mẫu của engine dựng phim như thể đó là lời thoại thật. Nếu nhận diện lỗi, AI không được gọi cho video đó.

Mỗi video gửi tối đa **300 ký tự đầu của lời thoại**, bản thoại đầy đủ vẫn được lưu. Màn chi tiết cho xem đoạn thoại đã gửi. Đây là giới hạn đầu vào do ứng dụng chọn, không phải giới hạn ngữ cảnh của nhà cung cấp. Có thể tắt lời thoại để chỉ viết lại caption. XAH không nhận file âm thanh/video; Google nhận âm thanh khi cần nhận diện. Việc nhận diện có thể lâu hơn viết lại caption đơn thuần. Giữ trang mở đến khi các batch hoàn thành; caption của những batch đã thành công được giữ khi tải lại trang, các batch chưa chạy không tự khởi động lại.

Sau khi cập nhật từ giao diện một trang, đóng Studio cũ và chạy lại `run.bat` để nạp các route mới. Cấu trúc template, module JavaScript và backend được mô tả trong [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md).

---

## 🌟 Tính Năng Nổi Bật

1. **Quản Lý Nội Dung Trực Quan (GUI Dashboard):**
   - Bảng quản lý thông minh với số thứ tự (STT), hình thu nhỏ (Thumbnail), tiêu đề, thời lượng và trạng thái xử lý theo thời gian thực (Mới tải về 🟡, Đang dựng 🔵, Đã hoàn thành 🟢, Lỗi 🔴).
   - Xem video TikTok gốc ngay trên trình duyệt (không watermark).
   - Xem và tải video hoạt hình thành phẩm chuẩn 9:16 trực tiếp.

2. **Tải Video & Kênh TikTok Tự Động:**
   - Hỗ trợ tải video riêng lẻ từ link TikTok.
   - Hỗ trợ tải hàng loạt video từ một kênh (ví dụ: `@60daykyluat`) với tùy chọn số lượng (1, 3, 5, 10, 20 video).

3. **Chuyển Thể Hoạt Hình 2D Cozy Storytelling (Remotion Engine):**
   - **Giữ nguyên 100% âm thanh gốc** (giọng đọc, nhạc nền cảm xúc).
   - **Trích xuất giọng nói & Tách câu theo nhịp**: Tự động nhận diện tiếng Việt và căn chỉnh thời gian xuất hiện từng từ khóa.
   - **Nhận diện cảm xúc (Mood Detection)**: Tự động phân tích nội dung để chọn hành động cho nhân vật người que (suy ngẫm `reflecting`, kiên định `loyal`, xúc động `sad`, bình an `peace`, bài học `regret`, tự hào `proud`).
   - **Kinetic Typography 2 Tầng**: Dòng chữ nói ngữ cảnh + Huy hiệu pill phóng to giật nảy (Spring physics) không lo bị đè chữ.
   - **Cozy Sticky Notes**: Tờ giấy note dán băng keo Washi đung đưa hiển thị thông điệp cốt lõi của từng phân cảnh.
   - **Hiệu ứng môi trường Cozy**: Đèn đom đóm lung linh treo trần nhà, ly cà phê bốc khói nghi ngút, đốm sáng lấp lánh nhẹ nhàng.

4. **Dựng video cục bộ:**
   - Phần dựng chạy trên máy; viết caption qua XAH cần API key và có thể tính phí.
   - Kết xuất trực tiếp qua Remotion Engine & GPU/CPU máy tính cá nhân.

---

## 🚀 Hướng Dẫn Khởi Động

### Cách 1: Chạy Bằng File Batch (Khuyên dùng)
Nhấp đúp chuột vào file:
```
TikTok_Animator_Studio\run.bat
```
Trình duyệt sẽ tự động mở trang web quản trị tại: `http://localhost:5000`

### Cách 2: Chạy Bằng Terminal / PowerShell
```powershell
cd c:\Users\nguye\Desktop\Video\TikTok_Animator_Studio
python app.py
```
Sau đó truy cập: `http://localhost:5000`

---

## 📁 Cấu Trúc Dự Án

Xem [cấu trúc thư mục hiện tại](docs/PROJECT_STRUCTURE.md).

## Trình duyệt TikTok

Mỗi nền tảng dùng một hồ sơ trình duyệt riêng trong `data/social/profiles/`. TikTok đăng nhập và đăng tự động bằng Google Chrome chính thức; các nền tảng khác dùng Chromium của Playwright. Cách thường dùng: vào **Tài khoản**, bấm **Kết nối**, đăng nhập thủ công trong cửa sổ vừa mở, kiểm tra đúng tài khoản rồi bấm **Lưu phiên**. Cần giữ Chrome tương thích Playwright. Nếu TikTok vẫn yêu cầu xác minh hoặc từ chối phiên, hoàn tất theo hướng dẫn của TikTok; đổi trình duyệt không bảo đảm hết hạn chế đăng nhập.

Nếu cửa sổ Studio gặp lỗi, vào **Tài khoản → nền tảng → Mở trình duyệt để đăng nhập**. Nút mở Chrome cho TikTok hoặc Chromium cho nền tảng khác bằng đúng hồ sơ riêng của nền tảng đó. Đăng nhập thủ công rồi đóng trình duyệt hoàn toàn; quay lại Studio bấm **Kết nối** (hoặc **Kết nối lại**), kiểm tra tài khoản trong cửa sổ mới mở và bấm **Lưu phiên**. Hồ sơ đăng nhập nằm riêng trên từng máy; máy mới cần đăng nhập lại. Không copy hồ sơ này sang máy khác hoặc đưa cookie lên Git.

Bộ đăng xử lý hai hộp giới thiệu TikTok đã nhận diện và đối chiếu caption trước khi bấm đăng để tránh tên file tự chèn vào mô tả. Nếu TikTok chuyển thẳng sang danh sách bài nhưng app chưa lấy được link, tác vụ chuyển **Cần kiểm tra**. Mở TikTok Studio xác minh bài và bổ sung link; không thử lại khi chưa biết bài đã được đăng hay chưa. Lượt thử riêng nền tảng có thể dùng `Store.create_batch(..., platforms=['tiktok'])`; giao diện lịch và lịch tự động mặc định vẫn chọn cả năm nền tảng.

## Ảnh bìa khi đăng bài

Trong **Thư viện**, bấm vào video → **Ảnh bìa đăng bài**. Chọn mốc khung hình hoặc tải JPEG/PNG/WebP (tối đa 5 MiB, 20 triệu điểm ảnh), sửa tiêu đề và lưu. Có thể căn vùng cắt ảnh trong tùy chỉnh; hệ thống tạo cả bản dọc 1080×1920 và ngang 1280×720. Để trống tiêu đề nếu muốn giữ ảnh không có chữ. Tạo bìa chạy tại máy, không gọi AI.

Video dựng mới được thử tạo bìa mặc định; video cũ chưa có bìa được thử tạo khi lên lịch. Mỗi lịch lưu bản sao video, caption và ảnh bìa riêng: thay ảnh trong thư viện không đổi lịch đã tạo. Xóa video trong thư viện xóa các ảnh bìa của record nhưng giữ bản sao thuộc lịch đăng.

Ảnh bìa tự tạo trước khi báo dựng hoàn thành và hiện ở cột **Ảnh bìa** trong thư viện. Nếu tạo ảnh thất bại, video vẫn được giữ và nhật ký báo rõ. YouTube Shorts dùng bản dọc; bản ngang chỉ hiện trong chi tiết video ngang. Khi đổi tỷ lệ rồi dựng lại, lịch mới chọn bản bìa theo tỷ lệ video hiện tại; giữ nguyên ảnh và chữ đã chỉnh.

**Kết quả đăng** và chi tiết video có trạng thái bìa riêng: đã xác minh ảnh mới trong xem trước, đã chọn khung video, dùng ảnh tự động hoặc cần kiểm tra. Playwright chỉ dùng chức năng bìa mà giao diện tài khoản thực tế cung cấp; không bảo đảm mọi tài khoản/nền tảng cho tải ảnh riêng. Threads hiện dùng xem trước tự động. Trạng thái bìa là xác minh trước khi đăng, chưa xác nhận ảnh cuối cùng trên bài đã xuất bản. Không chèn ảnh bìa vào đầu video.
